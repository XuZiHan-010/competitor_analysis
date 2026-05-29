from fastapi.testclient import TestClient

from main import app


def test_create_scoping_draft() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/tasks/scoping",
        json={
            "user_brief": "分析 Notion 和 Lark 的协作能力",
            "known_competitors": ["Notion", "Lark"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["scope_contract"]["competitors"]) >= 3
    assert data["scope_contract"]["user_research_plan"]["enabled"] is True
    questionnaire = data["scope_contract"]["user_research_plan"]["questionnaire"]
    assert questionnaire["design_rationale"]
    assert questionnaire["questions"][0]["intent"]

    task_id = data["scope_contract"]["id"]
    saved_response = client.get(f"/api/tasks/scoping/drafts/{task_id}")
    assert saved_response.status_code == 200
    assert saved_response.json()["scope_contract"]["id"] == task_id
