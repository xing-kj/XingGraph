import os

import pytest

import xinggraph
from xinggraph.modules.users.methods import get_default_user
from xinggraph.infrastructure.databases.dataset_database_handler import DatasetDatabaseHandlerInterface
from xinggraph.shared.logging_utils import setup_logging, ERROR
from xinggraph.api.v1.search import SearchType


class LanceDBTestDatasetDatabaseHandler(DatasetDatabaseHandlerInterface):
    @classmethod
    async def create_dataset(cls, dataset_id, user):
        import pathlib

        xinggraph_directory_path = str(
            pathlib.Path(
                os.path.join(
                    pathlib.Path(__file__).parent, ".xinggraph_system/test_dataset_database_handler"
                )
            ).resolve()
        )
        databases_directory_path = os.path.join(xinggraph_directory_path, "databases", str(user.id))
        os.makedirs(databases_directory_path, exist_ok=True)

        vector_db_name = "test.lance.db"

        return {
            "vector_dataset_database_handler": "custom_lancedb_handler",
            "vector_database_name": vector_db_name,
            "vector_database_url": os.path.join(databases_directory_path, vector_db_name),
            "vector_database_provider": "lancedb",
        }


class LadybugTestDatasetDatabaseHandler(DatasetDatabaseHandlerInterface):
    @classmethod
    async def create_dataset(cls, dataset_id, user):
        import pathlib

        xinggraph_directory_path = str(
            pathlib.Path(
                os.path.join(
                    pathlib.Path(__file__).parent, ".xinggraph_system/test_dataset_database_handler"
                )
            ).resolve()
        )
        databases_directory_path = os.path.join(xinggraph_directory_path, "databases", str(user.id))
        os.makedirs(databases_directory_path, exist_ok=True)

        graph_db_name = "test.lbug"
        return {
            "graph_dataset_database_handler": "custom_ladybug_handler",
            "graph_database_name": graph_db_name,
            "graph_database_url": os.path.join(databases_directory_path, graph_db_name),
            "graph_database_provider": "ladybug",
        }


async def _run_custom_dataset_database_handler_flow():
    import pathlib

    data_directory_path = str(
        pathlib.Path(
            os.path.join(
                pathlib.Path(__file__).parent, ".data_storage/test_dataset_database_handler"
            )
        ).resolve()
    )
    xinggraph.config.data_root_directory(data_directory_path)
    xinggraph_directory_path = str(
        pathlib.Path(
            os.path.join(
                pathlib.Path(__file__).parent, ".xinggraph_system/test_dataset_database_handler"
            )
        ).resolve()
    )
    xinggraph.config.system_root_directory(xinggraph_directory_path)

    # Add custom dataset database handler
    from xinggraph.infrastructure.databases.dataset_database_handler.use_dataset_database_handler import (
        use_dataset_database_handler,
    )

    use_dataset_database_handler(
        "custom_lancedb_handler", LanceDBTestDatasetDatabaseHandler, "lancedb"
    )
    use_dataset_database_handler(
        "custom_ladybug_handler", LadybugTestDatasetDatabaseHandler, "ladybug"
    )

    # Create a clean slate for xinggraph -- reset data and system state
    print("Resetting xinggraph data...")
    await xinggraph.prune.prune_data()
    await xinggraph.prune.prune_system(metadata=True)
    print("Data reset complete.\n")

    # xinggraph knowledge graph will be created based on this text
    text = """
    Natural language processing (NLP) is an interdisciplinary
    subfield of computer science and information retrieval.
    """

    print("Adding text to xinggraph:")
    print(text.strip())

    # Add the text, and make it available for cognify
    await xinggraph.add(text)
    print("Text added successfully.\n")

    # Use LLMs and xinggraph to create knowledge graph
    await xinggraph.cognify()
    print("Cognify process complete.\n")

    query_text = "Tell me about NLP"
    print(f"Searching xinggraph for insights with query: '{query_text}'")
    # Query xinggraph for insights on the added text
    search_results = await xinggraph.search(
        query_type=SearchType.GRAPH_COMPLETION, query_text=query_text
    )

    print("Search results:")
    # Display results
    for result_text in search_results:
        print(result_text)

    default_user = await get_default_user()
    # Assert that the custom database files were created based on the custom dataset database handlers
    assert os.path.exists(
        os.path.join(xinggraph_directory_path, "databases", str(default_user.id), "test.lbug")
    ), "Graph database file not found."
    assert os.path.exists(
        os.path.join(xinggraph_directory_path, "databases", str(default_user.id), "test.lance.db")
    ), "Vector database file not found."


@pytest.mark.asyncio
async def test_custom_dataset_database_handlers(monkeypatch):
    monkeypatch.setenv("VECTOR_DATASET_DATABASE_HANDLER", "custom_lancedb_handler")
    monkeypatch.setenv("GRAPH_DATASET_DATABASE_HANDLER", "custom_ladybug_handler")

    await _run_custom_dataset_database_handler_flow()


if __name__ == "__main__":
    import asyncio

    os.environ["VECTOR_DATASET_DATABASE_HANDLER"] = "custom_lancedb_handler"
    os.environ["GRAPH_DATASET_DATABASE_HANDLER"] = "custom_ladybug_handler"

    setup_logging(log_level=ERROR)
    asyncio.run(_run_custom_dataset_database_handler_flow())
