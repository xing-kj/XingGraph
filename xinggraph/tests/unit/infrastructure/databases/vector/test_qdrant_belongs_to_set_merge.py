"""Upserting the same DataPoint with different `belongs_to_set` values must
accumulate the set names, not overwrite them, and detagging must strip tags
from shared rows / delete orphaned rows (Qdrant backend).
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


def _new_adapter() -> QdrantAdapter:
    return QdrantAdapter(
        url=QDRANT_URL,
        api_key=None,
        embedding_engine=_FakeEmbeddingEngine(),
        database_name="",
    )


async def test_belongs_to_set_merges_across_upserts():
    adapter = _new_adapter()
    collection = "Tagged_text"
    point_id = str(uuid4())
    try:
        first = IndexSchema(id=point_id, text="shared", belongs_to_set=["DatasetA"])
        await adapter.create_collection(collection, type(first))
        await adapter.create_data_points(collection, [first])

        second = IndexSchema(id=point_id, text="shared", belongs_to_set=["DatasetB"])
        await adapter.create_data_points(collection, [second])

        results = await adapter.retrieve(collection, [point_id])
        assert len(results) == 1
        assert sorted(results[0].payload["belongs_to_set"]) == ["DatasetA", "DatasetB"]
    finally:
        await adapter.prune()
        await adapter.close()


async def test_bag_dedupes_on_repeat_upsert():
    adapter = _new_adapter()
    collection = "Tagged_text"
    point_id = str(uuid4())
    try:
        point = IndexSchema(id=point_id, text="shared", belongs_to_set=["DatasetA"])
        await adapter.create_collection(collection, type(point))
        await adapter.create_data_points(collection, [point])
        await adapter.create_data_points(collection, [point])

        results = await adapter.retrieve(collection, [point_id])
        assert results[0].payload["belongs_to_set"] == ["DatasetA"]
    finally:
        await adapter.prune()
        await adapter.close()


async def test_bag_merges_tags_across_in_batch_duplicates():
    adapter = _new_adapter()
    collection = "Tagged_text"
    point_id = str(uuid4())
    try:
        first = IndexSchema(id=point_id, text="shared", belongs_to_set=["DatasetA"])
        second = IndexSchema(id=point_id, text="shared", belongs_to_set=["DatasetB"])
        await adapter.create_collection(collection, type(first))
        await adapter.create_data_points(collection, [first, second])

        results = await adapter.retrieve(collection, [point_id])
        assert len(results) == 1
        assert sorted(results[0].payload["belongs_to_set"]) == ["DatasetA", "DatasetB"]
    finally:
        await adapter.prune()
        await adapter.close()


async def test_remove_bag_strips_and_deletes():
    adapter = _new_adapter()
    collection = "Tagged_text"
    shared_id = str(uuid4())
    orphaned_id = str(uuid4())
    untouched_id = str(uuid4())
    try:
        shared = IndexSchema(id=shared_id, text="shared", belongs_to_set=["Dev", "DevMirror"])
        orphaned = IndexSchema(id=orphaned_id, text="orphaned", belongs_to_set=["Dev"])
        untouched = IndexSchema(id=untouched_id, text="untouched", belongs_to_set=["Production"])

        await adapter.create_collection(collection, type(shared))
        await adapter.create_data_points(collection, [shared, orphaned, untouched])

        await adapter.remove_belongs_to_set_tags(["Dev"])

        surviving = await adapter.retrieve(collection, [shared_id, untouched_id])
        surviving_by_id = {str(r.id): r for r in surviving}

        assert sorted(surviving_by_id[shared_id].payload["belongs_to_set"]) == ["DevMirror"]
        assert surviving_by_id[untouched_id].payload["belongs_to_set"] == ["Production"]
        assert await adapter.retrieve(collection, [orphaned_id]) == []
    finally:
        await adapter.prune()
        await adapter.close()


async def test_remove_bag_noop_for_empty_input():
    adapter = _new_adapter()
    collection = "Tagged_text"
    point_id = str(uuid4())
    try:
        point = IndexSchema(id=point_id, text="shared", belongs_to_set=["Dev"])
        await adapter.create_collection(collection, type(point))
        await adapter.create_data_points(collection, [point])

        await adapter.remove_belongs_to_set_tags([])

        result = (await adapter.retrieve(collection, [point_id]))[0]
        assert result.payload["belongs_to_set"] == ["Dev"]
    finally:
        await adapter.prune()
        await adapter.close()


async def test_remove_bag_scoped_by_node_ids():
    adapter = _new_adapter()
    collection = "Tagged_text"
    targeted_id = str(uuid4())
    untouched_same_tag_id = str(uuid4())
    try:
        targeted = IndexSchema(id=targeted_id, text="shared", belongs_to_set=["alfa", "beta"])
        untouched = IndexSchema(id=untouched_same_tag_id, text="mock_only", belongs_to_set=["alfa"])

        await adapter.create_collection(collection, type(targeted))
        await adapter.create_data_points(collection, [targeted, untouched])

        await adapter.remove_belongs_to_set_tags(["alfa"], node_ids=[targeted_id])

        targeted_after = (await adapter.retrieve(collection, [targeted_id]))[0]
        assert targeted_after.payload["belongs_to_set"] == ["beta"]

        untouched_after = (await adapter.retrieve(collection, [untouched_same_tag_id]))[0]
        assert untouched_after.payload["belongs_to_set"] == ["alfa"]
    finally:
        await adapter.prune()
        await adapter.close()