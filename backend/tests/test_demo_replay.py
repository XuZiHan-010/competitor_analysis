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


def test_demo_replay_returns_static_bundle() -> None:
    client = TestClient(app)
    response = client.get("/api/demo/replay")

    assert response.status_code == 200
    data = response.json()
    assert data["demo_mode"] is True
    assert data["route_scope"] == "demo_only"
    assert data["scope"]["task_id"] == data["report"]["task_id"]
    assert data["trace"]
    assert data["sources"]
    assert data["export_formats"] == ["markdown", "pdf", "pptx"]


def test_demo_replay_does_not_seed_production_reports() -> None:
    client = TestClient(app)
    replay_response = client.get("/api/demo/replay")
    assert replay_response.status_code == 200

    search_response = client.get(
        "/api/reports/search",
        params={"q": replay_response.json()["demo_id"]},
    )
    assert search_response.status_code == 200
    assert search_response.json()["results"] == []


def test_demo_replay_snapshot_from_completed_run_without_writing() -> None:
    client = TestClient(app)
    scope_contract = _scope_contract(client)
    task_id = scope_contract["id"]
    run_response = client.post(
        f"/api/tasks/{task_id}/run",
        json={"scope_contract": scope_contract, "force_feedback_demo": True},
    )
    assert run_response.status_code == 200
    run_id = run_response.json()["id"]

    response = client.post(
        "/api/demo/replay/snapshot",
        params={"task_id": task_id, "run_id": run_id},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["written"] is False
    assert data["bundle"]["source"] == "generated_from_completed_run"
    assert data["bundle"]["scope"]["id"] == task_id
    assert data["bundle"]["report"]["task_id"] == task_id
    assert data["bundle"]["trace"]
    assert data["bundle"]["sources"]
