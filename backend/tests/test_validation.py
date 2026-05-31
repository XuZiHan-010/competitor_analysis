from fastapi.testclient import TestClient

from main import app


def test_e2e_smoke_validation_runs_three_cases() -> None:
    client = TestClient(app)
    response = client.post("/api/validation/e2e-smoke")
    assert response.status_code == 200
    data = response.json()
    assert data["case_count"] == 3
    assert len(data["cases"]) == 3
    assert all(case["report_ready"] for case in data["cases"])
    assert all(case["claim_count"] > 0 for case in data["cases"])
    assert all(case["source_count"] > 0 for case in data["cases"])
    assert all(case["survey_result_count"] > 0 for case in data["cases"])
    assert all(case["survey_stage_count"] >= 7 for case in data["cases"])
    assert all(case["export_checks"]["pdf_bytes"] > 0 for case in data["cases"])
    assert all(case["retry_count"] >= 0 for case in data["cases"])


def test_platform_readiness_reports_missing_local_infra() -> None:
    client = TestClient(app)
    response = client.get("/api/validation/platform-readiness")

    assert response.status_code == 200
    data = response.json()
    assert data["passed"] is False
    assert data["mode"] == "mock"
    assert data["db"]["configured"] is False
    assert data["redis"]["configured"] is False
    assert data["required_env_present"]["DATABASE_URL"] is False
