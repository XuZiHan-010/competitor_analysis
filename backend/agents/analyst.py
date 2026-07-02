import asyncio
from typing import Any

import structlog

from graph.retry_scope import has_retry_correction, retry_target_competitors
from graph.state import (
    CrossCompetitorAnalysis,
    ExtensionFinding,
    RawCollectionResult,
    StructuredCompetitorProfile,
    WorkflowState,
)
from schemas.source import SourceCitation
from services.agents.decorators import traced_node
from services.agents.language import language_instruction
from services.llm import LLMClient
from services.llm.usage import record_degradation
from settings import get_settings

logger = structlog.get_logger(__name__)

# Full fetched page bodies (``raw_content``) can be tens of KB each; dumping all
# of them per competitor bloats the prompt and slows generation. Keep enough for
# evidence-grounded extraction without sending whole articles.
_MAX_RAW_CONTENT_CHARS = 5000
_MAX_COMPETITOR_RAW_CONTENT_CHARS = 24000
_DEFAULT_POSITIONING_SCORE = 50.0
# Competitors are extracted independently, so their LLM calls are run concurrently;
# the bound keeps in-flight DeepSeek requests modest (each competitor still issues
# its core + per-extension calls sequentially inside its own coroutine).
_MAX_COMPETITOR_CONCURRENCY = 4
_FEATURE_STATUS_ALIASES = {
    "supported": "supported",
    "support": "supported",
    "yes": "supported",
    "true": "supported",
    "available": "supported",
    "支持": "supported",
    "partial": "partial",
    "partially_supported": "partial",
    "limited": "partial",
    "weak": "partial",
    "部分支持": "partial",
    "有限支持": "partial",
    "unsupported": "unsupported",
    "not_supported": "unsupported",
    "no": "unsupported",
    "false": "unsupported",
    "unavailable": "unsupported",
    "不支持": "unsupported",
    "unknown": "unknown",
    "unverified": "unknown",
    "unchecked": "unknown",
    "": "unknown",
}


def _clamp_position(value: float) -> float:
    return min(max(value, 0.0), 100.0)


def _lowest_price_score(profile: StructuredCompetitorProfile) -> float:
    prices: list[float] = []
    for tier in profile.pricing.get("tiers") or []:
        if not isinstance(tier, dict):
            continue
        price_text = " ".join(
            str(tier.get(key) or "") for key in ("price", "price_text", "tier", "plan_name")
        ).lower()
        if any(token in price_text for token in ("free", "$0", "usd 0", "0 usd")):
            prices.append(0.0)
            continue
        normalized = price_text.replace(",", "")
        for prefix in ("$", "usd", "rmb", "cny"):
            normalized = normalized.replace(prefix, " ")
        for token in normalized.split():
            try:
                prices.append(float(token))
            except ValueError:
                continue
    if not prices:
        return _DEFAULT_POSITIONING_SCORE
    return _clamp_position(min(prices))


def _build_positioning_map(
    cross: CrossCompetitorAnalysis,
    profiles: dict[str, StructuredCompetitorProfile],
) -> dict[str, Any]:
    competitors = cross.feature_matrix.get("competitors") or list(profiles.keys())
    rows = cross.feature_matrix.get("rows") or []
    breadth_counts = dict.fromkeys((str(name) for name in competitors), 0.0)
    for row in rows:
        for cell in row.get("cells") or []:
            competitor = str(cell.get("competitor") or "")
            status = _canonical_feature_status(cell.get("status"))
            if competitor not in breadth_counts:
                continue
            if status == "supported":
                breadth_counts[competitor] += 1.0
            elif status == "partial":
                breadth_counts[competitor] += 0.5

    max_breadth = max(breadth_counts.values(), default=0.0)
    points: list[dict[str, Any]] = []
    for name in competitors:
        competitor = str(name)
        profile = profiles.get(competitor)
        if profile is None:
            continue
        y = (
            _DEFAULT_POSITIONING_SCORE
            if max_breadth <= 0
            else _clamp_position((breadth_counts[competitor] / max_breadth) * 100)
        )
        points.append(
            {
                "id": competitor,
                "x": _lowest_price_score(profile),
                "y": y,
                "label": competitor,
            }
        )
    return {
        "x_axis": "Cost, higher is more expensive",
        "y_axis": "Feature breadth, higher is stronger",
        "competitors": points,
    }


def _source_for_prompt(source: SourceCitation) -> dict[str, Any]:
    """Trim a source to the fields the extractor needs, truncating raw_content."""
    payload = source.model_dump(mode="json")
    raw = payload.get("raw_content")
    if isinstance(raw, str) and len(raw) > _MAX_RAW_CONTENT_CHARS:
        payload["raw_content"] = raw[:_MAX_RAW_CONTENT_CHARS] + "…[truncated]"
    return payload


def _sources_for_prompt(sources: list[SourceCitation]) -> list[dict[str, Any]]:
    payloads = [_source_for_prompt(source) for source in sources]
    remaining = _MAX_COMPETITOR_RAW_CONTENT_CHARS
    for payload in payloads:
        raw = payload.get("raw_content")
        if not isinstance(raw, str):
            continue
        if remaining <= 0:
            payload["raw_content"] = ""
            continue
        if len(raw) > remaining:
            payload["raw_content"] = raw[:remaining] + "…[truncated]"
            remaining = 0
        else:
            remaining -= len(raw)
    return payloads


def _coerce_mapping(value: Any) -> dict[str, Any]:
    """Schema 要 dict，但 LLM 偶尔把对象返成 list/标量；在边界兜成 dict。"""
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                return item
    return {}


def _coerce_personas(value: Any) -> list[dict[str, Any]]:
    """``user_personas`` schema 要 list[dict]，但 DeepSeek 实测会返回单个 dict
    或 ``{"personas": [...]}`` 包一层；统一兜成 list[dict]，避免真实结果被丢弃。"""
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        # 形如 {"personas": [{...}, {...}]}：取内层 list[dict]。但要避开把
        # 单个 persona 自身的标量 list 字段（如 source_ids: [str]）误当成画像列表。
        for inner in value.values():
            if isinstance(inner, list) and any(isinstance(item, dict) for item in inner):
                return [item for item in inner if isinstance(item, dict)]
        return [value]
    return []


def _canonical_feature_status(value: object) -> str:
    return _FEATURE_STATUS_ALIASES.get(str(value or "").strip().lower(), "unknown")


def _empty_profile(name: str) -> StructuredCompetitorProfile:
    """A schema-valid but empty profile for a competitor whose extraction failed.

    Keeping the competitor in the result (rather than dropping it) lets QA raise
    its citation/feature blockers and the report surface the gap explicitly.
    """
    return StructuredCompetitorProfile(
        competitor_name=name,
        feature_tree={"rows": []},
        pricing={},
        user_personas=[],
        swot={},
        source_ids=[],
    )


def _cited_source_ids(
    feature_tree: dict[str, Any],
    pricing: dict[str, Any],
    personas: list[dict[str, Any]],
    swot: dict[str, Any],
    collected_ids: set[str],
) -> list[str]:
    """Union of the source ids the LLM actually cited, restricted to real ones.

    Stamping the profile with every collected source id let parametric-knowledge
    output sail past QA's "no citations" blocker; ids the LLM invented are
    dropped for the same reason.
    """
    items: list[Any] = list(feature_tree.get("rows") or [])
    items += list(pricing.get("tiers") or [])
    items += personas
    for quadrant in ("strengths", "weaknesses", "opportunities", "threats"):
        items += list(swot.get(quadrant) or [])
    cited = [
        str(source_id)
        for item in items
        if isinstance(item, dict)
        for source_id in (item.get("source_ids") or [])
        if str(source_id) in collected_ids
    ]
    return list(dict.fromkeys(cited))


def _sanitize_source_ids(value: Any, valid_ids: set[str]) -> Any:
    """Drop every nested ``source_ids`` entry that isn't a real collected id.

    The model occasionally pattern-completes plausible-looking ids (e.g. an extra
    ``src_tavily_<task>_NNN``) that were never in the prompt. Only the profile-level
    ``source_ids`` was filtered before (via ``_cited_source_ids``); a stray id left
    inside feature_tree/pricing/swot/persona rows reaches the Writer's integrity
    gate and fails the whole run. This filters every nested occurrence too.
    """
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            if key == "source_ids" and isinstance(item, list):
                cleaned[key] = list(
                    dict.fromkeys(sid for sid in item if isinstance(sid, str) and sid in valid_ids)
                )
            else:
                cleaned[key] = _sanitize_source_ids(item, valid_ids)
        return cleaned
    if isinstance(value, list):
        return [_sanitize_source_ids(item, valid_ids) for item in value]
    return value


def _canonical_feature_cell(cell: dict[str, Any], competitor: str) -> dict[str, Any]:
    return {
        **cell,
        "competitor": str(cell.get("competitor") or competitor),
        "status": _canonical_feature_status(cell.get("status")),
        "note": str(cell.get("note") or ""),
    }


class AnalystAgent:
    @traced_node(
        agent_name="AnalystAgent",
        node_name="run_analyst",
        prompt="Extract structured competitor profiles from collected sources.",
    )
    async def run(
        self,
        state: WorkflowState,
        *,
        trace_context: object | None = None,
    ) -> tuple[
        dict[str, StructuredCompetitorProfile],
        list[ExtensionFinding],
        CrossCompetitorAnalysis | None,
    ]:
        settings = get_settings()
        llm = LLMClient(settings)
        if settings.mock_llm:
            return self._run_fallback(state)
        if not settings.deepseek_api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is required for AnalystAgent in real mode")
        try:
            return await self._run_llm(state, llm)
        except Exception as exc:
            logger.warning("analyst_llm_failed", exc_info=True)
            record_degradation(f"analyst: {type(exc).__name__}: {exc}")
            raise RuntimeError(f"AnalystAgent LLM failed: {type(exc).__name__}: {exc}") from exc

    async def _run_llm(
        self,
        state: WorkflowState,
        llm: LLMClient,
    ) -> tuple[
        dict[str, StructuredCompetitorProfile],
        list[ExtensionFinding],
        CrossCompetitorAnalysis | None,
    ]:
        settings = get_settings()
        language = state.report_language
        lang_directive = language_instruction(language)

        core_dims = [d for d in state.scope_contract.dimensions if d.layer == "core" and d.enabled]
        ext_dims = [
            d for d in state.scope_contract.dimensions if d.layer == "extension" and d.enabled
        ]

        # Each competitor is independent; run them concurrently (bounded) instead of
        # one slow sequential chain of C×(1+E) DeepSeek calls. On QA retry, a precise
        # target list lets us re-pay only the failed competitors and reuse prior work.
        retry_targets = retry_target_competitors(state) if has_retry_correction(state) else None
        raw_to_extract = {
            name: result
            for name, result in state.raw_collections.items()
            if retry_targets is None or name in retry_targets
        }

        # On scoped retry, a competitor that never made it into structured_profiles
        # (first run failed mid-gather) would be silently dropped at the filter below.
        # Force-extract those competitors now so they aren't missing from the final report.
        if retry_targets is not None:
            already_have = (
                set(state.structured_profiles.keys()) if state.structured_profiles else set()
            )
            all_scope = {c.name for c in state.scope_contract.competitors}
            orphaned = all_scope - already_have - retry_targets
            if orphaned:
                logger.warning(
                    "analyst_scoped_retry_orphaned_competitors", competitors=sorted(orphaned)
                )
                for name in orphaned:
                    if name in state.raw_collections and name not in raw_to_extract:
                        raw_to_extract[name] = RawCollectionResult.model_validate(
                            state.raw_collections[name]
                        )

        semaphore = asyncio.Semaphore(_MAX_COMPETITOR_CONCURRENCY)

        async def extract(
            name: str, result: RawCollectionResult
        ) -> tuple[str, StructuredCompetitorProfile, list[ExtensionFinding]]:
            async with semaphore:
                return await self._extract_competitor(
                    name, result, core_dims, ext_dims, llm, settings, lang_directive
                )

        # return_exceptions: one competitor's extraction blowing up (e.g. a truncated
        # DeepSeek JSON) must not take the whole gather — and the whole run — down with
        # it. The failed competitor gets an empty profile so QA still raises blockers
        # for it (and reports the gap) instead of silently dropping it from the report.
        names = list(raw_to_extract)
        extracted = await asyncio.gather(
            *(extract(name, raw_to_extract[name]) for name in names),
            return_exceptions=True,
        )
        combined_profiles = dict(state.structured_profiles) if retry_targets is not None else {}
        # Drop prior findings for *every* competitor we're re-extracting this round —
        # both the explicit retry targets and any orphans force-added above. Filtering on
        # retry_targets alone would keep an orphan's stale findings while the loop appends
        # a fresh set, duplicating that competitor's extension block in the report.
        reextracted = set(raw_to_extract)
        extension_findings = (
            [
                finding
                for finding in state.extension_findings
                if finding.competitor_name not in reextracted
            ]
            if retry_targets is not None
            else []
        )
        for name, outcome in zip(names, extracted, strict=True):
            if isinstance(outcome, BaseException):
                logger.warning(
                    "analyst_extract_failed", competitor=name, error=str(outcome)
                )
                record_degradation(
                    f"analyst: extraction failed for {name}: "
                    f"{type(outcome).__name__}: {outcome}"
                )
                combined_profiles[name] = _empty_profile(name)
                continue
            extracted_name, profile, findings = outcome
            combined_profiles[extracted_name] = profile
            extension_findings.extend(findings)

        structured_profiles = {
            competitor.name: combined_profiles[competitor.name]
            for competitor in state.scope_contract.competitors
            if competitor.name in combined_profiles
        }
        # Cross-analysis is a second, independent LLM pass over the already-extracted
        # profiles. A failure here (timeout, malformed JSON, a bad profile tripping the
        # matrix build) must not discard the per-competitor profiles we already paid for —
        # degrade to no cross-analysis instead of taking the whole run down.
        try:
            cross = self._build_cross_analysis(structured_profiles)
            cross = await self._enrich_cross_matrix(
                cross, structured_profiles, state.raw_collections, llm, language
            )
        except Exception as exc:
            logger.warning("analyst_cross_analysis_failed", exc_info=True)
            record_degradation(f"analyst_cross_analysis: {type(exc).__name__}: {exc}")
            cross = None
        return structured_profiles, extension_findings, cross

    async def _extract_competitor(
        self,
        name: str,
        result: RawCollectionResult,
        core_dims: list[Any],
        ext_dims: list[Any],
        llm: LLMClient,
        settings: Any,
        lang_directive: str,
    ) -> tuple[str, StructuredCompetitorProfile, list[ExtensionFinding]]:
        sources_payload = _sources_for_prompt(result.sources)
        valid_ids = {s.id for s in result.sources}

        # Core layer: fixed schema extractors for all 4 core dimensions at once
        core_dim_ids = {d.id for d in core_dims}
        core_sources = [s for s in result.sources if s.dimension_id in core_dim_ids]
        core_payload = await llm.complete_json(
            provider="deepseek",
            model=settings.analyst_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are AnalystAgent (core extractor). Return JSON with "
                        "feature_tree, pricing, user_personas, swot. "
                        "The root object must contain only those four keys. "
                        "Every source_ids value must be copied from the provided sources. "
                        "Do not use academic_sample, satisfaction-model, literature review, "
                        "or research-sample sources to support hard product facts such as "
                        "pricing tiers, product capabilities, SWOT, monetization, or creator "
                        "incentives. If only those sources exist for a field, leave that "
                        "field empty. "
                        "Each source carries an authority tier A>B>C (A=official/authoritative, "
                        "B=credible media, C=user reviews/blogs/unknown); prefer higher-tier "
                        "evidence and, when sources conflict on a fact, trust the higher tier. "
                        "Do not output placeholder text such as 需验证, 待确认, 标准版, "
                        "unknown, TBD, or needs verification. If evidence is missing, "
                        "leave the specific list empty instead of inventing a placeholder. "
                        "description, note, evidence, highlights, and SWOT text must "
                        "contain concrete evidence such as numbers, version names, quoted "
                        "phrases, pricing rules, or clearly attributed product facts. "
                        "Keep output compact: at most 8 feature rows, 5 pricing tiers, "
                        "3 personas, and 4 items per SWOT quadrant; omit weaker points. "
                        'Return exactly this shape: {"feature_tree":{"rows":[{"feature":'
                        '"Real feature name","description":"Evidence-backed detail",'
                        '"cells":[{"competitor":"Competitor name","status":"supported",'
                        '"note":"Specific evidence-backed note"}],"source_ids":["src_id"]}]},'
                        '"pricing":{"tiers":[{"competitor":"Competitor name","tier":'
                        '"Plan name","price":"Published price or pricing rule",'
                        '"highlights":["Evidence-backed highlight"],"source_ids":["src_id"]}]},'
                        '"user_personas":[{"competitor":"Competitor name","label":'
                        '"Persona label","size":"majority","needs":["Need"],'
                        '"pain_points":["Pain point"],"evidence":"Evidence summary",'
                        '"source_ids":["src_id"]}],"swot":{"strengths":[{"text":"Strength",'
                        '"source_ids":["src_id"]}],"weaknesses":[],"opportunities":[],'
                        '"threats":[]}}.' + lang_directive
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Competitor: {name}\n"
                        f"Core dimensions: {[d.model_dump() for d in core_dims]}\n"
                        f"Sources: {_sources_for_prompt(core_sources) or sources_payload}"
                    ),
                },
            ],
            expected_shape='{"feature_tree":{},"pricing":{},"user_personas":[],"swot":{}}',
        )
        # Filter every nested source_ids down to ids actually collected for this
        # competitor before they propagate into the cross matrix and the report.
        feature_tree = _sanitize_source_ids(
            _coerce_mapping(core_payload.get("feature_tree")), valid_ids
        )
        pricing = _sanitize_source_ids(_coerce_mapping(core_payload.get("pricing")), valid_ids)
        user_personas = _sanitize_source_ids(
            _coerce_personas(core_payload.get("user_personas")), valid_ids
        )
        swot = _sanitize_source_ids(_coerce_mapping(core_payload.get("swot")), valid_ids)
        profile = StructuredCompetitorProfile(
            competitor_name=name,
            feature_tree=feature_tree,
            pricing=pricing,
            user_personas=user_personas,
            swot=swot,
            source_ids=_cited_source_ids(feature_tree, pricing, user_personas, swot, valid_ids),
        )

        # Extension layer: generic extractor per dimension with intent injected
        findings: list[ExtensionFinding] = []
        for dim in ext_dims:
            dim_sources = [s for s in result.sources if s.dimension_id == dim.id]
            ext_payload = await llm.complete_json(
                provider="deepseek",
                model=settings.analyst_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are AnalystAgent (extension extractor). "
                            "Return JSON with summary, bullets (list[str]), "
                            "table_data (list[dict]), source_ids (list[str]). "
                            "Every summary, bullet, and table note must include concrete "
                            "evidence such as numbers, version names, quoted phrases, or "
                            "specific product facts. Do not output 需验证, 待确认, 标准版, "
                            "unknown, TBD, or needs verification; omit unsupported points. "
                            "Each source carries an authority tier A>B>C; prefer higher-tier "
                            "evidence and, when sources conflict, trust the higher tier."
                            + lang_directive
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Competitor: {name}\n"
                            f"Dimension intent: {dim.intent}\n"
                            f"Sources: {_sources_for_prompt(dim_sources) or sources_payload}"
                        ),
                    },
                ],
            )
            ext_source_ids = [
                sid for sid in (ext_payload.get("source_ids") or []) if sid in valid_ids
            ] or [s.id for s in dim_sources]
            findings.append(
                ExtensionFinding(
                    dimension_id=dim.id,
                    competitor_name=name,
                    summary=str(ext_payload.get("summary", "")),
                    bullets=ext_payload.get("bullets") or [],
                    table_data=_sanitize_source_ids(ext_payload.get("table_data") or [], valid_ids),
                    source_ids=ext_source_ids,
                )
            )
        return name, profile, findings

    def _run_fallback(self, state: WorkflowState) -> tuple[
        dict[str, StructuredCompetitorProfile],
        list[ExtensionFinding],
        CrossCompetitorAnalysis | None,
    ]:
        retry_targets = retry_target_competitors(state) if has_retry_correction(state) else None
        structured_profiles: dict[str, StructuredCompetitorProfile] = (
            dict(state.structured_profiles) if retry_targets is not None else {}
        )
        extension_findings: list[ExtensionFinding] = (
            [
                finding
                for finding in state.extension_findings
                if finding.competitor_name not in retry_targets
            ]
            if retry_targets is not None
            else []
        )
        ext_dims = [
            d for d in state.scope_contract.dimensions if d.layer == "extension" and d.enabled
        ]

        raw_to_extract = {
            name: result
            for name, result in state.raw_collections.items()
            if retry_targets is None or name in retry_targets
        }
        for name, result in raw_to_extract.items():
            source_ids = [s.id for s in result.sources]
            structured_profiles[name] = StructuredCompetitorProfile(
                competitor_name=name,
                feature_tree={
                    "rows": [
                        {
                            "feature": "核心功能",
                            "description": "基础工作流与协作能力",
                            "cells": [
                                {
                                    "competitor": name,
                                    "status": "supported",
                                    "note": "insufficient evidence",
                                }
                            ],
                            "source_ids": source_ids[:1],
                        }
                    ]
                },
                pricing={
                    "tiers": [
                        {
                            "competitor": name,
                            "tier": "Documented plan",
                            "price": "insufficient evidence",
                            "highlights": ["订阅制"],
                            "source_ids": source_ids[:1],
                        }
                    ]
                },
                user_personas=[
                    {
                        "competitor": name,
                        "label": "核心用户",
                        "size": "majority",
                        "needs": ["高效分析"],
                        "pain_points": ["人工研究耗时"],
                        "evidence": "insufficient evidence",
                        "source_ids": source_ids[:1],
                    }
                ],
                swot={
                    "strengths": [{"text": "结构化工作流", "source_ids": source_ids[:1]}],
                    "weaknesses": [{"text": "insufficient evidence", "source_ids": source_ids[:1]}],
                    "opportunities": [{"text": "AI 辅助分析", "source_ids": source_ids[:1]}],
                    "threats": [{"text": "竞品快速迭代", "source_ids": source_ids[:1]}],
                },
                source_ids=source_ids,
            )
            for dim in ext_dims:
                dim_source_ids = [s.id for s in result.sources if s.dimension_id == dim.id]
                extension_findings.append(
                    ExtensionFinding(
                        dimension_id=dim.id,
                        competitor_name=name,
                        summary=f"Extension analysis for {name} on dimension: {dim.title}.",
                        bullets=[f"Signal derived from {len(dim_source_ids)} sources."],
                        source_ids=dim_source_ids,
                    )
                )

        structured_profiles = {
            competitor.name: structured_profiles[competitor.name]
            for competitor in state.scope_contract.competitors
            if competitor.name in structured_profiles
        }
        cross = self._build_cross_analysis(structured_profiles)
        return structured_profiles, extension_findings, cross

    def _build_cross_analysis(
        self, profiles: dict[str, StructuredCompetitorProfile]
    ) -> CrossCompetitorAnalysis:
        # Collect all unique feature names across profiles
        feature_names: list[str] = []
        seen: set[str] = set()
        for profile in profiles.values():
            for row in profile.feature_tree.get("rows") or []:
                feat = str(row.get("feature", ""))
                if feat and feat not in seen:
                    feature_names.append(feat)
                    seen.add(feat)

        # Build cross-competitor feature matrix rows
        matrix_rows: list[dict] = []
        for feat in feature_names:
            cells: list[dict] = []
            source_ids: list[str] = []
            for name, profile in profiles.items():
                rows_list = profile.feature_tree.get("rows") or []
                row = next(
                    (r for r in rows_list if r.get("feature") == feat),
                    None,
                )
                if row:
                    competitor_cell = next(
                        (c for c in (row.get("cells") or []) if c.get("competitor") == name),
                        {"competitor": name, "status": "unknown", "note": ""},
                    )
                    cells.append(_canonical_feature_cell(competitor_cell, name))
                    source_ids.extend(row.get("source_ids") or [])
                else:
                    cells.append({"competitor": name, "status": "unknown", "note": ""})
            matrix_rows.append(
                {
                    "feature": feat,
                    "cells": cells,
                    "source_ids": list(dict.fromkeys(source_ids)),
                }
            )

        pricing_comparison = {name: profile.pricing for name, profile in profiles.items()}
        competitors = list(profiles.keys())
        cross = CrossCompetitorAnalysis(
            feature_matrix={"rows": matrix_rows, "competitors": competitors},
            pricing_comparison=pricing_comparison,
            differentiation_summary=(
                f"Cross-analysis of {len(profiles)} competitors covering "
                "features, pricing, personas, and SWOT."
            ),
        )
        cross.positioning_map = _build_positioning_map(cross, profiles)
        return cross

    async def _enrich_cross_matrix(
        self,
        cross: CrossCompetitorAnalysis,
        profiles: dict[str, StructuredCompetitorProfile],
        raw_collections: dict[str, RawCollectionResult],
        llm: LLMClient,
        language: str,
    ) -> CrossCompetitorAnalysis:
        """Fill ``unknown`` matrix cells via a second, *evidence-gated* LLM pass.

        Each competitor's feature_tree is extracted independently, so the unioned
        cross matrix is sparse: a feature one competitor documents is ``unknown``
        for every other. We re-ask the model — per competitor, over that
        competitor's own sources — to classify only the gap features. A
        classification is accepted **only** when the model cites source_ids that
        actually belong to that competitor; otherwise the cell stays ``unknown``.
        This keeps the fill strictly grounded and immune to world-knowledge
        guessing. Enrichment never blocks the run: any failure leaves the matrix
        as-is.
        """
        rows = cross.feature_matrix.get("rows") or []
        competitors = cross.feature_matrix.get("competitors") or []
        if not rows or not competitors:
            return cross

        settings = get_settings()
        targets: list[tuple[str, list[str], RawCollectionResult]] = []
        for name in competitors:
            result = raw_collections.get(name)
            if result is None:
                continue
            gap_features = [
                str(row.get("feature", "")) for row in rows if self._cell_is_unknown(row, name)
            ]
            gap_features = [f for f in gap_features if f]
            if gap_features:
                targets.append((name, gap_features, result))

        async def classify(
            name: str, gap_features: list[str], result: RawCollectionResult
        ) -> tuple[str, RawCollectionResult, dict[str, Any] | None]:
            try:
                payload = await llm.complete_json(
                    provider="deepseek",
                    model=settings.analyst_model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are AnalystAgent (cross-fill). For the given competitor, "
                                "classify each listed feature using ONLY the provided sources. "
                                'Return JSON {"features":[{"feature":"<exact name>","status":'
                                '"supported|partial|unsupported","note":"evidence-backed note",'
                                '"source_ids":["src_id"]}]}. status and source_ids are required: '
                                "every classification must cite source_ids copied from the "
                                "provided sources. If a feature has no supporting evidence in "
                                "these sources, OMIT it entirely — never guess from prior "
                                "knowledge, never output unknown/TBD/需验证."
                                + language_instruction(language)
                            ),
                        },
                        {
                            "role": "user",
                            "content": (
                                f"Competitor: {name}\n"
                                f"Features to classify: {gap_features}\n"
                                f"Sources: {_sources_for_prompt(result.sources)}"
                            ),
                        },
                    ],
                )
            except Exception as exc:
                logger.warning("analyst_cross_fill_failed", competitor=name, exc_info=True)
                record_degradation(f"analyst_cross_fill: {type(exc).__name__}: {exc}")
                return name, result, None
            return name, result, payload

        # Fan the per-competitor gap-fill calls out concurrently, then apply the
        # results sequentially so concurrent writes never race on shared rows.
        fills = await asyncio.gather(*(classify(*target) for target in targets))
        for name, result, payload in fills:
            if payload is None:
                continue
            valid_ids = {s.id for s in result.sources}
            classified = self._accepted_classifications(payload.get("features"), valid_ids)
            for row in rows:
                info = classified.get(str(row.get("feature", "")))
                if info is None:
                    continue
                for cell in row.get("cells") or []:
                    if cell.get("competitor") == name and self._cell_is_unknown(row, name):
                        cell["status"] = info["status"]
                        cell["note"] = info["note"]
                row["source_ids"] = list(
                    dict.fromkeys([*(row.get("source_ids") or []), *info["source_ids"]])
                )
        cross.positioning_map = _build_positioning_map(cross, profiles)
        return cross

    @staticmethod
    def _cell_is_unknown(row: dict[str, Any], competitor: str) -> bool:
        return any(
            cell.get("competitor") == competitor
            and _canonical_feature_status(cell.get("status")) == "unknown"
            for cell in row.get("cells") or []
        )

    @staticmethod
    def _accepted_classifications(items: Any, valid_ids: set[str]) -> dict[str, dict[str, Any]]:
        """Keep only classifications that name a real status AND cite the
        competitor's own sources — the evidence gate against hallucination."""
        accepted: dict[str, dict[str, Any]] = {}
        if not isinstance(items, list):
            return accepted
        for item in items:
            if not isinstance(item, dict):
                continue
            feat = str(item.get("feature") or "").strip()
            status = _canonical_feature_status(item.get("status"))
            cited = [sid for sid in (item.get("source_ids") or []) if sid in valid_ids]
            if not feat or status == "unknown" or not cited:
                continue
            accepted[feat] = {
                "status": status,
                "note": str(item.get("note") or ""),
                "source_ids": cited,
            }
        return accepted
