import os
import asyncio
import pathlib
from uuid import UUID

import xinggraph
from xinggraph.shared.logging_utils import setup_logging, ERROR
from xinggraph.modules.data.methods.delete_dataset import delete_dataset
from xinggraph.modules.data.methods.get_dataset import get_dataset
from xinggraph.modules.data.methods.get_dataset_databases import get_dataset_databases
from xinggraph.modules.users.methods import get_default_user


async def get_dataset_database(dataset_id: UUID, user_id: UUID):
    dataset_databases = await get_dataset_databases()
    for dataset_database in dataset_databases:
        if dataset_database.dataset_id == dataset_id and dataset_database.owner_id == user_id:
            return dataset_database
    raise AssertionError(f"Dataset database not found for dataset {dataset_id}.")


async def main():
    # Set data and system directory paths
    data_directory_path = str(
        pathlib.Path(
            os.path.join(pathlib.Path(__file__).parent, ".data_storage/test_dataset_delete")
        ).resolve()
    )
    xinggraph.config.data_root_directory(data_directory_path)
    xinggraph_directory_path = str(
        pathlib.Path(
            os.path.join(pathlib.Path(__file__).parent, ".xinggraph_system/test_dataset_delete")
        ).resolve()
    )
    xinggraph.config.system_root_directory(xinggraph_directory_path)

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

    # Add the text, and make it available for cognify
    await xinggraph.add(text, "nlp_dataset")
    await xinggraph.add("Quantum computing is the study of quantum computers.", "quantum_dataset")

    # Use LLMs and xinggraph to create knowledge graph
    ret_val = await xinggraph.cognify()
    user = await get_default_user()

    for val in ret_val:
        dataset_id = UUID(str(val))
        dataset_database = await get_dataset_database(dataset_id, user.id)
        graph_db_path = os.path.join(
            xinggraph_directory_path,
            "databases",
            str(user.id),
            dataset_database.graph_database_name,
        )
        vector_db_path = dataset_database.vector_database_url

        # Check if databases are properly created and exist before deletion
        assert os.path.exists(graph_db_path), "Graph database file not found."
        assert os.path.exists(vector_db_path), "Vector database file not found."

        dataset = await get_dataset(user_id=user.id, dataset_id=dataset_id)
        await delete_dataset(dataset)

        # Confirm databases have been deleted
        assert not os.path.exists(graph_db_path), "Graph database file found."
        assert not os.path.exists(vector_db_path), "Vector database file found."


if __name__ == "__main__":
    logger = setup_logging(log_level=ERROR)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
