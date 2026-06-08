from collections.abc import Awaitable, Callable
from typing import TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from db.repositories import RunRepository
from schemas.report import Report, ReportSearchBackendResult
from schemas.scope import TaskScopeContract
from schemas.traces import AgentTrace
from services.runs.manager import RunRecord

T = TypeVar("T")


class SqlRunPersistence:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sessionmaker = sessionmaker

    async def upsert_user(self, email: str) -> UUID:
        return await self._with_repo_result(lambda repo: repo.get_or_create_user(email))

    async def ensure_task(
        self,
        scope_contract: TaskScopeContract,
        *,
        user_id: UUID,
        user_email: str,
    ) -> None:
        await self._with_repo(
            lambda repo: repo.ensure_task(
                scope_contract,
                user_id=user_id,
                user_email=user_email,
            )
        )

    async def create_run(self, record: RunRecord) -> None:
        await self._with_repo(lambda repo: repo.create_run(record))

    async def update_run(self, record: RunRecord) -> None:
        await self._with_repo(lambda repo: repo.update_run(record))

    async def add_trace(self, trace: AgentTrace) -> None:
        await self._with_repo(lambda repo: repo.add_trace(trace))

    async def get_run(self, run_id: UUID) -> RunRecord | None:
        return await self._with_repo_result(lambda repo: repo.get_run(run_id))

    async def get_task_owner(self, task_id: UUID) -> UUID | None:
        return await self._with_repo_result(lambda repo: repo.get_task_owner(task_id))

    async def list_runs(
        self,
        limit: int = 50,
        *,
        user_id: UUID | None = None,
    ) -> list[RunRecord]:
        return await self._with_repo_result(
            lambda repo: repo.list_runs(limit=limit, user_id=user_id)
        )

    async def get_timeline(self, run_id: UUID) -> list[AgentTrace]:
        return await self._with_repo_result(lambda repo: repo.get_timeline(run_id))

    async def get_report(self, task_id: UUID, *, user_id: UUID | None = None) -> Report | None:
        return await self._with_repo_result(
            lambda repo: repo.get_report_by_task(task_id, user_id=user_id)
        )

    async def search_reports(
        self,
        query: str,
        *,
        limit: int = 10,
        user_id: UUID | None = None,
    ) -> ReportSearchBackendResult:
        return await self._with_repo_result(
            lambda repo: repo.search_reports(query, limit=limit, user_id=user_id)
        )

    async def save_report(self, report: Report, task_id: UUID) -> None:
        await self._with_repo(lambda repo: repo.save_report(report, task_id))

    async def delete_task(self, task_id: UUID) -> None:
        await self._with_repo(lambda repo: repo.delete_task(task_id))

    async def _with_repo(self, call: Callable[[RunRepository], Awaitable[None]]) -> None:
        async with self._sessionmaker() as session:
            await call(RunRepository(session))

    async def _with_repo_result(self, call: Callable[[RunRepository], Awaitable[T]]) -> T:
        async with self._sessionmaker() as session:
            return await call(RunRepository(session))
