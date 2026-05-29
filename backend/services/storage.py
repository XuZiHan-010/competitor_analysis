from collections import defaultdict
from uuid import UUID

from schemas.report import Report
from schemas.scope import ScopingDraft, TaskScopeContract
from schemas.survey import SurveyEvidence
from schemas.traces import AgentTrace


class InMemoryStore:
    def __init__(self) -> None:
        self.scoping_drafts: dict[UUID, ScopingDraft] = {}
        self.task_scopes: dict[UUID, TaskScopeContract] = {}
        self.task_reports: dict[UUID, Report] = {}
        self.survey_uploads: dict[UUID, list[SurveyEvidence]] = defaultdict(list)
        self.traces_by_run: dict[UUID, list[AgentTrace]] = defaultdict(list)

    def add_trace(self, trace: AgentTrace) -> None:
        self.traces_by_run[trace.task_run_id].append(trace)

    def next_trace_sequence(self, run_id: UUID) -> int:
        return len(self.traces_by_run[run_id]) + 1

    def update_report(self, report: Report) -> None:
        self.task_reports[report.task_id] = report

    def search_reports(self, query: str, *, limit: int = 10) -> list[Report]:
        terms = _tokenize(query)
        if not terms:
            return []
        scored: list[tuple[int, Report]] = []
        for report in self.task_reports.values():
            haystack = " ".join(
                [
                    report.markdown_content,
                    str(report.structured_content),
                    " ".join(claim.claim_text for claim in report.claims),
                    " ".join(f"{source.title} {source.snippet}" for source in report.sources),
                ]
            ).lower()
            score = sum(haystack.count(term) for term in terms)
            if score > 0:
                scored.append((score, report))
        scored.sort(key=lambda item: (item[0], item[1].created_at), reverse=True)
        return [report for _, report in scored[:limit]]


def _tokenize(query: str) -> list[str]:
    return [term for term in query.lower().split() if term.strip()]


store = InMemoryStore()
