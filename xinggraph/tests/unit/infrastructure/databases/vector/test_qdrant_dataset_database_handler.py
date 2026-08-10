from importlib import import_module
from types import SimpleNamespace
from uuid import uuid4

import pytest
import re

import xinggraph.infrastructure.databases.dataset_database_handler  # noqa: F401


handler_module = import_module(
    "xinggraph.infrastructure.databases.vector.qdrant.QdrantDatasetDatabaseHandler"
)


@pytest.mark.asyncio
async def test_qdrant_dataset_handler_create_dataset(monkeypatch):
    """Verify the handler returns a unique per-dataset Qdrant database name."""
    user = SimpleNamespace(id=uuid4())
    dataset_id = uuid4()

    monkeypatch.setattr(
        handler_module,
        "get_vectordb_config",
        lambda: SimpleNamespace(
            vector_db_provider="qdrant",
            vector_db_url="http://localhost:6333",
            vector_db_key="",
        ),
    )

    dataset_config = await handler_module.QdrantDatasetDatabaseHandler.create_dataset(
        dataset_id, user
    )

    assert dataset_config["vector_database_provider"] == "qdrant"
    assert dataset_config["vector_database_url"] == "http://localhost:6333"
    assert dataset_config["vector_database_key"] == ""
    assert dataset_config["vector_database_name"] == str(dataset_id)
    assert dataset_config["vector_dataset_database_handler"] == "qdrant"


@pytest.mark.asyncio
async def test_qdrant_dataset_handler_rejects_non_qdrant_provider(monkeypatch):
    """The qdrant handler refuses to run when another provider is configured."""
    dataset_id = uuid4()

    monkeypatch.setattr(
        handler_module,
        "get_vectordb_config",
        lambda: SimpleNamespace(
            vector_db_provider="lancedb",
            vector_db_url="database/xinggraph.lancedb",
            vector_db_key="",
        ),
    )

    import pytest as _pytest

    with _pytest.raises(ValueError, match=re.compile("qdrant", re.IGNORECASE)):
        await handler_module.QdrantDatasetDatabaseHandler.create_dataset(dataset_id, None)