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
        merged: list[SourceCitation] = []
        seen_keys: set[str] = set()

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
                added = 0
                for result in results:
                    dedupe_key = _dedupe_key(result)
                    if dedupe_key in seen_keys:
                        continue
                    seen_keys.add(dedupe_key)
                    merged.append(result)
                    added += 1
                logger.info(
                    "search.invoke",
                    extra={
                        "provider": provider.name,
                        "query": query,
                        "results_count": len(results),
                        "merged_count": len(merged),
                        "added_count": added,
                    },
                )
                continue

            # Empty result treated as a soft failure → try next provider
            tried.append(provider.name)
            errors.append(f"{provider.name}: empty results")

        if merged:
            return merged

        logger.error(
            "search.exhausted",
            extra={"tried_providers": tried, "final_error": "; ".join(errors)},
        )
        raise SearchUnavailableError("; ".join(errors) or "no search providers configured")


def _dedupe_key(source: SourceCitation) -> str:
    if source.url:
        return str(source.url).rstrip("/").lower()
    return source.id.lower()
