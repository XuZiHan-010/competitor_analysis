import asyncio

import httpx
import pytest
import respx

from services.search.providers import PermanentProviderError
from services.search.tavily import TavilyProvider


def test_maps_tavily_results_to_source_citations() -> None:
    with respx.mock:
        respx.post("https://api.tavily.com/search").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "url": "https://example.com/cursor",
                            "title": "Cursor",
                            "content": "Cursor pricing overview.",
                        }
                    ]
                },
            )
        )

        results = asyncio.run(TavilyProvider("key").search("query", max_results=5))

    assert len(results) == 1
    assert str(results[0].url) == "https://example.com/cursor"
    assert results[0].provider == "tavily"


def test_432_surfaces_response_body_for_diagnosis() -> None:
    with respx.mock:
        respx.post("https://api.tavily.com/search").mock(
            return_value=httpx.Response(432, text="rate limit exceeded: 100 RPM")
        )

        with pytest.raises(PermanentProviderError) as exc_info:
            asyncio.run(TavilyProvider("key").search("query"))

    message = str(exc_info.value)
    # The body lets us tell a rate-limit blip apart from a real credit exhaustion.
    assert "rate limit exceeded" in message
    assert "replenish credits" not in message
