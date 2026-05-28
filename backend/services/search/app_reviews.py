from urllib.parse import quote_plus

from schemas.source import SourceCitation


class AppReviewProvider:
    async def fetch_reviews(self, app_name: str, max_results: int = 3) -> list[SourceCitation]:
        query = quote_plus(f"{app_name} app reviews")
        return [
            SourceCitation(
                id=f"src_app_review_{quote_plus(app_name.lower())}_{index}",
                type="app_review",
                category="user_feedback",
                url=f"https://www.google.com/search?q={query}",
                title=f"{app_name} public app review signal #{index}",
                snippet=(
                    "Public app review provider placeholder; replace with "
                    "store-specific parser in S1."
                ),
                provider="app_review_provider",
            )
            for index in range(1, max_results + 1)
        ]
