from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy import Text, delete, or_, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from db import models
from schemas.report import Report, ReportClaim, ReportMetrics, ReportSearchBackendResult
from schemas.scope import TaskScopeContract
from schemas.source import SourceCitation
from schemas.traces import AgentTrace
from services.auth import user_id_for_email
from services.report_integrity import assert_report_sources_resolvable
from services.report_search import (
    competitor_names_from_items,
    rank_reports_for_query,
    tokenize_report_query,
)
from services.runs.manager import RunRecord
from services.search.embeddings import EmbeddingService, vector_literal
from settings import get_settings

logger = structlog.get_logger(__name__)


class RunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create_user(self, email: str) -> UUID:
        user_id = user_id_for_email(email)
        user = await self._session.get(models.User, user_id)
        now = datetime.now(UTC)
        if user is None:
            user = models.User(id=user_id, email=email.lower(), last_login_at=now)
            self._session.add(user)
        else:
            user.email = email.lower()
            user.last_login_at = now
        await self._session.commit()
        return user_id

    async def ensure_task(
        self,
        scope_contract: TaskScopeContract,
        *,
        user_id: UUID,
        user_email: str,
    ) -> None:
        await self.get_or_create_user(user_email)
        task = await self._session.get(models.Task, scope_contract.id)
        if task is not None:
            if task.user_id is None:
                task.user_id = user_id
                await self._session.commit()
            return
        self._session.add(
            models.Task(
                id=scope_contract.id,
                user_id=user_id,
                target_brief=scope_contract.user_brief,
                competitor_names=[
                    competitor.model_dump(mode="json") for competitor in scope_contract.competitors
                ],
                dimensions=[
                    dimension.model_dump(mode="json") for dimension in scope_contract.dimensions
                ],
                status="pending",
            )
        )
        await self._session.commit()

    async def create_run(self, record: RunRecord) -> None:
        self._session.add(
            models.TaskRun(
                id=record.id,
                task_id=record.task_id,
                status=record.status,
                retry_count=record.retry_count,
                error_summary=record.error_summary,
                started_at=record.started_at,
                completed_at=record.completed_at,
            )
        )
        await self._session.commit()

    async def update_run(self, record: RunRecord) -> None:
        run = await self._session.get(models.TaskRun, record.id)
        if run is None:
            return
        run.status = record.status
        run.retry_count = record.retry_count
        run.error_summary = record.error_summary
        run.started_at = record.started_at
        run.completed_at = record.completed_at
        await self._session.commit()

    async def delete_task(self, task_id: UUID) -> None:
        # Raw DELETE relies on the FK ondelete="CASCADE" so Postgres removes the
        # task's runs, reports, sources, traces and claims in one statement.
        await self._session.execute(delete(models.Task).where(models.Task.id == task_id))
        await self._session.commit()

    async def get_run(self, run_id: UUID) -> RunRecord | None:
        result = await self._session.execute(
            select(models.TaskRun, models.Task.user_id, models.Task.competitor_names)
            .join(models.Task, models.Task.id == models.TaskRun.task_id)
            .where(models.TaskRun.id == run_id)
        )
        row = result.one_or_none()
        if row is None:
            return None
        run, user_id, competitor_names = row
        return _run_from_model(run, user_id=user_id, competitor_names=competitor_names)

    async def get_task_owner(self, task_id: UUID) -> UUID | None:
        result = await self._session.execute(
            select(models.Task.user_id).where(models.Task.id == task_id)
        )
        return result.scalar_one_or_none()

    async def list_runs(
        self,
        limit: int = 50,
        *,
        user_id: UUID | None = None,
    ) -> list[RunRecord]:
        statement = select(models.TaskRun, models.Task.user_id, models.Task.competitor_names).join(
            models.Task,
            models.Task.id == models.TaskRun.task_id,
        )
        if user_id is not None:
            statement = statement.where(models.Task.user_id == user_id)
        result = await self._session.execute(
            statement.order_by(models.TaskRun.started_at.desc().nullslast()).limit(limit)
        )
        return [
            _run_from_model(run, user_id=owner_id, competitor_names=competitor_names)
            for run, owner_id, competitor_names in result.all()
        ]

    async def add_trace(self, trace: AgentTrace) -> None:
        self._session.add(
            models.AgentTrace(
                id=trace.id,
                task_run_id=trace.task_run_id,
                sequence_no=trace.sequence_no,
                agent_name=trace.agent_name,
                node_name=trace.node_name,
                status=trace.status,
                prompt=trace.prompt,
                input_payload=trace.input_payload,
                output_payload=trace.output_payload,
                tokens_in=trace.tokens_in,
                tokens_out=trace.tokens_out,
                cost_usd=trace.cost_usd,
                latency_ms=trace.latency_ms,
                langsmith_run_id=trace.langsmith_run_id,
                decision_meta=trace.decision_meta,
                started_at=trace.started_at,
                completed_at=trace.completed_at,
                created_at=trace.created_at,
            )
        )
        await self._session.commit()

    async def get_timeline(self, run_id: UUID) -> list[AgentTrace]:
        result = await self._session.execute(
            select(models.AgentTrace)
            .where(models.AgentTrace.task_run_id == run_id)
            .order_by(models.AgentTrace.sequence_no)
        )
        return [_trace_from_model(trace) for trace in result.scalars().all()]

    async def save_report(self, report: Report, task_id: UUID) -> None:
        assert_report_sources_resolvable(
            sources=report.sources,
            claims=report.claims,
            structured_content=report.structured_content,
        )
        embedding_service = EmbeddingService(get_settings())
        report_embedding, source_embeddings, claim_embeddings = await _report_embeddings(
            report,
            embedding_service,
        )
        for source in report.sources:
            await self._session.merge(
                models.SourceCitation(
                    id=source.id,
                    task_id=task_id,
                    type=source.type,
                    category=source.category,
                    url=str(source.url) if source.url else None,
                    title=source.title,
                    snippet=source.snippet,
                    raw_content=source.raw_content,
                    provider=source.provider,
                    valid=source.valid,
                    fetched_at=source.fetched_at,
                    fetched_by_agent="CollectorAgent",
                )
            )
        await self._session.merge(
            models.Report(
                id=report.id,
                task_id=task_id,
                structured_content=report.structured_content,
                markdown_content=report.markdown_content,
                language=report.language,
                qa_status=report.qa_status,
                qa_issues=report.qa_issues,
                metrics=report.metrics.model_dump(mode="json"),
                created_at=report.created_at,
            )
        )
        for claim in report.claims:
            await self._session.merge(
                models.ReportClaim(
                    id=claim.id,
                    report_id=report.id,
                    claim_path=claim.claim_path,
                    claim_text=claim.claim_text,
                    layer=claim.layer,
                    field_type=claim.field_type,
                    source_ids=claim.source_ids,
                    generating_agent=claim.generating_agent,
                    qa_status=claim.qa_status,
                    source_support=claim.source_support,
                    validity=claim.validity,
                    edit_status=claim.edit_status,
                    review_status=claim.review_status,
                    correction_type=claim.correction_type,
                )
            )
        await self._session.commit()
        await self._write_embeddings(
            report=report,
            report_embedding=report_embedding,
            source_embeddings=source_embeddings,
            claim_embeddings=claim_embeddings,
        )

    async def get_report_by_task(
        self,
        task_id: UUID,
        *,
        user_id: UUID | None = None,
    ) -> Report | None:
        statement = select(models.Report).join(models.Task).where(models.Report.task_id == task_id)
        if user_id is not None:
            statement = statement.where(models.Task.user_id == user_id)
        report_result = await self._session.execute(
            statement
            .order_by(models.Report.created_at.desc())
            .limit(1)
        )
        report = report_result.scalar_one_or_none()
        if report is None:
            return None
        return await self._report_from_model(report)

    async def search_reports(
        self,
        query: str,
        *,
        limit: int = 10,
        user_id: UUID | None = None,
    ) -> ReportSearchBackendResult:
        if query.strip():
            reports = await self._search_reports_pgvector(query, limit=limit, user_id=user_id)
            if reports:
                return ReportSearchBackendResult(mode="pgvector", reports=reports)
        reports = await self._search_reports_keyword(query, limit=limit, user_id=user_id)
        return ReportSearchBackendResult(mode="in_memory_semantic_fallback", reports=reports)

    async def _search_reports_keyword(
        self,
        query: str,
        *,
        limit: int = 10,
        user_id: UUID | None = None,
    ) -> list[Report]:
        terms = tokenize_report_query(query)
        statement = select(models.Report).join(models.Task)
        if user_id is not None:
            statement = statement.where(models.Task.user_id == user_id)
        if not terms:
            result = await self._session.execute(
                statement.order_by(models.Report.created_at.desc()).limit(limit)
            )
            return [await self._report_from_model(report) for report in result.scalars().all()]

        patterns = [f"%{term}%" for term in terms]
        claim_conditions = [
            models.ReportClaim.claim_text.ilike(pattern) for pattern in patterns
        ]
        source_conditions = [
            column.ilike(pattern)
            for pattern in patterns
            for column in (
                models.SourceCitation.title,
                models.SourceCitation.snippet,
                models.SourceCitation.raw_content,
            )
        ]
        report_conditions = [
            column.ilike(pattern)
            for pattern in patterns
            for column in (
                models.Report.markdown_content,
                models.Report.structured_content.cast(Text),
            )
        ]
        matching_claim_report_ids = select(models.ReportClaim.report_id).where(
            or_(*claim_conditions)
        )
        matching_source_task_ids = select(models.SourceCitation.task_id).where(
            or_(*source_conditions)
        )
        result = await self._session.execute(
            statement.where(
                or_(
                    *report_conditions,
                    models.Report.id.in_(matching_claim_report_ids),
                    models.Report.task_id.in_(matching_source_task_ids),
                )
            )
            .order_by(models.Report.created_at.desc())
        )
        reports = [await self._report_from_model(report) for report in result.scalars().all()]
        return rank_reports_for_query(reports, query, limit=limit, require_match=True)

    async def _search_reports_pgvector(
        self,
        query: str,
        *,
        limit: int = 10,
        user_id: UUID | None = None,
    ) -> list[Report]:
        try:
            query_embedding = await EmbeddingService(get_settings()).embed_text(query)
            user_filter = "AND tasks.user_id = :user_id" if user_id is not None else ""
            result = await self._session.execute(
                text(
                    f"""
                    WITH ranked_reports AS (
                        SELECT reports.id AS report_id,
                               reports.embedding <=> CAST(:embedding AS vector) AS score
                        FROM reports
                        JOIN tasks ON tasks.id = reports.task_id
                        WHERE reports.embedding IS NOT NULL
                        {user_filter}
                        UNION ALL
                        SELECT report_claims.report_id,
                               MIN(report_claims.embedding <=> CAST(:embedding AS vector)) AS score
                        FROM report_claims
                        JOIN reports ON reports.id = report_claims.report_id
                        JOIN tasks ON tasks.id = reports.task_id
                        WHERE report_claims.embedding IS NOT NULL
                        {user_filter}
                        GROUP BY report_claims.report_id
                    )
                    SELECT report_id
                    FROM ranked_reports
                    GROUP BY report_id
                    ORDER BY MIN(score)
                    LIMIT :limit
                    """
                ),
                {"embedding": vector_literal(query_embedding), "limit": limit, "user_id": user_id},
            )
            reports: list[Report] = []
            for row in result.all():
                report = await self._session.get(models.Report, row.report_id)
                if report is not None:
                    reports.append(await self._report_from_model(report))
            return rank_reports_for_query(reports, query, limit=limit, require_match=False)
        except SQLAlchemyError:
            logger.warning("pgvector_search_failed_falling_back_to_keyword", exc_info=True)
            await self._session.rollback()
            return []

    async def _write_embeddings(
        self,
        *,
        report: Report,
        report_embedding: list[float],
        source_embeddings: dict[str, list[float]],
        claim_embeddings: dict[UUID, list[float]],
    ) -> None:
        try:
            await self._session.execute(
                text("UPDATE reports SET embedding = CAST(:embedding AS vector) WHERE id = :id"),
                {"id": report.id, "embedding": vector_literal(report_embedding)},
            )
            for source_id, embedding in source_embeddings.items():
                await self._session.execute(
                    text(
                        "UPDATE source_citations "
                        "SET embedding = CAST(:embedding AS vector) "
                        "WHERE id = :id"
                    ),
                    {"id": source_id, "embedding": vector_literal(embedding)},
                )
            for claim_id, embedding in claim_embeddings.items():
                await self._session.execute(
                    text(
                        "UPDATE report_claims "
                        "SET embedding = CAST(:embedding AS vector) "
                        "WHERE id = :id"
                    ),
                    {"id": claim_id, "embedding": vector_literal(embedding)},
                )
            await self._session.commit()
        except SQLAlchemyError:
            # Report/claims already committed above; embeddings are best-effort and
            # backfillable, so a failure here must not roll back the saved report.
            logger.warning("embedding_write_failed_report_saved_without_vectors", exc_info=True)
            await self._session.rollback()

    async def _report_from_model(self, report: models.Report) -> Report:
        sources_result = await self._session.execute(
            select(models.SourceCitation).where(models.SourceCitation.task_id == report.task_id)
        )
        claims_result = await self._session.execute(
            select(models.ReportClaim).where(models.ReportClaim.report_id == report.id)
        )
        return Report(
            id=report.id,
            task_id=report.task_id,
            language=report.language,
            structured_content=report.structured_content,
            markdown_content=report.markdown_content,
            sources=[_source_from_model(source) for source in sources_result.scalars().all()],
            claims=[_claim_from_model(claim) for claim in claims_result.scalars().all()],
            metrics=ReportMetrics.model_validate(report.metrics),
            qa_status=report.qa_status,
            qa_issues=report.qa_issues,
            created_at=report.created_at,
        )


def _trace_from_model(trace: models.AgentTrace) -> AgentTrace:
    return AgentTrace(
        id=trace.id,
        task_run_id=trace.task_run_id,
        sequence_no=trace.sequence_no,
        agent_name=trace.agent_name,
        node_name=trace.node_name,
        status=trace.status,
        prompt=trace.prompt,
        input_payload=trace.input_payload,
        output_payload=trace.output_payload,
        tokens_in=trace.tokens_in,
        tokens_out=trace.tokens_out,
        cost_usd=float(trace.cost_usd),
        latency_ms=trace.latency_ms,
        langsmith_run_id=trace.langsmith_run_id,
        decision_meta=trace.decision_meta,
        started_at=trace.started_at,
        completed_at=trace.completed_at,
        created_at=trace.created_at,
    )


def _run_from_model(
    run: models.TaskRun,
    *,
    user_id: UUID | None = None,
    competitor_names: object = None,
) -> RunRecord:
    return RunRecord(
        id=run.id,
        task_id=run.task_id,
        user_id=user_id,
        status=run.status,
        retry_count=run.retry_count,
        error_summary=run.error_summary,
        started_at=run.started_at,
        completed_at=run.completed_at,
        competitors=competitor_names_from_items(competitor_names),
    )


def _source_from_model(source: models.SourceCitation) -> SourceCitation:
    return SourceCitation(
        id=source.id,
        type=source.type,
        category=source.category,
        url=source.url,
        title=source.title,
        snippet=source.snippet,
        raw_content=source.raw_content,
        provider=source.provider,
        fetched_at=source.fetched_at,
        valid=source.valid,
    )


def _claim_from_model(claim: models.ReportClaim) -> ReportClaim:
    return ReportClaim(
        id=claim.id,
        claim_path=claim.claim_path,
        claim_text=claim.claim_text,
        layer=claim.layer,
        field_type=claim.field_type,
        source_ids=claim.source_ids,
        generating_agent=claim.generating_agent,
        qa_status=claim.qa_status,
        source_support=claim.source_support,
        validity=claim.validity,
        edit_status=claim.edit_status,
        review_status=claim.review_status,
        correction_type=claim.correction_type,
    )


async def _report_embeddings(
    report: Report,
    embedding_service: EmbeddingService,
) -> tuple[list[float], dict[str, list[float]], dict[UUID, list[float]]]:
    source_texts = [_source_embedding_text(source) for source in report.sources]
    claim_texts = [claim.claim_text for claim in report.claims]
    embeddings = await embedding_service.embed_texts(
        [_report_embedding_text(report), *source_texts, *claim_texts]
    )
    report_embedding = embeddings[0]
    source_embeddings = {
        source.id: embedding
        for source, embedding in zip(
            report.sources,
            embeddings[1 : 1 + len(report.sources)],
            strict=True,
        )
    }
    claim_start = 1 + len(report.sources)
    claim_embeddings = {
        claim.id: embedding
        for claim, embedding in zip(report.claims, embeddings[claim_start:], strict=True)
    }
    return report_embedding, source_embeddings, claim_embeddings


def _report_embedding_text(report: Report) -> str:
    title = str(report.structured_content.get("title") or "")
    summary = str(report.structured_content.get("summary") or "")
    competitors = " ".join(str(item) for item in report.structured_content.get("competitors") or [])
    return "\n".join([title, summary, competitors, report.markdown_content[:6000]])


def _source_embedding_text(source: SourceCitation) -> str:
    return "\n".join(
        [
            source.title,
            source.snippet,
            source.raw_content or "",
            source.category,
        ]
    )
