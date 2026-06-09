import asyncio

from schemas.source import SourceCitation
from services.search.hybrid import HybridSearch


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


def test_hybrid_search_merges_providers_and_dedupes_by_url() -> None:
    tavily = _Provider(
        "tavily",
        [
            _source("src_tavily_001", "https://example.com/a", "tavily"),
            _source("src_tavily_002", "https://example.com/b", "tavily"),
        ],
    )
    serpapi = _Provider(
        "serpapi",
        [
            _source("src_serpapi_001", "https://example.com/b/", "serpapi"),
            _source("src_serpapi_002", "https://example.com/c", "serpapi"),
        ],
    )

    results = asyncio.run(HybridSearch([tavily, serpapi]).search("query", max_results=10))

    assert tavily.calls == 1
    assert serpapi.calls == 1
    assert [str(source.url) for source in results] == [
        "https://example.com/a",
        "https://example.com/b",
        "https://example.com/c",
    ]
