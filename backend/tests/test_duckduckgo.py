import asyncio
from typing import Any

from services.search.duckduckgo import DuckDuckGoProvider


def _rows() -> list[dict[str, Any]]:
    return [
        {
            "title": "Cursor pricing",
            "href": "https://example.com/cursor",
            "body": "Cursor offers free and pro tiers.",
        },
        {
            "title": "Trae overview",
            "href": "https://example.com/trae",
            "body": "Trae is an AI coding assistant.",
        },
        # Rows without an href are unusable citations and must be dropped.
        {"title": "No link", "href": "", "body": "orphan"},
    ]


def test_maps_ddgs_rows_to_source_citations(monkeypatch: Any) -> None:
    provider = DuckDuckGoProvider()
    monkeypatch.setattr(provider, "_search_sync", lambda query, max_results: _rows())

    results = asyncio.run(provider.search("query", max_results=5))

    # The hrefless row is dropped → 2 valid citations.
    assert len(results) == 2
    first = results[0]
    assert first.id == "src_duckduckgo_1"
    assert first.provider == "duckduckgo"
    assert str(first.url) == "https://example.com/cursor"
    assert first.title == "Cursor pricing"
    assert first.snippet == "Cursor offers free and pro tiers."
    assert first.raw_content == "Cursor offers free and pro tiers."


def test_respects_max_results(monkeypatch: Any) -> None:
    provider = DuckDuckGoProvider()
    monkeypatch.setattr(provider, "_search_sync", lambda query, max_results: _rows())

    results = asyncio.run(provider.search("query", max_results=1))

    assert len(results) == 1
    assert str(results[0].url) == "https://example.com/cursor"


def test_relative_url_row_is_skipped_without_voiding_batch(monkeypatch: Any) -> None:
    # ddgs' Startpage backend can return relative redirect hrefs; one such row
    # must not raise HttpUrl validation and drop the whole result set.
    rows = [
        {"title": "Good", "href": "https://example.com/good", "body": "ok"},
        {"title": "Startpage redirect", "href": "/clev?event=StartpageResult", "body": "bad"},
        {"title": "Also good", "href": "https://example.com/also", "body": "ok"},
    ]
    provider = DuckDuckGoProvider()
    monkeypatch.setattr(provider, "_search_sync", lambda query, max_results: rows)

    results = asyncio.run(provider.search("query", max_results=5))

    assert [str(r.url) for r in results] == [
        "https://example.com/good",
        "https://example.com/also",
    ]
    # IDs stay contiguous over the surviving rows.
    assert [r.id for r in results] == ["src_duckduckgo_1", "src_duckduckgo_2"]


def test_missing_title_falls_back_to_placeholder(monkeypatch: Any) -> None:
    provider = DuckDuckGoProvider()
    monkeypatch.setattr(
        provider,
        "_search_sync",
        lambda query, max_results: [{"title": "", "href": "https://example.com/x", "body": ""}],
    )

    results = asyncio.run(provider.search("query"))

    assert results[0].title == "Untitled source"
    assert results[0].snippet == ""
