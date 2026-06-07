from uuid import uuid4

from schemas.report import Report, ReportClaim, ReportMetrics
from schemas.source import SourceCitation
from services.storage import InMemoryStore


def test_in_memory_report_search_prioritizes_competitor_label() -> None:
    owner_id = uuid4()
    label_match = _report(competitors=["Trae"], markdown="general competitor analysis")
    body_match = _report(competitors=["Cursor"], markdown="Trae Trae Trae body-only mention")

    store = InMemoryStore()
    store.task_owner[label_match.task_id] = owner_id
    store.task_owner[body_match.task_id] = owner_id
    store.update_report(body_match)
    store.update_report(label_match)

    results = store.search_reports("Trae", user_id=owner_id)

    assert [report.task_id for report in results] == [label_match.task_id, body_match.task_id]


def test_in_memory_report_search_empty_query_returns_owned_reports_by_created_at() -> None:
    owner_id = uuid4()
    other_owner_id = uuid4()
    older = _report(competitors=["Notion"], markdown="older")
    newer = _report(competitors=["Lark"], markdown="newer")
    other = _report(competitors=["Airtable"], markdown="other")

    store = InMemoryStore()
    store.task_owner[older.task_id] = owner_id
    store.task_owner[newer.task_id] = owner_id
    store.task_owner[other.task_id] = other_owner_id
    store.update_report(older)
    store.update_report(newer)
    store.update_report(other)

    results = store.search_reports("", user_id=owner_id)

    assert [report.task_id for report in results] == [newer.task_id, older.task_id]


def _report(*, competitors: list[str], markdown: str) -> Report:
    task_id = uuid4()
    return Report(
        task_id=task_id,
        structured_content={
            "title": f"{' / '.join(competitors)} report",
            "summary": "Summary",
            "competitors": competitors,
        },
        markdown_content=markdown,
        sources=[
            SourceCitation(
                id=f"{competitors[0]}_source",
                type="official",
                category="official",
                title=f"{competitors[0]} source",
                snippet="source snippet",
                provider="test",
                valid=True,
            )
        ],
        claims=[
            ReportClaim(
                claim_path="summary",
                claim_text=markdown,
                layer="core",
                field_type="free_text",
                source_ids=[f"{competitors[0]}_source"],
                generating_agent="WriterAgent",
            )
        ],
        metrics=ReportMetrics(
            field_coverage_rate=1.0,
            citation_coverage_rate=1.0,
            manual_correction_rate=0.0,
        ),
    )
