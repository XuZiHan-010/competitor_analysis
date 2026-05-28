from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx


@dataclass(frozen=True)
class FetchResult:
    url: str
    title: str
    content: str
    skipped: bool = False
    skip_reason: str | None = None


class RobotsChecker:
    def __init__(self, user_agent: str = "CompetitorAnalysisBot") -> None:
        self._user_agent = user_agent
        self._cache: dict[str, RobotFileParser] = {}

    async def can_fetch(self, url: str) -> bool:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        parser = self._cache.get(base_url)
        if parser is None:
            parser = RobotFileParser()
            robots_url = f"{base_url}/robots.txt"
            parser.set_url(robots_url)
            try:
                async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
                    response = await client.get(robots_url)
                if response.status_code >= 400:
                    parser.parse([])
                else:
                    parser.parse(response.text.splitlines())
            except httpx.HTTPError:
                parser.parse([])
            self._cache[base_url] = parser
        return parser.can_fetch(self._user_agent, url)


class RobotsPolicy(Protocol):
    async def can_fetch(self, url: str) -> bool: ...


class PageFetcher:
    def __init__(self, robots_checker: RobotsPolicy | None = None) -> None:
        self._robots_checker = robots_checker or RobotsChecker()

    async def fetch_page(self, url: str) -> FetchResult:
        if not await self._robots_checker.can_fetch(url):
            return FetchResult(
                url=url, title="", content="", skipped=True, skip_reason="robots.txt"
            )
        try:
            return await self._fetch_with_playwright(url)
        except Exception:
            return await self._fetch_with_httpx(url)

    async def _fetch_with_playwright(self, url: str) -> FetchResult:
        from playwright.async_api import async_playwright

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            try:
                page = await browser.new_page(
                    extra_http_headers={"User-Agent": "CompetitorAnalysisBot"}
                )
                await page.goto(url, timeout=20_000, wait_until="domcontentloaded")
                title = await page.title()
                content = await page.inner_text("body")
                return FetchResult(url=url, title=title, content=content[:8000])
            finally:
                await browser.close()

    async def _fetch_with_httpx(self, url: str) -> FetchResult:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "CompetitorAnalysisBot"})
            response.raise_for_status()
        title = _extract_title(response.text) or url
        return FetchResult(url=url, title=title, content=response.text[:8000])


def _extract_title(html: str) -> str | None:
    lower = html.lower()
    start = lower.find("<title>")
    end = lower.find("</title>")
    if start == -1 or end == -1 or end <= start:
        return None
    return html[start + len("<title>") : end].strip()
