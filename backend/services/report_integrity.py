from typing import Any

from schemas.report import ReportClaim
from schemas.source import SourceCitation

PLACEHOLDER_MARKERS = (
    "需验证",
    "待确认",
    "标准版",
    "S0 mock report",
    "needs verification",
    "TBD",
)


def placeholder_issues(*, structured_content: dict[str, Any], markdown_content: str) -> list[dict]:
    payload = f"{structured_content}\n{markdown_content}"
    return [
        {
            "severity": "blocker",
            "target_agent": "AnalystAgent",
            "failed_field": "report.placeholder_content",
            "message": f"Report contains placeholder marker: {marker}",
            "retryable": True,
        }
        for marker in PLACEHOLDER_MARKERS
        if marker in payload
    ]


def assert_report_sources_resolvable(
    *,
    sources: list[SourceCitation],
    claims: list[ReportClaim],
    structured_content: dict[str, Any],
) -> None:
    source_ids = [source.id for source in sources]
    duplicate_ids = sorted(
        {source_id for source_id in source_ids if source_ids.count(source_id) > 1}
    )
    if duplicate_ids:
        raise ValueError(f"duplicate report source ids: {', '.join(duplicate_ids)}")

    known_ids = set(source_ids)
    referenced_ids = {source_id for claim in claims for source_id in claim.source_ids}
    referenced_ids.update(_source_ids_from_payload(structured_content))
    unresolved_ids = sorted(source_id for source_id in referenced_ids if source_id not in known_ids)
    if unresolved_ids:
        raise ValueError(f"unresolved report source ids: {', '.join(unresolved_ids)}")


def _source_ids_from_payload(value: Any) -> set[str]:
    if isinstance(value, dict):
        dict_source_ids: set[str] = set()
        for key, item in value.items():
            if key == "source_ids" and isinstance(item, list):
                dict_source_ids.update(
                    source_id for source_id in item if isinstance(source_id, str)
                )
            else:
                dict_source_ids.update(_source_ids_from_payload(item))
        return dict_source_ids
    if isinstance(value, list):
        list_source_ids: set[str] = set()
        for item in value:
            list_source_ids.update(_source_ids_from_payload(item))
        return list_source_ids
    return set()
