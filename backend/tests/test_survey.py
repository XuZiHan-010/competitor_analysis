from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from main import app
from schemas.source import SourceCitation
from schemas.survey import Questionnaire, SurveyQuestion
from services.survey import redact_sensitive_text
from services.survey.existing_survey_finder import ExistingSurveyFinder
from services.survey.questionnaire_designer import QuestionnaireDesigner


def test_redact_sensitive_text() -> None:
    text = "姓名：张三 phone 138-0000-0000 email eric@example.com"
    redacted = redact_sensitive_text(text)
    assert "张三" not in redacted
    assert "138-0000-0000" not in redacted
    assert "eric@example.com" not in redacted


def test_upload_survey_redacts_and_counts_evidence() -> None:
    client = TestClient(app)
    task_id = uuid4()
    response = client.post(
        f"/api/tasks/{task_id}/survey/upload",
        json={
            "kind": "interview_record",
            "content": "姓名：李四\n喜欢功能矩阵\n电话 13900000000",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["parsed_evidence_count"] == 3
    assert all(item["source_type"] == "user_uploaded_primary" for item in data["evidence"])
    assert "李四" not in str(data)
    assert "13900000000" not in str(data)


def test_uploaded_survey_evidence_enters_workflow() -> None:
    client = TestClient(app)
    scope_response = client.post(
        "/api/tasks/scoping",
        json={
            "user_brief": "分析 Notion、Lark、Airtable 的协作能力",
            "known_competitors": ["Notion", "Lark", "Airtable"],
        },
    )
    assert scope_response.status_code == 200
    scope_contract = scope_response.json()["scope_contract"]
    task_id = scope_contract["id"]

    upload_response = client.post(
        f"/api/tasks/{task_id}/survey/upload",
        json={"kind": "interview_record", "content": "用户反馈：团队协作模板很好用"},
    )
    assert upload_response.status_code == 200

    run_response = client.post(
        f"/api/tasks/{task_id}/run",
        json={"scope_contract": scope_contract},
    )
    assert run_response.status_code == 200
    report_response = client.get(f"/api/reports/{task_id}")
    assert report_response.status_code == 200
    survey = report_response.json()["structured_content"]["survey"][0]
    assert survey["source_breakdown"]["user_uploaded_primary"] >= 1


@pytest.mark.asyncio
async def test_questionnaire_designer_fallback_returns_prd_shape() -> None:
    questionnaire = await QuestionnaireDesigner().design(
        competitor="Notion",
        dimensions=[],
        existing_questionnaire=None,
    )
    assert questionnaire.competitor == "Notion"
    assert len(questionnaire.questions) >= 5
    assert questionnaire.questions[0].intent
    assert questionnaire.design_rationale


@pytest.mark.asyncio
async def test_existing_survey_finder_maps_search_results_to_evidence() -> None:
    class FakeSearch:
        name = "fake"

        async def search(self, query: str, max_results: int = 5) -> list[SourceCitation]:
            return [
                SourceCitation(
                    id="survey_src_1",
                    type="published_survey",
                    category="media",
                    url="https://example.com/survey",
                    title="Survey report",
                    snippet="Users mention collaboration pain points.",
                    provider="fake",
                )
            ]

    questionnaire = Questionnaire(
        competitor="Notion",
        dimension_intent="用户声音",
        questions=[
            SurveyQuestion(
                id="sq_001",
                text="为什么选择该产品？",
                type="open",
                intent="识别采用动机。",
            )
        ],
        design_rationale="test",
    )
    result = await ExistingSurveyFinder(FakeSearch()).find(
        competitor="Notion",
        questionnaire=questionnaire,
    )
    evidence = result.evidence
    assert evidence[0].source_type == "published_survey"
    assert evidence[0].question_id == "sq_001"
    assert evidence[0].source_id == "survey_src_1"
    assert result.sources[0].id == "survey_src_1"


@pytest.mark.asyncio
async def test_existing_survey_finder_rejects_non_research_sources() -> None:
    class FakeSearch:
        name = "fake"

        async def search(self, query: str, max_results: int = 5) -> list[SourceCitation]:
            return [
                SourceCitation(
                    id="marketing_src",
                    type="official",
                    category="official",
                    url="https://example.com/product",
                    title="Product homepage",
                    snippet="Beautiful landing page with features and pricing.",
                    provider="fake",
                ),
                SourceCitation(
                    id="survey_src_2",
                    type="published_survey",
                    category="media",
                    url="https://example.com/research",
                    title="Customer satisfaction research report",
                    snippet="Survey respondents mention collaboration workflows.",
                    provider="fake",
                ),
            ]

    questionnaire = Questionnaire(
        competitor="Notion",
        dimension_intent="用户声音",
        questions=[
            SurveyQuestion(
                id="sq_001",
                text="为什么选择该产品？",
                type="open",
                intent="识别采用动机。",
            )
        ],
        design_rationale="test",
    )
    result = await ExistingSurveyFinder(FakeSearch()).find(
        competitor="Notion",
        questionnaire=questionnaire,
    )
    assert [source.id for source in result.sources] == ["survey_src_2"]
    assert result.rejected_count == 1
