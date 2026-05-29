from collections.abc import Awaitable, Callable
from typing import TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from db.repositories import RunRepository
from schemas.report import Report
from schemas.scope import TaskScopeContract
from schemas.traces import AgentTrace
from services.runs.manager import RunRecord

T = TypeVar("T")


class SqlRunPersistence:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sessionmaker = sessionmaker

    async def ensure_task(self, scope_contract: TaskScopeContract) -> None:
        await self._with_repo(lambda repo: repo.ensure_task(scope_contract))

    async def create_run(self, record: RunRecord) -> None:
        await self._with_repo(lambda repo: repo.create_run(record))

    async def update_run(self, record: RunRecord) -> None:
        await self._with_repo(lambda repo: repo.update_run(record))

    async def add_trace(self, trace: AgentTrace) -> None:
        await self._with_repo(lambda repo: repo.add_trace(trace))

    async def get_run(self, run_id: UUID) -> RunRecord | None:
        return await self._with_repo_result(lambda repo: repo.get_run(run_id))

    async def get_timeline(self, run_id: UUID) -> list[AgentTrace]:
        return await self._with_repo_result(lambda repo: repo.get_timeline(run_id))

    async def get_report(self, task_id: UUID) -> Report | None:
        return await self._with_repo_result(lambda repo: repo.get_report_by_task(task_id))

    async def search_reports(self, query: str, *, limit: int = 10) -> list[Report]:
        return await self._with_repo_result(lambda repo: repo.search_reports(query, limit=limit))

    async def save_report(self, report: Report, task_id: UUID) -> None:
        await self._with_repo(lambda repo: repo.save_report(report, task_id))

    async def _with_repo(self, call: Callable[[RunRepository], Awaitable[None]]) -> None:
        async with self._sessionmaker() as session:
            await call(RunRepository(session))

    async def _with_repo_result(self, call: Callable[[RunRepository], Awaitable[T]]) -> T:
        async with self._sessionmaker() as session:
            return await call(RunRepository(session))
