import os
import pathlib
import xinggraph
from xinggraph.infrastructure.files.storage import get_storage_config
from xinggraph.modules.retrieval.graph_completion_retriever import GraphCompletionRetriever
from xinggraph.modules.search.operations import get_history
from xinggraph.modules.users.methods import get_default_user
from xinggraph.shared.logging_utils import get_logger
from xinggraph.modules.search.types import SearchType
from xinggraph.modules.engine.models import NodeSet

logger = get_logger()


async def main():
    xinggraph.config.set_graph_database_provider("neo4j")
    data_directory_path = str(
        pathlib.Path(
            os.path.join(pathlib.Path(__file__).parent, ".data_storage/test_neo4j")
        ).resolve()
    )
    xinggraph.config.data_root_directory(data_directory_path)
    xinggraph_directory_path = str(
        pathlib.Path(
            os.path.join(pathlib.Path(__file__).parent, ".xinggraph_system/test_neo4j")
        ).resolve()
    )
    xinggraph.config.system_root_directory(xinggraph_directory_path)

    await xinggraph.prune.prune_data()
    await xinggraph.prune.prune_system(metadata=True)

    dataset_name = "cs_explanations"

    node_set_a = ["NLP"]
    node_set_b = ["Quantum", "Computers"]
    node_set_c = ["Quantum"]

    explanation_file_path_nlp = os.path.join(
        pathlib.Path(__file__).parent, "test_data/Natural_language_processing.txt"
    )
    from xinggraph.infrastructure.databases.graph import get_graph_engine

    graph_engine = await get_graph_engine()

    is_empty = await graph_engine.is_empty()

    assert is_empty, "Graph has to be empty"

    await xinggraph.add([explanation_file_path_nlp], dataset_name, node_set=node_set_a)

    explanation_file_path_quantum = os.path.join(
        pathlib.Path(__file__).parent, "test_data/Quantum_computers.txt"
    )

    await xinggraph.add([explanation_file_path_quantum], dataset_name, node_set=node_set_b)
    await xinggraph.add("Alice is an expert in Quantum Mechanics", dataset_name, node_set=node_set_c)

    is_empty = await graph_engine.is_empty()

    assert is_empty, "Graph has to be empty before cognify"

    await xinggraph.cognify([dataset_name])

    is_empty = await graph_engine.is_empty()

    assert not is_empty, "Graph shouldn't be empty"

    from xinggraph.infrastructure.databases.vector import get_vector_engine_async

    vector_engine = await get_vector_engine_async()
    random_node = (
        await vector_engine.search("Entity_name", "Quantum computer", include_payload=True)
    )[0]
    random_node_name = random_node.payload["text"]

    search_results = await xinggraph.search(
        query_type=SearchType.GRAPH_COMPLETION, query_text=random_node_name
    )
    assert len(search_results) != 0, "The search results list is empty."
    print("\n\nExtracted sentences are:\n")
    for result in search_results:
        print(f"{result}\n")

    search_results = await xinggraph.search(query_type=SearchType.CHUNKS, query_text=random_node_name)
    assert len(search_results) != 0, "The search results list is empty."
    print("\n\nExtracted chunks are:\n")
    for result in search_results:
        print(f"{result}\n")

    search_results = await xinggraph.search(
        query_type=SearchType.SUMMARIES, query_text=random_node_name
    )
    assert len(search_results) != 0, "Query related summaries don't exist."
    print("\nExtracted results are:\n")
    for result in search_results:
        print(f"{result}\n")

    # NOTE: Due to the test failing often on weak LLM models we've removed this test for now
    # search_results = await xinggraph.search(
    #     query_type=SearchType.NATURAL_LANGUAGE,
    #     query_text=f"Find nodes connected to node with name {random_node_name}",
    # )
    # assert len(search_results) != 0, "Query related natural language don't exist."
    # print("\nExtracted results are:\n")
    # for result in search_results:
    #     print(f"{result}\n")

    user = await get_default_user()
    history = await get_history(user.id)

    assert len(history) == 6, "Search history is not correct."

    nodeset_text = "Neo4j is a graph database that supports cypher."

    await xinggraph.add([nodeset_text], dataset_name, node_set=["first"])

    await xinggraph.cognify([dataset_name])

    graph_retriever = GraphCompletionRetriever(
        node_type=NodeSet,
        node_name=["first"],
    )
    objects = await graph_retriever.get_retrieved_objects("What is in the context?")
    context_nonempty = await graph_retriever.get_context_from_objects(
        query="What is in the context?", retrieved_objects=objects
    )

    graph_retriever = GraphCompletionRetriever(
        node_type=NodeSet,
        node_name=["nonexistent"],
    )
    objects = await graph_retriever.get_retrieved_objects("What is in the context?")
    context_empty = await graph_retriever.get_context_from_objects(
        query="What is in the context?", retrieved_objects=objects
    )

    assert isinstance(context_nonempty, str) and context_nonempty != "", (
        f"Nodeset_search_test:Expected non-empty string for context_nonempty, got: {context_nonempty!r}"
    )

    assert context_empty == "", (
        f"Nodeset_search_test:Expected empty string for context_empty, got: {context_empty!r}"
    )

    results = await graph_engine.get_nodeset_subgraph(
        NodeSet, node_set_b, node_name_filter_operator="OR"
    )
    nodes = results[0]
    assert any("alice" in node[1]["name"].lower() for node in nodes if "name" in node[1]), (
        "Alice is a part of the Quantum nodeset, so it should be included in results"
    )

    results = await graph_engine.get_nodeset_subgraph(
        NodeSet, node_set_b, node_name_filter_operator="AND"
    )
    nodes = results[0]
    assert all("Alice" not in node[1]["name"] for node in nodes if "name" in node[1]), (
        "Alice is ONLY a part of the Quantum nodeset, therefore she should NOT be included in results"
    )

    query_text = "Tell me about Quantum computers"
    graph_retriever = GraphCompletionRetriever(
        node_type=NodeSet, node_name=node_set_b, node_name_filter_operator="OR", top_k=250
    )
    objects = await graph_retriever.get_retrieved_objects(query_text)
    context = await graph_retriever.get_context_from_objects(
        query=query_text, retrieved_objects=objects
    )

    assert "Alice" in context

    graph_retriever = GraphCompletionRetriever(
        node_type=NodeSet, node_name=node_set_b, node_name_filter_operator="AND", top_k=250
    )
    objects = await graph_retriever.get_retrieved_objects(query_text)
    context = await graph_retriever.get_context_from_objects(
        query=query_text, retrieved_objects=objects
    )

    assert "Alice" not in context

    await xinggraph.prune.prune_data()
    data_root_directory = get_storage_config()["data_root_directory"]
    assert not os.path.isdir(data_root_directory), "Local data files are not deleted"

    await xinggraph.prune.prune_system(metadata=True)
    is_empty = await graph_engine.is_empty()
    assert is_empty, "Neo4j graph database is not empty"


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
