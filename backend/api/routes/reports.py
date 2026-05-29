from uuid import UUID

from fastapi import APIRouter, HTTPException, Response

from api.dependencies import run_manager
from schemas.report import (
    ClaimReviewRequest,
    FieldCorrectionRequest,
    LanguageRequest,
    Report,
    ReportMetrics,
    ReportSearchResponse,
    ReportSearchResult,
)
from services.exporter import export_markdown, export_pdf, export_pptx

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/search", response_model=ReportSearchResponse)
async def search_reports(q: str, limit: int = 10) -> ReportSearchResponse:
    reports = await run_manager.search_reports(q, limit=limit)
    return ReportSearchResponse(
        query=q,
        mode="in_memory_semantic_fallback",
        results=[_search_result(report, q) for report in reports],
    )


@router.get("/{task_id}", response_model=Report)
async def get_report(task_id: UUID) -> Report:
    report = await run_manager.get_report(task_id)
    if report is None:
        raise HTTPException(status_code=404, detail="report not found")
    return report


@router.get("/{task_id}/metrics", response_model=ReportMetrics)
async def get_report_metrics(task_id: UUID) -> ReportMetrics:
    report = await run_manager.get_report(task_id)
    if report is None:
        raise HTTPException(status_code=404, detail="report not found")
    return report.metrics


@router.get("/{task_id}/export")
async def export_report(task_id: UUID, format: str = "markdown") -> Response:
    report = await run_manager.get_report(task_id)
    if report is None:
        raise HTTPException(status_code=404, detail="report not found")
    exporters = {
        "markdown": (
            export_markdown,
            "text/markdown; charset=utf-8",
            "md",
        ),
        "pdf": (export_pdf, "application/pdf", "pdf"),
        "pptx": (
            export_pptx,
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "pptx",
        ),
    }
    if format not in exporters:
        raise HTTPException(status_code=400, detail="unsupported export format")
    exporter, media_type, extension = exporters[format]
    filename = f"report-{task_id}.{extension}"
    return Response(
        content=exporter(report),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{task_id}/language", response_model=Report)
async def switch_report_language(task_id: UUID, request: LanguageRequest) -> Report:
    report = await run_manager.get_report(task_id)
    if report is None:
        raise HTTPException(status_code=404, detail="report not found")
    if report.language == request.language:
        return report
    translated = report.model_copy(
        update={
            "language": request.language,
            "structured_content": {
                **report.structured_content,
                "language": request.language,
            },
            "markdown_content": _localized_markdown(report.markdown_content, request.language),
        },
        deep=True,
    )
    await run_manager.update_report(translated)
    return translated


@router.patch("/{task_id}/field", response_model=Report)
async def correct_field(task_id: UUID, request: FieldCorrectionRequest) -> Report:
    report = await run_manager.get_report(task_id)
    if report is None:
        raise HTTPException(status_code=404, detail="report not found")
    claim_index = _claim_index(report, request.claim_id)
    claims = list(report.claims)
    claims[claim_index] = claims[claim_index].model_copy(
        update={
            "edit_status": "edited",
            "correction_type": request.correction_type,
        }
    )
    structured_content = dict(report.structured_content)
    _set_field_path(structured_content, request.field_path, request.new_value)
    updated = report.model_copy(
        update={"claims": claims, "structured_content": structured_content},
        deep=True,
    )
    if request.triggered_rerun:
        updated.metrics.rerun_rate = max(updated.metrics.rerun_rate or 0.0, 1.0)
    return await run_manager.recompute_report_metrics(updated)


@router.patch("/{task_id}/claims/{claim_id}/review", response_model=Report)
async def review_claim(
    task_id: UUID,
    claim_id: UUID,
    request: ClaimReviewRequest,
) -> Report:
    report = await run_manager.get_report(task_id)
    if report is None:
        raise HTTPException(status_code=404, detail="report not found")
    claim_index = _claim_index(report, claim_id)
    claims = list(report.claims)
    claims[claim_index] = claims[claim_index].model_copy(
        update={"review_status": request.review_status}
    )
    updated = report.model_copy(update={"claims": claims}, deep=True)
    return await run_manager.recompute_report_metrics(updated)


@router.post("/{task_id}/dimensions/{dimension_id}/regenerate")
async def regenerate_dimension(task_id: UUID, dimension_id: str) -> dict[str, str]:
    report = await run_manager.get_report(task_id)
    if report is None:
        raise HTTPException(status_code=404, detail="report not found")
    return {"task_id": str(task_id), "dimension_id": dimension_id, "status": "queued_mock"}


def _claim_index(report: Report, claim_id: UUID) -> int:
    for index, claim in enumerate(report.claims):
        if claim.id == claim_id:
            return index
    raise HTTPException(status_code=404, detail="claim not found")


def _set_field_path(payload: dict, field_path: str, value: object) -> None:
    parts = [part for part in field_path.split(".") if part]
    if not parts:
        return
    cursor = payload
    for part in parts[:-1]:
        next_value = cursor.get(part)
        if not isinstance(next_value, dict):
            next_value = {}
            cursor[part] = next_value
        cursor = next_value
    cursor[parts[-1]] = value


def _localized_markdown(markdown: str, language: str) -> str:
    if language == "en":
        return markdown.replace("# 竞品分析报告", "# Competitor Analysis Report").replace(
            "S0 mock report with traceable claims.",
            "Backend-generated report with traceable claims.",
        )
    return markdown.replace("# Competitor Analysis Report", "# 竞品分析报告")


def _search_result(report: Report, query: str) -> ReportSearchResult:
    matching_claims = [
        claim
        for claim in report.claims
        if query.lower() in claim.claim_text.lower() or not query.strip()
    ]
    claims = matching_claims or report.claims[:2]
    source_ids = sorted({source_id for claim in claims for source_id in claim.source_ids})
    snippet = claims[0].claim_text if claims else report.markdown_content[:160]
    return ReportSearchResult(
        report_id=report.id,
        task_id=report.task_id,
        language=report.language,
        title=str(report.structured_content.get("summary") or "Competitor analysis report"),
        snippet=snippet,
        claim_ids=[claim.id for claim in claims],
        source_ids=source_ids,
    )
