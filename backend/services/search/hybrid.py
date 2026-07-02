import asyncio

import structlog

from schemas.source import SourceCitation
from services.redaction import redact_secrets
from services.search.providers import PermanentProviderError, SearchProvider

logger = structlog.get_logger(__name__)

# Max simultaneous in-flight search API calls across all concurrent competitor queries.
# Prevents the ~48-request flood (3 competitors × 16 queries) that triggers 429 on SerpAPI.
_MAX_CONCURRENT_SEARCHES = 5


class SearchUnavailableError(RuntimeError):
    def __init__(self, message: str, *, permanent: bool = False) -> None:
        super().__init__(message)
        self.permanent = permanent


class HybridSearch:
    """Tiered search: each tier's providers are merged; tiers are tried in order.

    A tier is a list of providers queried together and merged/deduped. The first
    tier that yields any results wins — lower tiers are never touched. This keeps
    a scarce fallback provider (e.g. SerpAPI's 100/month quota) from being spent
    when the primary tier (Tavily + DuckDuckGo) already answered the query.
    """

    name = "hybrid_search"

    def __init__(self, tiers: list[list[SearchProvider]]) -> None:
        self._tiers = tiers
        self._semaphore = asyncio.Semaphore(_MAX_CONCURRENT_SEARCHES)
        # Providers that returned a permanent error (quota exhausted) are skipped
        # for all subsequent queries in this analysis run, across every tier.
        self._exhausted: set[str] = set()

    async def search(self, query: str, max_results: int = 5) -> list[SourceCitation]:
        async with self._semaphore:
            return await self._search_inner(query, max_results)

    async def _search_inner(self, query: str, max_results: int) -> list[SourceCitation]:
        tried: list[str] = []
        errors: list[str] = []
        permanent_failures: list[bool] = []

        logger.info(
            "search.invoke",
            query=query,
            tiers=[[p.name for p in tier] for tier in self._tiers],
        )

        for tier_index, tier in enumerate(self._tiers):
            merged: list[SourceCitation] = []
            seen_keys: set[str] = set()

            for provider in tier:
                if provider.name in self._exhausted:
                    tried.append(provider.name)
                    errors.append(f"{provider.name}: quota exhausted (circuit open — skipped)")
                    permanent_failures.append(True)
                    continue

                try:
                    results = await provider.search(query, max_results=max_results)
                except PermanentProviderError as exc:
                    self._exhausted.add(provider.name)
                    logger.warning(
                        "search.provider_exhausted",
                        provider=provider.name,
                        reason=redact_secrets(str(exc)),
                    )
                    tried.append(provider.name)
                    errors.append(f"{provider.name}: {exc}")
                    permanent_failures.append(True)
                    continue
                except Exception as exc:
                    logger.warning(
                        "search.fallback",
                        failed_provider=provider.name,
                        failure_reason=redact_secrets(str(exc)),
                    )
                    tried.append(provider.name)
                    errors.append(f"{provider.name}: {exc}")
                    permanent_failures.append(False)
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
                        provider=provider.name,
                        query=query,
                        tier_index=tier_index,
                        results_count=len(results),
                        merged_count=len(merged),
                        added_count=added,
                    )
                    continue

                # Empty result treated as a soft failure → try next provider in tier
                tried.append(provider.name)
                errors.append(f"{provider.name}: empty results")
                permanent_failures.append(False)

            # First tier with any results wins; lower tiers stay untouched.
            if merged:
                return merged

        logger.error(
            "search.exhausted",
            tried_providers=tried,
            final_error=redact_secrets("; ".join(errors)),
        )
        raise SearchUnavailableError(
            redact_secrets("; ".join(errors)) or "no search providers configured",
            permanent=bool(permanent_failures) and all(permanent_failures),
        )


def _dedupe_key(source: SourceCitation) -> str:
    if source.url:
        return str(source.url).rstrip("/").lower()
    return source.id.lower()
