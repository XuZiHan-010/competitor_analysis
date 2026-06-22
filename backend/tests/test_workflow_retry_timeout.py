import asyncio
from uuid import UUID, uuid4

import pytest

from agents.analyst import AnalystAgent
from agents.collector import CollectorAgent
from graph.retry_scope import retry_target_competitors
from graph.state import (
    ExtensionFinding,
    RawCollectionResult,
    StructuredCompetitorProfile,
    WorkflowState,
)
from schemas.report import Report, ReportClaim, ReportMetrics, ReportSearchBackendResult
from schemas.scope import CompetitorCandidate, ScopeDimension, TaskScopeContract
from schemas.source import SourceCitation
from schemas.traces import AgentTrace
from services.runs.manager import RunManager, RunRecord, _checkpointer_ctx
from services.storage import InMemoryStore
from services.streaming.bridge import InMemoryStreamBridge
from settings import Settings


def _scope() -> TaskScopeContract:
    return TaskScopeContract(
        user_brief="Compare collaboration tools",
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
            ),
            ScopeDimension(
                id="ext.ecosystem",
                title="Ecosystem",
                intent="Compare ecosystems",
                layer="extension",
                order=5,
            ),
        ],
    )


def _source(source_id: str, *, dimension_id: str | None = None) -> SourceCitation:
    return SourceCitation(
        id=source_id,
        type="media",
        category="media",
        title="Source",
        snippet="Evidence",
        provider="tavily",
        dimension_id=dimension_id,
    )


def _profile(name: str, source_id: str) -> StructuredCompetitorProfile:
    return StructuredCompetitorProfile(
        competitor_name=name,
        feature_tree={
            "rows": [
                {
                    "feature": f"{name} feature",
                    "cells": [{"competitor": name, "status": "supported", "note": "old"}],
                    "source_ids": [source_id],
                }
            ]
        },
        pricing={"tiers": []},
        user_personas=[],
        swot={},
        source_ids=[source_id],
    )


def _retry_state(*, target_competitor: str | None = "B") -> WorkflowState:
    issue = {
        "target_agent": "CollectorAgent",
        "failed_field": "pricing",
        "message": "missing pricing",
        "retryable": True,
    }
    if target_competitor is not None:
        issue["target_competitor"] = target_competitor
    return WorkflowState(
        task_id=uuid4(),
        run_id=uuid4(),
        scope_contract=_scope(),
        raw_collections={
            "A": RawCollectionResult(
                competitor_name="A",
                sources=[_source("src_a_old", dimension_id="core.feature_tree")],
            )
        },
        structured_profiles={"A": _profile("A", "src_a_old")},
        extension_findings=[
            ExtensionFinding(
                dimension_id="ext.ecosystem",
                competitor_name="A",
                summary="old A extension",
                source_ids=["src_a_old"],
            )
        ],
        feedback_signals={"correction_detected": {"issues": [issue]}},
    )


def test_retry_target_competitors_requires_precise_targets() -> None:
    assert retry_target_competitors(_retry_state(target_competitor="B")) == {"B"}
    assert retry_target_competitors(_retry_state(target_competitor=None)) is None
    assert retry_target_competitors(_retry_state(target_competitor="Unknown")) is None


def test_collector_fallback_retry_reuses_untargeted_competitors() -> None:
    state = _retry_state(target_competitor="B")

    raw = asyncio.run(CollectorAgent()._run_fallback_collection(state))

    assert set(raw) == {"A", "B"}
    assert raw["A"].sources[0].provider == "tavily"
    assert any(source.provider == "feedback_recovery" for source in raw["B"].sources)


def test_analyst_fallback_retry_reuses_untargeted_profiles() -> None:
    state = _retry_state(target_competitor="B").model_copy(
        update={
            "raw_collections": {
                "A": RawCollectionResult(competitor_name="A", sources=[_source("src_a_old")]),
                "B": RawCollectionResult(competitor_name="B", sources=[_source("src_b_new")]),
            }
        }
    )

    profiles, findings, cross = AnalystAgent()._run_fallback(state)

    assert profiles["A"].feature_tree["rows"][0]["feature"] == "A feature"
    assert profiles["B"].feature_tree["rows"][0]["feature"] == "核心功能"
    assert any(finding.competitor_name == "A" for finding in findings)
    assert any(finding.competitor_name == "B" for finding in findings)
    assert cross is not None
    assert {point["id"] for point in cross.positioning_map["competitors"]} == {"A", "B"}


def test_run_manager_timeout_error_summary_is_readable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_run_workflow(*_: object, **__: object) -> WorkflowState:
        raise TimeoutError()

    monkeypatch.setattr("services.runs.manager.run_workflow", fake_run_workflow)

    store = InMemoryStore()
    bridge = InMemoryStreamBridge()
    manager = RunManager(store, bridge)
    record = RunRecord(task_id=uuid4(), user_id=uuid4())
    manager._runs[record.id] = record
    store.add_trace(
        AgentTrace(
            task_run_id=record.id,
            sequence_no=1,
            agent_name="QAAgent",
            node_name="check_qa",
            status="succeeded",
            prompt="qa",
            input_payload={},
            output_payload={},
        )
    )

    asyncio.run(
        manager._execute(
            record.id,
            WorkflowState(
                task_id=record.task_id,
                run_id=record.id,
                scope_contract=_scope(),
            ),
        )
    )

    assert record.status == "failed"
    assert record.error_summary is not None
    assert record.error_summary["exception_class"] == "TimeoutError"
    assert record.error_summary["stage_hint"] == "write"
    assert "运行超过" in record.error_summary["message"]


def _report(task_id: UUID) -> Report:
    return Report(
        task_id=task_id,
        structured_content={
            "title": "A / B report",
            "summary": "Summary",
            "competitors": ["A", "B"],
        },
        markdown_content="Report body",
        sources=[
            SourceCitation(
                id="src_a",
                type="official",
                category="official",
                title="A source",
                snippet="Evidence",
                provider="test",
                valid=True,
            )
        ],
        claims=[
            ReportClaim(
                claim_path="summary",
                claim_text="Report body",
                layer="core",
                field_type="free_text",
                source_ids=["src_a"],
                generating_agent="WriterAgent",
            )
        ],
        metrics=ReportMetrics(
            field_coverage_rate=1.0,
            citation_coverage_rate=1.0,
            manual_correction_rate=0.0,
        ),
    )


class RecordingPersistence:
    def __init__(self) -> None:
        self.saved_reports: list[tuple[Report, UUID]] = []
        self.updated_runs: list[RunRecord] = []
        self.traces: list[AgentTrace] = []

    async def upsert_user(self, email: str) -> UUID:
        return uuid4()

    async def ensure_task(
        self,
        scope_contract: TaskScopeContract,
        *,
        user_id: UUID,
        user_email: str,
    ) -> None:
        return None

    async def create_run(self, record: RunRecord) -> None:
        return None

    async def update_run(self, record: RunRecord) -> None:
        self.updated_runs.append(record.model_copy(deep=True))

    async def add_trace(self, trace: AgentTrace) -> None:
        self.traces.append(trace)

    async def save_report(self, report: Report, task_id: UUID) -> None:
        self.saved_reports.append((report, task_id))

    async def delete_task(self, task_id: UUID) -> None:
        return None

    async def get_run(self, run_id: UUID) -> RunRecord | None:
        return None

    async def get_task_owner(self, task_id: UUID) -> UUID | None:
        return None

    async def list_runs(
        self,
        limit: int = 50,
        *,
        user_id: UUID | None = None,
    ) -> list[RunRecord]:
        return []

    async def get_timeline(self, run_id: UUID) -> list[AgentTrace]:
        return []

    async def get_report(self, task_id: UUID, *, user_id: UUID | None = None) -> Report | None:
        return None

    async def search_reports(
        self,
        query: str,
        *,
        limit: int = 10,
        user_id: UUID | None = None,
    ) -> ReportSearchBackendResult:
        return ReportSearchBackendResult(mode="in_memory_semantic_fallback", reports=[])


async def _memory_checkpointer_type() -> str:
    async with _checkpointer_ctx() as checkpointer:
        return checkpointer.__class__.__name__


def test_default_workflow_checkpointer_uses_memory_even_with_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_if_postgres_opens(dsn: str) -> tuple[object, object] | None:
        raise AssertionError("postgres checkpointer should be opt-in")

    monkeypatch.setattr(
        "services.runs.manager.get_settings",
        lambda: Settings(database_url="postgresql://example/db"),
    )
    monkeypatch.setattr("services.runs.manager._open_postgres_saver", fail_if_postgres_opens)

    assert asyncio.run(_memory_checkpointer_type()) == "InMemorySaver"


def test_run_manager_saves_report_and_publishes_terminal_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_run_workflow(
        state: WorkflowState,
        *,
        trace_context: object,
        checkpointer: object,
    ) -> WorkflowState:
        return state.model_copy(update={"report": _report(state.task_id)})

    monkeypatch.setattr("services.runs.manager.run_workflow", fake_run_workflow)

    store = InMemoryStore()
    bridge = InMemoryStreamBridge()
    persistence = RecordingPersistence()
    manager = RunManager(store, bridge, persistence=persistence)
    record = RunRecord(task_id=uuid4(), user_id=uuid4())
    manager._runs[record.id] = record

    asyncio.run(
        manager._execute(
            record.id,
            WorkflowState(
                task_id=record.task_id,
                run_id=record.id,
                scope_contract=_scope(),
            ),
        )
    )

    assert record.status == "succeeded"
    assert record.completed_at is not None
    assert store.task_reports[record.task_id].task_id == record.task_id
    assert persistence.saved_reports[0][1] == record.task_id
    assert persistence.updated_runs[-1].status == "succeeded"
    terminal = bridge._events[str(record.id)][-1]
    assert terminal.event == "run.succeeded"
    assert terminal.data["task_id"] == str(record.task_id)
    assert terminal.data["report_id"] == str(store.task_reports[record.task_id].id)