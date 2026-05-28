from datetime import UTC, datetime

import httpx

from schemas.source import SourceCitation
from services.search.providers import SearchProvider


class TavilyProvider(SearchProvider):
    name = "tavily"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def search(self, query: str, max_results: int = 5) -> list[SourceCitation]:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self._api_key,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": "basic",
                },
            )
            response.raise_for_status()
        payload = response.json()
        results = payload.get("results", [])
        return [
            SourceCitation(
                id=f"src_tavily_{index}",
                type="media",
                category="media",
                url=item.get("url"),
                title=item.get("title") or "Untitled source",
                snippet=item.get("content") or "",
                raw_content=item.get("content"),
                provider=self.name,
                fetched_at=datetime.now(UTC),
            )
            for index, item in enumerate(results[:max_results], start=1)
        ]
