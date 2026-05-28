from typing import Protocol

from schemas.source import SourceCitation


class SearchProvider(Protocol):
    name: str

    async def search(self, query: str, max_results: int = 5) -> list[SourceCitation]: ...
