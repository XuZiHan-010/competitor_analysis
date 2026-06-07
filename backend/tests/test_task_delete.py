import asyncio
from collections.abc import Callable
from uuid import uuid4

from fastapi.testclient import TestClient

from services.runs.manager import RunRecord


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


def test_delete_removes_task_and_report(
    auth_client_factory: Callable[[str], TestClient],
) -> None:
    client = auth_client_factory("eric@example.com")
    scope_contract = _scope_contract(client)
    task_id = scope_contract["id"]
    run_response = client.post(
        f"/api/tasks/{task_id}/run",
        json={"scope_contract": scope_contract},
    )
    assert run_response.status_code == 200
    run_id = run_response.json()["id"]
    assert client.get(f"/api/reports/{task_id}").status_code == 200

    delete_response = client.delete(f"/api/tasks/{run_id}")
    assert delete_response.status_code == 204

    assert all(task["id"] != run_id for task in client.get("/api/tasks").json())
    assert client.get(f"/api/tasks/{run_id}").status_code == 404
    assert client.get(f"/api/reports/{task_id}").status_code == 404


def test_delete_rejects_other_users_run(
    auth_client_factory: Callable[[str], TestClient],
) -> None:
    alice = auth_client_factory("alice@example.com")
    bob = auth_client_factory("bob@example.com")
    scope_contract = _scope_contract(alice)
    task_id = scope_contract["id"]
    run_id = alice.post(
        f"/api/tasks/{task_id}/run",
        json={"scope_contract": scope_contract},
    ).json()["id"]

    assert bob.delete(f"/api/tasks/{run_id}").status_code == 404
    # Alice's data is untouched by the rejected delete.
    assert alice.get(f"/api/reports/{task_id}").status_code == 200


def test_delete_running_task_cancels_dag() -> None:
    from api.dependencies import run_manager

    async def scenario() -> None:
        user_id = uuid4()
        record = RunRecord(task_id=uuid4(), user_id=user_id, status="running")
        run_manager._runs[record.id] = record

        started = asyncio.Event()

        async def never_ending() -> None:
            started.set()
            await asyncio.sleep(3600)

        task = asyncio.create_task(never_ending())
        run_manager._tasks[record.id] = task
        await started.wait()

        deleted = await run_manager.delete_run(record.id, user_id=user_id)

        assert deleted is True
        assert task.cancelled()
        assert record.id not in run_manager._runs
        assert record.id not in run_manager._tasks

    asyncio.run(scenario())
