from typing import Any

import structlog

from graph.state import (
    CrossCompetitorAnalysis,
    ExtensionFinding,
    StructuredCompetitorProfile,
    WorkflowState,
)
from schemas.source import SourceCitation
from services.agents.decorators import traced_node
from services.llm import LLMClient
from services.llm.usage import record_degradation
from settings import get_settings

logger = structlog.get_logger(__name__)

# Full fetched page bodies (``raw_content``) can be tens of KB each; dumping all
# of them per competitor bloats the prompt and slows generation. Keep enough for
# evidence-grounded extraction without sending whole articles.
_MAX_RAW_CONTENT_CHARS = 5000
_MAX_COMPETITOR_RAW_CONTENT_CHARS = 24000


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
                            "Every source_ids value must be copied from the provided sources. "
                            "Do not output placeholder text such as 需验证, 待确认, 标准版, "
                            "unknown, TBD, or needs verification. If evidence is missing, "
                            "leave the specific list empty instead of inventing a placeholder. "
                            "description, note, evidence, highlights, and SWOT text must "
                            "contain concrete evidence such as numbers, version names, quoted "
                            "phrases, pricing rules, or clearly attributed product facts. "
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
            )
            source_ids = [s.id for s in result.sources]
            structured_profiles[name] = StructuredCompetitorProfile(
                competitor_name=name,
                feature_tree=_coerce_mapping(core_payload.get("feature_tree")),
                pricing=_coerce_mapping(core_payload.get("pricing")),
                user_personas=_coerce_personas(core_payload.get("user_personas")),
                swot=_coerce_mapping(core_payload.get("swot")),
                source_ids=source_ids,
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
                    "weaknesses": [{"text": "insufficient evidence", "source_ids": []}],
                    "opportunities": [{"text": "AI 辅助分析", "source_ids": []}],
                    "threats": [{"text": "竞品快速迭代", "source_ids": []}],
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
                    cells.append(competitor_cell)
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
