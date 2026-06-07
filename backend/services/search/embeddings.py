import hashlib
import math

import structlog
from openai import AsyncOpenAI

from settings import Settings

EMBEDDING_DIMENSIONS = 1536

logger = structlog.get_logger(__name__)


class EmbeddingService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        normalized = [_normalize_text(text) for text in texts]
        if self._settings.openai_api_key and normalized:
            try:
                client = AsyncOpenAI(api_key=self._settings.openai_api_key)
                response = await client.embeddings.create(
                    model=self._settings.embedding_model,
                    input=normalized,
                )
                return [item.embedding for item in response.data]
            except Exception:
                logger.warning("embedding_api_failed_using_hash_fallback", exc_info=True)
        return [_hash_embedding(text) for text in normalized]

    async def embed_text(self, text: str) -> list[float]:
        return (await self.embed_texts([text]))[0]


def vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in vector) + "]"


def _normalize_text(text: str) -> str:
    return " ".join(text.split())[:8000]


def _hash_embedding(text: str) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    tokens = text.lower().split()
    if not tokens:
        tokens = [text.lower() or "empty"]
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % EMBEDDING_DIMENSIONS
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]
