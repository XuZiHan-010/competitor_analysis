import os
from uuid import uuid4

import pytest
from sqlalchemy.engine import make_url

from schemas.report import Report, ReportClaim, ReportMetrics
from schemas.source import SourceCitation
from services.exporter import render_report_pdf
from services.validation.platform import _check_db, _check_redis

pytestmark = pytest.mark.smoke


def _smoke_urls() -> tuple[str, str]:
    if os.getenv("SMOKE_ALLOW_REMOTE") != "true":
        pytest.skip("Set SMOKE_ALLOW_REMOTE=true for dedicated remote smoke infrastructure")
    database_url = os.getenv("SMOKE_DATABASE_URL", "").strip()
    redis_url = os.getenv("SMOKE_REDIS_URL", "").strip()
    if not database_url or not redis_url:
        pytest.skip("SMOKE_DATABASE_URL and SMOKE_REDIS_URL are required")
    if database_url == os.getenv("DATABASE_URL") or redis_url == os.getenv("REDIS_URL"):
        pytest.fail("Smoke infrastructure must not reuse production connections")
    if make_url(database_url).host in {None, ""} or make_url(redis_url).host in {None, ""}:
        pytest.fail("Smoke infrastructure URLs must be valid")
    return database_url, redis_url


@pytest.mark.asyncio
async def test_dedicated_database_and_redis_are_production_compatible() -> None:
    database_url, redis_url = _smoke_urls()

    database = await _check_db(database_url)
    redis = await _check_redis(redis_url)

    assert database.connected is True
    assert database.vector_extension is True
    assert database.alembic_revision == "0003"
    assert all(database.embedding_columns.values())
    assert redis.connected is True


@pytest.mark.asyncio
async def test_real_chromium_pdf_render() -> None:
    _smoke_urls()
    source_id = f"src_{uuid4().hex}"
    report = Report(
        task_id=uuid4(),
        structured_content={"title": "Smoke report", "summary": "Rendered by Chromium"},
        markdown_content="# Smoke report\n\nRendered by Chromium.",
        sources=[
            SourceCitation(
                id=source_id,
                type="official",
                category="official",
                title="Smoke source",
                snippet="Evidence",
                provider="smoke",
            )
        ],
        claims=[
            ReportClaim(
                claim_path="summary",
                claim_text="Rendered by Chromium",
                layer="core",
                field_type="free_text",
                source_ids=[source_id],
                generating_agent="WriterAgent",
            )
        ],
        metrics=ReportMetrics(
            field_coverage_rate=1.0,
            citation_coverage_rate=1.0,
            manual_correction_rate=0.0,
        ),
    )

    pdf = await render_report_pdf(report)

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000
