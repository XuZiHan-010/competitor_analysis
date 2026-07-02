import asyncio
from uuid import uuid4

import pytest

from agents.analyst import AnalystAgent
from agents.qa import QAAgent
from agents.writer import WriterAgent
from graph.state import (
    QAIssue,
    QAResult,
    RawCollectionResult,
    StructuredCompetitorProfile,
    WorkflowState,
)
from graph.workflow import _qa_node
from schemas.scope import CompetitorCandidate, ScopeDimension, TaskScopeContract
from schemas.source import SourceCitation
from services.metrics import calculate_report_metrics
from services.search.authority import grade_source_authority
from services.search.relevance import filter_relevant_sources


class _FailingLLM:
    enabled = True

    async def complete_json(self, **kwargs: object) -> dict:
        raise RuntimeError("llm unavailable")


def _source(
    source_id: str,
    title: str,
    snippet: str,
    *,
    provider: str = "tavily",
) -> SourceCitation:
    return SourceCitation(
        id=source_id,
        type="media",
        category="media",
        title=title,
        snippet=snippet,
        provider=provider,
    )


def _scope() -> TaskScopeContract:
    return TaskScopeContract(
        user_brief="Compare products",
        intent_mode="list",
        competitors=[CompetitorCandidate(name="Douyin", source="nl_extracted")],
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


def _state(profile: StructuredCompetitorProfile, sources: list[SourceCitation]) -> WorkflowState:
    scope = _scope()
    return WorkflowState(
        task_id=scope.id,
        run_id=uuid4(),
        scope_contract=scope,
        raw_collections={
            profile.competitor_name: RawCollectionResult(
                competitor_name=profile.competitor_name,
                sources=sources,
                completeness_score=1.0,
            )
        },
        structured_profiles={profile.competitor_name: profile},
    )


def test_relevance_drops_academic_sample_sources_with_rule_fallback() -> None:
    academic = _source(
        "paper",
        "ACSI satisfaction model for short-video platforms",
        "A journal paper uses Douyin as a research sample in a satisfaction model.",
    )
    product = _source(
        "official",
        "Douyin official product features",
        "Official product page describing creation tools and app features.",
    )

    result = asyncio.run(
        filter_relevant_sources("Douyin", [academic, product], _FailingLLM())  # type: ignore[arg-type]
    )

    assert result.kept == [product]
    assert result.dropped == [academic]


def test_relevance_drops_academic_sources_for_hard_fact_dimensions() -> None:
    academic = _source(
        "paper",
        "Douyin ACSI satisfaction model",
        "A journal paper uses Douyin as a research sample in a satisfaction model.",
    ).model_copy(update={"dimension_id": "core.pricing"})

    result = asyncio.run(
        filter_relevant_sources("Douyin", [academic], _FailingLLM())  # type: ignore[arg-type]
    )

    assert result.kept == []
    assert result.dropped == [academic]


def test_relevance_keeps_product_pricing_model_for_hard_fact_dimensions() -> None:
    pricing = _source(
        "pricing",
        "Douyin pricing model and creator monetization",
        "Official product pricing model page for subscriptions, ads, and commercial plans.",
    ).model_copy(update={"dimension_id": "core.pricing", "category": "commercial"})

    result = asyncio.run(
        filter_relevant_sources("Douyin", [pricing], _FailingLLM())  # type: ignore[arg-type]
    )

    assert result.kept == [pricing]
    assert result.dropped == []


def test_relevance_keeps_all_when_llm_and_rules_cannot_decide() -> None:
    source = _source("ambiguous", "Douyin ecosystem", "A brief mention with no academic markers.")

    result = asyncio.run(
        filter_relevant_sources("Douyin", [source], _FailingLLM())  # type: ignore[arg-type]
    )

    assert result.kept == [source]
    assert result.dropped == []


def test_qa_blocks_missing_core_schema_fields() -> None:
    source = _source("src1", "Source", "Evidence")
    profile = StructuredCompetitorProfile(
        competitor_name="Douyin",
        feature_tree={
            "rows": [
                {
                    "feature": "Pricing",
                    "cells": [{"competitor": "Douyin", "status": "unknown"}],
                }
            ]
        },
        pricing={},
        user_personas=[],
        swot={"strengths": ["Large audience"]},
        source_ids=[source.id],
    )

    result = QAAgent()._deterministic_checks(_state(profile, [source] * 5))
    fields = {issue.failed_field for issue in result.issues if issue.severity == "blocker"}

    assert {"feature_tree", "pricing", "user_personas", "swot"}.issubset(fields)
    assert not result.passed
    issue_by_field = {issue.failed_field: issue for issue in result.issues}
    assert issue_by_field["pricing"].code == "pricing_missing"
    assert issue_by_field["swot"].code == "swot_incomplete"
    assert "缺少" in issue_by_field["pricing"].message


def _healthy_pricing_profile(pricing_source_id: str) -> StructuredCompetitorProfile:
    return StructuredCompetitorProfile(
        competitor_name="Douyin",
        feature_tree={
            "rows": [
                {
                    "feature": "Editing",
                    "cells": [{"competitor": "Douyin", "status": "supported"}],
                    "source_ids": ["src_official"],
                }
            ]
        },
        pricing={
            "tiers": [
                {
                    "competitor": "Douyin",
                    "tier": "Pro",
                    "price": "$10/mo",
                    "highlights": ["Unlimited"],
                    "source_ids": [pricing_source_id],
                }
            ]
        },
        user_personas=[
            {"competitor": "Douyin", "label": "Creator", "source_ids": ["src_official"]}
        ],
        swot={
            "strengths": [{"text": "Reach", "source_ids": ["src_official"]}],
            "weaknesses": [{"text": "Cost", "source_ids": ["src_official"]}],
        },
        source_ids=["src_official"],
    )


def _pricing_sources(pricing_source: SourceCitation) -> list[SourceCitation]:
    official = SourceCitation(
        id="src_official",
        type="official",
        category="official",
        title="Douyin official",
        snippet="Official overview.",
        provider="tavily",
    )
    return [official, pricing_source, *([official] * 3)]


def test_qa_blocks_pricing_backed_only_by_user_reviews() -> None:
    review = SourceCitation(
        id="src_review",
        type="app_review",
        category="user_feedback",
        title="App store reviews",
        snippet="Users mention paying around $10.",
        provider="app_review_fetch",
    )
    profile = _healthy_pricing_profile("src_review")

    result = QAAgent()._deterministic_checks(_state(profile, _pricing_sources(review)))

    pricing_blockers = [
        issue
        for issue in result.issues
        if issue.severity == "blocker" and issue.failed_field == "pricing.source_ids"
    ]
    assert len(pricing_blockers) == 1
    assert pricing_blockers[0].code == "pricing_source_weak"
    assert not result.passed


@pytest.mark.asyncio
async def test_qa_accepts_pricing_when_official_domain_media_source_regraded() -> None:
    # A provider stamps the official pricing page as type=media; once grading upgrades
    # its category to official, the pricing gate must stop flagging it as a weak source.
    raw = SourceCitation(
        id="src_pricing",
        type="media",
        category="media",
        url="https://www.douyin.com/pricing",
        title="Douyin pricing",
        snippet="Pro plan is $10/mo.",
        provider="tavily",
    )
    [graded] = await grade_source_authority("Douyin", [raw], llm=None)
    assert graded.category == "official"  # precondition: the re-stamp happened

    profile = _healthy_pricing_profile("src_pricing")
    result = QAAgent()._deterministic_checks(_state(profile, _pricing_sources(graded)))

    assert not [i for i in result.issues if i.code == "pricing_source_weak"]


def test_qa_accepts_pricing_backed_by_commercial_source() -> None:
    commercial = SourceCitation(
        id="src_commercial",
        type="commercial",
        category="commercial",
        title="Pricing page",
        snippet="Pro plan is $10/mo.",
        provider="fetch_pages",
    )
    profile = _healthy_pricing_profile("src_commercial")

    result = QAAgent()._deterministic_checks(_state(profile, _pricing_sources(commercial)))

    assert not [issue for issue in result.issues if issue.failed_field == "pricing.source_ids"]


def test_qa_warns_when_core_section_rows_lack_citations() -> None:
    profile = _healthy_pricing_profile("src_official")
    profile.feature_tree["rows"][0]["source_ids"] = []

    result = QAAgent()._deterministic_checks(_state(profile, _pricing_sources(
        SourceCitation(
            id="src_official",
            type="official",
            category="official",
            title="Official",
            snippet="x",
            provider="tavily",
        )
    )))

    warnings = [issue for issue in result.issues if issue.failed_field == "core.source_ids"]
    assert len(warnings) == 1
    assert warnings[0].severity == "warning"
    assert "feature_tree" in warnings[0].message
    # A citation gap is a warning, not a blocker — the run still passes.
    assert result.passed


def test_retry_exhaustion_writes_field_verification_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scope = _scope()
    issue = QAIssue(
        severity="blocker",
        target_agent="CollectorAgent",
        target_competitor="Douyin",
        failed_field="pricing",
        message="Pricing tiers are missing.",
    )

    class _FakeQAAgent:
        async def run(
            self,
            state: WorkflowState,
            *,
            trace_context: object | None = None,
        ) -> QAResult:
            return QAResult(passed=False, issues=[issue])

    state = WorkflowState(
        task_id=scope.id,
        run_id=uuid4(),
        scope_contract=scope,
        retry_counts={"collector": 2},
    )

    import graph.workflow as workflow

    monkeypatch.setattr(workflow, "QAAgent", _FakeQAAgent)
    update = asyncio.run(_qa_node(state, {}))

    status = update["field_verification_status"]["Douyin.pricing"]
    assert status["status"] == "unverified"
    assert status["reason"] == "Pricing tiers are missing."


def test_metrics_and_writer_treat_unverified_fields_as_uncovered() -> None:
    source = _source("src1", "Source", "Evidence")
    profile = StructuredCompetitorProfile(
        competitor_name="Douyin",
        feature_tree={
            "rows": [
                {
                    "feature": "Editing",
                    "cells": [{"competitor": "Douyin", "status": "unknown"}],
                }
            ]
        },
        pricing={},
        user_personas=[],
        swot={},
        source_ids=[source.id],
    )
    state = _state(profile, [source])
    state.field_verification_status["Douyin.feature_tree"] = {
        "competitor": "Douyin",
        "field_path": "feature_tree",
        "status": "unverified",
        "reason": "Feature tree has too many unknown cells.",
        "source_ids": [],
    }

    report = WriterAgent()._run_fallback(state, language="zh")

    cell = report.structured_content["feature_tree"]["rows"][0]["cells"][0]
    assert cell["status"] == "unknown"
    assert "Feature tree has too many unknown cells." in cell["note"]
    assert report.metrics.field_coverage_rate < 1.0
    assert report.qa_status == "issues"
    assert report.metrics.ai_self_assessment["needs_human_review"] is True
    assert any(
        gap["field_path"] == "pricing"
        for gap in report.structured_content["field_gaps"]
    )


def test_metrics_reports_full_coverage_for_filled_core_fields() -> None:
    metrics = calculate_report_metrics(
        claims=[],
        sources=[],
        structured_content={
            "feature_tree": {
                "rows": [{"cells": [{"competitor": "A", "status": "supported"}]}]
            },
            "pricing": {"tiers": [{"plan_name": "Pro", "price": "$10"}]},
            "user_personas": {"personas": [{"label": "PM", "traits": "Ships products"}]},
            "swot": {
                "blocks": [
                    {
                        "strengths": ["Brand"],
                        "weaknesses": ["Cost"],
                        "opportunities": ["Growth"],
                        "threats": ["Rivals"],
                    }
                ]
            },
        },
    )

    assert metrics.field_coverage_rate == 1.0


def test_analyst_cross_analysis_normalizes_feature_status_values() -> None:
    profiles = {
        "Douyin": StructuredCompetitorProfile(
            competitor_name="Douyin",
            feature_tree={
                "rows": [
                    {
                        "feature": "Editing",
                        "cells": [{"competitor": "Douyin", "status": "unverified"}],
                        "source_ids": ["src1"],
                    },
                    {
                        "feature": "Search",
                        "cells": [{"competitor": "Douyin", "status": "yes"}],
                        "source_ids": ["src1"],
                    },
                    {
                        "feature": "Commerce",
                        "cells": [{"competitor": "Douyin", "status": "不支持"}],
                        "source_ids": ["src1"],
                    },
                ]
            },
            pricing={},
            user_personas=[],
            swot={},
            source_ids=["src1"],
        )
    }

    cross = AnalystAgent()._build_cross_analysis(profiles)
    statuses = [
        row["cells"][0]["status"]
        for row in cross.feature_matrix["rows"]
    ]

    assert statuses == ["unknown", "supported", "unsupported"]
