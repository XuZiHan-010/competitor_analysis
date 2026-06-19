"""Regression tests for the "empty report" failure mode.

When web search fails for some competitors (e.g. SerpApi 429 / quota), the run
still completes but those competitors carry no real sources. These tests pin the
fixes that make that visible and stop the pipeline from wasting retries or
leaking field-path placeholders into the report.
"""

from agents.analyst import _cited_source_ids
from agents.qa import QAAgent
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

    assert [gap["competitor"] for gap in gaps] == ["抖音"]
    assert "429" in gaps[0]["reason"]


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
