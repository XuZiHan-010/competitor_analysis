from collections import Counter

from schemas.report import ReportClaim, ReportMetrics
from schemas.source import SourceCitation


def calculate_report_metrics(
    *,
    claims: list[ReportClaim],
    sources: list[SourceCitation],
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
        field_coverage_rate=1.0 if total_claims else 0.0,
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
