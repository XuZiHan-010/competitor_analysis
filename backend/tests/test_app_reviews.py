import asyncio

import httpx
import respx

from services.search.app_reviews import AppReviewProvider


def test_app_review_provider_fetches_apple_app_store_reviews() -> None:
    with respx.mock:
        respx.get("https://itunes.apple.com/search").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "trackId": 123,
                            "trackName": "Notion",
                            "trackViewUrl": "https://apps.apple.com/us/app/notion/id123",
                        }
                    ]
                },
            )
        )
        respx.get("https://itunes.apple.com/rss/customerreviews/id=123/sortBy=mostRecent/json").mock(
            return_value=httpx.Response(
                200,
                json={
                    "feed": {
                        "entry": [
                            {"title": {"label": "Notion"}},
                            {
                                "title": {"label": "Great workspace"},
                                "content": {"label": "Databases and docs work well together."},
                                "im:rating": {"label": "5"},
                                "author": {"name": {"label": "Reviewer"}},
                                "link": {
                                    "attributes": {
                                        "href": "https://apps.apple.com/us/review/notion"
                                    }
                                },
                            },
                        ]
                    }
                },
            )
        )

        reviews = asyncio.run(AppReviewProvider().fetch_reviews("Notion", max_results=2))

    assert len(reviews) == 1
    assert reviews[0].type == "app_review"
    assert reviews[0].category == "user_feedback"
    assert reviews[0].provider == "apple_app_store_reviews"
    assert reviews[0].raw_content == "Databases and docs work well together."
    assert "Rating: 5/5" in reviews[0].snippet


def test_app_review_provider_falls_back_to_public_review_search() -> None:
    with respx.mock:
        respx.get("https://itunes.apple.com/search").mock(return_value=httpx.Response(500))

        reviews = asyncio.run(AppReviewProvider().fetch_reviews("Unknown App", max_results=2))

    assert len(reviews) == 2
    assert reviews[0].type == "public_review"
    assert reviews[0].category == "user_feedback"
    assert reviews[0].provider == "fallback_public_review_search"
    assert "Unknown App" in reviews[0].title
