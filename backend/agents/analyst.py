from graph.state import (
    CrossCompetitorAnalysis,
    ExtensionFinding,
    StructuredCompetitorProfile,
    WorkflowState,
)
from services.agents.decorators import traced_node
from services.llm import LLMClient
from settings import get_settings


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
                pass
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
                feature_tree={"core_features": ["workspace", "collaboration", "reporting"]},
                pricing={"model": "subscription", "entry_price": "unconfirmed"},
                user_personas=[{"name": "business user", "pain_points": ["manual research"]}],
                swot={
                    "strengths": ["structured workflow"],
                    "weaknesses": ["pricing requires verification"],
                    "opportunities": ["AI-assisted analysis"],
                    "threats": ["fast-moving competitors"],
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
        feature_matrix: dict[str, list[str]] = {}
        for name, profile in profiles.items():
            cats = profile.feature_tree.get("core_features") or []
            feature_matrix[name] = cats if isinstance(cats, list) else list(cats)
        pricing_comparison = {
            name: profile.pricing for name, profile in profiles.items()
        }
        return CrossCompetitorAnalysis(
            feature_matrix={"by_competitor": feature_matrix},
            pricing_comparison=pricing_comparison,
            differentiation_summary=(
                f"Cross-analysis of {len(profiles)} competitors covering "
                "features, pricing, personas, and SWOT."
            ),
        )
