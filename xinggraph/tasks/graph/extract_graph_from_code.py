import asyncio
from typing import TYPE_CHECKING, Type, List

from pydantic import BaseModel

from xinggraph.infrastructure.llm.extraction import extract_content_graph
from xinggraph.modules.chunking.models.DocumentChunk import DocumentChunk
from xinggraph.tasks.storage import add_data_points

if TYPE_CHECKING:
    from xinggraph.modules.pipelines.models import PipelineContext


async def extract_graph_from_code(
    data_chunks: list[DocumentChunk],
    graph_model: Type[BaseModel],
    ctx: "PipelineContext" = None,
) -> List[DocumentChunk]:
    """
    Extracts a knowledge graph from code document chunks.

    Args:
        data_chunks: Document chunks containing code text.
        graph_model: Pydantic model defining the graph schema.
        ctx: Pipeline runtime context for provenance tracking.
    """
    chunk_graphs = await asyncio.gather(
        *[extract_content_graph(chunk.text, graph_model) for chunk in data_chunks]
    )

    for chunk_index, _ in enumerate(data_chunks):
        chunk_graph = chunk_graphs[chunk_index]
        await add_data_points(chunk_graph.nodes, ctx=ctx)

    return data_chunks
