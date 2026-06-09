import asyncio
from uuid import uuid4

import pytest

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
    assert cell["status"] == "unverified"
    assert report.metrics.field_coverage_rate < 1.0
    assert report.qa_status == "issues"
    assert report.metrics.ai_self_assessment["needs_human_review"] is True


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
