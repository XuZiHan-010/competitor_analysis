import asyncio
from functools import partial
from urllib.parse import quote_plus

import structlog

from graph.state import RawCollectionResult, WorkflowState
from schemas.scope import ScopeDimension
from schemas.source import SourceCitation
from services.agents.decorators import traced_node
from services.agents.wrappers import ToolError, run_tool_safely
from services.llm import LLMClient
from services.scraper import PageFetcher
from services.search import AppReviewProvider, HybridSearch
from services.search.providers import SearchProvider
from services.search.serpapi import SerpApiProvider
from services.search.tavily import TavilyProvider
from services.survey.existing_survey_finder import ExistingSurveyFinder
from services.survey.tool import SurveyTool
from settings import get_settings

_COLLECTOR_TIMEOUT_S = 60

logger = structlog.get_logger(__name__)


class CollectorAgent:
    @traced_node(
        agent_name="CollectorAgent",
        node_name="run_collector",
        prompt="Collect public sources and app review signals for each competitor.",
    )
    async def run(
        self,
        state: WorkflowState,
        *,
        trace_context: object | None = None,
    ) -> tuple[dict[str, RawCollectionResult], dict]:
        settings = get_settings()
        if not settings.mock_llm:
            providers: list[SearchProvider] = []
            if settings.tavily_api_key:
                providers.append(TavilyProvider(settings.tavily_api_key))
            if settings.serpapi_api_key:
                providers.append(SerpApiProvider(settings.serpapi_api_key))
            if providers:
                search = HybridSearch(providers)
                llm = LLMClient(settings)
                raw = await self._run_real_collection(state, search, llm=llm)
                survey = await SurveyTool(
                    existing_survey_finder=ExistingSurveyFinder(search),
                    llm_client=llm,
                ).run(
                    state.model_copy(update={"raw_collections": raw}),
                    trace_context=trace_context,
                )
                return raw, survey
        raw = await self._run_fallback_collection(state)
        survey = await SurveyTool().run(
            state.model_copy(update={"raw_collections": raw}),
            trace_context=trace_context,
        )
        return raw, survey

    def _build_dimension_queries(
        self, competitor_name: str, dimensions: list[ScopeDimension]
    ) -> list[tuple[str, str]]:
        """Return (dimension_id, query) pairs for enabled dimensions."""
        queries: list[tuple[str, str]] = []
        for dim in dimensions:
            if not dim.enabled:
                continue
            if dim.layer == "core":
                if dim.id == "core.feature_tree":
                    queries.append((dim.id, f"{competitor_name} features product capabilities"))
                elif dim.id == "core.pricing":
                    queries.append((dim.id, f"{competitor_name} pricing plans subscription"))
                elif dim.id == "core.persona":
                    queries.append((dim.id, f"{competitor_name} target users reviews who uses"))
                elif dim.id == "core.swot":
                    queries.append((dim.id, f"{competitor_name} strengths weaknesses analysis"))
            else:
                # Extension dim: use intent to rewrite query
                queries.append((dim.id, f"{competitor_name} {dim.intent}"))
        if not queries:
            queries.append(("default", f"{competitor_name} pricing features user reviews"))
        return queries

    def _build_feedback_queries(
        self,
        competitor_name: str,
        dimensions: list[ScopeDimension],
        failed_fields: list[str],
    ) -> list[tuple[str, str]]:
        """Augment base queries with targeted recovery queries for QA-reported failed fields."""
        base = self._build_dimension_queries(competitor_name, dimensions)
        extra: list[tuple[str, str]] = []
        joined = " ".join(failed_fields).lower()
        if "pricing" in joined:
            extra.append((
                "core.pricing",
                f"{competitor_name} pricing cost subscription fee plans 2024",
            ))
        if "feature" in joined or "feature_tree" in joined:
            extra.append((
                "core.feature_tree",
                f"{competitor_name} product features capabilities detailed comparison",
            ))
        if "source_ids" in joined or "sources" in joined:
            extra.append((
                "default",
                f"{competitor_name} official site product overview documentation",
            ))
        if "swot" in joined:
            extra.append((
                "core.swot",
                f"{competitor_name} strengths weaknesses market position analysis",
            ))
        if "persona" in joined or "user_personas" in joined:
            extra.append((
                "core.persona",
                f"{competitor_name} target customers user reviews who uses",
            ))
        return base + extra

    async def _rewrite_queries(
        self,
        competitor_name: str,
        base_queries: list[tuple[str, str]],
        llm: LLMClient | None,
    ) -> list[tuple[str, str]]:
        """Rewrite static search queries with Gemini (PRD §五.X / §284).

        Falls back to the original queries on any failure or when Gemini is
        unavailable, so collection degrades gracefully rather than aborting.
        """
        settings = get_settings()
        if llm is None or not llm.enabled or not settings.gemini_api_key:
            return base_queries
        try:
            payload = await llm.complete_json(
                provider="gemini",
                model=settings.collector_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are CollectorAgent's search planner. Rewrite each query to "
                            "maximize retrieval of high-signal public sources (official docs, "
                            "pricing pages, credible reviews). Preserve every dimension_id "
                            'exactly. Return JSON {"queries": [{"dimension_id": str, '
                            '"query": str}]}.'
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Competitor: {competitor_name}\n"
                            f"Queries: {[{'dimension_id': d, 'query': q} for d, q in base_queries]}"
                        ),
                    },
                ],
            )
        except Exception:
            logger.warning("collector_query_rewrite_failed", competitor=competitor_name)
            return base_queries
        rewritten = payload.get("queries")
        if not isinstance(rewritten, list):
            return base_queries
        result = [
            (str(item["dimension_id"]), str(item["query"]))
            for item in rewritten
            if isinstance(item, dict) and item.get("dimension_id") and item.get("query")
        ]
        return result or base_queries

    async def _run_real_collection(
        self,
        state: WorkflowState,
        search: HybridSearch,
        app_reviews: AppReviewProvider | None = None,
        fetcher: PageFetcher | None = None,
        llm: LLMClient | None = None,
    ) -> dict[str, RawCollectionResult]:
        app_reviews = app_reviews or AppReviewProvider()
        fetcher = fetcher or PageFetcher()

        # When QA detected blockers, re-run with targeted recovery queries
        correction = state.feedback_signals.get("correction_detected")
        failed_fields: list[str] = []
        if correction and isinstance(correction, dict):
            failed_fields = [
                issue.get("failed_field", "")
                for issue in correction.get("issues", [])
                if issue.get("failed_field")
            ]

        def _queries(competitor_name: str) -> list[tuple[str, str]]:
            if failed_fields:
                return self._build_feedback_queries(
                    competitor_name, state.scope_contract.dimensions, failed_fields
                )
            return self._build_dimension_queries(competitor_name, state.scope_contract.dimensions)

        query_map: dict[str, list[tuple[str, str]]] = {}
        for competitor in state.scope_contract.competitors:
            base_queries = _queries(competitor.name)
            query_map[competitor.name] = await self._rewrite_queries(
                competitor.name, base_queries, llm
            )

        tasks = {
            competitor.name: asyncio.wait_for(
                self._collect_real_competitor(
                    competitor.name,
                    search,
                    app_reviews,
                    fetcher,
                    dimension_queries=query_map[competitor.name],
                ),
                timeout=_COLLECTOR_TIMEOUT_S,
            )
            for competitor in state.scope_contract.competitors
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        output: dict[str, RawCollectionResult] = {}
        for name, result in zip(tasks.keys(), results, strict=False):
            if isinstance(result, BaseException):
                output[name] = RawCollectionResult(
                    competitor_name=name,
                    sources=[],
                    errors=[f"collection_timeout_or_error: {result}"],
                )
            else:
                output[name] = result
        return output

    async def _collect_fallback_competitor(self, competitor_name: str) -> RawCollectionResult:
        source_id = f"src_{quote_plus(competitor_name.lower())}_001"
        sources = [
            SourceCitation(
                id=source_id,
                type="official",
                category="official",
                url="https://example.com",
                title=f"{competitor_name} official overview",
                snippet=f"Fallback source for {competitor_name}.",
                provider="fallback_web_search",
            ),
            SourceCitation(
                id=f"{source_id}_review",
                type="app_review",
                category="user_feedback",
                url="https://example.com/reviews",
                title=f"{competitor_name} public reviews",
                snippet=f"Fallback app review signal for {competitor_name}.",
                provider="fallback_app_review_fetch",
            ),
        ]
        return RawCollectionResult(
            competitor_name=competitor_name,
            completeness_score=min(len(sources) / 5, 1.0),
            sources=sources,
        )

    async def _collect_feedback_fallback_competitor(
        self,
        competitor_name: str,
    ) -> RawCollectionResult:
        base = await self._collect_fallback_competitor(competitor_name)
        source_prefix = f"src_{quote_plus(competitor_name.lower())}"
        recovery_sources = [
            SourceCitation(
                id=f"{source_prefix}_pricing_recovery",
                type="commercial",
                category="commercial",
                url="https://example.com/pricing",
                title=f"{competitor_name} pricing recovery source",
                snippet=f"Recovered pricing and packaging signal for {competitor_name}.",
                provider="feedback_recovery",
                dimension_id="core.pricing",
            ),
            SourceCitation(
                id=f"{source_prefix}_feature_recovery",
                type="media",
                category="media",
                url="https://example.com/features",
                title=f"{competitor_name} feature recovery source",
                snippet=f"Recovered feature comparison signal for {competitor_name}.",
                provider="feedback_recovery",
                dimension_id="core.feature_tree",
            ),
            SourceCitation(
                id=f"{source_prefix}_persona_recovery",
                type="user_feedback",
                category="user_feedback",
                url="https://example.com/persona",
                title=f"{competitor_name} persona recovery source",
                snippet=f"Recovered user persona signal for {competitor_name}.",
                provider="feedback_recovery",
                dimension_id="core.persona",
            ),
        ]
        sources = [*base.sources, *recovery_sources]
        return RawCollectionResult(
            competitor_name=competitor_name,
            completeness_score=min(len(sources) / 5, 1.0),
            sources=sources,
        )

    async def _collect_real_competitor(
        self,
        competitor_name: str,
        search: HybridSearch,
        app_reviews: AppReviewProvider,
        fetcher: PageFetcher,
        dimension_queries: list[tuple[str, str]] | None = None,
    ) -> RawCollectionResult:
        skipped_urls: list[str] = []
        errors: list[str] = []
        sources: list[SourceCitation] = []

        for dimension_id, query in dimension_queries or []:
            search_result = await run_tool_safely(
                "web_search", partial(search.search, query, max_results=5)
            )
            if isinstance(search_result, ToolError):
                errors.append(f"search({query}): {search_result.error_content}")
            else:
                # Tag each source with the dimension that produced it
                sources.extend(
                    s.model_copy(update={"dimension_id": dimension_id}) for s in search_result
                )

        review_result = await run_tool_safely(
            "app_review_fetch",
            lambda: app_reviews.fetch_reviews(competitor_name, max_results=2),
        )
        if isinstance(review_result, ToolError):
            errors.append(f"app_reviews: {review_result.error_content}")
        else:
            sources.extend(review_result)

        enriched_sources: list[SourceCitation] = []
        for source in sources:
            if not source.url:
                enriched_sources.append(source)
                continue
            fetch_result = await run_tool_safely(
                "fetch_page", partial(fetcher.fetch_page, str(source.url))
            )
            if isinstance(fetch_result, ToolError):
                errors.append(f"fetch_page {source.url}: {fetch_result.error_content}")
                enriched_sources.append(source)
                continue
            if fetch_result.skipped:
                skipped_urls.append(fetch_result.url)
                continue
            enriched_sources.append(
                source.model_copy(
                    update={
                        "raw_content": fetch_result.content,
                        "snippet": source.snippet or fetch_result.content[:500],
                        "title": source.title or fetch_result.title,
                    }
                )
            )

        completeness = min(len(enriched_sources) / 5, 1.0)
        return RawCollectionResult(
            competitor_name=competitor_name,
            sources=enriched_sources,
            completeness_score=completeness,
            skipped_urls=skipped_urls,
            errors=errors,
        )

    async def _run_fallback_collection(
        self, state: WorkflowState
    ) -> dict[str, RawCollectionResult]:
        recovery_mode = bool(state.feedback_signals.get("correction_detected")) or (
            state.retry_counts.get("collector", 0) > 0
        )
        tasks = [
            (
                self._collect_feedback_fallback_competitor(competitor.name)
                if recovery_mode
                else self._collect_fallback_competitor(competitor.name)
            )
            for competitor in state.scope_contract.competitors
        ]
        results = await asyncio.gather(*tasks)
        return {r.competitor_name: r for r in results}
