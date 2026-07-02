import pytest
from fastapi.testclient import TestClient

from main import app
from services.validation.platform import DbReadiness, RedisReadiness, check_platform_readiness
from settings import Settings


def test_e2e_smoke_validation_runs_three_cases(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_render_report_pdf(report: object) -> bytes:
        return b"%PDF-1.4\n% test pdf\n"

    monkeypatch.setattr(
        "services.validation.e2e_smoke.render_report_pdf",
        fake_render_report_pdf,
    )

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


@pytest.mark.asyncio
async def test_platform_readiness_fails_when_pgvector_extension_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def database_without_vector(_: str | None) -> DbReadiness:
        return DbReadiness(
            configured=True,
            connected=True,
            vector_extension=False,
            embedding_columns={
                "reports.embedding": True,
                "report_claims.embedding": True,
                "source_citations.embedding": True,
            },
        )

    async def healthy_redis(_: str | None) -> RedisReadiness:
        return RedisReadiness(configured=True, connected=True)

    monkeypatch.setattr("services.validation.platform._check_db", database_without_vector)
    monkeypatch.setattr("services.validation.platform._check_redis", healthy_redis)
    monkeypatch.setattr(
        "services.validation.platform.get_settings",
        lambda: Settings(
            database_url="postgresql://placeholder/test",
            redis_url="redis://localhost/15",
            jwt_secret="placeholder",
        ),
    )

    readiness = await check_platform_readiness()

    assert readiness.passed is False
    assert readiness.db.connected is True
    assert readiness.db.vector_extension is False
