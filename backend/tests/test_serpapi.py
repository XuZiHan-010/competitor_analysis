import asyncio

import httpx
import pytest
import respx

from services.search.serpapi import SerpApiProvider


def test_serpapi_retries_429_then_returns_results(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = 0

    def response(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            return httpx.Response(429, text="rate limited")
        return httpx.Response(
            200,
            json={
                "organic_results": [
                    {
                        "link": "https://example.com/result",
                        "title": "Result",
                        "snippet": "Evidence",
                    }
                ]
            },
        )

    async def no_delay(_: float) -> None:
        return None

    monkeypatch.setattr("services.search.serpapi.asyncio.sleep", no_delay)
    with respx.mock:
        route = respx.get("https://serpapi.com/search.json").mock(side_effect=response)
        results = asyncio.run(SerpApiProvider("placeholder").search("query"))

    assert route.call_count == 3
    assert results[0].provider == "serpapi"


def test_serpapi_raises_after_permanent_429_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    async def no_delay(_: float) -> None:
        return None

    monkeypatch.setattr("services.search.serpapi.asyncio.sleep", no_delay)
    with respx.mock:
        route = respx.get("https://serpapi.com/search.json").mock(
            return_value=httpx.Response(429, text="rate limited")
        )
        with pytest.raises(httpx.HTTPStatusError):
            asyncio.run(SerpApiProvider("placeholder").search("query"))

    assert route.call_count == 3
