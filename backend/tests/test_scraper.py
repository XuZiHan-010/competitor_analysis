import asyncio

from services.scraper import PageFetcher


class DenyRobots:
    async def can_fetch(self, url: str) -> bool:
        return False


def test_page_fetcher_skips_robots_disallowed_url() -> None:
    result = asyncio.run(PageFetcher(DenyRobots()).fetch_page("https://example.com/private"))
    assert result.skipped is True
    assert result.skip_reason == "robots.txt"
