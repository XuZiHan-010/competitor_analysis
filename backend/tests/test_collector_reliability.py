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

    async def fetch_pages(self, urls: list[str]) -> list[FetchResult]:
        self.batch_calls += 1
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
