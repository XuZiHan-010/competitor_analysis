import asyncio

import pytest

from schemas.source import SourceCitation
from services.search.hybrid import HybridSearch, SearchUnavailableError
from services.search.providers import PermanentProviderError


class _Provider:
    def __init__(self, name: str, results: list[SourceCitation]) -> None:
        self.name = name
        self.results = results
        self.calls = 0

    async def search(self, query: str, max_results: int = 5) -> list[SourceCitation]:
        self.calls += 1
        return self.results[:max_results]


def _source(source_id: str, url: str, provider: str) -> SourceCitation:
    return SourceCitation(
        id=source_id,
        type="media",
        category="media",
        url=url,
        title=source_id,
        snippet="Evidence.",
        provider=provider,
    )


class _FailingProvider:
    def __init__(
        self, name: str, exc: Exception, results: list[SourceCitation] | None = None
    ) -> None:
        self.name = name
        self._exc = exc
        self._results = results or []
        self.calls = 0

    async def search(self, query: str, max_results: int = 5) -> list[SourceCitation]:
        self.calls += 1
        if self.calls == 1:
            raise self._exc
        return self._results[:max_results]


def test_hybrid_search_merges_providers_within_a_tier_and_dedupes_by_url() -> None:
    tavily = _Provider(
        "tavily",
        [
            _source("src_tavily_001", "https://example.com/a", "tavily"),
            _source("src_tavily_002", "https://example.com/b", "tavily"),
        ],
    )
    duckduckgo = _Provider(
        "duckduckgo",
        [
            _source("src_ddg_001", "https://example.com/b/", "duckduckgo"),
            _source("src_ddg_002", "https://example.com/c", "duckduckgo"),
        ],
    )

    # Both providers share one tier → merged and deduped together.
    results = asyncio.run(HybridSearch([[tavily, duckduckgo]]).search("query", max_results=10))

    assert tavily.calls == 1
    assert duckduckgo.calls == 1
    assert [str(source.url) for source in results] == [
        "https://example.com/a",
        "https://example.com/b",
        "https://example.com/c",
    ]


def test_primary_tier_results_leave_fallback_tier_untouched() -> None:
    """When the primary tier answers, the scarce fallback tier is never queried."""
    primary = _Provider("tavily", [_source("src_t_001", "https://example.com/a", "tavily")])
    fallback = _Provider("serpapi", [_source("src_s_001", "https://example.com/b", "serpapi")])

    results = asyncio.run(HybridSearch([[primary], [fallback]]).search("q"))

    assert primary.calls == 1
    assert fallback.calls == 0  # quota conserved
    assert [str(source.url) for source in results] == ["https://example.com/a"]


def test_fallback_tier_queried_when_primary_tier_empty() -> None:
    """An empty primary tier falls through to the fallback tier."""
    primary = _Provider("tavily", [])
    fallback = _Provider("serpapi", [_source("src_s_001", "https://example.com/b", "serpapi")])

    results = asyncio.run(HybridSearch([[primary], [fallback]]).search("q"))

    assert primary.calls == 1
    assert fallback.calls == 1
    assert [str(source.url) for source in results] == ["https://example.com/b"]


def test_circuit_breaker_skips_exhausted_provider_on_subsequent_queries() -> None:
    """After a PermanentProviderError, the provider is skipped for all remaining queries."""
    exhausted = _FailingProvider(
        "tavily",
        PermanentProviderError("quota exhausted"),
        results=[_source("src_t_001", "https://example.com/tavily", "tavily")],
    )
    fallback = _Provider(
        "serpapi",
        [_source("src_s_001", "https://example.com/serpapi", "serpapi")],
    )

    async def _run() -> tuple[list[SourceCitation], list[SourceCitation], int, int]:
        # One tier with both providers: tavily exhausts, serpapi covers the tier.
        hs = HybridSearch([[exhausted, fallback]])
        first = await hs.search("q1")
        # After q1: tavily tried once (raises), fallback used once
        calls_after_q1 = (exhausted.calls, fallback.calls)
        second = await hs.search("q2")
        # After q2: tavily circuit-open (not called again), fallback called again
        return first, second, *calls_after_q1

    first, second, exhausted_after_q1, fallback_after_q1 = asyncio.run(_run())

    # q1: tavily tried and permanently failed → fallback used
    assert exhausted_after_q1 == 1
    assert fallback_after_q1 == 1
    assert len(first) == 1 and str(first[0].url) == "https://example.com/serpapi"

    # q2: tavily circuit-open (NOT called again) → fallback called directly
    assert exhausted.calls == 1  # still 1 — circuit prevented the retry
    assert fallback.calls == 2
    assert len(second) == 1


def test_circuit_breaker_spans_tiers() -> None:
    """A provider exhausted in the primary tier stays skipped even across tiers."""
    exhausted = _FailingProvider("tavily", PermanentProviderError("quota"))
    fallback = _Provider("serpapi", [_source("src_s_001", "https://example.com/b", "serpapi")])

    async def _run() -> tuple[int, int]:
        hs = HybridSearch([[exhausted], [fallback]])
        await hs.search("q1")
        await hs.search("q2")
        return exhausted.calls, fallback.calls

    exhausted_calls, fallback_calls = asyncio.run(_run())

    assert exhausted_calls == 1  # circuit opened after q1, never retried
    assert fallback_calls == 2


def test_hybrid_raises_when_all_providers_exhausted() -> None:
    provider = _FailingProvider("tavily", PermanentProviderError("quota"))
    with pytest.raises(SearchUnavailableError):
        asyncio.run(HybridSearch([[provider]]).search("q"))
