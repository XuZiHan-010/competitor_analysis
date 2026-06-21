import asyncio

import pytest

from agents.writer import WriterAgent
from graph.state import (
    ExtensionFinding,
    RawCollectionResult,
    StructuredCompetitorProfile,
    WorkflowState,
)
from schemas.scope import CompetitorCandidate, ScopeDimension, TaskScopeContract
from schemas.source import SourceCitation
from schemas.survey import (
    DistributionHandle,
    Questionnaire,
    SurveyEvidence,
    SurveyInsight,
    SurveyQuestion,
    SurveyResult,
    TargetPersona,
)
from services.agents.language import language_instruction
from services.report_integrity import assert_report_sources_resolvable


def test_language_instruction_zh_covers_extraction_and_translation() -> None:
    directive = language_instruction("zh")
    assert "简体中文" in directive
    # Analyst extraction fields must stay covered after the move out of analyst.py.
    for field in ("feature names", "pricing tiers", "SWOT", "source_ids"):
        assert field in directive
    # Brand/plan names and numbers stay verbatim; prose gets translated.
    assert "verbatim" in directive
    assert "translate" in directive.lower()


def test_writer_survey_claims_reference_report_sources() -> None:
    source = SourceCitation(
        id="src_tavily_deadbeef_001",
        type="app_review",
        category="user_feedback",
        url=None,
        title="Public review",
        snippet="Users like the collaboration workflow.",
        provider="tavily",
    )
    scope = TaskScopeContract(
        user_brief="Compare collaboration tools",
        intent_mode="list",
        competitors=[CompetitorCandidate(name="Notion", source="nl_extracted")],
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
    question = SurveyQuestion(
        id="sq_001",
        text="Why do users adopt it?",
        type="open",
        intent="Adoption driver",
    )
    persona = TargetPersona(
        label="Team lead",
        traits="Runs collaborative projects",
        est_size="majority",
        inferred_from=[source.id],
    )
    survey = SurveyResult(
        competitor="Notion",
        dimension_intent="User voice",
        questionnaire=Questionnaire(
            id="qn_001",
            competitor="Notion",
            dimension_intent="User voice",
            questions=[question],
            design_rationale="Test",
        ),
        target_personas=[persona],
        distribution=DistributionHandle(
            id="dist_001",
            distributor_impl="SimulatedDistributor",
            questionnaire_id="qn_001",
            target_personas=[persona],
            sample_size=1,
            status="completed",
        ),
        responses=[],
        evidence=[
            SurveyEvidence(
                id="se_001",
                question_id=question.id,
                source_type="public_review",
                source_id=source.id,
                raw_quote=source.snippet,
            )
        ],
        insights=[
            SurveyInsight(
                question_id=question.id,
                point="Users value collaboration workflows.",
                frequency=1,
                representative_quotes=[source.snippet],
                evidence_ids=["se_001"],
                confidence="high",
            )
        ],
        coverage_note="Test",
        source_breakdown={"public_review": 1},
    )
    state = WorkflowState(
        task_id=scope.id,
        run_id=scope.id,
        scope_contract=scope,
        raw_collections={
            "Notion": RawCollectionResult(
                competitor_name="Notion",
                sources=[source],
                completeness_score=1.0,
            )
        },
        structured_profiles={
            "Notion": StructuredCompetitorProfile(
                competitor_name="Notion",
                feature_tree={},
                pricing={},
                user_personas=[],
                swot={},
                source_ids=[source.id],
            )
        },
        survey_results={"Notion": survey},
    )

    report = WriterAgent()._run_fallback(state, language="zh")
    survey_claim = next(
        claim for claim in report.claims if claim.generating_agent == "SurveyTool"
    )

    assert survey_claim.source_ids == [source.id]
    assert set(survey_claim.source_ids).issubset({item.id for item in report.sources})


def test_writer_fallback_report_has_rendered_markdown_without_placeholder_issue() -> None:
    source = SourceCitation(
        id="src_tavily_deadbeef_001",
        type="media",
        category="media",
        title="Source",
        snippet="Evidence.",
        provider="tavily",
    )
    scope = TaskScopeContract(
        user_brief="Compare AI coding tools",
        intent_mode="list",
        competitors=[CompetitorCandidate(name="Trae", source="nl_extracted")],
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
    state = WorkflowState(
        task_id=scope.id,
        run_id=scope.id,
        scope_contract=scope,
        raw_collections={
            "Trae": RawCollectionResult(
                competitor_name="Trae",
                sources=[source],
                completeness_score=1.0,
            )
        },
        structured_profiles={
            "Trae": StructuredCompetitorProfile(
                competitor_name="Trae",
                feature_tree={},
                pricing={},
                user_personas=[],
                swot={},
                source_ids=[source.id],
            )
        },
    )

    report = WriterAgent()._run_fallback(state, language="zh")

    assert "S0 mock report" not in report.markdown_content
    assert "待确认" not in str(report.structured_content)
    assert "需验证" not in str(report.structured_content)
    assert "标准版" not in str(report.structured_content)
    assert not any(
        issue.get("failed_field") == "report.placeholder_content"
        for issue in report.qa_issues
    )


def test_writer_llm_consumes_markdown_and_section_intros() -> None:
    source = SourceCitation(
        id="src_tavily_deadbeef_001",
        type="media",
        category="media",
        title="Source",
        snippet="Evidence.",
        provider="tavily",
    )
    scope = TaskScopeContract(
        user_brief="Compare AI coding tools",
        intent_mode="list",
        competitors=[CompetitorCandidate(name="Trae", source="nl_extracted")],
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
    state = WorkflowState(
        task_id=scope.id,
        run_id=scope.id,
        scope_contract=scope,
        raw_collections={
            "Trae": RawCollectionResult(
                competitor_name="Trae",
                sources=[source],
                completeness_score=1.0,
            )
        },
        structured_profiles={
            "Trae": StructuredCompetitorProfile(
                competitor_name="Trae",
                feature_tree={},
                pricing={},
                user_personas=[],
                swot={},
                source_ids=[source.id],
            )
        },
    )

    class _LLM:
        async def complete_json(self, **kwargs: object) -> dict:
            return {
                "markdown": "# Custom Report\n\nNarrative comparison.",
                "summary": "Executive summary.",
                "section_intros": {
                    "feature_tree": "Trae differentiates through editor workflow depth.",
                    "pricing": "Pricing signals remain tied to public packaging evidence.",
                },
                "claims": [
                    {
                        "competitor_name": "Trae",
                        "claim_text": "Trae has public product evidence.",
                        "source_ids": [source.id],
                    }
                ],
            }

    report = asyncio.run(WriterAgent()._run_llm(state, _LLM(), language="zh"))  # type: ignore[arg-type]

    assert report.markdown_content == "# Custom Report\n\nNarrative comparison."
    assert (
        report.structured_content["feature_tree"]["intro"]
        == "Trae differentiates through editor workflow depth."
    )


def test_writer_llm_system_prompt_forces_chinese() -> None:
    """English sources must be translated: the Writer prompt carries the shared
    Chinese normalization directive, not just a weak 'requested language' hint."""
    source = SourceCitation(
        id="src_tavily_deadbeef_001",
        type="media",
        category="media",
        title="Source",
        snippet="Evidence.",
        provider="tavily",
    )
    scope = TaskScopeContract(
        user_brief="Compare AI coding tools",
        intent_mode="list",
        competitors=[CompetitorCandidate(name="Trae", source="nl_extracted")],
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
    state = WorkflowState(
        task_id=scope.id,
        run_id=scope.id,
        scope_contract=scope,
        raw_collections={
            "Trae": RawCollectionResult(
                competitor_name="Trae",
                sources=[source],
                completeness_score=1.0,
            )
        },
        structured_profiles={
            "Trae": StructuredCompetitorProfile(
                competitor_name="Trae",
                feature_tree={},
                pricing={},
                user_personas=[],
                swot={},
                source_ids=[source.id],
            )
        },
    )

    captured: dict[str, object] = {}

    class _CapturingLLM:
        async def complete_json(self, **kwargs: object) -> dict:
            captured["messages"] = kwargs["messages"]
            return {"markdown": "# 报告", "summary": "摘要", "section_intros": {}, "claims": []}

    asyncio.run(WriterAgent()._run_llm(state, _CapturingLLM(), language="zh"))  # type: ignore[arg-type]

    messages = captured["messages"]
    assert isinstance(messages, list)
    system_prompt = messages[0]["content"]
    assert "简体中文" in system_prompt
    assert "translate" in system_prompt.lower()


def test_writer_normalizes_feature_matrix_status_values() -> None:
    source = SourceCitation(
        id="src_tavily_deadbeef_001",
        type="media",
        category="media",
        title="Source",
        snippet="Evidence.",
        provider="tavily",
    )
    scope = TaskScopeContract(
        user_brief="Compare AI coding tools",
        intent_mode="list",
        competitors=[CompetitorCandidate(name="Trae", source="nl_extracted")],
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
    state = WorkflowState(
        task_id=scope.id,
        run_id=scope.id,
        scope_contract=scope,
        raw_collections={
            "Trae": RawCollectionResult(
                competitor_name="Trae",
                sources=[source],
                completeness_score=1.0,
            )
        },
        structured_profiles={
            "Trae": StructuredCompetitorProfile(
                competitor_name="Trae",
                feature_tree={
                    "rows": [
                        {
                            "feature": "Verified cells",
                            "cells": [
                                {"competitor": "Trae", "status": "unverified", "note": ""},
                            ],
                            "source_ids": [source.id],
                        },
                        {
                            "feature": "Boolean cells",
                            "cells": [
                                {"competitor": "Trae", "status": "yes", "note": "Present"},
                            ],
                            "source_ids": [source.id],
                        },
                        {
                            "feature": "Localized cells",
                            "cells": [
                                {"competitor": "Trae", "status": "部分支持", "note": "Limited"},
                            ],
                            "source_ids": [source.id],
                        },
                    ]
                },
                pricing={},
                user_personas=[],
                swot={},
                source_ids=[source.id],
            )
        },
    )

    report = WriterAgent()._run_fallback(state, language="zh")

    statuses = [
        row["cells"][0]["status"]
        for row in report.structured_content["feature_tree"]["rows"]
    ]
    assert statuses == ["unknown", "supported", "partial"]


def test_report_source_integrity_rejects_duplicate_and_unresolved_ids() -> None:
    source = SourceCitation(
        id="src_tavily_deadbeef_001",
        type="media",
        category="media",
        title="Source",
        snippet="Evidence.",
        provider="tavily",
    )

    with pytest.raises(ValueError, match="duplicate report source ids"):
        assert_report_sources_resolvable(
            sources=[source, source],
            claims=[],
            structured_content={},
        )

    with pytest.raises(ValueError, match="unresolved report source ids"):
        assert_report_sources_resolvable(
            sources=[source],
            claims=[],
            structured_content={"feature_tree": {"rows": [{"source_ids": ["missing"]}]}},
        )


def test_writer_filters_disabled_extension_findings_and_metrics() -> None:
    source = SourceCitation(
        id="src_tavily_deadbeef_001",
        type="media",
        category="media",
        title="Source",
        snippet="Evidence.",
        provider="tavily",
    )
    scope = TaskScopeContract(
        user_brief="Compare AI coding tools",
        intent_mode="list",
        competitors=[CompetitorCandidate(name="Trae", source="nl_extracted")],
        dimensions=[
            ScopeDimension(
                id="core.feature_tree",
                title="Feature tree",
                intent="Compare features",
                layer="core",
                order=1,
            ),
            ScopeDimension(
                id="ext.enabled",
                title="Enabled extension",
                intent="Current scope extension",
                layer="extension",
                order=5,
                source="ai_suggested",
            ),
            ScopeDimension(
                id="ext.deleted",
                title="Enterprise pricing strategy",
                intent="Deleted by user",
                layer="extension",
                order=6,
                enabled=False,
                source="ai_suggested",
            ),
        ],
    )
    state = WorkflowState(
        task_id=scope.id,
        run_id=scope.id,
        scope_contract=scope,
        raw_collections={
            "Trae": RawCollectionResult(
                competitor_name="Trae",
                sources=[source],
                completeness_score=1.0,
            )
        },
        structured_profiles={
            "Trae": StructuredCompetitorProfile(
                competitor_name="Trae",
                feature_tree={
                    "rows": [
                        {
                            "feature": "AI completion",
                            "cells": [
                                {
                                    "competitor": "Trae",
                                    "status": "supported",
                                    "note": "Has evidence",
                                }
                            ],
                            "source_ids": [source.id],
                        }
                    ]
                },
                pricing={},
                user_personas=[],
                swot={},
                source_ids=[source.id],
            )
        },
        extension_findings=[
            ExtensionFinding(
                dimension_id="ext.enabled",
                competitor_name="Trae",
                summary="Enabled summary",
                bullets=["Enabled finding"],
                source_ids=[source.id],
            ),
            ExtensionFinding(
                dimension_id="ext.deleted",
                competitor_name="Trae",
                summary="Deleted summary",
                bullets=["Deleted finding"],
                source_ids=[source.id],
            ),
        ],
        retry_counts={"collector": 1},
    )

    report = WriterAgent()._run_fallback(state, language="zh")

    extensions = report.structured_content["extensions"]
    assert [extension["dimension_id"] for extension in extensions] == ["ext.enabled"]
    assert "Enterprise pricing strategy" not in report.markdown_content
    assert "Deleted finding" not in str(report.structured_content)
    assert report.metrics.rerun_rate == 0.5
