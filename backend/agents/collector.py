import asyncio
import re
from functools import partial
from urllib.parse import quote_plus
from uuid import UUID

import structlog

from graph.state import RawCollectionResult, WorkflowState
from schemas.scope import ScopeDimension
from schemas.source import SourceCitation
from schemas.survey import SurveyResult
from services.agents.decorators import traced_node
from services.agents.wrappers import ToolError, run_tool_safely
from services.llm import LLMClient
from services.scraper import FetchResult, PageFetcher
from services.search import AppReviewProvider, HybridSearch
from services.search.providers import SearchProvider
from services.search.relevance import filter_relevant_sources
from services.search.serpapi import SerpApiProvider
from services.search.tavily import TavilyProvider
from services.survey.existing_survey_finder import ExistingSurveyFinder
from services.survey.tool import SurveyTool
from settings import get_settings

_COLLECTOR_TIMEOUT_S = 60

logger = structlog.get_logger(__name__)


def _normalize_raw_source_ids(
    raw: dict[str, RawCollectionResult],
    task_id: UUID,
) -> dict[str, dict[str, str]]:
    task_slug = task_id.hex[:8]
    next_sequence = 1
    emitted: set[str] = set()
    source_id_maps: dict[str, dict[str, str]] = {}

    for result in raw.values():
        for source in result.sources:
            sequence = _normalized_source_sequence(source.id, task_slug)
            if sequence is not None:
                next_sequence = max(next_sequence, sequence + 1)

    for competitor_name, result in raw.items():
        remapped_sources: list[SourceCitation] = []
        source_id_map: dict[str, str] = {}
        for source in result.sources:
            original_id = source.id
            if (
                _normalized_source_sequence(original_id, task_slug) is not None
                and original_id not in emitted
            ):
                source_id = original_id
            else:
                provider = _source_provider_slug(source.provider)
                source_id = f"src_{provider}_{task_slug}_{next_sequence:03d}"
                next_sequence += 1
            emitted.add(source_id)
            source_id_map.setdefault(original_id, source_id)
            remapped_sources.append(source.model_copy(update={"id": source_id}))
        result.sources = remapped_sources
        source_id_maps[competitor_name] = source_id_map
    return source_id_maps


def _remap_survey_source_ids(
    survey_results: dict[str, SurveyResult],
    source_id_maps: dict[str, dict[str, str]],
) -> None:
    for competitor_name, survey in survey_results.items():
        source_id_map = source_id_maps.get(competitor_name, {})
        survey.evidence = [
            evidence.model_copy(
                update={"source_id": source_id_map.get(evidence.source_id, evidence.source_id)}
            )
            for evidence in survey.evidence
        ]


def _source_provider_slug(provider: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", provider.lower()).strip("_") or "source"


def _normalized_source_sequence(source_id: str, task_slug: str) -> int | None:
    marker = f"_{task_slug}_"
    if not source_id.startswith("src_") or marker not in source_id:
        return None
    suffix = source_id.rsplit(marker, maxsplit=1)[-1]
    return int(suffix) if suffix.isdigit() else None


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
        providers: list[SearchProvider] = []
        if not settings.mock_llm and settings.tavily_api_key:
            providers.append(TavilyProvider(settings.tavily_api_key))
        if not settings.mock_llm and settings.serpapi_api_key:
            providers.append(SerpApiProvider(settings.serpapi_api_key))
        if providers:
            search = HybridSearch(providers)
            llm = LLMClient(settings)
            raw = await self._run_real_collection(state, search, llm=llm)
            _normalize_raw_source_ids(raw, state.task_id)
            survey = await SurveyTool(
                existing_survey_finder=ExistingSurveyFinder(search),
                llm_client=llm,
            ).run(
                state.model_copy(update={"raw_collections": raw}),
                trace_context=trace_context,
            )
            source_id_maps = _normalize_raw_source_ids(raw, state.task_id)
            _remap_survey_source_ids(survey, source_id_maps)
            return raw, survey
        raw = await self._run_fallback_collection(state)
        _normalize_raw_source_ids(raw, state.task_id)
        survey = await SurveyTool().run(
            state.model_copy(update={"raw_collections": raw}),
            trace_context=trace_context,
        )
        source_id_maps = _normalize_raw_source_ids(raw, state.task_id)
        _remap_survey_source_ids(survey, source_id_maps)
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
        """Rewrite static search queries with the collector LLM (PRD §五.X / §284).

        Falls back to the original queries on any failure or when the LLM is
        unavailable, so collection degrades gracefully rather than aborting.
        """
        settings = get_settings()
        if llm is None or not llm.enabled or not settings.openai_api_key:
            return base_queries
        try:
            payload = await llm.complete_json(
                provider="openai",
                model=settings.collector_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are CollectorAgent's search planner. Rewrite each query to "
                            "maximize retrieval of high-signal public sources in the product's "
                            "likely market language. Prefer official sites, product pages, "
                            "app stores, pricing pages, credible reviews, and industry media. "
                            "Explicitly avoid academic papers, satisfaction models, literature "
                            "reviews, and sources that only mention the product as a research "
                            "sample. Preserve every dimension_id exactly. Return JSON "
                            '{"queries": [{"dimension_id": str, "query": str}]}.'
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
        except Exception as exc:
            logger.warning(
                "collector_query_rewrite_failed",
                competitor=competitor_name,
                error=str(exc),
                error_type=type(exc).__name__,
            )
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
                    llm,
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
        _normalize_raw_source_ids(output, state.task_id)
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
        llm: LLMClient | None = None,
        dimension_queries: list[tuple[str, str]] | None = None,
    ) -> RawCollectionResult:
        skipped_urls: list[str] = []
        errors: list[str] = []
        sources: list[SourceCitation] = []

        # Run all dimension searches concurrently; a slow provider on one query no
        # longer serializes behind the others.
        search_results = await asyncio.gather(
            *(
                run_tool_safely("web_search", partial(search.search, query, max_results=10))
                for _, query in dimension_queries or []
            )
        )
        for (dimension_id, query), search_result in zip(
            dimension_queries or [], search_results, strict=True
        ):
            if isinstance(search_result, ToolError):
                errors.append(f"search({query}): {search_result.error_content}")
            else:
                # Tag each source with the dimension that produced it
                sources.extend(
                    s.model_copy(update={"dimension_id": dimension_id}) for s in search_result
                )

        review_result = await run_tool_safely(
            "app_review_fetch",
            lambda: app_reviews.fetch_reviews(competitor_name, max_results=5),
        )
        if isinstance(review_result, ToolError):
            errors.append(f"app_reviews: {review_result.error_content}")
        else:
            sources.extend(review_result)

        relevant = await filter_relevant_sources(competitor_name, sources, llm)
        sources = relevant.kept
        errors.extend(
            f"dropped_irrelevant: {source.url or source.id}" for source in relevant.dropped
        )

        # Enrich every page in one batched, single-browser pass instead of
        # launching a browser per URL. A skip/fetch failure keeps the original
        # search citation (with its snippet) rather than dropping the source, so
        # robots-blocked or flaky pages can't starve the QA ≥5-sources floor.
        fetch_urls = [str(source.url) for source in sources if source.url]
        fetched = await run_tool_safely("fetch_pages", partial(fetcher.fetch_pages, fetch_urls))
        if isinstance(fetched, ToolError):
            errors.append(f"fetch_pages: {fetched.error_content}")
            results_by_url: dict[str, FetchResult] = {}
        else:
            results_by_url = {result.url: result for result in fetched}

        enriched_sources: list[SourceCitation] = []
        for source in sources:
            if not source.url:
                enriched_sources.append(source)
                continue
            fetch_result = results_by_url.get(str(source.url))
            if fetch_result is None or fetch_result.skipped:
                if fetch_result is not None and fetch_result.skip_reason == "robots.txt":
                    skipped_urls.append(str(source.url))
                elif fetch_result is not None:
                    errors.append(f"fetch_page {source.url}: {fetch_result.skip_reason}")
                enriched_sources.append(source)
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

        post_fetch_relevance = await filter_relevant_sources(
            competitor_name,
            enriched_sources,
            llm,
            include_raw_content=True,
        )
        if post_fetch_relevance.dropped:
            enriched_sources = post_fetch_relevance.kept
            errors.extend(
                f"dropped_irrelevant: {source.url or source.id}"
                for source in post_fetch_relevance.dropped
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
        raw = {r.competitor_name: r for r in results}
        _normalize_raw_source_ids(raw, state.task_id)
        return raw
