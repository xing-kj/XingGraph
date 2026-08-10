"""White-box tests for QdrantAdapter against a running local Qdrant server.

Tests target the adapter's VectorDBInterface contract with a deterministic
stub embedding engine. They connect to the Qdrant instance configured via
``QDRANT_URL`` (default http://localhost:6333) and are skipped when Qdrant
is unreachable, mirroring how server-dependent suites (pgvector/neo4j)
behave.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from uuid import uuid4

import pytest

try:
    from qdrant_client import AsyncQdrantClient

    from xinggraph.infrastructure.databases.vector.qdrant.QdrantAdapter import (
        IndexSchema,
        QdrantAdapter,
    )

    HAS_QDRANT = True
except ModuleNotFoundError:
    HAS_QDRANT = False

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")


def _qdrant_reachable() -> bool:
    if not HAS_QDRANT:
        return False
    try:
        async def _probe():
            client = AsyncQdrantClient(url=QDRANT_URL, api_key=None, prefer_grpc=False)
            try:
                await client.get_collections()
            finally:
                await client.close()

        asyncio.run(_probe())
        return True
    except Exception:
        return False


pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(not _qdrant_reachable(), reason="Qdrant server not reachable"),
]


class _FakeEmbeddingEngine:
    """Deterministic stub embedding engine; avoids external API calls."""

    def get_vector_size(self):
        return 3

    def get_batch_size(self):
        return 100

    async def embed_text(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


def _new_adapter(database_name: str = "") -> QdrantAdapter:
    return QdrantAdapter(
        url=QDRANT_URL,
        api_key=None,
        embedding_engine=_FakeEmbeddingEngine(),
        database_name=database_name,
    )


async def _seed(adapter, collection, ids):
    await adapter.create_collection(collection, IndexSchema)
    await adapter.create_data_points(
        collection,
        [IndexSchema(id=str(i), text=f"text-{i}") for i in ids],
    )


async def test_create_has_and_prune_collection():
    adapter = _new_adapter()
    try:
        collection = f"test_lifecycle_{uuid4().hex[:8]}_text"
        assert await adapter.has_collection(collection) is False

        await adapter.create_collection(collection, IndexSchema)
        assert await adapter.has_collection(collection) is True

        await adapter.prune()
        assert await adapter.has_collection(collection) is False
    finally:
        await adapter.close()


async def test_upsert_search_retrieve_delete():
    adapter = _new_adapter()
    try:
        collection = f"test_crud_{uuid4().hex[:8]}_text"
        point_id = str(uuid4())
        await _seed(adapter, collection, [point_id])

        results = await adapter.search(
            collection,
            query_vector=[0.1, 0.2, 0.3],
            limit=3,
            include_payload=True,
        )
        assert len(results) == 1
        assert str(results[0].id) == point_id

        retrieved = await adapter.retrieve(collection, [point_id])
        assert len(retrieved) == 1
        assert str(retrieved[0].id) == point_id

        await adapter.delete_data_points(collection, [point_id])
        assert await adapter.retrieve(collection, [point_id]) == []
    finally:
        await adapter.prune()
        await adapter.close()


async def test_delete_data_points_missing_collection_is_noop():
    adapter = _new_adapter()
    try:
        await adapter.delete_data_points("NeverCreated_name", [str(uuid4())])
    finally:
        await adapter.close()


async def test_delete_data_points_empty_ids_is_noop():
    adapter = _new_adapter()
    try:
        collection = f"test_del_empty_{uuid4().hex[:8]}_name"
        point_id = str(uuid4())
        await _seed(adapter, collection, [point_id])

        await adapter.delete_data_points(collection, [])

        assert len(await adapter.retrieve(collection, [point_id])) == 1
    finally:
        await adapter.prune()
        await adapter.close()


async def test_retrieve_empty_ids_returns_empty():
    adapter = _new_adapter()
    try:
        assert await adapter.retrieve("any_collection", []) == []
    finally:
        await adapter.close()


async def test_batch_search():
    adapter = _new_adapter()
    try:
        collection = f"test_batch_{uuid4().hex[:8]}_text"
        ids = [str(uuid4()) for _ in range(3)]
        await _seed(adapter, collection, ids)

        results = await adapter.batch_search(
            collection,
            ["alpha", "beta"],
            limit=5,
            include_payload=True,
        )
        assert len(results) == 2
        for batch in results:
            assert len(batch) == 3
            assert {str(r.id) for r in batch} == set(ids)
    finally:
        await adapter.prune()
        await adapter.close()


async def test_upsert_raw_vectors():
    from pydantic import BaseModel

    class _RawPayload(BaseModel):
        slot: int
        label: str

    adapter = _new_adapter()
    try:
        collection = f"test_raw_{uuid4().hex[:8]}_vector"
        point_id = uuid4()

        await adapter.upsert_raw_vectors(
            collection,
            [
                {
                    "id": point_id,
                    "vector": [1.0, 0.0, 0.0],
                    "payload": {"slot": 0, "label": "first"},
                }
            ],
            payload_schema=_RawPayload,
        )
        await adapter.upsert_raw_vectors(
            collection,
            [
                {
                    "id": point_id,
                    "vector": [0.0, 1.0, 0.0],
                    "payload": {"slot": 0, "label": "updated"},
                }
            ],
            payload_schema=_RawPayload,
        )

        retrieved = await adapter.retrieve(collection, [str(point_id)])
        assert len(retrieved) == 1
        assert retrieved[0].payload["label"] == "updated"

        results = await adapter.search(
            collection,
            query_vector=[0.0, 1.0, 0.0],
            limit=1,
            include_payload=True,
        )
        assert str(results[0].id) == str(point_id)
        assert results[0].payload["label"] == "updated"
    finally:
        await adapter.prune()
        await adapter.close()


async def test_close_is_idempotent():
    adapter = _new_adapter()
    await adapter.get_connection()
    assert adapter._client is not None
    await adapter.close()
    assert adapter._client is None
    await adapter.close()  # second close must not raise


async def test_concurrent_first_get_connection_returns_same_object():
    adapter = _new_adapter()
    try:
        c1, c2 = await asyncio.gather(adapter.get_connection(), adapter.get_connection())
        assert c1 is c2, "concurrent first get_connection must converge on one connection"
        assert adapter._client is c1
    finally:
        await adapter.close()