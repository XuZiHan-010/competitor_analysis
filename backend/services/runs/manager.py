import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime
from typing import Any, Literal, Protocol
from uuid import UUID, uuid4

import structlog
from pydantic import BaseModel, Field

from graph.state import WorkflowState
from graph.workflow import WORKFLOW_DEADLINE_S, run_workflow
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


def _stage_hint_from_traces(traces: list[AgentTrace]) -> str:
    if not traces:
        return "workflow"
    latest = max(traces, key=lambda trace: trace.sequence_no)
    if latest.agent_name == "QAAgent" and latest.status == "succeeded":
        return "write"
    if latest.agent_name == "AnalystAgent" and latest.status == "succeeded":
        return "qa_check"
    if latest.agent_name == "CollectorAgent" and latest.status == "succeeded":
        return "analyze"
    if latest.agent_name == "WriterAgent":
        return "write"
    return latest.node_name


def _timeout_error_summary(exc: BaseException, traces: list[AgentTrace]) -> dict[str, Any]:
    stage_hint = _stage_hint_from_traces(traces)
    minutes = round(WORKFLOW_DEADLINE_S / 60)
    return {
        "exception_class": exc.__class__.__name__,
        "message": f"运行超过 {minutes} 分钟预算，最后已知阶段：{stage_hint}。",
        "stage_hint": stage_hint,
        "deadline_seconds": WORKFLOW_DEADLINE_S,
    }


async def _open_postgres_saver(dsn: str) -> tuple[Any, Any] | None:
    """Open a liveness-checked pool + AsyncPostgresSaver, or None on setup failure.

    Uses a connection pool rather than ``from_conn_string``'s single bare
    connection: workflow nodes idle for tens of seconds between checkpoint
    writes while LLMs run, long enough for Neon's pooler to recycle a lone
    connection - the next ``aput_writes`` then hits "the connection is closed".
    The pool re-checks liveness on checkout and reconnects. ``prepare_threshold=
    None`` is required because pgbouncer transaction pooling can't keep psycopg's
    prepared statements alive.
    """
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from psycopg import AsyncConnection
        from psycopg.rows import DictRow, dict_row
        from psycopg_pool import AsyncConnectionPool

        pool: AsyncConnectionPool[AsyncConnection[DictRow]] = AsyncConnectionPool(
            conninfo=dsn,
            min_size=1,
            max_size=4,
            open=False,
            kwargs={
                "autocommit": True,
                "prepare_threshold": None,
                "row_factory": dict_row,
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5,
            },
            check=AsyncConnectionPool.check_connection,
        )
        await pool.open(wait=True, timeout=10)
        saver = AsyncPostgresSaver(pool)
        await saver.setup()
        return pool, saver
    except Exception:
        logger.warning("postgres_checkpointer_unavailable_using_memory", exc_info=True)
        return None


@asynccontextmanager
async def _checkpointer_ctx() -> AsyncIterator[Any]:
    """Yield the configured LangGraph checkpointer for one live workflow run.

    Memory is the default because final workflow states can contain large scraped
    payloads; Postgres checkpointing is opt-in for debugging/resume work after
    the checkpoint state is trimmed.
    """
    settings = get_settings()
    if settings.workflow_checkpointer != "postgres" or not settings.database_url:
        from langgraph.checkpoint.memory import MemorySaver

        logger.info(
            "workflow_checkpointer_memory",
            configured=settings.workflow_checkpointer,
            database_configured=bool(settings.database_url),
        )
        yield MemorySaver()
        return

    opened = await _open_postgres_saver(settings.database_url)
    if opened is None:
        from langgraph.checkpoint.memory import MemorySaver

        logger.info("workflow_checkpointer_fallback_memory")
        yield MemorySaver()
        return
    pool, saver = opened
    try:
        yield saver
    finally:
        try:
            await pool.close()
        except Exception:
            # pool.close() can raise if a checkpoint write was in-flight when the
            # workflow was cancelled (e.g. asyncio.wait_for timeout).  Log and
            # swallow so the original TimeoutError is not masked by a secondary
            # connection-already-closed error.
            logger.warning("checkpointer_pool_close_on_cancel", exc_info=True)


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

    async def publish_event(self, event: str, data: dict[str, Any]) -> None:
        await self._bridge.publish(str(self.run_id), event, data)


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
        enabled_dimensions = [
            {
                "id": dimension.id,
                "title": dimension.title,
                "layer": dimension.layer,
                "source": dimension.source,
            }
            for dimension in scope_contract.dimensions
            if dimension.enabled
        ]
        # Full dimension table (incl. disabled) so a missing/disabled extension
        # dimension can be told apart from one the frontend silently re-sent.
        all_dimensions = [
            {
                "id": dimension.id,
                "title": dimension.title,
                "layer": dimension.layer,
                "enabled": dimension.enabled,
            }
            for dimension in scope_contract.dimensions
        ]
        logger.info(
            "task_scope_frozen",
            task_id=task_id,
            competitors=competitor_names_from_scope(scope_contract),
            enabled_dimensions=enabled_dimensions,
            all_dimensions=all_dimensions,
        )
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
        # FastAPI BackgroundTasks scheduling - which the test suite relies on for
        # synchronous completion - stays intact.
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
            try:
                await self._bridge.cleanup(str(sibling_id))
            except Exception:
                logger.warning("stream_cleanup_failed", run_id=sibling_id, exc_info=True)
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
            report_language=get_settings().report_language,
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
                logger.info(
                    "workflow_returned",
                    run_id=run_id,
                    task_id=record.task_id,
                    has_report=result.report is not None,
                )
        except Exception as exc:
            logger.exception(
                "run_failed",
                run_id=run_id,
                task_id=record.task_id,
                exception_class=exc.__class__.__name__,
            )
            record.status = "failed"
            traces = await self.get_timeline(run_id)
            record.error_summary = (
                _timeout_error_summary(exc, traces)
                if isinstance(exc, TimeoutError)
                else {
                    "exception_class": exc.__class__.__name__,
                    "message": str(exc),
                }
            )
            record.completed_at = datetime.now(UTC)
            if self._persistence is not None:
                try:
                    await self._persist_traces(run_id)
                    await self._persistence.update_run(record)
                except Exception:
                    logger.warning(
                        "db_unavailable_persist_failed_run", run_id=run_id, exc_info=True
                    )  # noqa: E501
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
            logger.info(
                "report_saved_memory",
                run_id=run_id,
                task_id=result.task_id,
                report_id=result.report.id,
            )
            if self._persistence is not None:
                try:
                    await self._persistence.save_report(result.report, result.task_id)
                    logger.info(
                        "report_saved_db",
                        run_id=run_id,
                        task_id=result.task_id,
                        report_id=result.report.id,
                    )
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
        logger.info(
            "run_terminal_published",
            run_id=run_id,
            task_id=result.task_id,
            status=record.status,
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
