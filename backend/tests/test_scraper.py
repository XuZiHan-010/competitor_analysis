import asyncio
import sys
import threading
from collections.abc import Iterable

import pytest

from services.scraper import FetchResult, PageFetcher


class DenyRobots:
    async def can_fetch(self, url: str) -> bool:
        return False


class AllowRobots:
    async def can_fetch(self, url: str) -> bool:
        return True


class _FakePage:
    def __init__(self, fail: bool = False) -> None:
        self._fail = fail

    async def goto(self, url: str, **_: object) -> None:
        if self._fail:
            raise RuntimeError("net::ERR_ABORTED")

    async def title(self) -> str:
        return "Fake Title"

    async def inner_text(self, _selector: str) -> str:
        return "fake body content"

    async def close(self) -> None:
        return None


class _FakeBrowser:
    def __init__(self, counter: dict[str, int], fail_urls: set[str]) -> None:
        self._counter = counter
        self._fail_urls = fail_urls

    async def new_page(self, **_: object) -> _FakePage:
        self._counter["pages"] += 1
        return _FakePage()

    async def close(self) -> None:
        self._counter["closed"] += 1


class _FakeChromium:
    def __init__(self, counter: dict[str, int], fail_urls: set[str]) -> None:
        self._counter = counter
        self._fail_urls = fail_urls

    async def launch(self, **_: object) -> _FakeBrowser:
        self._counter["launch"] += 1
        return _FakeBrowser(self._counter, self._fail_urls)


class _FakePlaywright:
    def __init__(self, counter: dict[str, int], fail_urls: set[str]) -> None:
        self.chromium = _FakeChromium(counter, fail_urls)

    async def __aenter__(self) -> "_FakePlaywright":
        return self

    async def __aexit__(self, *_: object) -> bool:
        return False


def _install_fake_playwright(
    monkeypatch: pytest.MonkeyPatch,
    counter: dict[str, int],
    fail_urls: Iterable[str] = frozenset(),
) -> None:
    counter.setdefault("launch", 0)
    counter.setdefault("pages", 0)
    counter.setdefault("closed", 0)
    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        lambda: _FakePlaywright(counter, set(fail_urls)),
    )


def test_page_fetcher_skips_robots_disallowed_url() -> None:
    result = asyncio.run(PageFetcher(DenyRobots()).fetch_page("https://example.com/private"))
    assert result.skipped is True
    assert result.skip_reason == "robots.txt"


def test_fetch_pages_reuses_single_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    counter: dict[str, int] = {}
    _install_fake_playwright(monkeypatch, counter)
    urls = [f"https://example.com/p{i}" for i in range(4)]

    results = asyncio.run(PageFetcher(AllowRobots()).fetch_pages(urls))

    assert counter["launch"] == 1  # one browser for all URLs, not one per URL
    assert counter["closed"] == 1
    assert [r.url for r in results] == urls
    assert all(not r.skipped for r in results)


def test_fetch_pages_does_not_launch_browser_when_all_robots_denied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    counter: dict[str, int] = {}
    _install_fake_playwright(monkeypatch, counter)

    results = asyncio.run(PageFetcher(DenyRobots()).fetch_pages(["https://a.com", "https://b.com"]))

    assert counter["launch"] == 0  # never spin up Chromium if nothing is allowed
    assert all(r.skipped and r.skip_reason == "robots.txt" for r in results)


def test_fetch_offloads_to_worker_thread_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    # On Windows the fetch must run on a dedicated ProactorEventLoop in a worker
    # thread (the main loop is SelectorEventLoop, which cannot spawn Chromium);
    # elsewhere it stays inline on the running loop.
    fetcher = PageFetcher(AllowRobots())
    seen_thread: dict[str, threading.Thread] = {}

    async def fake_fetch_allowed_async(urls: list[str]) -> list[FetchResult]:
        seen_thread["thread"] = threading.current_thread()
        return [FetchResult(url=url, title="t", content="c") for url in urls]

    monkeypatch.setattr(fetcher, "_fetch_allowed_async", fake_fetch_allowed_async)

    results = asyncio.run(fetcher.fetch_pages(["https://example.com/a"]))

    assert [r.url for r in results] == ["https://example.com/a"]
    if sys.platform == "win32":
        assert seen_thread["thread"] is not threading.main_thread()
    else:
        assert seen_thread["thread"] is threading.main_thread()
