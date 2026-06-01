import structlog

from graph.state import (
    CrossCompetitorAnalysis,
    ExtensionFinding,
    StructuredCompetitorProfile,
    WorkflowState,
)
from services.agents.decorators import traced_node
from services.llm import LLMClient
from settings import get_settings

logger = structlog.get_logger(__name__)


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
        if llm.enabled and settings.deepseek_api_key:
            try:
                return await self._run_llm(state, llm)
            except Exception:
                logger.warning("analyst_llm_failed_falling_back", exc_info=True)
        return self._run_fallback(state)

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
            sources_payload = [s.model_dump(mode="json") for s in result.sources]

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
                            "Every field must reference source_ids from provided sources."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Competitor: {name}\n"
                            f"Core dimensions: {[d.model_dump() for d in core_dims]}\n"
                            f"Sources: {[s.model_dump(mode='json') for s in core_sources] or sources_payload}"  # noqa: E501
                        ),
                    },
                ],
            )
            source_ids = [s.id for s in result.sources]
            structured_profiles[name] = StructuredCompetitorProfile(
                competitor_name=name,
                feature_tree=core_payload.get("feature_tree") or {},
                pricing=core_payload.get("pricing") or {},
                user_personas=core_payload.get("user_personas") or [],
                swot=core_payload.get("swot") or {},
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
                                "table_data (list[dict]), source_ids (list[str])."
                            ),
                        },
                        {
                            "role": "user",
                            "content": (
                                f"Competitor: {name}\n"
                                f"Dimension intent: {dim.intent}\n"
                                f"Sources: {[s.model_dump(mode='json') for s in dim_sources] or sources_payload}"  # noqa: E501
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
                                {"competitor": name, "status": "supported", "note": "需验证"}
                            ],
                            "source_ids": source_ids[:1],
                        }
                    ]
                },
                pricing={
                    "tiers": [
                        {
                            "competitor": name,
                            "tier": "标准版",
                            "price": "待确认",
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
                        "evidence": "待补充",
                        "source_ids": source_ids[:1],
                    }
                ],
                swot={
                    "strengths": [{"text": "结构化工作流", "source_ids": source_ids[:1]}],
                    "weaknesses": [{"text": "定价待验证", "source_ids": []}],
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
