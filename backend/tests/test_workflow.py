from time import sleep
from typing import Any

from fastapi.testclient import TestClient

from main import app


def _scope_contract(client: TestClient) -> dict:
    response = client.post(
        "/api/tasks/scoping",
        json={
            "user_brief": "分析 Notion、Lark、Airtable 的协作能力",
            "known_competitors": ["Notion", "Lark", "Airtable"],
        },
    )
    assert response.status_code == 200
    return response.json()["scope_contract"]


def test_run_mock_workflow_and_report_contract() -> None:
    client = TestClient(app)
    scope_contract = _scope_contract(client)
    task_id = scope_contract["id"]

    run_response = client.post(
        f"/api/tasks/{task_id}/run",
        json={"scope_contract": scope_contract, "force_feedback_demo": True},
    )
    assert run_response.status_code == 200
    run_id = run_response.json()["id"]

    report_response = None
    for _ in range(20):
        report_response = client.get(f"/api/reports/{task_id}")
        if report_response.status_code == 200:
            break
        sleep(0.05)

    assert report_response is not None
    assert report_response.status_code == 200
    report = report_response.json()
    assert report["claims"]
    assert all(claim["source_ids"] for claim in report["claims"])
    structured = report["structured_content"]
    assert structured["feature_tree"]["rows"]
    assert structured["pricing"]["tiers"]
    assert structured["user_personas"]["personas"]
    assert structured["swot"]["blocks"]
    assert structured["extensions"]
    assert structured["cross_analysis"]["feature_matrix"]["rows"]
    assert structured["cross_analysis"]["pricing_comparison"]
    assert report["structured_content"]["survey"]
    survey = report["structured_content"]["survey"][0]
    assert survey["questionnaire"]["design_rationale"]
    assert survey["distribution"]["distributor_impl"] == "SimulatedDistributor"
    assert survey["responses"]
    assert survey["coverage_note"]
    assert any(claim["generating_agent"] == "SurveyTool" for claim in report["claims"])
    assert survey["source_breakdown"]["public_review"] >= 1

    metrics_response = client.get(f"/api/reports/{task_id}/metrics")
    assert metrics_response.status_code == 200
    metrics = metrics_response.json()
    assert metrics["citation_coverage_rate"] == 1.0
    assert metrics["source_support_rate"] == 1.0
    assert metrics["rerun_rate"] > 0
    assert metrics["analysis_duration_seconds"] is not None

    timeline_response = client.get(f"/api/tasks/{run_id}/timeline")
    assert timeline_response.status_code == 200
    timeline = timeline_response.json()
    assert [trace["sequence_no"] for trace in timeline] == sorted(
        trace["sequence_no"] for trace in timeline
    )
    assert {trace["agent_name"] for trace in timeline} >= {
        "CollectorAgent",
        "AnalystAgent",
        "QAAgent",
        "WriterAgent",
    }
    survey_stages = {
        "survey.stage1.designer",
        "survey.stage2a.existing",
        "survey.stage2b.voice",
        "survey.stage3a.persona",
        "survey.stage3b.distribute",
        "survey.stage3c.collect",
        "survey.stage4.aggregate",
    }
    assert survey_stages.issubset({trace["node_name"] for trace in timeline})
    collector_traces = [trace for trace in timeline if trace["agent_name"] == "CollectorAgent"]
    assert len(collector_traces) >= 2
    recovered_sources = [
        source
        for source in report["sources"]
        if source["provider"] == "feedback_recovery"
    ]
    assert recovered_sources

    tasks_response = client.get("/api/tasks")
    assert tasks_response.status_code == 200
    tasks = tasks_response.json()
    assert any(task["id"] == run_id and task["status"] == "succeeded" for task in tasks)


def test_p1_contract_placeholders(monkeypatch: Any) -> None:
    client = TestClient(app)
    scope_contract = _scope_contract(client)
    task_id = scope_contract["id"]
    run_response = client.post(
        f"/api/tasks/{task_id}/run",
        json={"scope_contract": scope_contract},
    )
    assert run_response.status_code == 200

    report = client.get(f"/api/reports/{task_id}").json()
    claim_id = report["claims"][0]["id"]

    correction_response = client.patch(
        f"/api/reports/{task_id}/field",
        json={
            "claim_id": claim_id,
            "field_path": "summary",
            "new_value": "corrected summary",
            "correction_type": "fact_fix",
            "triggered_rerun": True,
        },
    )
    assert correction_response.status_code == 200
    corrected = correction_response.json()
    assert corrected["structured_content"]["summary"] == "corrected summary"
    assert corrected["claims"][0]["edit_status"] == "edited"
    assert corrected["metrics"]["manual_correction_rate"] > 0
    assert corrected["metrics"]["rerun_rate"] == 1.0

    review_response = client.patch(
        f"/api/reports/{task_id}/claims/{claim_id}/review",
        json={"review_status": "correct"},
    )
    assert review_response.status_code == 200
    reviewed = review_response.json()
    assert reviewed["claims"][0]["review_status"] == "correct"
    assert reviewed["metrics"]["human_verified_accuracy_rate"] == 1.0

    language_response = client.post(
        f"/api/reports/{task_id}/language",
        json={"language": "en"},
    )
    assert language_response.status_code == 200
    assert language_response.json()["language"] == "en"

    markdown_response = client.get(f"/api/reports/{task_id}/export", params={"format": "markdown"})
    assert markdown_response.status_code == 200
    assert markdown_response.content

    pdf_response = client.get(f"/api/reports/{task_id}/export", params={"format": "pdf"})
    assert pdf_response.status_code == 200
    assert pdf_response.content.startswith(b"%PDF")

    pptx_response = client.get(f"/api/reports/{task_id}/export", params={"format": "pptx"})
    assert pptx_response.status_code == 200
    assert pptx_response.content.startswith(b"PK")

    search_response = client.get("/api/reports/search", params={"q": "corrected"})
    assert search_response.status_code == 200
    data = search_response.json()
    assert data["mode"] == "in_memory_semantic_fallback"
    assert data["results"]

    claim_search_response = client.get("/api/reports/search", params={"q": "collaboration"})
    assert claim_search_response.status_code == 200
    claim_search_results = claim_search_response.json()["results"]
    assert claim_search_results
    assert claim_search_results[0]["claim_ids"]
    assert claim_search_results[0]["source_ids"]

    class FakeLLMClient:
        enabled = True

        def __init__(self, settings: object) -> None:
            self._settings = settings

        async def complete_json(
            self,
            *,
            provider: str,
            model: str,
            messages: list[dict[str, str]],
        ) -> dict[str, object]:
            return {
                "summary": "Regenerated user voice",
                "bullets": [
                    {
                        "competitor": "Notion",
                        "points": ["Regenerated claim"],
                        "source_ids": ["Notion_default"],
                    }
                ],
            }

    monkeypatch.setattr("api.routes.reports.LLMClient", FakeLLMClient)
    regenerate_response = client.post(
        f"/api/reports/{task_id}/dimensions/ext.user_voice/regenerate"
    )
    assert regenerate_response.status_code == 200
    regenerated = regenerate_response.json()
    assert regenerated["structured_content"]["extensions"][0]["summary"] == "Regenerated user voice"
    assert regenerated["metrics"]["rerun_rate"] == 1.0
