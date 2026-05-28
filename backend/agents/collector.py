import asyncio
from urllib.parse import quote_plus

from graph.state import RawCollectionResult, WorkflowState
from schemas.scope import ScopeDimension
from schemas.source import SourceCitation
from services.agents.decorators import traced_node
from services.agents.wrappers import ToolError, run_tool_safely
from services.scraper import PageFetcher
from services.search import AppReviewProvider, HybridSearch
from services.search.providers import SearchProvider
from services.search.serpapi import SerpApiProvider
from services.search.tavily import TavilyProvider
from services.survey.tool import SurveyTool
from settings import get_settings

_COLLECTOR_TIMEOUT_S = 60


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
                raw = await self._run_real_collection(state, HybridSearch(providers))
                survey = SurveyTool().run(
                    state.model_copy(update={"raw_collections": raw})
                )
                return raw, survey
        raw = await self._run_fallback_collection(state)
        survey = SurveyTool().run(state.model_copy(update={"raw_collections": raw}))
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

    async def _run_real_collection(
        self,
        state: WorkflowState,
        search: HybridSearch,
        app_reviews: AppReviewProvider | None = None,
        fetcher: PageFetcher | None = None,
    ) -> dict[str, RawCollectionResult]:
        app_reviews = app_reviews or AppReviewProvider()
        fetcher = fetcher or PageFetcher()
        tasks = {
            competitor.name: asyncio.wait_for(
                self._collect_real_competitor(
                    competitor.name,
                    search,
                    app_reviews,
                    fetcher,
                    dimension_queries=self._build_dimension_queries(
                        competitor.name, state.scope_contract.dimensions
                    ),
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
        return RawCollectionResult(
            competitor_name=competitor_name,
            completeness_score=0.3,
            sources=[
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
            ],
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

        for dimension_id, query in (dimension_queries or []):
            search_result = await run_tool_safely(
                "web_search", lambda q=query: search.search(q, max_results=5)
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
                "fetch_page", lambda url=str(source.url): fetcher.fetch_page(url)
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
        tasks = [
            self._collect_fallback_competitor(competitor.name)
            for competitor in state.scope_contract.competitors
        ]
        results = await asyncio.gather(*tasks)
        return {r.competitor_name: r for r in results}
