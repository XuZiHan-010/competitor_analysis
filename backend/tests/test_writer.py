import pytest

from agents.writer import WriterAgent
from graph.state import RawCollectionResult, StructuredCompetitorProfile, WorkflowState
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
from services.report_integrity import assert_report_sources_resolvable


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


def test_writer_fallback_report_marks_placeholder_quality_issue() -> None:
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

    assert report.qa_status == "issues"
    assert any(
        issue.get("failed_field") == "report.placeholder_content"
        for issue in report.qa_issues
    )


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
