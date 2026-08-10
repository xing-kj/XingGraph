import asyncio

import xinggraph
from xinggraph import SearchType
from xinggraph.modules.engine.operations.setup import setup
from xinggraph.modules.pipelines import Task
from xinggraph.modules.users.methods import get_default_user
from xinggraph.shared.logging_utils import INFO, setup_logging

# Prerequisites:
# 1. Copy `.env.template` and rename it to `.env`.
# 2. Add your OpenAI API key to the `.env` file in the `LLM_API_KEY` field:
#    LLM_API_KEY = "your_key_here"


async def main():
    # Create a clean slate for xinggraph -- reset data and system state
    print("Resetting xinggraph data...")
    await xinggraph.prune.prune_data()
    await xinggraph.prune.prune_system(metadata=True)
    print("Data reset complete.\n")

    # Create relational database and tables
    await setup()

    # xinggraph knowledge graph will be created based on this text
    text = """
    Natural language processing (NLP) is an interdisciplinary
    subfield of computer science and information retrieval.
    """

    print("Adding text to xinggraph:")
    print(text.strip())

    # Let's recreate the xinggraph add pipeline through the custom pipeline framework
    from xinggraph.tasks.ingestion import ingest_data, resolve_data_directories

    user = await get_default_user()

    # Values for tasks need to be filled before calling the pipeline
    add_tasks = [
        Task(resolve_data_directories, include_subdirectories=True),
        Task(
            ingest_data,
            "main_dataset",
            user,
        ),
    ]
    # Forward tasks to custom pipeline along with data and user information
    await xinggraph.run_custom_pipeline(
        tasks=add_tasks, data=text, user=user, dataset="main_dataset", pipeline_name="add_pipeline"
    )
    print("Text added successfully.\n")

    # Use LLMs and xinggraph to create knowledge graph
    from xinggraph.api.v1.cognify.cognify import get_default_tasks

    cognify_tasks = await get_default_tasks(user=user)
    print("Recreating existing cognify pipeline in custom pipeline to create knowledge graph...\n")
    await xinggraph.run_custom_pipeline(
        tasks=cognify_tasks, user=user, dataset="main_dataset", pipeline_name="cognify_pipeline"
    )
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


if __name__ == "__main__":
    logger = setup_logging(log_level=INFO)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
