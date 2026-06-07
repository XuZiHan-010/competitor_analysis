import asyncio
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
import structlog

logger = structlog.get_logger(__name__)

_GOTO_TIMEOUT_MS = 8_000
_PAGE_BUDGET_S = 12
_MAX_FETCH_CONCURRENCY = 5


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
    def __init__(
        self,
        robots_checker: RobotsPolicy | None = None,
        *,
        max_concurrency: int = _MAX_FETCH_CONCURRENCY,
    ) -> None:
        self._robots_checker = robots_checker or RobotsChecker()
        self._max_concurrency = max(1, max_concurrency)

    async def fetch_page(self, url: str) -> FetchResult:
        results = await self.fetch_pages([url])
        return results[0]

    async def fetch_pages(self, urls: list[str]) -> list[FetchResult]:
        """Fetch many URLs reusing a single Chromium instance with bounded concurrency.

        Launching a fresh browser per URL (the previous behavior) dominated
        collection latency; a single shared browser + capped parallelism keeps a
        whole competitor's pages well under the collector timeout, and a flaky URL
        no longer starves the others.
        """
        allowed = await asyncio.gather(*(self._robots_checker.can_fetch(url) for url in urls))
        by_url: dict[str, FetchResult] = {}
        to_fetch = [url for url, ok in zip(urls, allowed, strict=True) if ok]
        for url, ok in zip(urls, allowed, strict=True):
            if not ok:
                by_url[url] = FetchResult(
                    url=url, title="", content="", skipped=True, skip_reason="robots.txt"
                )

        if to_fetch:
            for result in await self._fetch_allowed(to_fetch):
                by_url[result.url] = result

        return [by_url[url] for url in urls]

    async def _fetch_allowed(self, urls: list[str]) -> list[FetchResult]:
        from playwright.async_api import async_playwright

        semaphore = asyncio.Semaphore(self._max_concurrency)
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            try:

                async def _one(url: str) -> FetchResult:
                    async with semaphore:
                        return await self._fetch_on_browser(browser, url)

                return await asyncio.gather(*(_one(url) for url in urls))
            finally:
                await browser.close()

    async def _fetch_on_browser(self, browser: object, url: str) -> FetchResult:
        try:
            return await asyncio.wait_for(
                self._render_page(browser, url), timeout=_PAGE_BUDGET_S
            )
        except Exception as exc:
            # Navigation/render failures (e.g. net::ERR_ABORTED, timeouts) are
            # common for real sites; surface a skip so the caller keeps the
            # search-provided citation instead of dropping the source entirely.
            logger.warning("page_fetch_failed", url=url, error_type=type(exc).__name__)
            return FetchResult(
                url=url, title="", content="", skipped=True, skip_reason="fetch_error"
            )

    async def _render_page(self, browser: object, url: str) -> FetchResult:
        page = await browser.new_page(  # type: ignore[attr-defined]
            extra_http_headers={"User-Agent": "CompetitorAnalysisBot"}
        )
        await page.goto(url, timeout=_GOTO_TIMEOUT_MS, wait_until="domcontentloaded")
        title = await page.title()
        content = await page.inner_text("body")
        return FetchResult(url=url, title=title, content=content[:8000])
