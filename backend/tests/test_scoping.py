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
