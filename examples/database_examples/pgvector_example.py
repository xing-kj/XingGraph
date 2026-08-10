# ruff: noqa: E402
import os
import pathlib
import asyncio

from dotenv import load_dotenv

load_dotenv(override=True)

DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")

import xinggraph
from xinggraph import SearchType


async def main():
    """
    Example script demonstrating how to use XingGraph with PGVector

    This example:
    1. Configures XingGraph to use PostgreSQL with PGVector extension as vector database
    2. Sets up data directories
    3. Stores sample data with remember to XingGraph
    4. Performs different types of searches
    """
    # Configure PGVector as the vector database provider
    xinggraph.config.set_vector_db_config(
        {
            "vector_db_provider": "pgvector",  # Specify PGVector as provider
            "vector_dataset_database_handler": "pgvector",
            "vector_db_name": "xinggraph_db",
            "vector_db_host": os.environ.get("DB_HOST", "127.0.0.1"),
            "vector_db_port": "5432",
            "vector_db_username": "xinggraph",
            "vector_db_password": "xinggraph",
        }
    )

    # Configure PostgreSQL connection details
    # These settings are required for PGVector
    xinggraph.config.set_relational_db_config(
        {
            "db_path": "",
            "db_name": "xinggraph_db",
            "db_host": DB_HOST,
            "db_port": "5432",
            "db_username": "xinggraph",
            "db_password": "xinggraph",
            "db_provider": "postgres",
        }
    )

    # Set up data directories for storing documents and system files
    # You should adjust these paths to your needs
    current_dir = pathlib.Path(__file__).parent
    data_directory_path = str(current_dir / "data_storage")
    xinggraph.config.data_root_directory(data_directory_path)

    xinggraph_directory_path = str(current_dir / "xinggraph_system")
    xinggraph.config.system_root_directory(xinggraph_directory_path)

    # Clean any existing data (optional)
    # await xinggraph.forget(everything=True)

    # Create a dataset
    dataset_name = "pgvector_example"

    # Add sample text to the dataset
    sample_text = """PGVector is an extension for PostgreSQL that adds vector similarity search capabilities.
    It supports multiple indexing methods, including IVFFlat, HNSW, and brute-force search.
    PGVector allows you to store vector embeddings directly in your PostgreSQL database.
    It provides distance functions like L2 distance, inner product, and cosine distance.
    Using PGVector, you can perform both metadata filtering and vector similarity search in a single query.
    The extension is often used for applications like semantic search, recommendations, and image similarity."""

    # Add the sample text to the dataset
    await xinggraph.remember([sample_text], dataset_name=dataset_name, self_improvement=False)

    # Now let's perform some searches
    # 1. Search for insights related to "PGVector"
    insights_results = await xinggraph.recall(
        query_type=SearchType.GRAPH_COMPLETION, query_text="PGVector"
    )
    print("\nInsights about PGVector:")
    for result in insights_results:
        print(f"- {result}")

    # 2. Search for text chunks related to "vector similarity"
    chunks_results = await xinggraph.recall(
        query_type=SearchType.CHUNKS, query_text="vector similarity", datasets=[dataset_name]
    )
    print("\nChunks about vector similarity:")
    for result in chunks_results:
        print(f"- {result}")

    # 3. Get graph completion related to databases
    graph_completion_results = await xinggraph.recall(
        query_type=SearchType.GRAPH_COMPLETION, query_text="database"
    )
    print("\nGraph completion for databases:")
    for result in graph_completion_results:
        print(f"- {result}")

    # Clean up (optional)
    # await xinggraph.forget(everything=True)


if __name__ == "__main__":
    asyncio.run(main())
