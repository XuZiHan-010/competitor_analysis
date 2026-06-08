import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime
from typing import Any, Literal, Protocol
from uuid import UUID, uuid4

import structlog
from pydantic import BaseModel, Field

from graph.state import WorkflowState
from graph.workflow import run_workflow
from schemas.report import Report, ReportSearchBackendResult
from schemas.scope import ScopingDraft, TaskScopeContract
from schemas.survey import SurveyEvidence
from schemas.traces import AgentTrace
from services.metrics import calculate_report_metrics
from services.report_search import competitor_names_from_scope
from services.storage import InMemoryStore
from services.streaming.bridge import StreamBridge
from settings import get_settings

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def _checkpointer_ctx() -> AsyncIterator[Any]:
    """Yield an AsyncPostgresSaver when DATABASE_URL is configured, else MemorySaver.

    A configured-but-unreachable Postgres is logged as a warning (the run still
    proceeds on an in-memory checkpointer, but state will not survive a restart);
    an unconfigured DATABASE_URL is the expected dev path and stays silent.
    """
    settings = get_settings()
    if settings.database_url:
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

            async with AsyncPostgresSaver.from_conn_string(settings.database_url) as saver:
                await saver.setup()
                yield saver
                return
        except Exception:
            logger.warning("postgres_checkpointer_unavailable_using_memory", exc_info=True)
    from langgraph.checkpoint.memory import MemorySaver

    yield MemorySaver()


class RunRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    user_id: UUID | None = None
    status: Literal["pending", "running", "succeeded", "failed", "cancelled"] = "pending"
    retry_count: int = 0
    error_summary: dict | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    competitors: list[str] = Field(default_factory=list)


class RunPersistence(Protocol):
    async def upsert_user(self, email: str) -> UUID: ...

    async def ensure_task(
        self,
        scope_contract: TaskScopeContract,
        *,
        user_id: UUID,
        user_email: str,
    ) -> None: ...

    async def create_run(self, record: RunRecord) -> None: ...

    async def update_run(self, record: RunRecord) -> None: ...

    async def add_trace(self, trace: AgentTrace) -> None: ...

    async def save_report(self, report: Report, task_id: UUID) -> None: ...

    async def delete_task(self, task_id: UUID) -> None: ...

    async def get_run(self, run_id: UUID) -> RunRecord | None: ...

    async def get_task_owner(self, task_id: UUID) -> UUID | None: ...

    async def list_runs(
        self,
        limit: int = 50,
        *,
        user_id: UUID | None = None,
    ) -> list[RunRecord]: ...

    async def get_timeline(self, run_id: UUID) -> list[AgentTrace]: ...

    async def get_report(self, task_id: UUID, *, user_id: UUID | None = None) -> Report | None: ...

    async def search_reports(
        self,
        query: str,
        *,
        limit: int = 10,
        user_id: UUID | None = None,
    ) -> ReportSearchBackendResult: ...


class RunTraceContext:
    def __init__(self, run_id: UUID, store: InMemoryStore, bridge: StreamBridge) -> None:
        self.run_id = run_id
        self._store = store
        self._bridge = bridge

    def next_sequence(self) -> int:
        return self._store.next_trace_sequence(self.run_id)

    def record_trace(self, trace: AgentTrace) -> None:
        self._store.add_trace(trace)

    async def publish_trace(self, trace: AgentTrace) -> None:
        event = "node.failed" if trace.status == "failed" else "node.succeeded"
        await self._bridge.publish(
            str(self.run_id),
            event,
            trace.model_dump(mode="json"),
        )


class RunManager:
    def __init__(
        self,
        store: InMemoryStore,
        bridge: StreamBridge,
        persistence: RunPersistence | None = None,
    ) -> None:
        self._store = store
        self._bridge = bridge
        self._persistence = persistence
        self._runs: dict[UUID, RunRecord] = {}
        self._tasks: dict[UUID, asyncio.Task[None]] = {}

    async def start_run(
        self,
        scope_contract: TaskScopeContract,
        *,
        user_id: UUID,
        user_email: str,
    ) -> RunRecord:
        task_id = scope_contract.id
        owner = await self.get_task_owner(task_id)
        if owner is not None and owner != user_id:
            raise PermissionError("task belongs to another user")
        self._store.task_scopes[task_id] = scope_contract
        self._store.task_owner[task_id] = user_id
        if self._persistence is not None:
            try:
                await self._persistence.ensure_task(
                    scope_contract,
                    user_id=user_id,
                    user_email=user_email,
                )
            except Exception:
                logger.warning("db_unavailable_ensure_task", task_id=task_id, exc_info=True)
        record = RunRecord(
            task_id=task_id,
            user_id=user_id,
            competitors=competitor_names_from_scope(scope_contract),
        )
        self._runs[record.id] = record
        if self._persistence is not None:
            try:
                await self._persistence.create_run(record)
            except Exception:
                logger.warning("db_unavailable_create_run", run_id=record.id, exc_info=True)
        return record

    async def execute_run(self, run_id: UUID, state: WorkflowState) -> None:
        # Register the running task so a delete can cancel an in-flight DAG.
        # current_task() is captured here (rather than via create_task) so the
        # FastAPI BackgroundTasks scheduling — which the test suite relies on for
        # synchronous completion — stays intact.
        current = asyncio.current_task()
        if current is not None:
            self._tasks[run_id] = current
        try:
            await self._execute(run_id, state)
        finally:
            self._tasks.pop(run_id, None)

    async def delete_run(self, run_id: UUID, *, user_id: UUID) -> bool:
        run = await self.get_run(run_id)
        if run is None or run.user_id != user_id:
            return False
        task = self._tasks.pop(run_id, None)
        if task is not None and not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        task_id = run.task_id
        for sibling_id in [rid for rid, r in self._runs.items() if r.task_id == task_id]:
            self._runs.pop(sibling_id, None)
            self._store.traces_by_run.pop(sibling_id, None)
        self._store.task_scopes.pop(task_id, None)
        self._store.task_owner.pop(task_id, None)
        self._store.task_reports.pop(task_id, None)
        self._store.scoping_drafts.pop(task_id, None)
        self._store.survey_uploads.pop(task_id, None)
        if self._persistence is not None:
            try:
                await self._persistence.delete_task(task_id)
            except Exception:
                logger.warning("db_unavailable_delete_task", task_id=task_id, exc_info=True)
        return True

    def build_initial_state(
        self,
        record: RunRecord,
        scope_contract: TaskScopeContract,
        *,
        force_feedback_demo: bool = False,
    ) -> WorkflowState:
        return WorkflowState(
            task_id=scope_contract.id,
            run_id=record.id,
            scope_contract=scope_contract,
            uploaded_survey_evidence=list(self._store.survey_uploads.get(scope_contract.id, [])),
            feedback_signals={"force_pricing_blocker": force_feedback_demo},
        )

    async def get_run(self, run_id: UUID) -> RunRecord | None:
        run = self._runs.get(run_id)
        if run is not None:
            return self._with_scope_competitors(run)
        if self._persistence is not None:
            try:
                return await self._persistence.get_run(run_id)
            except Exception:
                logger.warning("db_unavailable_get_run", run_id=run_id, exc_info=True)
        return None

    async def list_runs(self, limit: int = 50, *, user_id: UUID | None = None) -> list[RunRecord]:
        _epoch = datetime.min.replace(tzinfo=UTC)
        runs_by_id = {
            run_id: run
            for run_id, run in self._runs.items()
            if user_id is None or run.user_id == user_id
        }
        if self._persistence is not None:
            try:
                for run in await self._persistence.list_runs(limit=limit, user_id=user_id):
                    runs_by_id.setdefault(run.id, run)
            except Exception:
                logger.warning("db_unavailable_list_runs", exc_info=True)
        runs = sorted(
            (self._with_scope_competitors(run) for run in runs_by_id.values()),
            key=lambda r: r.started_at if r.started_at is not None else _epoch,
            reverse=True,
        )
        return list(runs[:limit])

    async def get_report(self, task_id: UUID, *, user_id: UUID | None = None) -> Report | None:
        if user_id is not None and await self.get_task_owner(task_id) != user_id:
            return None
        if self._persistence is not None:
            try:
                report = await self._persistence.get_report(task_id, user_id=user_id)
                if report is not None:
                    self._store.update_report(report)
                    return report
            except Exception:
                logger.warning("db_unavailable_get_report", task_id=task_id, exc_info=True)
        return self._store.task_reports.get(task_id)

    async def update_report(self, report: Report) -> None:
        self._store.update_report(report)
        if self._persistence is not None:
            await self._persistence.save_report(report, report.task_id)

    def add_survey_upload(self, task_id: UUID, evidence: list[SurveyEvidence]) -> None:
        self._store.survey_uploads[task_id].extend(evidence)

    def save_scoping_draft(self, draft: ScopingDraft, *, user_id: UUID) -> None:
        self._store.scoping_drafts[draft.scope_contract.id] = draft
        self._store.task_scopes[draft.scope_contract.id] = draft.scope_contract
        self._store.task_owner[draft.scope_contract.id] = user_id

    def get_scoping_draft(
        self,
        task_id: UUID,
        *,
        user_id: UUID | None = None,
    ) -> ScopingDraft | None:
        if user_id is not None and self._store.task_owner.get(task_id) != user_id:
            return None
        return self._store.scoping_drafts.get(task_id)

    def get_scope_contract(self, task_id: UUID) -> TaskScopeContract | None:
        return self._store.task_scopes.get(task_id)

    async def search_reports(
        self,
        query: str,
        *,
        limit: int = 10,
        user_id: UUID | None = None,
    ) -> ReportSearchBackendResult:
        if self._persistence is not None:
            try:
                result = await self._persistence.search_reports(query, limit=limit, user_id=user_id)
                if result.reports:
                    for report in result.reports:
                        self._store.update_report(report)
                    return result
            except Exception:
                logger.warning("db_unavailable_search_reports", exc_info=True)
        return ReportSearchBackendResult(
            mode="in_memory_semantic_fallback",
            reports=self._store.search_reports(query, limit=limit, user_id=user_id),
        )

    async def get_timeline(self, run_id: UUID) -> list[AgentTrace]:
        traces = sorted(self._store.traces_by_run[run_id], key=lambda trace: trace.sequence_no)
        if traces:
            return traces
        if self._persistence is not None:
            try:
                return await self._persistence.get_timeline(run_id)
            except Exception:
                logger.warning("db_unavailable_get_timeline", run_id=run_id, exc_info=True)
        return []

    async def recompute_report_metrics(self, report: Report) -> Report:
        updated = report.model_copy(
            update={
                "metrics": calculate_report_metrics(
                    claims=report.claims,
                    sources=report.sources,
                    analysis_duration_seconds=report.metrics.analysis_duration_seconds,
                    rerun_count=1 if report.metrics.rerun_rate else 0,
                    ai_self_assessment=report.metrics.ai_self_assessment,
                )
            },
            deep=True,
        )
        await self.update_report(updated)
        return updated

    async def _execute(self, run_id: UUID, state: WorkflowState) -> None:
        record = self._runs[run_id]
        record.status = "running"
        record.started_at = datetime.now(UTC)
        if self._persistence is not None:
            try:
                await self._persistence.update_run(record)
            except Exception:
                logger.warning("db_unavailable_update_run_started", run_id=run_id, exc_info=True)
        await self._bridge.publish(str(run_id), "run.started", {"task_id": str(record.task_id)})
        try:
            async with _checkpointer_ctx() as checkpointer:
                result = await run_workflow(
                    state,
                    trace_context=RunTraceContext(
                        run_id=run_id,
                        store=self._store,
                        bridge=self._bridge,
                    ),
                    checkpointer=checkpointer,
                )
        except Exception as exc:
            record.status = "failed"
            record.error_summary = {
                "exception_class": exc.__class__.__name__,
                "message": str(exc),
            }
            record.completed_at = datetime.now(UTC)
            if self._persistence is not None:
                try:
                    await self._persist_traces(run_id)
                    await self._persistence.update_run(record)
                except Exception:
                    logger.warning("db_unavailable_persist_failed_run", run_id=run_id, exc_info=True)  # noqa: E501
            await self._bridge.publish(str(run_id), "run.failed", record.error_summary)
            return
        if result.qa_result and not result.qa_result.passed:
            await self._bridge.publish(
                str(run_id),
                "qa.blocker",
                {"issues": [issue.model_dump(mode="json") for issue in result.qa_result.issues]},
            )
        record.status = "succeeded"
        record.retry_count = result.retry_counts.get("collector", 0)
        record.completed_at = datetime.now(UTC)
        if result.report is not None:
            result.report.metrics.analysis_duration_seconds = (
                record.completed_at - (record.started_at or record.completed_at)
            ).total_seconds()
            self._store.task_reports[result.task_id] = result.report
            if self._persistence is not None:
                try:
                    await self._persistence.save_report(result.report, result.task_id)
                except Exception:
                    logger.warning("db_unavailable_save_report", run_id=run_id, exc_info=True)
        if self._persistence is not None:
            try:
                await self._persist_traces(run_id)
                await self._persistence.update_run(record)
            except Exception:
                logger.warning("db_unavailable_persist_succeeded_run", run_id=run_id, exc_info=True)
        await self._bridge.publish(
            str(run_id),
            "run.succeeded",
            {
                "task_id": str(result.task_id),
                "report_id": str(result.report.id if result.report else ""),
            },
        )

    async def _persist_traces(self, run_id: UUID) -> None:
        if self._persistence is None:
            return
        for trace in await self.get_timeline(run_id):
            await self._persistence.add_trace(trace)

    async def get_task_owner(self, task_id: UUID) -> UUID | None:
        owner = self._store.task_owner.get(task_id)
        if owner is not None:
            return owner
        if self._persistence is not None:
            try:
                owner = await self._persistence.get_task_owner(task_id)
                if owner is not None:
                    self._store.task_owner[task_id] = owner
                return owner
            except Exception:
                logger.warning("db_unavailable_get_task_owner", task_id=task_id, exc_info=True)
        return None

    def _with_scope_competitors(self, run: RunRecord) -> RunRecord:
        if run.competitors:
            return run
        competitors = competitor_names_from_scope(self._store.task_scopes.get(run.task_id))
        if not competitors:
            return run
        return run.model_copy(update={"competitors": competitors})
