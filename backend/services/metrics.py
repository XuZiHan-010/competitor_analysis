from collections import Counter
from typing import Any

from schemas.report import ReportClaim, ReportMetrics
from schemas.source import SourceCitation

_PLACEHOLDER_VALUES = {
    "",
    "?",
    "unknown",
    "tbd",
    "needs verification",
    "待确认",
    "需验证",
    "未确认",
    "unverified",
    "not_applicable",
}


def calculate_report_metrics(
    *,
    claims: list[ReportClaim],
    sources: list[SourceCitation],
    structured_content: dict[str, Any] | None = None,
    field_verification_status: dict[str, Any] | None = None,
    analysis_duration_seconds: float | None = None,
    rerun_count: int = 0,
    module_count: int = 1,
    ai_self_assessment: dict | None = None,
) -> ReportMetrics:
    total_claims = len(claims)
    edited_claims = [claim for claim in claims if claim.edit_status == "edited"]
    reviewed_claims = [claim for claim in claims if claim.review_status != "unreviewed"]
    correct_score = sum(
        (
            1.0
            if claim.review_status == "correct"
            else 0.5 if claim.review_status == "partial" else 0.0
        )
        for claim in reviewed_claims
    )
    source_ids = {source.id for source in sources}
    supported_claims = [
        claim
        for claim in claims
        if claim.source_support == "supported" and _source_ids_resolve(claim.source_ids, source_ids)
    ]
    sourced_claims = [
        claim for claim in claims if _source_ids_resolve(claim.source_ids, source_ids)
    ]
    invalid_sources = [source for source in sources if not source.valid]
    source_categories = {source.category for source in sources if source.category != "unknown"}
    correction_breakdown = Counter(
        claim.correction_type for claim in claims if claim.correction_type is not None
    )

    return ReportMetrics(
        analysis_duration_seconds=analysis_duration_seconds,
        field_coverage_rate=_field_coverage_rate(
            structured_content or {},
            field_verification_status or {},
        ),
        citation_coverage_rate=_rate(len(sourced_claims), total_claims),
        manual_correction_rate=_rate(len(edited_claims), total_claims),
        human_verified_accuracy_rate=(
            _rate(correct_score, len(reviewed_claims)) if reviewed_claims else None
        ),
        source_support_rate=_rate(len(supported_claims), total_claims) if claims else None,
        source_type_coverage_rate=min(len(source_categories) / 5, 1.0),
        invalid_source_rate=_rate(len(invalid_sources), len(sources)) if sources else 0.0,
        rerun_rate=_rate(rerun_count, module_count),
        correction_type_breakdown={str(key): value for key, value in correction_breakdown.items()},
        ai_self_assessment=ai_self_assessment or {},
    )


def _rate(numerator: float, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(float(numerator) / denominator, 4)


def _source_ids_resolve(claim_source_ids: list[str], report_source_ids: set[str]) -> bool:
    return bool(claim_source_ids) and all(
        source_id in report_source_ids for source_id in claim_source_ids
    )


def _field_coverage_rate(
    structured_content: dict[str, Any],
    field_verification_status: dict[str, Any],
) -> float:
    numerator = 0
    denominator = 0

    feature_rows = _as_list(_as_dict(structured_content.get("feature_tree")).get("rows"))
    if feature_rows:
        for row in feature_rows:
            for cell in _as_list(_as_dict(row).get("cells")):
                denominator += 1
                numerator += int(_is_filled(_as_dict(cell).get("status")))
    else:
        denominator += 1

    tiers = _as_list(_as_dict(structured_content.get("pricing")).get("tiers"))
    if tiers:
        for tier in tiers:
            denominator += 1
            tier_map = _as_dict(tier)
            numerator += int(
                _is_filled(tier_map.get("price"))
                or _is_filled(tier_map.get("plan_name"))
                or _is_filled(tier_map.get("name"))
            )
    else:
        denominator += 1

    personas = _as_list(_as_dict(structured_content.get("user_personas")).get("personas"))
    if personas:
        for persona in personas:
            denominator += 1
            persona_map = _as_dict(persona)
            numerator += int(
                _is_filled(persona_map.get("name"))
                or _is_filled(persona_map.get("label"))
                or _is_filled(persona_map.get("traits"))
            )
    else:
        denominator += 1

    blocks = _as_list(_as_dict(structured_content.get("swot")).get("blocks"))
    if blocks:
        for block in blocks:
            block_map = _as_dict(block)
            for quadrant in ("strengths", "weaknesses", "opportunities", "threats"):
                denominator += 1
                numerator += int(bool(_as_list(block_map.get(quadrant))))
    else:
        denominator += 4

    denominator += len(field_verification_status)
    return _rate(numerator, denominator)


def _is_filled(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        lowered = value.strip().lower()
        return bool(lowered) and lowered not in _PLACEHOLDER_VALUES and "未确认" not in value
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
