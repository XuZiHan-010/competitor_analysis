from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, Literal, Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from graph.state import WorkflowState
from graph.workflow import run_workflow
from schemas.report import Report
from schemas.scope import ScopingDraft, TaskScopeContract
from schemas.survey import SurveyEvidence
from schemas.traces import AgentTrace
from services.metrics import calculate_report_metrics
from services.storage import InMemoryStore
from services.streaming.bridge import StreamBridge
from settings import get_settings


@asynccontextmanager
async def _checkpointer_ctx() -> AsyncIterator[Any]:
    """Yield an AsyncPostgresSaver when DATABASE_URL is configured, else MemorySaver."""
    settings = get_settings()
    if settings.database_url:
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

            async with AsyncPostgresSaver.from_conn_string(settings.database_url) as saver:
                await saver.setup()
                yield saver
                return
        except Exception:
            pass
    from langgraph.checkpoint.memory import MemorySaver

    yield MemorySaver()


class RunRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    status: Literal["pending", "running", "succeeded", "failed", "cancelled"] = "pending"
    retry_count: int = 0
    error_summary: dict | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class RunPersistence(Protocol):
    async def ensure_task(self, scope_contract: TaskScopeContract) -> None: ...

    async def create_run(self, record: RunRecord) -> None: ...

    async def update_run(self, record: RunRecord) -> None: ...

    async def add_trace(self, trace: AgentTrace) -> None: ...

    async def save_report(self, report: Report, task_id: UUID) -> None: ...

    async def get_run(self, run_id: UUID) -> RunRecord | None: ...

    async def get_timeline(self, run_id: UUID) -> list[AgentTrace]: ...

    async def get_report(self, task_id: UUID) -> Report | None: ...

    async def search_reports(self, query: str, *, limit: int = 10) -> list[Report]: ...


class RunTraceContext:
    def __init__(self, run_id: UUID, store: InMemoryStore) -> None:
        self.run_id = run_id
        self._store = store

    def next_sequence(self) -> int:
        return self._store.next_trace_sequence(self.run_id)

    def record_trace(self, trace: AgentTrace) -> None:
        self._store.add_trace(trace)


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

    async def start_run(
        self,
        scope_contract: TaskScopeContract,
        *,
        force_feedback_demo: bool = False,
    ) -> RunRecord:
        task_id = scope_contract.id
        self._store.task_scopes[task_id] = scope_contract
        if self._persistence is not None:
            await self._persistence.ensure_task(scope_contract)
        record = RunRecord(task_id=task_id)
        self._runs[record.id] = record
        if self._persistence is not None:
            await self._persistence.create_run(record)
        return record

    async def execute_run(self, run_id: UUID, state: WorkflowState) -> None:
        await self._execute(run_id, state)

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
            return run
        if self._persistence is not None:
            return await self._persistence.get_run(run_id)
        return None

    async def get_report(self, task_id: UUID) -> Report | None:
        if self._persistence is not None:
            report = await self._persistence.get_report(task_id)
            if report is not None:
                self._store.update_report(report)
                return report
        return self._store.task_reports.get(task_id)

    async def update_report(self, report: Report) -> None:
        self._store.update_report(report)
        if self._persistence is not None:
            await self._persistence.save_report(report, report.task_id)

    def add_survey_upload(self, task_id: UUID, evidence: list[SurveyEvidence]) -> None:
        self._store.survey_uploads[task_id].extend(evidence)

    def save_scoping_draft(self, draft: ScopingDraft) -> None:
        self._store.scoping_drafts[draft.scope_contract.id] = draft
        self._store.task_scopes[draft.scope_contract.id] = draft.scope_contract

    def get_scoping_draft(self, task_id: UUID) -> ScopingDraft | None:
        return self._store.scoping_drafts.get(task_id)

    async def search_reports(self, query: str, *, limit: int = 10) -> list[Report]:
        if self._persistence is not None:
            reports = await self._persistence.search_reports(query, limit=limit)
            if reports:
                for report in reports:
                    self._store.update_report(report)
                return reports
        return self._store.search_reports(query, limit=limit)

    async def get_timeline(self, run_id: UUID) -> list[AgentTrace]:
        traces = sorted(self._store.traces_by_run[run_id], key=lambda trace: trace.sequence_no)
        if traces:
            return traces
        if self._persistence is not None:
            return await self._persistence.get_timeline(run_id)
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
            await self._persistence.update_run(record)
        await self._bridge.publish(str(run_id), "run.started", {"task_id": str(record.task_id)})
        try:
            async with _checkpointer_ctx() as checkpointer:
                result = await run_workflow(
                    state,
                    trace_context=RunTraceContext(run_id=run_id, store=self._store),
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
                await self._persist_traces(run_id)
                await self._persistence.update_run(record)
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
                await self._persistence.save_report(result.report, result.task_id)
        if self._persistence is not None:
            await self._persist_traces(run_id)
            await self._persistence.update_run(record)
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
