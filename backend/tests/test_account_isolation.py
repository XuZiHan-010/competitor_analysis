from collections.abc import Callable
from uuid import uuid4

from fastapi.testclient import TestClient

from main import app


def _scope_contract(client: TestClient, brief: str) -> dict:
    response = client.post(
        "/api/tasks/scoping",
        json={
            "user_brief": brief,
            "known_competitors": ["Notion", "Lark", "Airtable"],
        },
    )
    assert response.status_code == 200
    return response.json()["scope_contract"]


def test_history_is_filtered_by_authenticated_user(
    auth_client_factory: Callable[[str], TestClient],
) -> None:
    user_a = auth_client_factory("alice@example.com")
    user_b = auth_client_factory("bob@example.com")

    scope_contract = _scope_contract(user_a, "分析 Notion、Lark、Airtable 的协作能力")
    task_id = scope_contract["id"]
    run_response = user_a.post(
        f"/api/tasks/{task_id}/run",
        json={"scope_contract": scope_contract},
    )
    assert run_response.status_code == 200
    run_id = run_response.json()["id"]

    assert user_a.get(f"/api/reports/{task_id}").status_code == 200
    assert user_b.get(f"/api/reports/{task_id}").status_code == 404
    assert user_b.get(f"/api/tasks/{run_id}/timeline").status_code == 404

    tasks_response = user_b.get("/api/tasks")
    assert tasks_response.status_code == 200
    assert all(task["task_id"] != task_id for task in tasks_response.json())

    search_response = user_b.get("/api/reports/search", params={"q": "Notion"})
    assert search_response.status_code == 200
    assert search_response.json()["results"] == []

    empty_search_response = user_b.get("/api/reports/search", params={"q": ""})
    assert empty_search_response.status_code == 200
    assert empty_search_response.json()["results"] == []


def test_history_requires_token() -> None:
    client = TestClient(app)

    assert client.get("/api/tasks").status_code == 401
    assert client.get(f"/api/reports/{uuid4()}").status_code == 401
    assert client.post("/api/tasks/scoping", json={"user_brief": "分析 Notion"}).status_code == 401


def test_same_email_gets_stable_user_id() -> None:
    client = TestClient(app)

    assert client.post("/api/auth/login", json={"email": "Alice@example.com"}).status_code == 200
    first_me = client.get("/api/auth/me")
    assert first_me.status_code == 200

    assert client.post("/api/auth/login", json={"email": "alice@example.com"}).status_code == 200
    second_me = client.get("/api/auth/me")
    assert second_me.status_code == 200

    assert first_me.json()["user_id"] == second_me.json()["user_id"]
