from typing import Any

import structlog

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
        structured_profiles: dict[str, StructuredCompetitorProfile] = {}
        extension_findings: list[ExtensionFinding] = []

        core_dims = [d for d in state.scope_contract.dimensions if d.layer == "core" and d.enabled]
        ext_dims = [
            d for d in state.scope_contract.dimensions if d.layer == "extension" and d.enabled
        ]

        for name, result in state.raw_collections.items():
            sources_payload = _sources_for_prompt(result.sources)

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
                            '"threats":[]}}.'
                            + lang_directive
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
            source_ids = [s.id for s in result.sources]
            feature_tree = _coerce_mapping(core_payload.get("feature_tree"))
            pricing = _coerce_mapping(core_payload.get("pricing"))
            user_personas = _coerce_personas(core_payload.get("user_personas"))
            swot = _coerce_mapping(core_payload.get("swot"))
            structured_profiles[name] = StructuredCompetitorProfile(
                competitor_name=name,
                feature_tree=feature_tree,
                pricing=pricing,
                user_personas=user_personas,
                swot=swot,
                source_ids=_cited_source_ids(
                    feature_tree, pricing, user_personas, swot, set(source_ids)
                ),
            )

            # Extension layer: generic extractor per dimension with intent injected
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
                                "unknown, TBD, or needs verification; omit unsupported points."
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
                extension_findings.append(
                    ExtensionFinding(
                        dimension_id=dim.id,
                        competitor_name=name,
                        summary=str(ext_payload.get("summary", "")),
                        bullets=ext_payload.get("bullets") or [],
                        table_data=ext_payload.get("table_data") or [],
                        source_ids=ext_payload.get("source_ids") or source_ids,
                    )
                )

        cross = self._build_cross_analysis(structured_profiles)
        cross = await self._enrich_cross_matrix(
            cross, structured_profiles, state.raw_collections, llm, language
        )
        return structured_profiles, extension_findings, cross

    def _run_fallback(
        self, state: WorkflowState
    ) -> tuple[
        dict[str, StructuredCompetitorProfile],
        list[ExtensionFinding],
        CrossCompetitorAnalysis | None,
    ]:
        structured_profiles: dict[str, StructuredCompetitorProfile] = {}
        extension_findings: list[ExtensionFinding] = []
        ext_dims = [
            d for d in state.scope_contract.dimensions if d.layer == "extension" and d.enabled
        ]

        for name, result in state.raw_collections.items():
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
                extension_findings.append(
                    ExtensionFinding(
                        dimension_id=dim.id,
                        competitor_name=name,
                        summary=f"Extension analysis for {name} on dimension: {dim.title}.",
                        bullets=[f"Signal derived from {len(source_ids)} sources."],
                        source_ids=source_ids,
                    )
                )

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
            matrix_rows.append({
                "feature": feat,
                "cells": cells,
                "source_ids": list(dict.fromkeys(source_ids)),
            })

        pricing_comparison = {
            name: profile.pricing for name, profile in profiles.items()
        }
        competitors = list(profiles.keys())
        return CrossCompetitorAnalysis(
            feature_matrix={"rows": matrix_rows, "competitors": competitors},
            pricing_comparison=pricing_comparison,
            differentiation_summary=(
                f"Cross-analysis of {len(profiles)} competitors covering "
                "features, pricing, personas, and SWOT."
            ),
        )

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
        for name in competitors:
            result = raw_collections.get(name)
            if result is None:
                continue
            gap_features = [
                str(row.get("feature", ""))
                for row in rows
                if self._cell_is_unknown(row, name)
            ]
            gap_features = [f for f in gap_features if f]
            if not gap_features:
                continue

            valid_ids = {s.id for s in result.sources}
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
                continue

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
        return cross

    @staticmethod
    def _cell_is_unknown(row: dict[str, Any], competitor: str) -> bool:
        return any(
            cell.get("competitor") == competitor
            and _canonical_feature_status(cell.get("status")) == "unknown"
            for cell in row.get("cells") or []
        )

    @staticmethod
    def _accepted_classifications(
        items: Any, valid_ids: set[str]
    ) -> dict[str, dict[str, Any]]:
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
