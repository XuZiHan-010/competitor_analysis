from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from services.exporter import PdfRenderError


def _create_completed_run(client: TestClient) -> tuple[str, str, str]:
    scope_response = client.post(
        "/api/tasks/scoping",
        json={
            "user_brief": "Compare Notion and Lark collaboration",
            "known_competitors": ["Notion", "Lark"],
        },
    )
    assert scope_response.status_code == 200
    scope = scope_response.json()["scope_contract"]
    task_id = scope["id"]
    run_response = client.post(
        f"/api/tasks/{task_id}/run",
        json={"scope_contract": scope},
    )
    assert run_response.status_code == 200
    report_response = client.get(f"/api/reports/{task_id}")
    assert report_response.status_code == 200
    return task_id, run_response.json()["id"], report_response.json()["claims"][0]["id"]


def test_cross_user_report_writes_upload_and_stream_are_rejected(
    auth_client_factory: Callable[[str], TestClient],
) -> None:
    owner = auth_client_factory("owner@example.com")
    attacker = auth_client_factory("attacker@example.com")
    task_id, run_id, claim_id = _create_completed_run(owner)

    correction = attacker.patch(
        f"/api/reports/{task_id}/field",
        json={
            "claim_id": claim_id,
            "field_path": "summary",
            "new_value": "unauthorized edit",
            "correction_type": "fact_fix",
        },
    )
    review = attacker.patch(
        f"/api/reports/{task_id}/claims/{claim_id}/review",
        json={"review_status": "correct"},
    )
    export = attacker.get(f"/api/reports/{task_id}/export", params={"format": "markdown"})
    upload = attacker.post(
        f"/api/tasks/{task_id}/survey/upload",
        json={"kind": "interview_record", "content": "Participant said it was useful."},
    )
    stream = attacker.get(f"/api/tasks/{run_id}/events")

    assert correction.status_code == 404
    assert review.status_code == 404
    assert export.status_code == 404
    assert upload.status_code == 404
    assert stream.status_code == 403
    assert owner.get(f"/api/reports/{task_id}").json()["claims"][0]["edit_status"] == (
        "untouched"
    )


def test_invalid_write_payloads_and_field_paths_return_422(
    auth_client_factory: Callable[[str], TestClient],
) -> None:
    client = auth_client_factory("owner@example.com")
    task_id, _, claim_id = _create_completed_run(client)

    bad_path = client.patch(
        f"/api/reports/{task_id}/field",
        json={
            "claim_id": claim_id,
            "field_path": "missing.arbitrary.path",
            "new_value": "value",
            "correction_type": "fact_fix",
        },
    )
    bad_correction = client.patch(
        f"/api/reports/{task_id}/field",
        json={
            "claim_id": claim_id,
            "field_path": "summary",
            "new_value": "value",
            "correction_type": "not-an-enum",
        },
    )
    bad_review = client.patch(
        f"/api/reports/{task_id}/claims/{claim_id}/review",
        json={"review_status": "approved"},
    )
    bad_upload = client.post(
        f"/api/tasks/{task_id}/survey/upload",
        json={"kind": "spreadsheet", "content": "data"},
    )

    assert bad_path.status_code == 422
    assert bad_correction.status_code == 422
    assert bad_review.status_code == 422
    assert bad_upload.status_code == 422


def test_export_error_statuses(
    auth_client_factory: Callable[[str], TestClient],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = auth_client_factory("owner@example.com")
    task_id, _, _ = _create_completed_run(client)

    async def fail_pdf(_: object) -> bytes:
        raise PdfRenderError("renderer unavailable")

    monkeypatch.setattr("api.routes.reports.render_report_pdf", fail_pdf)

    pdf = client.get(f"/api/reports/{task_id}/export", params={"format": "pdf"})
    unknown = client.get(f"/api/reports/{task_id}/export", params={"format": "docx"})
    missing = client.get("/api/reports/00000000-0000-0000-0000-000000000000/export")

    assert pdf.status_code == 503
    assert unknown.status_code == 400
    assert missing.status_code == 404
