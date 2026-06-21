from datetime import UTC, datetime

import httpx

from schemas.source import SourceCitation
from services.search.providers import PermanentProviderError, SearchProvider


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
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                # 432 is Tavily's "usage limit reached" code, covering BOTH the plan
                # credit cap and per-minute rate limits. The response body distinguishes
                # them, so surface it instead of assuming the credit balance is zero.
                if exc.response.status_code == 432:
                    detail = exc.response.text[:300].strip()
                    raise PermanentProviderError(
                        f"Tavily usage limit reached (432): {detail}"
                    ) from exc
                raise
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
