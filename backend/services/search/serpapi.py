from datetime import UTC, datetime

import httpx

from schemas.source import SourceCitation
from services.search.providers import SearchProvider


class SerpApiProvider(SearchProvider):
    name = "serpapi"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def search(self, query: str, max_results: int = 5) -> list[SourceCitation]:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                "https://serpapi.com/search.json",
                params={
                    "engine": "google",
                    "q": query,
                    "api_key": self._api_key,
                    "num": max_results,
                },
            )
            response.raise_for_status()
        payload = response.json()
        results = payload.get("organic_results", [])
        return [
            SourceCitation(
                id=f"src_serpapi_{index}",
                type="media",
                category="media",
                url=item.get("link"),
                title=item.get("title") or "Untitled source",
                snippet=item.get("snippet") or "",
                raw_content=item.get("snippet"),
                provider=self.name,
                fetched_at=datetime.now(UTC),
            )
            for index, item in enumerate(results[:max_results], start=1)
        ]
