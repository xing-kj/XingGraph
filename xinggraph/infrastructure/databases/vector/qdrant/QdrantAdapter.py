import asyncio
from typing import Any, List, Optional
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import BaseModel

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qdrant_models

from xinggraph.infrastructure.databases.exceptions import MissingQueryParameterError
from xinggraph.infrastructure.engine import DataPoint
from xinggraph.infrastructure.engine.utils import parse_id
from xinggraph.infrastructure.databases.vector.exceptions import CollectionNotFoundError
from xinggraph.infrastructure.databases.vector.pgvector.serialize_data import serialize_data
from xinggraph.shared.logging_utils import get_logger

from ..embeddings.EmbeddingEngine import EmbeddingEngine
from ..models.ScoredResult import ScoredResult
from ..vector_db_interface import VectorDBInterface

logger = get_logger("QdrantAdapter")

# Qdrant caps a single search at this many results; when the caller asks for
# "everything" (limit=None) we still return a bounded set.
MAX_LIMIT = 10_000


class IndexSchema(DataPoint):
    """
    Represents a schema for an index data point containing an ID and text.

    Attributes:

    - id: A string representing the unique identifier for the data point.
    - text: A string representing the content of the data point.
    - metadata: A dictionary with default index fields for the schema, currently configured
      to include 'text'.
    """

    id: str
    text: str

    # Optional reference scalars carried for the search "Evidence" feature.
    # They stay None for non-chunk data points, so this schema remains
    # compatible with every indexed DataPoint type.
    document_id: Optional[str] = None
    document_name: Optional[str] = None
    chunk_index: Optional[int] = None
    source_chunk_id: Optional[str] = None
    importance_weight: Optional[float] = 0.5

    metadata: dict = {"index_fields": ["text"]}
    belongs_to_set: List[str] = []


class QdrantAdapter(VectorDBInterface):
    """Vector-database adapter backed by Qdrant; implements the VectorDBInterface contract.

    When constructed with a non-empty ``database_name`` (per-dataset routing with
    backend access control), every collection is namespaced as
    ``f"{database_name}__{collection_name}"`` so different datasets live in
    physically separate Qdrant collections (prefix isolation).
    """

    name = "Qdrant"

    def __init__(
        self,
        url: str,
        api_key: Optional[str],
        embedding_engine: EmbeddingEngine,
        database_name: str = "",
    ):
        if not url:
            raise ValueError(
                "QdrantAdapter requires a non-empty `url` (e.g. http://localhost:6333)."
            )
        self.url = url
        self.api_key = api_key
        self.embedding_engine = embedding_engine
        self.database_name = database_name
        self._client: Optional[AsyncQdrantClient] = None
        self._client_lock = asyncio.Lock()
        self.VECTOR_DB_LOCK = asyncio.Lock()

    async def get_connection(self) -> AsyncQdrantClient:
        if self._client is not None:
            return self._client
        async with self._client_lock:
            if self._client is None:
                self._client = AsyncQdrantClient(
                    url=self.url,
                    api_key=self.api_key or None,
                    prefer_grpc=False,
                )
            return self._client

    async def close(self) -> None:
        """Close the underlying AsyncQdrantClient. Idempotent."""
        client, self._client = self._client, None
        if client is not None:
            try:
                await client.close()
            except Exception as e:
                logger.warning("Error closing Qdrant client: %s", e)

    def _full_collection_name(self, collection_name: str) -> str:
        if self.database_name:
            return f"{self.database_name}__{collection_name}"
        return collection_name

    @staticmethod
    def _point_id(identifier) -> str:
        """Map a xinggraph id to a Qdrant-compatible point id byte-for-byte stably.

        Qdrant point ids must be unsigned integers or UUID strings. xinggraph ids may
        be arbitrary strings (e.g. graph-computed deterministic ids), so non-UUID
        values are hashed into a deterministic UUIDv5. The original id always
        lives in the record payload under ``id``.
        """
        value = parse_id(identifier)
        if isinstance(value, UUID):
            return str(value)
        return str(uuid5(NAMESPACE_URL, f"xinggraph:{value}"))

    @staticmethod
    def _result_id(point) -> Any:
        """Return the original xinggraph id for a Qdrant ScoredPoint/Record."""
        payload_id = (point.payload or {}).get("id")
        if payload_id is not None:
            return parse_id(payload_id)
        return parse_id(point.id)

    async def embed_data(self, data: list[str]) -> list[list[float]]:
        """Embed the provided text and return a list of embedded vectors."""
        return await self.embedding_engine.embed_text(data)

    async def has_collection(self, collection_name: str) -> bool:
        """Check if the given (logical) collection exists in Qdrant."""
        return await (await self.get_connection()).collection_exists(
            self._full_collection_name(collection_name)
        )

    async def create_collection(self, collection_name: str, payload_schema: Optional[Any] = None):
        """Create the Qdrant collection for ``collection_name`` if it does not exist."""
        vector_size = self.embedding_engine.get_vector_size()
        full_name = self._full_collection_name(collection_name)

        if not await self.has_collection(collection_name):
            async with self.VECTOR_DB_LOCK:
                if not await self.has_collection(collection_name):
                    try:
                        await (await self.get_connection()).create_collection(
                            collection_name=full_name,
                            vectors_config=qdrant_models.VectorParams(
                                size=vector_size,
                                distance=qdrant_models.Distance.COSINE,
                            ),
                        )
                    except Exception as e:
                        # Qdrant collection deletion is asynchronous: right after
                        # a drop (e.g. prune) the physical directory lingers
                        # while collection_exists reports False, so create fails
                        # with "already exists" even though no collection is
                        # visible. Wait for the stale state to settle, then
                        # retry the create a bounded number of times.
                        hint = ""
                        if getattr(e, "status_code", None) == 400:
                            hint = str(e).lower()
                        elif getattr(e, "content", None):
                            try:
                                hint = str(e.content).lower()
                            except Exception:
                                hint = ""
                        if "already exists" not in hint:
                            raise

                        logger.debug(
                            "collection '%s' create raced with an async delete, "
                            "retrying: %s",
                            full_name,
                            e,
                        )
                        for attempt in range(10):
                            await asyncio.sleep(0.5)
                            if await self.has_collection(collection_name):
                                return
                            try:
                                await (await self.get_connection()).create_collection(
                                    collection_name=full_name,
                                    vectors_config=qdrant_models.VectorParams(
                                        size=vector_size,
                                        distance=qdrant_models.Distance.COSINE,
                                    ),
                                )
                                return
                            except Exception as retry_e:
                                hint = str(retry_e).lower()
                                if getattr(retry_e, "content", None):
                                    try:
                                        hint = str(retry_e.content).lower()
                                    except Exception:
                                        pass
                                if "already exists" not in hint:
                                    raise
                        # Stale on-disk state never cleared; surface the original
                        # error instead of silently proceeding with a phantom.
                        raise

    async def get_collection(self, collection_name: str):
        """Return the Qdrant CollectionInfo for a logical collection or raise."""
        if not await self.has_collection(collection_name):
            raise CollectionNotFoundError(f"Collection '{collection_name}' not found!")
        full_name = self._full_collection_name(collection_name)
        return await (await self.get_connection()).get_collection(full_name)

    async def create_data_points(self, collection_name: str, data_points: list[DataPoint]):
        """Upsert DataPoints into the Qdrant collection, merging belongs_to_set arrays."""
        if not data_points:
            return

        if not await self.has_collection(collection_name):
            await self.create_collection(collection_name, type(data_points[0]))

        data_vectors = await self.embed_data(
            [DataPoint.get_embeddable_data(data_point) for data_point in data_points]
        )

        # The prefetch of existing `belongs_to_set` values and the subsequent
        # upsert must run inside the same lock section: if a second upsert ran
        # between our read and our write, we'd clobber tags we never saw and
        # lose them silently (mirrors LanceDBAdapter.create_data_points).
        async with self.VECTOR_DB_LOCK:
            payload_schema = type(data_points[0])
            schema_model = self.get_data_point_schema(payload_schema)

            # Prefetch existing `belongs_to_set` arrays for the incoming ids so
            # the upsert unions tags instead of clobbering them.
            existing_belongs_to_set: dict[str, list] = {}
            try:
                existing_records = await self.retrieve(
                    collection_name, [str(data_point.id) for data_point in data_points]
                )
                for record in existing_records:
                    prior = (record.payload or {}).get("belongs_to_set") or []
                    if prior:
                        existing_belongs_to_set[str(record.id)] = list(prior)
            except Exception as e:
                logger.debug(
                    "belongs_to_set merge lookup failed for '%s': %s",
                    collection_name,
                    e,
                )

            def _payload_for(data_point: DataPoint, vector: list[float]) -> dict:
                properties = schema_model.model_validate(
                    serialize_data(data_point.model_dump())
                ).model_dump()
                properties["id"] = str(data_point.id)
                prior = existing_belongs_to_set.get(str(data_point.id))
                if prior:
                    incoming = properties.get("belongs_to_set") or []
                    properties["belongs_to_set"] = list(
                        dict.fromkeys(list(prior) + list(incoming))
                    )
                return properties

            points = [
                qdrant_models.PointStruct(
                    id=self._point_id(data_point.id),
                    vector=data_vectors[idx],
                    payload=_payload_for(data_point, data_vectors[idx]),
                )
                for idx, data_point in enumerate(data_points)
            ]

            # Dedup by id within the batch, unioning belongs_to_set on duplicates.
            deduped: dict[str, qdrant_models.PointStruct] = {}
            for point in points:
                existing = deduped.get(point.id)
                if existing is None:
                    deduped[point.id] = point
                    continue
                existing_tags = (existing.payload or {}).get("belongs_to_set") or []
                incoming_tags = (point.payload or {}).get("belongs_to_set") or []
                if existing_tags or incoming_tags:
                    merged_tags = list(dict.fromkeys(list(existing_tags) + list(incoming_tags)))
                    existing.payload["belongs_to_set"] = merged_tags
                deduped[point.id] = existing

            client = await self.get_connection()
            await client.upsert(
                collection_name=self._full_collection_name(collection_name),
                points=list(deduped.values()),
            )

    async def upsert_raw_vectors(
        self,
        collection_name: str,
        points: list[dict],
        payload_schema: Optional[type[BaseModel]] = None,
    ) -> None:
        """Upsert caller-provided vectors without invoking the embedding engine."""
        if not points:
            return

        if not await self.has_collection(collection_name):
            await self.create_collection(collection_name, payload_schema)

        vector_size = self.embedding_engine.get_vector_size()
        raw_points = []
        for point in points:
            point_id = point.get("id")
            vector = point.get("vector")
            payload_value = point.get("payload")
            if point_id is None:
                raise ValueError("Raw vector point is missing id")
            if not isinstance(vector, list):
                raise ValueError("Raw vector point vector must be a list")
            if len(vector) != vector_size:
                raise ValueError(
                    f"Raw vector size {len(vector)} does not match expected size {vector_size}"
                )
            payload_obj = dict(payload_value) if payload_value else {}
            if payload_schema is not None:
                payload_obj = payload_schema.model_validate(payload_obj).model_dump()
            payload_obj["id"] = str(point_id)
            raw_points.append(
                qdrant_models.PointStruct(
                    id=self._point_id(point_id),
                    vector=vector,
                    payload=payload_obj,
                )
            )

        await (await self.get_connection()).upsert(
            collection_name=self._full_collection_name(collection_name),
            points=raw_points,
        )

    async def retrieve(
        self, collection_name: str, data_point_ids: list[str], *, include_vector: bool = False
    ):
        """Return records from the collection whose id is in ``data_point_ids``."""
        if not data_point_ids:
            return []
        if not await self.has_collection(collection_name):
            return []

        client = await self.get_connection()
        records = await client.retrieve(
            collection_name=self._full_collection_name(collection_name),
            ids=[self._point_id(data_point_id) for data_point_id in data_point_ids],
            with_vectors=include_vector,
            with_payload=True,
        )

        results = []
        for record in records:
            payload = dict(record.payload or {})
            if include_vector and record.vector is not None:
                vector = (
                    record.vector
                    if isinstance(record.vector, list)
                    else list(record.vector.values())[0]
                )
                payload["vector"] = vector
            results.append(
                ScoredResult(
                    id=self._result_id(record),
                    payload=payload,
                    score=0,
                )
            )
        return results

    async def search(
        self,
        collection_name: str,
        query_text: Optional[str] = None,
        query_vector: Optional[List[float]] = None,
        limit: Optional[int] = None,
        with_vector: bool = False,
        include_payload: bool = False,
        node_name: Optional[List[str]] = None,
        node_name_filter_operator: str = "OR",
    ):
        """Perform a vector search over the Qdrant collection."""
        if query_text is None and query_vector is None:
            raise MissingQueryParameterError()

        if query_text and not query_vector:
            query_vector = (await self.embedding_engine.embed_text([query_text]))[0]

        query_vector = list(query_vector)

        if not await self.has_collection(collection_name):
            return []

        if limit is None or limit <= 0:
            limit = MAX_LIMIT
        else:
            limit = min(int(limit), MAX_LIMIT)

        query_filter = self._build_filter(node_name, node_name_filter_operator)

        client = await self.get_connection()
        response = await client.query_points(
            collection_name=self._full_collection_name(collection_name),
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=include_payload,
            with_vectors=with_vector,
        )
        results = response.points

        return [
            ScoredResult(
                id=self._result_id(result),
                payload=result.payload if include_payload else None,
                score=float(result.score),
            )
            for result in results
        ]

    async def batch_search(
        self,
        collection_name: str,
        query_texts: List[str],
        limit: Optional[int] = None,
        with_vectors: bool = False,
        include_payload: bool = False,
        node_name: Optional[List[str]] = None,
    ):
        query_vectors = await self.embedding_engine.embed_text(query_texts)

        if limit is None or limit <= 0:
            effective_limit = MAX_LIMIT
        else:
            effective_limit = min(int(limit), MAX_LIMIT)

        query_filter = self._build_filter(node_name, "OR")

        client = await self.get_connection()
        full_name = self._full_collection_name(collection_name)
        requests = [
            qdrant_models.QueryRequest(
                query=qdrant_models.NearestQuery(nearest=query_vector),
                limit=effective_limit,
                filter=query_filter,
                with_payload=include_payload,
                with_vector=with_vectors,
            )
            for query_vector in query_vectors
        ]
        batch_results = await client.query_batch_points(
            collection_name=full_name,
            requests=requests,
        )
        return [
            [
                ScoredResult(
                    id=self._result_id(result),
                    payload=result.payload if include_payload else None,
                    score=float(result.score),
                )
                for result in response.points
            ]
            for response in batch_results
        ]

    def _build_filter(
        self, node_name: Optional[List[str]], node_name_filter_operator: str
    ) -> Optional[qdrant_models.Filter]:
        if not node_name:
            return None
        return_models = qdrant_models
        if node_name_filter_operator == "AND":
            # Every value must be present in the belongs_to_set array.
            return return_models.Filter(
                must=[
                    return_models.FieldCondition(
                        key="belongs_to_set",
                        match=return_models.MatchValue(value=name),
                    )
                    for name in node_name
                ]
            )
        # OR (default): any value is sufficient.
        return return_models.Filter(
            must=[
                return_models.FieldCondition(
                    key="belongs_to_set",
                    match=return_models.MatchAny(any=node_name),
                )
            ]
        )

    async def delete_data_points(self, collection_name: str, data_point_ids: list[UUID]):
        # Idempotent: a missing collection (or empty id list) is a no-op.
        if not await self.has_collection(collection_name):
            return
        if not data_point_ids:
            return

        client = await self.get_connection()
        await client.delete(
            collection_name=self._full_collection_name(collection_name),
            points_selector=qdrant_models.PointIdsList(
                points=[self._point_id(data_point_id) for data_point_id in data_point_ids]
            ),
        )

    async def remove_belongs_to_set_tags(
        self,
        tags: List[str],
        node_ids: Optional[List[str]] = None,
    ) -> None:
        """Strip the given tag names from `belongs_to_set` arrays in every
        collection and delete rows whose array becomes empty. Used to reconcile
        surviving shared rows after a dataset/NodeSet is deleted.

        Qdrant does not support in-place payload mutation, so the path reads
        rows that reference any target tag, rewrites the payload with the tag
        removed, and either overwrites the point via upsert (merge) or deletes
        it when the array is empty.
        """
        if not tags:
            return None
        if node_ids is not None and not node_ids:
            return None

        tag_set = set(tags)
        id_set: Optional[set[str]] = (
            {str(nid) for nid in node_ids} if node_ids is not None else None
        )
        client = await self.get_connection()

        full_name = self._full_collection_name("").rstrip("__")
        all_collections = (await client.get_collections()).collections
        prefix = f"{full_name}__" if full_name else ""

        for collection_info in all_collections:
            collection_name = collection_info.name
            if prefix and not collection_name.startswith(prefix):
                continue

            must = [
                qdrant_models.FieldCondition(
                    key="belongs_to_set",
                    match=qdrant_models.MatchAny(any=list(tag_set)),
                )
            ]
            if id_set is not None:
                must.append(
                    qdrant_models.FieldCondition(
                        key="id",
                        match=qdrant_models.MatchAny(any=list(id_set)),
                    )
                )
            qfilter = qdrant_models.Filter(must=must)

            scroll_response = await client.scroll(
                collection_name=collection_name,
                scroll_filter=qfilter,
                limit=10_000,
                with_payload=True,
            )
            points, _ = scroll_response

            rows_to_delete: list[str] = []
            rows_to_update = []
            for point in points:
                payload = point.payload or {}
                current = payload.get("belongs_to_set") or []
                if not any(tag in tag_set for tag in current):
                    continue
                remaining = [tag for tag in current if tag not in tag_set]
                if remaining:
                    payload["belongs_to_set"] = remaining
                    rows_to_update.append(point)
                else:
                    rows_to_delete.append(str(point.id))

            if rows_to_delete:
                await client.delete(
                    collection_name=collection_name,
                    points_selector=qdrant_models.PointIdsList(
                        points=rows_to_delete
                    ),
                )

            for point in rows_to_update:
                await client.set_payload(
                    collection_name=collection_name,
                    payload=point.payload,
                    points=[str(point.id)],
                )

        return None

    async def create_vector_index(self, index_name: str, index_property_name: str):
        await self.create_collection(
            f"{index_name}_{index_property_name}", payload_schema=IndexSchema
        )

    async def index_data_points(
        self, index_name: str, index_property_name: str, data_points: list[DataPoint]
    ):
        await self.create_data_points(
            f"{index_name}_{index_property_name}",
            [
                IndexSchema(
                    id=str(data_point.id),
                    text=getattr(data_point, data_point.metadata["index_fields"][0]),
                    document_id=getattr(data_point, "document_id", None),
                    document_name=getattr(data_point, "document_name", None),
                    chunk_index=getattr(data_point, "chunk_index", None),
                    source_chunk_id=getattr(data_point, "source_chunk_id", None),
                    importance_weight=getattr(data_point, "importance_weight", None),
                    belongs_to_set=(data_point.belongs_to_set or []),
                )
                for data_point in data_points
            ],
        )

    async def prune(self):
        """Delete every Qdrant collection owned by this adapter.

        When a per-dataset prefix is set, only collections under that prefix are
        removed; otherwise all collections on the server are removed (mirrors
        LanceDB dropping its shared store).
        """
        client = await self.get_connection()
        collections = (await client.get_collections()).collections

        prefix = self._full_collection_name("")
        for info in collections:
            name = info.name
            if prefix and not name.startswith(prefix):
                continue
            try:
                await client.delete_collection(name)
            except Exception as e:
                logger.warning("prune: failed to drop '%s': %s", name, e)

    def get_data_point_schema(self, model_type: BaseModel) -> BaseModel:
        """Return the payload schema for ``model_type`` unchanged (Qdrant is schemaless)."""
        return model_type

    async def run_migrations(self):
        return None