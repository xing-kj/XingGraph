"""Prefix-isolation tests for QdrantAdapter.

In multi-tenant mode every dataset gets its own ``database_name`` (== dataset
UUID); the adapter must namespace each collection as ``{database_name}__
{collection}`` so different datasets are physically separated on the shared
Qdrant server, and ``prune()`` must only remove collections under its own
prefix.
"""

from __future__ import annotations

import asyncio
import os
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
    def get_vector_size(self):
        return 3

    def get_batch_size(self):
        return 100

    async def embed_text(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


def _new_adapter(database_name: str) -> QdrantAdapter:
    return QdrantAdapter(
        url=QDRANT_URL,
        api_key=None,
        embedding_engine=_FakeEmbeddingEngine(),
        database_name=database_name,
    )


async def test_same_logical_collection_is_isolated_per_database():
    logical = "Chunks_text"
    prefix_a = str(uuid4())
    prefix_b = str(uuid4())
    adapter_a = _new_adapter(prefix_a)
    adapter_b = _new_adapter(prefix_b)

    try:
        id_a = str(uuid4())
        id_b = str(uuid4())

        await adapter_a.create_collection(logical, IndexSchema)
        await adapter_b.create_collection(logical, IndexSchema)
        await adapter_a.create_data_points(logical, [IndexSchema(id=id_a, text="aaa")])
        await adapter_b.create_data_points(logical, [IndexSchema(id=id_b, text="bbb")])

        # Each adapter can only see its own data through the same logical name.
        assert len(await adapter_a.retrieve(logical, [id_a, id_b])) == 1
        assert len(await adapter_b.retrieve(logical, [id_a, id_b])) == 1

        # Physical collections are distinct on the server.
        client = await adapter_a.get_connection()
        names = [c.name for c in (await client.get_collections()).collections]
        assert f"{prefix_a}__{logical}" in names
        assert f"{prefix_b}__{logical}" in names
    finally:
        await adapter_a.prune()
        await adapter_b.prune()

    # After both prunes, neither prefixed collection remains.
    probe = AsyncQdrantClient(url=QDRANT_URL, api_key=None, prefer_grpc=False)
    try:
        names = [c.name for c in (await probe.get_collections()).collections]
    finally:
        await probe.close()

    assert f"{prefix_a}__{logical}" not in names
    assert f"{prefix_b}__{logical}" not in names


async def test_prune_only_drops_collections_under_own_prefix():
    prefix_a = str(uuid4())
    prefix_b = str(uuid4())
    adapter_a = _new_adapter(prefix_a)
    adapter_b = _new_adapter(prefix_b)

    try:
        await adapter_a.create_collection("Entity_name", IndexSchema)
        await adapter_b.create_collection("Entity_name", IndexSchema)

        await adapter_a.prune()

        client_b = await adapter_b.get_connection()
        names = [c.name for c in (await client_b.get_collections()).collections]

        assert f"{prefix_a}__Entity_name" not in names
        assert f"{prefix_b}__Entity_name" in names
    finally:
        await adapter_b.prune()