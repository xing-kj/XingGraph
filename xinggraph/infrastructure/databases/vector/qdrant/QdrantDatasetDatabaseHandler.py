from uuid import UUID
from typing import Optional

from qdrant_client import AsyncQdrantClient

from xinggraph.modules.users.models import User
from xinggraph.modules.users.models import DatasetDatabase
from xinggraph.infrastructure.databases.vector import get_vectordb_config
from xinggraph.infrastructure.databases.vector.create_vector_engine import (
    aevict_vector_engines_for_database,
)
from xinggraph.infrastructure.databases.dataset_database_handler import DatasetDatabaseHandlerInterface


class QdrantDatasetDatabaseHandler(DatasetDatabaseHandlerInterface):
    """
    Handler for interacting with Qdrant Dataset databases.

    Qdrant is a shared server, so per-dataset isolation is achieved by giving
    every dataset a unique ``vector_database_name`` (= dataset UUID). The
    QdrantAdapter then namespaces every collection as
    ``{vector_database_name}__{collection}`` (prefix isolation).
    """

    @classmethod
    async def create_dataset(cls, dataset_id: Optional[UUID], user: Optional[User]) -> dict:
        vector_config = get_vectordb_config()

        if vector_config.vector_db_provider != "qdrant":
            raise ValueError(
                "QdrantDatasetDatabaseHandler can only be used with Qdrant vector database provider."
            )

        vector_db_name = f"{dataset_id}"

        return {
            "vector_database_provider": vector_config.vector_db_provider,
            "vector_database_url": vector_config.vector_db_url,
            "vector_database_name": vector_db_name,
            "vector_database_key": vector_config.vector_db_key,
            "vector_dataset_database_handler": "qdrant",
        }

    @classmethod
    async def resolve_dataset_connection_info(
        cls, dataset_database: DatasetDatabase
    ) -> DatasetDatabase:
        vector_config = get_vectordb_config()
        # The Qdrant connection parameters never live in the relational DB; they
        # are always resolved from the current vector config.
        dataset_database.vector_database_url = vector_config.vector_db_url
        dataset_database.vector_database_key = vector_config.vector_db_key
        return dataset_database

    @classmethod
    async def delete_dataset(cls, dataset_database: DatasetDatabase):
        # Evict every cached engine for this database so a live engine with a
        # stale collection cache cannot be reused, then drop this dataset's
        # prefixed collections directly over the shared Qdrant server.
        await aevict_vector_engines_for_database(dataset_database.vector_database_name)

        client = AsyncQdrantClient(
            url=dataset_database.vector_database_url,
            api_key=dataset_database.vector_database_key or None,
            prefer_grpc=False,
        )
        try:
            collections = (await client.get_collections()).collections
            prefix = f"{dataset_database.vector_database_name}__"
            targets = [c.name for c in collections if c.name.startswith(prefix)]
            for collection_name in targets:
                await client.delete_collection(collection_name)
        finally:
            await client.close()