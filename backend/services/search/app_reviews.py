import re
from typing import Any
from urllib.parse import quote_plus

import httpx

from schemas.source import SourceCitation


class AppReviewProvider:
    name = "apple_app_store_reviews"

    def __init__(self, *, country: str = "us", timeout: float = 12.0) -> None:
        self._country = country
        self._timeout = timeout

    async def fetch_reviews(self, app_name: str, max_results: int = 3) -> list[SourceCitation]:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                app = await self._find_app(client, app_name)
                if app is None:
                    return self._fallback_sources(app_name, max_results)
                reviews = await self._fetch_app_store_reviews(client, app, max_results)
        except httpx.HTTPError:
            return self._fallback_sources(app_name, max_results)
        if not reviews:
            return self._fallback_sources(app_name, max_results)
        return reviews

    async def _find_app(
        self,
        client: httpx.AsyncClient,
        app_name: str,
    ) -> dict[str, Any] | None:
        response = await client.get(
            "https://itunes.apple.com/search",
            params={
                "term": app_name,
                "entity": "software",
                "country": self._country,
                "limit": 1,
            },
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        if not results or not isinstance(results[0], dict):
            return None
        return results[0]

    async def _fetch_app_store_reviews(
        self,
        client: httpx.AsyncClient,
        app: dict[str, Any],
        max_results: int,
    ) -> list[SourceCitation]:
        track_id = app.get("trackId")
        if not track_id:
            return []
        response = await client.get(
            f"https://itunes.apple.com/rss/customerreviews/id={track_id}/sortBy=mostRecent/json",
            params={"cc": self._country},
        )
        response.raise_for_status()
        entries = response.json().get("feed", {}).get("entry", [])
        if not isinstance(entries, list):
            return []

        app_title = str(app.get("trackName") or app.get("trackCensoredName") or "App")
        app_url = app.get("trackViewUrl")
        citations: list[SourceCitation] = []
        for entry in entries:
            if not isinstance(entry, dict) or "im:rating" not in entry:
                continue
            title = _label(entry.get("title")) or f"{app_title} App Store review"
            content = _label(entry.get("content"))
            rating = _label(entry.get("im:rating"))
            author = _label(entry.get("author", {}).get("name"))
            snippet_parts = [
                part for part in [content, f"Rating: {rating}/5" if rating else ""] if part
            ]
            citations.append(
                SourceCitation(
                    id=f"src_app_store_{_slug(app_title)}_{len(citations) + 1}",
                    type="app_review",
                    category="user_feedback",
                    url=entry.get("link", {}).get("attributes", {}).get("href") or app_url,
                    title=title,
                    snippet=" ".join(snippet_parts) or f"Public App Store review by {author}.",
                    raw_content=content,
                    provider=self.name,
                )
            )
            if len(citations) >= max_results:
                break
        return citations

    def _fallback_sources(self, app_name: str, max_results: int) -> list[SourceCitation]:
        query = quote_plus(f"{app_name} app reviews")
        return [
            SourceCitation(
                id=f"src_public_review_{_slug(app_name)}_{index}",
                type="public_review",
                category="user_feedback",
                url=f"https://www.google.com/search?q={query}",
                title=f"{app_name} public review fallback #{index}",
                snippet=f"Fallback public review search result for {app_name}.",
                provider="fallback_public_review_search",
            )
            for index in range(1, max_results + 1)
        ]


def _label(payload: Any) -> str:
    if isinstance(payload, dict):
        value = payload.get("label")
        return str(value) if value is not None else ""
    return str(payload) if payload is not None else ""


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "app"
