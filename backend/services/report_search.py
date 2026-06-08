from collections.abc import Iterable

from schemas.report import Report
from schemas.scope import TaskScopeContract


def tokenize_report_query(query: str) -> list[str]:
    return [term for term in query.lower().split() if term.strip()]


def competitor_names_from_items(items: object) -> list[str]:
    if not isinstance(items, list):
        return []
    names: list[str] = []
    for item in items:
        name = _competitor_name(item)
        if name and name not in names:
            names.append(name)
    return names


def competitor_names_from_scope(scope: TaskScopeContract | None) -> list[str]:
    if scope is None:
        return []
    return [competitor.name for competitor in scope.competitors if competitor.name]


def report_competitor_names(report: Report) -> list[str]:
    return competitor_names_from_items(report.structured_content.get("competitors"))


def report_label(report: Report) -> str:
    structured = report.structured_content
    title = str(structured.get("title") or "")
    summary = str(structured.get("summary") or "")
    return " ".join([*report_competitor_names(report), title, summary]).strip()


def report_search_title(report: Report) -> str:
    competitors = report_competitor_names(report)
    if competitors:
        return " / ".join(competitors)
    return str(report.structured_content.get("summary") or "Competitor analysis report")


def score_report_for_query(report: Report, terms: Iterable[str]) -> int:
    label = report_label(report).lower()
    body = _report_body(report).lower()
    score = 0
    for term in terms:
        score += label.count(term) * 10
        score += body.count(term)
    return score


def rank_reports_for_query(
    reports: Iterable[Report],
    query: str,
    *,
    limit: int,
    require_match: bool,
) -> list[Report]:
    terms = tokenize_report_query(query)
    if not terms:
        return sorted(reports, key=lambda report: report.created_at, reverse=True)[:limit]

    scored: list[tuple[int, Report]] = []
    for report in reports:
        score = score_report_for_query(report, terms)
        if score > 0 or not require_match:
            scored.append((score, report))
    scored.sort(key=lambda item: (item[0], item[1].created_at), reverse=True)
    return [report for _, report in scored[:limit]]


def _report_body(report: Report) -> str:
    return " ".join(
        [
            report.markdown_content,
            " ".join(claim.claim_text for claim in report.claims),
            " ".join(f"{source.title} {source.snippet}" for source in report.sources),
        ]
    )


def _competitor_name(item: object) -> str:
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        for key in ("name", "competitor", "title", "product"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    name = getattr(item, "name", None)
    if isinstance(name, str) and name.strip():
        return name.strip()
    return ""
