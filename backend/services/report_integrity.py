import re
from copy import deepcopy
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


def prune_report_sources_to_references(
    *,
    sources: list[SourceCitation],
    claims: list[ReportClaim],
    structured_content: dict[str, Any],
) -> tuple[list[SourceCitation], list[ReportClaim], dict[str, Any], dict[str, str]]:
    referenced_ids = {source_id for claim in claims for source_id in claim.source_ids}
    referenced_ids.update(source_ids_from_payload(structured_content))

    id_mapping: dict[str, str] = {}
    canonical_by_key: dict[str, SourceCitation] = {}
    pruned_sources: list[SourceCitation] = []
    for source in sources:
        if source.id not in referenced_ids:
            continue
        key = _source_dedupe_key(source)
        canonical = canonical_by_key.get(key)
        if canonical is None:
            canonical_by_key[key] = source
            pruned_sources.append(source)
            id_mapping[source.id] = source.id
        else:
            id_mapping[source.id] = canonical.id

    remapped_claims = [
        claim.model_copy(update={"source_ids": _remap_source_ids(claim.source_ids, id_mapping)})
        for claim in claims
    ]
    remapped_content = _remap_payload_source_ids(deepcopy(structured_content), id_mapping)
    return pruned_sources, remapped_claims, remapped_content, id_mapping


def remap_markdown_source_ids(markdown: str, id_mapping: dict[str, str]) -> str:
    for old_id, canonical_id in id_mapping.items():
        if old_id != canonical_id:
            markdown = re.sub(r"\b" + re.escape(old_id) + r"\b", canonical_id, markdown)
    return markdown


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
    referenced_ids.update(source_ids_from_payload(structured_content))
    unresolved_ids = sorted(source_id for source_id in referenced_ids if source_id not in known_ids)
    if unresolved_ids:
        raise ValueError(f"unresolved report source ids: {', '.join(unresolved_ids)}")


def source_ids_from_payload(value: Any) -> set[str]:
    if isinstance(value, dict):
        dict_source_ids: set[str] = set()
        for key, item in value.items():
            if key == "source_ids" and isinstance(item, list):
                dict_source_ids.update(
                    source_id for source_id in item if isinstance(source_id, str)
                )
            else:
                dict_source_ids.update(source_ids_from_payload(item))
        return dict_source_ids
    if isinstance(value, list):
        list_source_ids: set[str] = set()
        for item in value:
            list_source_ids.update(source_ids_from_payload(item))
        return list_source_ids
    return set()


def _source_ids_from_payload(value: Any) -> set[str]:
    return source_ids_from_payload(value)


def _source_dedupe_key(source: SourceCitation) -> str:
    if source.url:
        return str(source.url).rstrip("/").lower()
    return source.id.lower()


def _remap_source_ids(source_ids: list[str], id_mapping: dict[str, str]) -> list[str]:
    remapped: list[str] = []
    for source_id in source_ids:
        mapped_id = id_mapping.get(source_id, source_id)
        if mapped_id not in remapped:
            remapped.append(mapped_id)
    return remapped


def _remap_payload_source_ids(value: Any, id_mapping: dict[str, str]) -> Any:
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "source_ids" and isinstance(item, list):
                value[key] = _remap_source_ids(
                    [source_id for source_id in item if isinstance(source_id, str)],
                    id_mapping,
                )
            else:
                value[key] = _remap_payload_source_ids(item, id_mapping)
        return value
    if isinstance(value, list):
        return [_remap_payload_source_ids(item, id_mapping) for item in value]
    return value
