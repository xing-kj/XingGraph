"""QdrantAdapter must honor the ScoredResult contract: cosine distance (lower = better).

Qdrant's query API returns cosine similarity (higher = better); the adapter is
responsible for converting it to distance so ranking by ascending score and the
``1 - score`` conversions downstream stay correct.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from xinggraph.infrastructure.databases.vector.qdrant.QdrantAdapter import QdrantAdapter


class _FakeEmbeddingEngine:
    def get_vector_size(self):
        return 3

    async def embed_text(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


class _FakePoint:
    def __init__(self, point_id, score, payload=None):
        self.id = point_id
        self.score = score
        self.payload = payload or {}


def _adapter_with_client(client):
    adapter = QdrantAdapter(
        url="http://localhost:6333",
        api_key=None,
        embedding_engine=_FakeEmbeddingEngine(),
    )
    adapter.has_collection = AsyncMock(return_value=True)
    adapter.get_connection = AsyncMock(return_value=client)
    return adapter


@pytest.mark.asyncio
async def test_search_converts_similarity_to_cosine_distance():
    client = MagicMock()
    response = MagicMock()
    response.points = [
        _FakePoint("a", 0.9999, {"id": "2509e38d-ef45-5980-a13a-72318d6da22f"}),
        _FakePoint("b", 0.5866, {"id": "8d2702e0-1171-5bb0-9570-ae34cc942154"}),
    ]
    client.query_points = AsyncMock(return_value=response)
    adapter = _adapter_with_client(client)

    results = await adapter.search("Entity_name", query_text="双循环制冷系统", include_payload=True)

    assert [r.score for r in results] == pytest.approx([0.0001, 0.4134])
    assert str(results[0].id) == "2509e38d-ef45-5980-a13a-72318d6da22f"


@pytest.mark.asyncio
async def test_batch_search_converts_similarity_to_cosine_distance():
    client = MagicMock()
    response = MagicMock()
    response.points = [
        _FakePoint("a", 0.9, {"id": "2509e38d-ef45-5980-a13a-72318d6da22f"}),
        _FakePoint("b", 0.7, {"id": "8d2702e0-1171-5bb0-9570-ae34cc942154"}),
    ]
    client.query_batch_points = AsyncMock(return_value=[response])
    adapter = _adapter_with_client(client)

    results = await adapter.batch_search("Entity_name", ["query one"])

    assert [r.score for r in results[0]] == pytest.approx([0.1, 0.3])