import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from db import models
from db.persistence import SqlRunPersistence
from schemas.report import Report, ReportClaim, ReportMetrics
from schemas.scope import CompetitorCandidate, ScopeDimension, TaskScopeContract
from schemas.source import SourceCitation
from schemas.traces import AgentTrace
from services.auth import user_id_for_email
from services.runs.manager import RunManager, RunRecord
from services.storage import InMemoryStore
from services.streaming.bridge import InMemoryStreamBridge

pytestmark = pytest.mark.integration


def _scope(*, task_id: UUID | None = None, competitor: str = "Alpha") -> TaskScopeContract:
    return TaskScopeContract(
        id=task_id or uuid4(),
        user_brief=f"Compare {competitor}",
        intent_mode="list",
        competitors=[CompetitorCandidate(name=competitor, source="nl_extracted")],
        dimensions=[
            ScopeDimension(
                id="core.feature_tree",
                title="Feature tree",
                intent="Compare features",
                layer="core",
                order=1,
            )
        ],
    )


def _report(task_id: UUID, *, term: str = "alphaunique") -> Report:
    source_id = f"src_{uuid4().hex}"
    return Report(
        task_id=task_id,
        structured_content={
            "title": f"{term} report",
            "summary": f"Evidence about {term}",
            "competitors": [term],
        },
        markdown_content=f"# {term}\n\n{term} capabilities and pricing.",
        sources=[
            SourceCitation(
                id=source_id,
                type="official",
                category="official",
                title=f"{term} source",
                snippet=f"Primary evidence for {term}",
                provider="integration",
            )
        ],
        claims=[
            ReportClaim(
                claim_path="summary",
                claim_text=f"{term} has documented capabilities",
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


@pytest.mark.asyncio
async def test_full_persistence_round_trip_restart_isolation_and_cascade(
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    persistence = SqlRunPersistence(db_sessionmaker)
    user_id = await persistence.upsert_user("owner@example.com")
    other_user_id = await persistence.upsert_user("other@example.com")
    scope = _scope()
    await persistence.ensure_task(scope, user_id=user_id, user_email="owner@example.com")
    run = RunRecord(
        task_id=scope.id,
        user_id=user_id,
        status="succeeded",
        started_at=datetime.now(UTC),
    )
    await persistence.create_run(run)
    trace = AgentTrace(
        task_run_id=run.id,
        sequence_no=1,
        agent_name="CollectorAgent",
        node_name="run_collector",
        status="succeeded",
        prompt="collect",
        input_payload={"task_id": str(scope.id)},
        output_payload={"source_count": 1},
    )
    await persistence.add_trace(trace)
    report = _report(scope.id)
    await persistence.save_report(report, scope.id)

    restarted = SqlRunPersistence(db_sessionmaker)
    loaded_run = await restarted.get_run(run.id)
    loaded_report = await restarted.get_report(scope.id, user_id=user_id)
    hidden_report = await restarted.get_report(scope.id, user_id=other_user_id)
    timeline = await restarted.get_timeline(run.id)

    assert loaded_run is not None and loaded_run.status == "succeeded"
    assert loaded_report is not None
    assert loaded_report.model_dump(mode="json") == report.model_dump(mode="json")
    assert hidden_report is None
    assert timeline[0].id == trace.id
    assert await restarted.list_runs(user_id=other_user_id) == []

    await restarted.delete_task(scope.id)
    async with db_sessionmaker() as session:
        assert await session.get(models.Task, scope.id) is None
        assert await session.get(models.TaskRun, run.id) is None
        assert await session.get(models.AgentTrace, trace.id) is None
        assert await session.get(models.Report, report.id) is None
        assert await session.get(models.ReportClaim, report.claims[0].id) is None
        assert await session.get(models.SourceCitation, report.sources[0].id) is None


@pytest.mark.asyncio
async def test_transaction_rollback_does_not_leave_user(
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    user_id = uuid4()
    async with db_sessionmaker() as session:
        session.add(models.User(id=user_id, email=f"rollback-{user_id}@example.com"))
        await session.flush()
        await session.rollback()
    async with db_sessionmaker() as session:
        assert await session.get(models.User, user_id) is None


@pytest.mark.asyncio
async def test_pgvector_search_and_concurrent_report_writes(
    db_engine: AsyncEngine,
) -> None:
    committed_sessionmaker = async_sessionmaker(db_engine, expire_on_commit=False)
    persistence = SqlRunPersistence(committed_sessionmaker)
    user_id = await persistence.upsert_user("search-owner@example.com")
    alpha_scope = _scope(competitor="Alpha")
    beta_scope = _scope(competitor="Beta")
    await persistence.ensure_task(
        alpha_scope,
        user_id=user_id,
        user_email="search-owner@example.com",
    )
    await persistence.ensure_task(
        beta_scope,
        user_id=user_id,
        user_email="search-owner@example.com",
    )
    alpha_report = _report(alpha_scope.id, term="alphaunique")
    beta_report = _report(beta_scope.id, term="betaunique")

    try:
        await asyncio.gather(
            persistence.save_report(alpha_report, alpha_scope.id),
            persistence.save_report(beta_report, beta_scope.id),
        )
        result = await persistence.search_reports("alphaunique", user_id=user_id)

        assert result.mode == "pgvector"
        assert result.reports
        assert result.reports[0].task_id == alpha_scope.id
        async with committed_sessionmaker() as session:
            embeddings = (
                await session.execute(
                    text(
                        "SELECT id FROM reports "
                        "WHERE id IN (:alpha_id, :beta_id) AND embedding IS NOT NULL"
                    ),
                    {"alpha_id": alpha_report.id, "beta_id": beta_report.id},
                )
            ).scalars().all()
        assert set(embeddings) == {alpha_report.id, beta_report.id}
    finally:
        await persistence.delete_task(alpha_scope.id)
        await persistence.delete_task(beta_scope.id)
        async with committed_sessionmaker() as session:
            await session.execute(delete(models.User).where(models.User.id == user_id))
            await session.commit()


@pytest.mark.asyncio
async def test_run_manager_does_not_silently_fallback_from_database(
    db_sessionmaker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    warnings: list[str] = []

    def capture_warning(event: str, **_: object) -> None:
        warnings.append(event)

    monkeypatch.setattr("services.runs.manager.logger.warning", capture_warning)
    persistence = SqlRunPersistence(db_sessionmaker)
    manager = RunManager(InMemoryStore(), InMemoryStreamBridge(), persistence=persistence)
    scope = _scope()
    user_id = user_id_for_email("manager-owner@example.com")

    record = await manager.start_run(
        scope,
        user_id=user_id,
        user_email="manager-owner@example.com",
    )

    assert not any(event.startswith("db_unavailable_") for event in warnings)
    async with db_sessionmaker() as session:
        persisted = await session.get(models.TaskRun, record.id)
    assert persisted is not None
    assert persisted.task_id == scope.id
