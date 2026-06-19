import asyncio

from agents.collector import CollectorAgent
from schemas.source import SourceCitation
from services.scraper import FetchResult


class _FakeSearch:
    def __init__(self, per_query: int = 2) -> None:
        self._per_query = per_query

    async def search(self, query: str, max_results: int = 5) -> list[SourceCitation]:
        return [
            SourceCitation(
                id=f"src_{abs(hash((query, i)))}",
                type="media",
                category="media",
                url=f"https://example.com/{abs(hash((query, i)))}",
                title=f"{query} result {i}",
                snippet=f"snippet for {query} {i}",
                provider="tavily",
            )
            for i in range(self._per_query)
        ]


class _FakeAppReviews:
    async def fetch_reviews(self, competitor: str, max_results: int = 2) -> list[SourceCitation]:
        return []


class _RecordingFetcher:
    """fetch_pages that skips half the URLs (robots/fetch_error) and enriches the rest."""

    def __init__(self) -> None:
        self.batch_calls = 0
        self.last_url_count = 0

    async def fetch_pages(self, urls: list[str]) -> list[FetchResult]:
        self.batch_calls += 1
        self.last_url_count = len(urls)
        results: list[FetchResult] = []
        for idx, url in enumerate(urls):
            if idx % 2 == 0:
                results.append(FetchResult(url=url, title="T", content="real page body"))
            else:
                results.append(
                    FetchResult(
                        url=url, title="", content="", skipped=True, skip_reason="robots.txt"
                    )
                )
        return results


class _FailingSearch:
    """Mimics SerpApi 429 / quota exhaustion: every query raises."""

    async def search(self, query: str, max_results: int = 5) -> list[SourceCitation]:
        raise RuntimeError("serpapi: Client error '429 Too Many Requests'")


class _FallbackAppReviews:
    """Returns only content-free fallback stubs (provider startswith 'fallback')."""

    async def fetch_reviews(self, competitor: str, max_results: int = 5) -> list[SourceCitation]:
        return [
            SourceCitation(
                id=f"src_public_review_{competitor}_{i}",
                type="public_review",
                category="user_feedback",
                url=f"https://www.google.com/search?q={competitor}",
                title=f"{competitor} public review fallback #{i}",
                snippet=f"Fallback public review search result for {competitor}.",
                provider="fallback_public_review_search",
            )
            for i in range(1, max_results + 1)
        ]


class _NoopFetcher:
    async def fetch_pages(self, urls: list[str]) -> list[FetchResult]:
        return []


def test_collector_flags_degradation_when_only_fallback_sources() -> None:
    """When web search fails for every query and only fallback stubs survive, the
    collector must record a degradation so the empty report has a visible cause."""
    from services.llm.usage import collected_degradations, reset_capture, start_capture

    agent = CollectorAgent()
    token = start_capture()
    try:
        asyncio.run(
            agent._collect_real_competitor(
                "飞书",
                _FailingSearch(),  # type: ignore[arg-type]
                _FallbackAppReviews(),  # type: ignore[arg-type]
                _NoopFetcher(),  # type: ignore[arg-type]
                dimension_queries=[("core.pricing", "飞书 pricing plans")],
            )
        )
        degradations = collected_degradations()
    finally:
        reset_capture(token)

    assert any("no real sources" in d for d in degradations), degradations


def test_collector_keeps_sources_when_page_fetch_skipped() -> None:
    agent = CollectorAgent()
    search = _FakeSearch(per_query=3)
    fetcher = _RecordingFetcher()
    queries = [("core.pricing", "Notion pricing"), ("core.feature_tree", "Notion features")]

    result = asyncio.run(
        agent._collect_real_competitor(
            "Notion",
            search,  # type: ignore[arg-type]
            _FakeAppReviews(),  # type: ignore[arg-type]
            fetcher,  # type: ignore[arg-type]
            dimension_queries=queries,
        )
    )

    # 2 queries * 3 results = 6 sources; none dropped even though half were skipped
    assert len(result.sources) == 6
    # Page enrichment is batched into a single fetch_pages call, not per-URL
    assert fetcher.batch_calls == 1
    # Enriched sources carry scraped content; skipped ones keep their search snippet
    enriched = [s for s in result.sources if s.raw_content]
    kept_snippets = [s for s in result.sources if not s.raw_content and s.snippet]
    assert enriched, "at least some pages should be enriched"
    assert kept_snippets, "skipped pages must retain their search snippet, not be dropped"


def test_collector_caps_page_fetches_without_dropping_sources() -> None:
    agent = CollectorAgent()
    search = _FakeSearch(per_query=8)
    fetcher = _RecordingFetcher()
    queries = [("core.pricing", "Notion pricing"), ("core.feature_tree", "Notion features")]

    result = asyncio.run(
        agent._collect_real_competitor(
            "Notion",
            search,  # type: ignore[arg-type]
            _FakeAppReviews(),  # type: ignore[arg-type]
            fetcher,  # type: ignore[arg-type]
            dimension_queries=queries,
        )
    )

    assert len(result.sources) == 16
    assert fetcher.batch_calls == 1
    assert fetcher.last_url_count == 10
