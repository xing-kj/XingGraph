import asyncio
import pathlib

import xinggraph
from xinggraph import SearchType


async def main():
    """
    Example script demonstrating how to use XingGraph with Ladybug

    This example:
    1. Configures XingGraph to use Ladybug as graph database
    2. Sets up data directories
    3. Stores sample data with remember to XingGraph
    4. Performs different types of searches
    """
    # Configure Ladybug as the graph database provider
    xinggraph.config.set_graph_db_config(
        {
            "graph_database_provider": "ladybug",  # Specify Ladybug as provider
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
    dataset_name = "ladybug_example"

    # Add sample text to the dataset
    sample_text = """Ladybug is a graph database system optimized for running complex graph analytics.
    It is designed to be a high-performance graph database for data science workloads.
    Ladybug is built with modern hardware optimizations in mind.
    It provides support for property graphs and offers a Cypher-like query language.
    Ladybug can handle both transactional and analytical graph workloads.
    The database now includes vector search capabilities for AI applications and semantic search."""

    # Add the sample text to the dataset
    await xinggraph.remember([sample_text], dataset_name=dataset_name, self_improvement=False)

    # Now let's perform some searches
    # 1. Search for insights related to "Ladybug"
    insights_results = await xinggraph.recall(
        query_type=SearchType.GRAPH_COMPLETION, query_text="Ladybug"
    )
    print("\nInsights about Ladybug:")
    for result in insights_results:
        print(f"- {result}")

    # 2. Search for text chunks related to "graph database"
    chunks_results = await xinggraph.recall(
        query_type=SearchType.CHUNKS, query_text="graph database", datasets=[dataset_name]
    )
    print("\nChunks about graph database:")
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
