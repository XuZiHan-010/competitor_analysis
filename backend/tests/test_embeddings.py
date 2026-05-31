import math

import pytest

from services.search.embeddings import EMBEDDING_DIMENSIONS, EmbeddingService, vector_literal
from settings import Settings


@pytest.mark.asyncio
async def test_hash_embedding_fallback_is_pgvector_ready() -> None:
    service = EmbeddingService(Settings(mock_llm=True))

    vector = await service.embed_text("pricing claims customer support")

    assert len(vector) == EMBEDDING_DIMENSIONS
    assert math.isclose(math.sqrt(sum(value * value for value in vector)), 1.0)
    literal = vector_literal(vector)
    assert literal.startswith("[")
    assert literal.endswith("]")
    assert len(literal.split(",")) == EMBEDDING_DIMENSIONS
