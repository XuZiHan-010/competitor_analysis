"""Regression tests for the "empty report" failure mode.

When web search fails for some competitors (e.g. SerpApi 429 / quota), the run
still completes but those competitors carry no real sources. These tests pin the
fixes that make that visible and stop the pipeline from wasting retries or
leaking field-path placeholders into the report.
"""

import asyncio
from typing import Any

from agents.analyst import _cited_source_ids, _empty_profile
from agents.qa import _MIN_SOURCES_PER_COMPETITOR, QAAgent
from agents.writer import _collection_gaps, _field_level_core_claims
from graph.state import (
    QAIssue,
    QAResult,
    RawCollectionResult,
    StructuredCompetitorProfile,
    WorkflowState,
)
from graph.workflow import _route_after_qa
from schemas.report import Report
from schemas.scope import CompetitorCandidate, ScopeDimension, TaskScopeContract
from schemas.source import SourceCitation
from services.report_html import build_report_html


def _source(sid: str, *, provider: str = "tavily", snippet: str = "Evidence.") -> SourceCitation:
    return SourceCitation(
        id=sid,
        type="media",
        category="media",
        title="Doc",
        snippet=snippet,
        provider=provider,
    )


def _scope(*competitors: str) -> TaskScopeContract:
    return TaskScopeContract(
        user_brief="Compare tools",
        intent_mode="list",
        competitors=[CompetitorCandidate(name=c, source="nl_extracted") for c in competitors],
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


def test_has_real_sources_ignores_fallback_and_empty_stubs() -> None:
    real = RawCollectionResult(competitor_name="A", sources=[_source("s1")])
    fallback_only = RawCollectionResult(
        competitor_name="B",
        sources=[_source("s2", provider="fallback_public_review_search")],
    )
    empty = RawCollectionResult(competitor_name="C", sources=[], errors=["429"])
    assert real.has_real_sources()
    assert not fallback_only.has_real_sources()
    assert not empty.has_real_sources()


class _FakeQALLM:
    """Returns a fixed QA payload for every complete_json call."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    async def complete_json(self, **_: Any) -> dict[str, Any]:
        return self._payload


def test_llm_collector_blocker_defaults_non_retryable() -> None:
    """An LLM-emitted CollectorAgent blocker with no retryable flag defaults to
    non-retryable; an AnalystAgent blocker keeps the retryable default (True)."""
    name = "抖音"
    scope = _scope(name)
    state = WorkflowState(
        task_id=scope.id,
        run_id=scope.id,
        scope_contract=scope,
        # Recoverable (real source) so the unrecoverable override can't interfere —
        # this isolates the parse default itself.
        raw_collections={name: RawCollectionResult(competitor_name=name, sources=[_source("s1")])},
        structured_profiles={name: _empty_profile(name)},
    )
    llm = _FakeQALLM(
        {
            "issues": [
                {
                    "severity": "blocker",
                    "target_agent": "CollectorAgent",
                    "target_competitor": name,
                    "failed_field": "pricing.tiers",
                    "message": "LLM-COLLECTOR",
                },
                {
                    "severity": "blocker",
                    "target_agent": "AnalystAgent",
                    "target_competitor": name,
                    "failed_field": "swot",
                    "message": "LLM-ANALYST",
                },
            ]
        }
    )

    result = asyncio.run(QAAgent()._run_llm(state, llm))  # type: ignore[arg-type]

    by_msg = {issue.message: issue for issue in result.issues}
    assert by_msg["LLM-COLLECTOR"].retryable is False
    assert by_msg["LLM-ANALYST"].retryable is True


def test_llm_collector_blocker_downgraded_for_unrecoverable_competitor() -> None:
    """The P0-A bug: even when the LLM insists retryable=True, a dead-collection
    competitor's CollectorAgent blocker must be forced non-retryable."""
    name = "抖音"
    scope = _scope(name)
    state = WorkflowState(
        task_id=scope.id,
        run_id=scope.id,
        scope_contract=scope,
        raw_collections={
            name: RawCollectionResult(
                competitor_name=name, sources=[], errors=["x"], unrecoverable=True
            )
        },
        structured_profiles={name: _empty_profile(name)},
    )
    llm = _FakeQALLM(
        {
            "issues": [
                {
                    "severity": "blocker",
                    "target_agent": "CollectorAgent",
                    "target_competitor": name,
                    "failed_field": "sources",
                    "message": "LLM-RETRY",
                    "retryable": True,
                }
            ]
        }
    )

    result = asyncio.run(QAAgent()._run_llm(state, llm))  # type: ignore[arg-type]

    by_msg = {issue.message: issue for issue in result.issues}
    assert by_msg["LLM-RETRY"].retryable is False


def test_llm_global_collector_blocker_downgraded_when_all_unrecoverable() -> None:
    """A CollectorAgent blocker with no target_competitor (global) is downgraded
    only when every collected competitor is unrecoverable."""
    name = "抖音"
    scope = _scope(name)
    state = WorkflowState(
        task_id=scope.id,
        run_id=scope.id,
        scope_contract=scope,
        raw_collections={
            name: RawCollectionResult(
                competitor_name=name, sources=[], errors=["x"], unrecoverable=True
            )
        },
        structured_profiles={name: _empty_profile(name)},
    )
    llm = _FakeQALLM(
        {
            "issues": [
                {
                    "severity": "blocker",
                    "target_agent": "CollectorAgent",
                    "target_competitor": None,
                    "failed_field": "sources",
                    "message": "LLM-GLOBAL",
                    "retryable": True,
                }
            ]
        }
    )

    result = asyncio.run(QAAgent()._run_llm(state, llm))  # type: ignore[arg-type]

    by_msg = {issue.message: issue for issue in result.issues}
    assert by_msg["LLM-GLOBAL"].retryable is False


def test_llm_global_collector_blocker_stays_retryable_when_some_recoverable() -> None:
    scope = _scope("A", "B")
    state = WorkflowState(
        task_id=scope.id,
        run_id=scope.id,
        scope_contract=scope,
        raw_collections={
            "A": RawCollectionResult(
                competitor_name="A", sources=[], errors=["x"], unrecoverable=True
            ),
            "B": RawCollectionResult(competitor_name="B", sources=[_source("s1")]),
        },
        structured_profiles={"A": _empty_profile("A"), "B": _empty_profile("B")},
    )
    llm = _FakeQALLM(
        {
            "issues": [
                {
                    "severity": "blocker",
                    "target_agent": "CollectorAgent",
                    "target_competitor": None,
                    "failed_field": "sources",
                    "message": "LLM-GLOBAL2",
                    "retryable": True,
                }
            ]
        }
    )

    result = asyncio.run(QAAgent()._run_llm(state, llm))  # type: ignore[arg-type]

    by_msg = {issue.message: issue for issue in result.issues}
    assert by_msg["LLM-GLOBAL2"].retryable is True


def test_qa_marks_quota_blockers_non_retryable() -> None:
    scope = _scope("抖音")
    state = WorkflowState(
        task_id=scope.id,
        run_id=scope.id,
        scope_contract=scope,
        raw_collections={
            "抖音": RawCollectionResult(
                competitor_name="抖音",
                sources=[],
                errors=["search(抖音): serpapi 429 Too Many Requests"],
            )
        },
        structured_profiles={
            "抖音": StructuredCompetitorProfile(
                competitor_name="抖音",
                feature_tree={"rows": []},
                pricing={},
                user_personas=[],
                swot={},
                source_ids=[],
            )
        },
    )

    result = QAAgent()._run_fallback(state)

    assert not result.passed
    collector_blockers = [
        issue
        for issue in result.issues
        if issue.severity == "blocker" and issue.target_agent == "CollectorAgent"
    ]
    assert collector_blockers, "empty profile should raise collector blockers"
    assert all(not issue.retryable for issue in collector_blockers)


def test_qa_unrecoverable_flag_marks_non_retryable_without_keyword() -> None:
    """The structured flag drives the verdict — no error-string keyword needed."""
    scope = _scope("抖音")
    state = WorkflowState(
        task_id=scope.id,
        run_id=scope.id,
        scope_contract=scope,
        raw_collections={
            "抖音": RawCollectionResult(
                competitor_name="抖音",
                sources=[],
                # No quota/auth keyword in the text — only the structured flag.
                errors=["search(抖音): provider unavailable"],
                unrecoverable=True,
            )
        },
        structured_profiles={
            "抖音": StructuredCompetitorProfile(
                competitor_name="抖音",
                feature_tree={"rows": []},
                pricing={},
                user_personas=[],
                swot={},
                source_ids=[],
            )
        },
    )

    result = QAAgent()._run_fallback(state)

    collector_blockers = [
        issue
        for issue in result.issues
        if issue.severity == "blocker" and issue.target_agent == "CollectorAgent"
    ]
    assert collector_blockers
    assert all(not issue.retryable for issue in collector_blockers)


def test_qa_dropped_irrelevant_url_with_digits_stays_retryable() -> None:
    """A dropped-source URL containing '429'/'403' must not look like a quota wall."""
    scope = _scope("抖音")
    state = WorkflowState(
        task_id=scope.id,
        run_id=scope.id,
        scope_contract=scope,
        raw_collections={
            "抖音": RawCollectionResult(
                competitor_name="抖音",
                sources=[],
                errors=[
                    "dropped_irrelevant: https://example.com/article-429",
                    "dimension_gap(core.feature_tree): no relevant sources",
                ],
            )
        },
        structured_profiles={
            "抖音": StructuredCompetitorProfile(
                competitor_name="抖音",
                feature_tree={"rows": []},
                pricing={},
                user_personas=[],
                swot={},
                source_ids=[],
            )
        },
    )

    result = QAAgent()._run_fallback(state)

    collector_blockers = [
        issue
        for issue in result.issues
        if issue.severity == "blocker" and issue.target_agent == "CollectorAgent"
    ]
    assert collector_blockers
    assert all(issue.retryable for issue in collector_blockers)


def test_qa_tavily_432_usage_limit_marks_non_retryable() -> None:
    scope = _scope("抖音")
    state = WorkflowState(
        task_id=scope.id,
        run_id=scope.id,
        scope_contract=scope,
        raw_collections={
            "抖音": RawCollectionResult(
                competitor_name="抖音",
                sources=[],
                errors=["search(抖音): Tavily usage limit reached (432): credits"],
            )
        },
        structured_profiles={
            "抖音": StructuredCompetitorProfile(
                competitor_name="抖音",
                feature_tree={"rows": []},
                pricing={},
                user_personas=[],
                swot={},
                source_ids=[],
            )
        },
    )

    result = QAAgent()._run_fallback(state)

    collector_blockers = [
        issue
        for issue in result.issues
        if issue.severity == "blocker" and issue.target_agent == "CollectorAgent"
    ]
    assert collector_blockers
    assert all(not issue.retryable for issue in collector_blockers)


def test_qa_empty_profile_with_real_sources_blames_analyst_not_collector() -> None:
    """A competitor collected with real sources but an empty profile is an Analyst
    extraction failure, not a collection gap: its blockers must target AnalystAgent and
    be non-retryable, so the pipeline doesn't burn a re-collection round that returns
    the same good sources and fails identically."""
    name = "抖音"
    scope = _scope(name)
    sources = [_source(f"s{i}") for i in range(_MIN_SOURCES_PER_COMPETITOR)]
    state = WorkflowState(
        task_id=scope.id,
        run_id=scope.id,
        scope_contract=scope,
        raw_collections={name: RawCollectionResult(competitor_name=name, sources=sources)},
        structured_profiles={name: _empty_profile(name)},
    )

    result = QAAgent()._run_fallback(state)

    collector_blockers = [
        issue
        for issue in result.issues
        if issue.severity == "blocker" and issue.target_agent == "CollectorAgent"
    ]
    analyst_blockers = [
        issue
        for issue in result.issues
        if issue.severity == "blocker" and issue.target_agent == "AnalystAgent"
    ]
    assert not collector_blockers
    assert analyst_blockers
    assert all(not issue.retryable for issue in analyst_blockers)


def test_demo_pricing_blocker_stays_retryable_when_all_unrecoverable() -> None:
    """The scripted demo blocker must keep driving its feedback-loop retry even when
    every competitor's live collection is unrecoverable — the unrecoverable override
    must not mute it."""
    name = "抖音"
    scope = _scope(name)
    state = WorkflowState(
        task_id=scope.id,
        run_id=scope.id,
        scope_contract=scope,
        raw_collections={
            name: RawCollectionResult(
                competitor_name=name, sources=[], errors=["x"], unrecoverable=True
            )
        },
        feedback_signals={"force_pricing_blocker": True},
        retry_counts={},
    )

    result = QAAgent()._run_fallback(state)

    demo = next(issue for issue in result.issues if issue.code == "pricing_demo_blocker")
    assert demo.retryable is True


def test_route_after_qa_skips_retry_when_all_blockers_unrecoverable() -> None:
    scope = _scope("抖音")
    issue = QAIssue(
        severity="blocker",
        target_agent="CollectorAgent",
        target_competitor="抖音",
        failed_field="sources",
        message="quota",
        retryable=False,
    )
    state = WorkflowState(
        task_id=scope.id,
        run_id=scope.id,
        scope_contract=scope,
        qa_result=QAResult(passed=False, issues=[issue]),
        retry_counts={},
    )
    assert _route_after_qa(state) == "write"


def test_route_after_qa_retries_when_blocker_recoverable() -> None:
    scope = _scope("抖音")
    issue = QAIssue(
        severity="blocker",
        target_agent="CollectorAgent",
        target_competitor="抖音",
        failed_field="sources",
        message="too few sources",
        retryable=True,
    )
    state = WorkflowState(
        task_id=scope.id,
        run_id=scope.id,
        scope_contract=scope,
        qa_result=QAResult(passed=False, issues=[issue]),
        retry_counts={},
    )
    assert _route_after_qa(state) == "collect"


def test_writer_drops_empty_field_claims_no_placeholder_leak() -> None:
    scope = _scope("抖音")
    state = WorkflowState(task_id=scope.id, run_id=scope.id, scope_contract=scope)
    structured_content = {
        "extensions": [
            {"dimension_id": "ext.x", "bullets": [{"competitor": "抖音", "points": []}]}
        ],
        "feature_tree": {"rows": [{"feature": "实时协作", "source_ids": ["s1"]}]},
    }

    claims = _field_level_core_claims(state, structured_content)

    assert all(claim.claim_text != "extensions[0].bullets[0]" for claim in claims)
    assert not any(claim.claim_path.startswith("extensions[0]") for claim in claims)
    assert any(claim.claim_text == "实时协作" for claim in claims)


def test_collection_gaps_lists_empty_competitors_with_reason() -> None:
    scope = _scope("抖音", "快手")
    state = WorkflowState(
        task_id=scope.id,
        run_id=scope.id,
        scope_contract=scope,
        raw_collections={
            "抖音": RawCollectionResult(
                competitor_name="抖音", sources=[], errors=["serpapi 429"]
            ),
            "快手": RawCollectionResult(competitor_name="快手", sources=[_source("s1")]),
        },
    )

    gaps = _collection_gaps(state)

    assert [gap["competitor"] for gap in gaps] == ["抖音", "快手"]
    assert "429" in gaps[0]["reason"]
    assert "仅采集到 1 条来源" in gaps[1]["reason"]


def test_collection_gaps_explains_rate_limited_partial_sources() -> None:
    scope = _scope("Trae")
    state = WorkflowState(
        task_id=scope.id,
        run_id=scope.id,
        scope_contract=scope,
        raw_collections={
            "Trae": RawCollectionResult(
                competitor_name="Trae",
                sources=[_source("s1")],
                errors=["tavily 432", "serpapi 429"],
            )
        },
    )

    gaps = _collection_gaps(state)

    assert [gap["competitor"] for gap in gaps] == ["Trae"]
    assert "搜索服务限流/失败" in gaps[0]["reason"]
    assert "432" in gaps[0]["reason"]
    assert "429" in gaps[0]["reason"]
    assert "仅采集到 1 条来源" in gaps[0]["reason"]


def test_cited_source_ids_keeps_only_collected_and_cited() -> None:
    feature_tree = {"rows": [{"feature": "f", "source_ids": ["s1", "hallucinated"]}]}
    pricing = {"tiers": [{"tier": "Free", "source_ids": ["s2"]}]}
    personas: list[dict] = [{"label": "p", "source_ids": []}]
    swot = {"strengths": [{"text": "s", "source_ids": ["s1"]}]}

    ids = _cited_source_ids(feature_tree, pricing, personas, swot, {"s1", "s2", "s3"})

    assert ids == ["s1", "s2"]


def test_report_html_renders_data_gap_banner() -> None:
    scope = _scope("抖音")
    report = Report(
        task_id=scope.id,
        structured_content={
            "title": "T",
            "data_gaps": [{"competitor": "抖音", "reason": "serpapi 429"}],
        },
        markdown_content="",
        sources=[],
        claims=[],
        metrics={
            "field_coverage_rate": 0.0,
            "citation_coverage_rate": 0.0,
            "manual_correction_rate": 0.0,
        },
    )

    html = build_report_html(report)

    assert "data-gaps" in html
    assert "抖音" in html
    assert "数据采集失败" in html

