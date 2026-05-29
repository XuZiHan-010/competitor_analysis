from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import models
from schemas.report import Report, ReportClaim, ReportMetrics
from schemas.scope import TaskScopeContract
from schemas.source import SourceCitation
from schemas.traces import AgentTrace
from services.runs.manager import RunRecord


class RunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ensure_task(self, scope_contract: TaskScopeContract) -> None:
        task = await self._session.get(models.Task, scope_contract.id)
        if task is not None:
            return
        self._session.add(
            models.Task(
                id=scope_contract.id,
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

    async def get_run(self, run_id: UUID) -> RunRecord | None:
        run = await self._session.get(models.TaskRun, run_id)
        if run is None:
            return None
        return RunRecord(
            id=run.id,
            task_id=run.task_id,
            status=run.status,
            retry_count=run.retry_count,
            error_summary=run.error_summary,
            started_at=run.started_at,
            completed_at=run.completed_at,
        )

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

    async def get_report_by_task(self, task_id: UUID) -> Report | None:
        report_result = await self._session.execute(
            select(models.Report)
            .where(models.Report.task_id == task_id)
            .order_by(models.Report.created_at.desc())
            .limit(1)
        )
        report = report_result.scalar_one_or_none()
        if report is None:
            return None
        return await self._report_from_model(report)

    async def search_reports(self, query: str, *, limit: int = 10) -> list[Report]:
        term = f"%{query}%"
        result = await self._session.execute(
            select(models.Report)
            .where(models.Report.markdown_content.ilike(term))
            .order_by(models.Report.created_at.desc())
            .limit(limit)
        )
        return [await self._report_from_model(report) for report in result.scalars().all()]

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
