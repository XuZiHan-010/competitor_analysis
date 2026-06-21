import asyncio
from datetime import UTC, datetime
from typing import Any

from ddgs import DDGS

from schemas.source import SourceCitation
from services.search.providers import SearchProvider


class DuckDuckGoProvider(SearchProvider):
    name = "duckduckgo"

    def __init__(self, *, region: str = "wt-wt", timeout: int = 20) -> None:
        self._region = region
        self._timeout = timeout

    async def search(self, query: str, max_results: int = 5) -> list[SourceCitation]:
        # ddgs is synchronous (primp under the hood); offload so the event loop
        # isn't blocked while it scrapes DuckDuckGo.
        rows = await asyncio.to_thread(self._search_sync, query, max_results)
        citations: list[SourceCitation] = []
        for row in rows[:max_results]:
            href = row.get("href")
            # ddgs drifts across backends; the Startpage backend returns relative
            # redirect hrefs (e.g. "/clev?event=..."), which aren't citable sources
            # and fail HttpUrl validation. Skip per-row so one bad href can't raise
            # and void the whole batch.
            if not href or not href.startswith(("http://", "https://")):
                continue
            citations.append(
                SourceCitation(
                    id=f"src_duckduckgo_{len(citations) + 1}",
                    type="media",
                    category="media",
                    url=href,
                    title=row.get("title") or "Untitled source",
                    snippet=row.get("body") or "",
                    raw_content=row.get("body"),
                    provider=self.name,
                    fetched_at=datetime.now(UTC),
                )
            )
        return citations

    def _search_sync(self, query: str, max_results: int) -> list[dict[str, Any]]:
        with DDGS(timeout=self._timeout) as ddgs:
            return list(ddgs.text(query, region=self._region, max_results=max_results))
