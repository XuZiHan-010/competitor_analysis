from collections import defaultdict
from uuid import UUID

from schemas.report import Report
from schemas.scope import ScopingDraft, TaskScopeContract
from schemas.survey import SurveyEvidence
from schemas.traces import AgentTrace
from services.report_search import rank_reports_for_query


class InMemoryStore:
    def __init__(self) -> None:
        self.scoping_drafts: dict[UUID, ScopingDraft] = {}
        self.task_scopes: dict[UUID, TaskScopeContract] = {}
        self.task_owner: dict[UUID, UUID] = {}
        self.task_reports: dict[UUID, Report] = {}
        self.survey_uploads: dict[UUID, list[SurveyEvidence]] = defaultdict(list)
        self.traces_by_run: dict[UUID, list[AgentTrace]] = defaultdict(list)

    def add_trace(self, trace: AgentTrace) -> None:
        self.traces_by_run[trace.task_run_id].append(trace)

    def next_trace_sequence(self, run_id: UUID) -> int:
        return len(self.traces_by_run[run_id]) + 1

    def update_report(self, report: Report) -> None:
        self.task_reports[report.task_id] = report

    def search_reports(
        self,
        query: str,
        *,
        limit: int = 10,
        user_id: UUID | None = None,
    ) -> list[Report]:
        reports = [
            report
            for report in self.task_reports.values()
            if user_id is None or self.task_owner.get(report.task_id) == user_id
        ]
        return rank_reports_for_query(reports, query, limit=limit, require_match=True)


store = InMemoryStore()
