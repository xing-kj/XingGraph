import asyncio
import inspect
from typing import Type, List, Optional
from uuid import uuid4

from pydantic import BaseModel

from xinggraph.modules.pipelines.tasks.task import task_summary
from xinggraph.modules.ontology.ontology_env_config import get_ontology_env_config
from xinggraph.modules.ontology.ontology_config import Config
from xinggraph.modules.ontology.get_default_ontology_resolver import (
    get_default_ontology_resolver,
    get_ontology_resolver_from_env,
)
from xinggraph.modules.ontology.base_ontology_resolver import BaseOntologyResolver
from xinggraph.modules.chunking.models.DocumentChunk import DocumentChunk
from xinggraph.modules.graph.utils import (
    expand_with_nodes_and_edges,
    retrieve_existing_edges,
    generate_chunk_wiki,
    propagate_chunk_entities,
)
from xinggraph.shared.data_models import KnowledgeGraph, ChunkWiki
from xinggraph.infrastructure.llm.extraction import extract_content_graph
from xinggraph.infrastructure.databases.graph import get_graph_engine
from xinggraph.infrastructure.databases.provenance import make_source_ref_key
from xinggraph.shared.logging_utils import get_logger

logger = get_logger("extract_graph_from_data")
from xinggraph.infrastructure.llm.pipeline_stage import pipeline_stage
from xinggraph.infrastructure.engine import DataPoint
from xinggraph.tasks.graph.exceptions import (
    InvalidGraphModelError,
    InvalidDataChunksError,
    InvalidChunkGraphInputError,
    InvalidOntologyAdapterError,
)


def _stamp_provenance_deep(data, pipeline_name, task_name, visited=None):
    """Recursively stamp all reachable DataPoints with provenance info."""
    if visited is None:
        visited = set()

    if isinstance(data, DataPoint):
        obj_id = id(data)
        if obj_id in visited:
            return
        visited.add(obj_id)

        if data.source_pipeline is None:
            data.source_pipeline = pipeline_name
        if data.source_task is None:
            data.source_task = task_name

        for field_name in data.model_fields:
            field_value = getattr(data, field_name, None)
            if field_value is not None:
                _stamp_provenance_deep(field_value, pipeline_name, task_name, visited)

    elif isinstance(data, (list, tuple)):
        for item in data:
            _stamp_provenance_deep(item, pipeline_name, task_name, visited)


async def integrate_chunk_graphs(
    data_chunks: list[DocumentChunk],
    chunk_graphs: list,
    graph_model: Type[BaseModel],
    ontology_resolver: BaseOntologyResolver,
    pipeline_name: str = None,
    task_name: str = None,
    reject_unknown_entities: bool = False,
    chunk_wikis: Optional[list] = None,
    **kwargs,
) -> List[DocumentChunk]:
    """Integrate chunk graphs with ontology validation and store in databases.

    This function processes document chunks and their associated knowledge graphs,
    validates entities against an ontology resolver, and stores the integrated
    data points and edges in the configured databases.

    Args:
        data_chunks: List of document chunks containing source data
        chunk_graphs: List of knowledge graphs corresponding to each chunk
        graph_model: Pydantic model class for graph data validation
        ontology_resolver: Resolver for validating entities against ontology
        reject_unknown_entities: If True, entities without ontology matches are dropped
        chunk_wikis: Optional list of ChunkWiki objects for wiki-based entity enrichment

    Returns:
        List of updated DocumentChunk objects with integrated data

    Raises:
        InvalidChunkGraphInputError: If input validation fails
        InvalidGraphModelError: If graph model validation fails
        InvalidOntologyAdapterError: If ontology resolver validation fails
    """

    if not isinstance(data_chunks, list) or not isinstance(chunk_graphs, list):
        raise InvalidChunkGraphInputError("data_chunks and chunk_graphs must be lists.")
    if len(data_chunks) != len(chunk_graphs):
        raise InvalidChunkGraphInputError(
            f"length mismatch: {len(data_chunks)} chunks vs {len(chunk_graphs)} graphs."
        )
    if not isinstance(graph_model, type) or not issubclass(graph_model, BaseModel):
        raise InvalidGraphModelError(graph_model)
    if ontology_resolver is None or not hasattr(ontology_resolver, "get_subgraph"):
        raise InvalidOntologyAdapterError(
            type(ontology_resolver).__name__ if ontology_resolver else "None"
        )

    if not issubclass(graph_model, KnowledgeGraph):
        for chunk_index, chunk_graph in enumerate(chunk_graphs):
            data_chunks[chunk_index].contains = chunk_graph

        return data_chunks

    existing_edges_map = await retrieve_existing_edges(
        data_chunks,
        chunk_graphs,
    )

    data_chunks, entity_nodes = expand_with_nodes_and_edges(
        data_chunks, chunk_graphs, ontology_resolver, existing_edges_map,
        reject_unknown_entities=kwargs.get("reject_unknown_entities", False),
        chunk_wikis=chunk_wikis,
    )

    if entity_nodes:
        if pipeline_name or task_name:
            for node in entity_nodes:
                _stamp_provenance_deep(node, pipeline_name, task_name)

        cache_entity_embeddings = kwargs.get("cache_entity_embeddings")
        if callable(cache_entity_embeddings):
            callback_result = cache_entity_embeddings(entity_nodes, **kwargs)
            if inspect.isawaitable(callback_result):
                await callback_result

    return data_chunks


@task_summary("Extracted graph from {n} chunk(s)")
async def extract_graph_from_data(
    data_chunks: List[DocumentChunk],
    graph_model: Type[BaseModel],
    config: Optional[Config] = None,
    custom_prompt: Optional[str] = None,
    ctx=None,
    **kwargs,
) -> List[DocumentChunk]:
    """
    Extracts and integrates a knowledge graph from the text content of document chunks using a specified graph model.
    """
    pipeline_name = ctx.pipeline_name if ctx else None

    if not isinstance(data_chunks, list) or not data_chunks:
        raise InvalidDataChunksError("must be a non-empty list of DocumentChunk.")
    if not all(hasattr(c, "text") for c in data_chunks):
        raise InvalidDataChunksError("each chunk must have a 'text' attribute")
    if not isinstance(graph_model, type) or not issubclass(graph_model, BaseModel):
        raise InvalidGraphModelError(graph_model)

    # Skip LLM extraction for DLT row chunks — their graph is built
    # deterministically by extract_dlt_fk_edges from schema metadata.
    from xinggraph.modules.data.processing.document_types import DltRowDocument

    # Partition in a single pass: a list-membership check against dlt_chunks
    # rescans the list for every chunk (O(n^2) with Pydantic __eq__ comparisons),
    # which becomes a bottleneck on the extraction hot path for large DLT sources.
    dlt_chunks = []
    non_dlt_chunks = []
    for c in data_chunks:
        if isinstance(getattr(c, "is_part_of", None), DltRowDocument):
            dlt_chunks.append(c)
        else:
            non_dlt_chunks.append(c)

    if not non_dlt_chunks:
        return data_chunks

    calculate_chunk_graphs = kwargs.get("calculate_chunk_graphs")
    if callable(calculate_chunk_graphs):
        extracted = calculate_chunk_graphs(non_dlt_chunks, graph_model, custom_prompt, **kwargs)
        chunk_graphs = await extracted if inspect.isawaitable(extracted) else extracted
    else:
        with pipeline_stage("extraction"):
            chunk_graphs = await asyncio.gather(
                *[
                    extract_content_graph(
                        chunk.text, graph_model, custom_prompt=custom_prompt, **kwargs
                    )
                    for chunk in non_dlt_chunks
                ]
            )
    cache_entity_embeddings = kwargs.get("cache_entity_embeddings")
    if callable(cache_entity_embeddings):
        callback_result = cache_entity_embeddings(chunk_graphs, **kwargs)
        if inspect.isawaitable(callback_result):
            await callback_result

    # Note: Filter edges with missing source or target nodes
    if issubclass(graph_model, KnowledgeGraph):
        for graph in chunk_graphs:
            valid_node_ids = {node.id for node in graph.nodes}
            graph.edges = [
                edge
                for edge in graph.edges
                if edge.source_node_id in valid_node_ids and edge.target_node_id in valid_node_ids
            ]

    # Extract resolver from config if provided, otherwise get default
    if config is None:
        ontology_config = get_ontology_env_config()
        if (
            ontology_config.ontology_file_path
            and ontology_config.ontology_resolver
            and ontology_config.matching_strategy
        ):
            config: Config = {
                "ontology_config": {
                    "ontology_resolver": get_ontology_resolver_from_env(**ontology_config.to_dict())
                }
            }
        else:
            config: Config = {
                "ontology_config": {"ontology_resolver": get_default_ontology_resolver()}
            }

    ontology_resolver = config["ontology_config"]["ontology_resolver"]

    # Read reject_unknown_entities from ontology config
    ontology_env = get_ontology_env_config()
    reject_unknown = kwargs.pop("reject_unknown_entities", ontology_env.reject_unknown_entities)

    task_name = "extract_graph_from_data"

    # --- Phase 0/1: ChunkWiki generation (before graph integration) ---
    chunk_wikis = []
    try:
        chunk_wikis = await asyncio.gather(
            *[
                generate_chunk_wiki(
                    chunk_text=chunk.text,
                    chunk_id=str(chunk.id),
                    neighbor_entities=_collect_neighbor_entity_names(non_dlt_chunks, i),
                )
                for i, chunk in enumerate(non_dlt_chunks)
            ]
        )
    except Exception as wiki_error:
        logger.warning(f"ChunkWiki generation failed (non-fatal): {wiki_error}")

    integrated = await integrate_chunk_graphs(
        non_dlt_chunks,
        chunk_graphs,
        graph_model,
        ontology_resolver,
        pipeline_name=pipeline_name,
        task_name=task_name,
        reject_unknown_entities=reject_unknown,
        chunk_wikis=chunk_wikis,
        **kwargs,
    )

    # --- Phase 0/1: Entity propagation (after graph integration) ---
    try:
        integrated = await propagate_chunk_entities(integrated)
    except Exception as prop_error:
        logger.warning(f"Entity propagation failed (non-fatal): {prop_error}")

    # --- Phase 0/1: Store ChunkWiki nodes + has_wiki edges ---
    if chunk_wikis:
        try:
            dataset = ctx.dataset if ctx else None
            pipeline_run_id = ctx.pipeline_run_id if ctx else None
            fold_run_arg = str(pipeline_run_id) if pipeline_run_id else None

            chunk_wiki_nodes = []
            has_wiki_edges = []
            for chunk, wiki in zip(non_dlt_chunks, chunk_wikis):
                if wiki is None:
                    continue
                wiki_id = str(uuid4())
                source_ref_key = (
                    make_source_ref_key(dataset.id, chunk.id)
                    if dataset is not None
                    else None
                )

                chunk_wiki_nodes.append(
                    {
                        "id": wiki_id,
                        "type": "ChunkWiki",
                        "name": wiki.summary[:50],
                        "chunk_id": wiki.chunk_id,
                        "wiki_id": wiki_id,
                        "summary": wiki.summary,
                        "key_topics": wiki.key_topics,
                        "key_entities": wiki.key_entities,
                        "content_type": wiki.content_type,
                    }
                )
                has_wiki_edges.append(
                    (
                        wiki.chunk_id,
                        wiki_id,
                        "has_wiki",
                        {
                            "source_node_id": wiki.chunk_id,
                            "target_node_id": wiki_id,
                            "relationship_name": "has_wiki",
                            "inference_layer": "chunk",
                            "implicit": False,
                        },
                    )
                )

            if chunk_wiki_nodes:
                graph_engine = await get_graph_engine()
                await graph_engine.add_nodes(
                    chunk_wiki_nodes,
                    source_ref_key=source_ref_key,
                    pipeline_run_id=fold_run_arg,
                )
                await graph_engine.add_edges(
                    has_wiki_edges,
                    source_ref_key=source_ref_key,
                    pipeline_run_id=fold_run_arg,
                )
        except Exception as storage_error:
            logger.warning(f"ChunkWiki storage failed (non-fatal): {storage_error}")

    return integrated + dlt_chunks


def _collect_neighbor_entity_names(chunks: List[DocumentChunk], center_index: int, window_size: int = 2) -> List[str]:
    """Collect unique entity names from neighboring chunks within window_size."""
    names = set()
    start = max(0, center_index - window_size)
    end = min(len(chunks), center_index + window_size + 1)
    for j in range(start, end):
        if j == center_index:
            continue
        neighbor = chunks[j]
        if neighbor.contains is None:
            continue
        for _, entity in neighbor.contains:
            name = getattr(entity, "name", None)
            if name:
                names.add(name)
    return list(names)

