import json
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
from services.exporter import export_markdown, export_pdf
from services.llm import LLMClient
from settings import get_settings

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/search", response_model=ReportSearchResponse)
async def search_reports(q: str, limit: int = 10) -> ReportSearchResponse:
    result = await run_manager.search_reports(q, limit=limit)
    return ReportSearchResponse(
        query=q,
        mode=result.mode,
        results=[_search_result(report, q) for report in result.reports],
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

    settings = get_settings()
    llm = LLMClient(settings)
    new_sc, new_markdown = await _translate_report(
        report=report,
        target_lang=request.language,
        llm=llm,
        model=settings.qa_model,
    )
    translated = report.model_copy(
        update={
            "language": request.language,
            "structured_content": new_sc,
            "markdown_content": new_markdown,
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


@router.post("/{task_id}/dimensions/{dimension_id}/regenerate", response_model=Report)
async def regenerate_dimension(task_id: UUID, dimension_id: str) -> Report:
    report = await run_manager.get_report(task_id)
    if report is None:
        raise HTTPException(status_code=404, detail="report not found")

    settings = get_settings()
    llm = LLMClient(settings)
    if not llm.enabled:
        raise HTTPException(
            status_code=501,
            detail="LLM disabled; set MOCK_LLM=false with a valid API key to regenerate dimensions",
        )

    sc = dict(report.structured_content)
    extensions: list[dict] = list(sc.get("extensions") or [])
    ext_idx = next(
        (i for i, e in enumerate(extensions) if e.get("dimension_id") == dimension_id),
        None,
    )
    if ext_idx is None:
        raise HTTPException(status_code=404, detail="dimension not found in report extensions")

    ext = extensions[ext_idx]
    competitors: list[str] = list(sc.get("competitors") or [])

    result = await llm.complete_json(
        provider="openai",
        model=settings.qa_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a competitive analysis expert. Regenerate the analysis section "
                    "for the given dimension. Return JSON with keys: "
                    "summary (string), bullets (array of {competitor: string, "
                    "points: string[], source_ids: []})."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Dimension: {ext.get('title', dimension_id)} "
                    f"(intent: {ext.get('intent', '')}). "
                    f"Competitors: {', '.join(competitors)}. "
                    "Regenerate with fresh, detailed analysis."
                ),
            },
        ],
    )

    extensions[ext_idx] = {
        **ext,
        "summary": str(result.get("summary") or ext.get("summary") or ""),
        "bullets": result.get("bullets") or ext.get("bullets") or [],
    }
    sc["extensions"] = extensions
    updated = report.model_copy(update={"structured_content": sc}, deep=True)
    updated.metrics.rerun_rate = max(updated.metrics.rerun_rate or 0.0, 1.0)
    return await run_manager.recompute_report_metrics(updated)


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


async def _translate_report(
    report: Report,
    target_lang: str,
    llm: LLMClient,
    model: str,
) -> tuple[dict, str]:
    """Translate key display fields + markdown via LLM; falls back to header swap."""
    sc = dict(report.structured_content)
    sc["language"] = target_lang

    if not llm.enabled:
        return sc, _header_swap(report.markdown_content, target_lang)

    lang_name = "English" if target_lang == "en" else "中文（简体）"

    fields: dict[str, str] = {
        "title": str(sc.get("title") or ""),
        "subtitle": str(sc.get("subtitle") or ""),
        "summary": str(sc.get("summary") or ""),
        "feature_tree_intro": str((sc.get("feature_tree") or {}).get("intro") or ""),
        "pricing_intro": str((sc.get("pricing") or {}).get("intro") or ""),
        "personas_intro": str((sc.get("user_personas") or {}).get("intro") or ""),
        "swot_intro": str((sc.get("swot") or {}).get("intro") or ""),
        "cross_summary": str(
            (sc.get("cross_analysis") or {}).get("differentiation_summary") or ""
        ),
    }
    try:
        t = await llm.complete_json(
            provider="openai",
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Translate every string value in the JSON to {lang_name}. "
                        "Return JSON with the exact same keys. Do not add or remove keys."
                    ),
                },
                {"role": "user", "content": json.dumps(fields, ensure_ascii=False)},
            ],
        )
    except Exception:
        t = fields

    sc["title"] = str(t.get("title") or sc.get("title") or "")
    sc["subtitle"] = str(t.get("subtitle") or sc.get("subtitle") or "")
    sc["summary"] = str(t.get("summary") or sc.get("summary") or "")
    if isinstance(sc.get("feature_tree"), dict):
        sc["feature_tree"] = {**sc["feature_tree"], "intro": t.get("feature_tree_intro", "")}
    if isinstance(sc.get("pricing"), dict):
        sc["pricing"] = {**sc["pricing"], "intro": t.get("pricing_intro", "")}
    if isinstance(sc.get("user_personas"), dict):
        sc["user_personas"] = {**sc["user_personas"], "intro": t.get("personas_intro", "")}
    if isinstance(sc.get("swot"), dict):
        sc["swot"] = {**sc["swot"], "intro": t.get("swot_intro", "")}
    if isinstance(sc.get("cross_analysis"), dict):
        sc["cross_analysis"] = {
            **sc["cross_analysis"],
            "differentiation_summary": t.get("cross_summary", ""),
        }

    try:
        new_markdown = await llm.complete_text(
            provider="openai",
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Translate the following Markdown document to {lang_name}. "
                        "Preserve all Markdown syntax, headings, tables, and bullet points. "
                        "Output only the translated Markdown, no preamble."
                    ),
                },
                {"role": "user", "content": report.markdown_content[:6000]},
            ],
        )
    except Exception:
        new_markdown = _header_swap(report.markdown_content, target_lang)

    return sc, new_markdown


def _header_swap(markdown: str, language: str) -> str:
    if language == "en":
        return markdown.replace("# 竞品分析报告", "# Competitor Analysis Report")
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
