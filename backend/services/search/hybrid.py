import logging

from schemas.source import SourceCitation
from services.search.providers import SearchProvider

logger = logging.getLogger(__name__)


class SearchUnavailableError(RuntimeError):
    pass


class HybridSearch:
    name = "hybrid_search"

    def __init__(self, providers: list[SearchProvider]) -> None:
        self._providers = providers

    async def search(self, query: str, max_results: int = 5) -> list[SourceCitation]:
        tried: list[str] = []
        errors: list[str] = []

        logger.info(
            "search.invoke",
            extra={"query": query, "providers": [p.name for p in self._providers]},
        )

        for provider in self._providers:
            try:
                results = await provider.search(query, max_results=max_results)
            except Exception as exc:
                logger.warning(
                    "search.fallback",
                    extra={
                        "failed_provider": provider.name,
                        "failure_reason": str(exc),
                        "next_provider": (
                            self._providers[self._providers.index(provider) + 1].name
                            if self._providers.index(provider) + 1 < len(self._providers)
                            else None
                        ),
                    },
                )
                tried.append(provider.name)
                errors.append(f"{provider.name}: {exc}")
                continue

            if results:
                logger.info(
                    "search.invoke",
                    extra={
                        "provider": provider.name,
                        "query": query,
                        "results_count": len(results),
                    },
                )
                return results

            # Empty result treated as a soft failure → try next provider
            tried.append(provider.name)
            errors.append(f"{provider.name}: empty results")

        logger.error(
            "search.exhausted",
            extra={"tried_providers": tried, "final_error": "; ".join(errors)},
        )
        raise SearchUnavailableError("; ".join(errors) or "no search providers configured")
