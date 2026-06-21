from typing import Protocol

from schemas.source import SourceCitation


class PermanentProviderError(RuntimeError):
    """Provider has a permanent failure for this billing period (e.g. quota exhausted)."""


class SearchProvider(Protocol):
    name: str

    async def search(self, query: str, max_results: int = 5) -> list[SourceCitation]: ...
