import asyncio
from typing import Any, cast
from uuid import uuid4

import pytest

from agents.collector import CollectorAgent
from agents.writer import WriterAgent
from graph.state import QAIssue, QAResult, RawCollectionResult, WorkflowState
from graph.workflow import _route_after_qa, run_workflow
from schemas.scope import CompetitorCandidate, ScopeDimension, TaskScopeContract
from schemas.source import SourceCitation
from settings import Settings


def _scope() -> TaskScopeContract:
    return TaskScopeContract(
        user_brief="Compare A and B",
        intent_mode="list",
        competitors=[
            CompetitorCandidate(name="A", source="nl_extracted"),
            CompetitorCandidate(name="B", source="nl_extracted"),
        ],
        dimensions=[
            ScopeDimension(
                id="core.feature_tree",
                title="Feature tree",
                intent="Compare features",
                layer="core",
                order=1,
            )
        ],
    )


def _state() -> WorkflowState:
    return WorkflowState(task_id=uuid4(), run_id=uuid4(), scope_contract=_scope())


@pytest.mark.asyncio
async def test_collector_runs_competitors_concurrently_and_isolates_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = CollectorAgent()
    started: set[str] = set()
    both_started = asyncio.Event()

    async def passthrough_rewrite(
        competitor_name: str,
        base_queries: list[tuple[str, str]],
        llm: object,
        domain_context: str,
    ) -> list[tuple[str, str]]:
        return base_queries

    async def collect(
        competitor_name: str,
        *_: object,
        dimension_queries: list[tuple[str, str]],
    ) -> RawCollectionResult:
        assert dimension_queries
        started.add(competitor_name)
        if len(started) == 2:
            both_started.set()
        await asyncio.wait_for(both_started.wait(), timeout=0.2)
        if competitor_name == "B":
            raise RuntimeError("isolated provider failure")
        return RawCollectionResult(
            competitor_name=competitor_name,
            sources=[
                SourceCitation(
                    id="src_a",
                    type="official",
                    category="official",
                    title="A",
                    snippet="Evidence",
                    provider="test",
                )
            ],
        )

    monkeypatch.setattr(agent, "_rewrite_queries", passthrough_rewrite)
    monkeypatch.setattr(agent, "_collect_real_competitor", collect)

    result = await agent._run_real_collection(
        _state(),
        cast(Any, object()),
        app_reviews=cast(Any, object()),
        fetcher=cast(Any, object()),
    )

    assert started == {"A", "B"}
    assert result["A"].has_real_sources()
    assert result["B"].sources == []
    assert "isolated provider failure" in result["B"].errors[0]


@pytest.mark.asyncio
async def test_collector_competitor_timeout_is_cancelled_and_isolated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = CollectorAgent()

    async def passthrough_rewrite(
        competitor_name: str,
        base_queries: list[tuple[str, str]],
        llm: object,
        domain_context: str,
    ) -> list[tuple[str, str]]:
        return base_queries

    async def never_finishes(*_: object, **__: object) -> RawCollectionResult:
        await asyncio.sleep(10)
        raise AssertionError("collector timeout did not cancel the task")

    monkeypatch.setattr(agent, "_rewrite_queries", passthrough_rewrite)
    monkeypatch.setattr(agent, "_collect_real_competitor", never_finishes)
    monkeypatch.setattr("agents.collector._COLLECTOR_TIMEOUT_S", 0.01)

    result = await agent._run_real_collection(
        _state(),
        cast(Any, object()),
        app_reviews=cast(Any, object()),
        fetcher=cast(Any, object()),
    )

    assert set(result) == {"A", "B"}
    assert all(collection.sources == [] for collection in result.values())
    assert all(
        "collection_timeout_or_error" in collection.errors[0]
        for collection in result.values()
    )


@pytest.mark.asyncio
async def test_writer_budget_timeout_is_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    async def never_finishes(
        self: WriterAgent,
        state: WorkflowState,
        llm: object,
        *,
        language: str,
    ) -> object:
        await asyncio.sleep(10)
        raise AssertionError("writer timeout did not cancel the task")

    monkeypatch.setattr(
        "agents.writer.get_settings",
        lambda: Settings(mock_llm=False, deepseek_api_key="placeholder"),
    )
    monkeypatch.setattr("agents.writer.WRITER_BUDGET_S", 0.01)
    monkeypatch.setattr(WriterAgent, "_run_llm", never_finishes)

    with pytest.raises(RuntimeError, match="WriterAgent timed out"):
        await WriterAgent().run(_state())


@pytest.mark.asyncio
async def test_global_workflow_deadline_cancels_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    class NeverEndingGraph:
        async def ainvoke(self, state: WorkflowState, config: object) -> WorkflowState:
            await asyncio.sleep(10)
            raise AssertionError("workflow deadline did not cancel the graph")

    monkeypatch.setattr(
        "graph.workflow.create_workflow_graph",
        lambda checkpointer=None: NeverEndingGraph(),
    )
    monkeypatch.setattr("graph.workflow.WORKFLOW_DEADLINE_S", 0.01)

    with pytest.raises(TimeoutError):
        await run_workflow(_state(), trace_context=object())


def test_retry_route_stops_after_single_collector_rerun() -> None:
    issue = QAIssue(
        severity="blocker",
        target_agent="CollectorAgent",
        target_competitor="A",
        failed_field="pricing",
        message="missing pricing",
        retryable=True,
    )
    first_failure = _state().model_copy(
        update={
            "qa_result": QAResult(passed=False, issues=[issue]),
            "retry_counts": {"collector": 1},
        }
    )
    repeated_failure = first_failure.model_copy(update={"retry_counts": {"collector": 2}})

    assert _route_after_qa(first_failure) == "collect"
    assert _route_after_qa(repeated_failure) == "write"
