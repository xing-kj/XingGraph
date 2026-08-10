"""Propagate entity mentions across neighboring chunks within a document."""

from typing import List

from xinggraph.infrastructure.engine.models.Edge import Edge
from xinggraph.modules.chunking.models.DocumentChunk import DocumentChunk
from xinggraph.modules.engine.models.Entity import Entity


async def propagate_chunk_entities(
    data_chunks: List[DocumentChunk],
    entity_nodes: list = None,
    window_size: int = 2,
) -> List[DocumentChunk]:
    """Propagate entity mentions across neighboring chunks within a document.

    For each chunk, examines its neighboring chunks (within ``window_size``
    positions) and adds implicit ``contains`` edges for entities that appear
    in a majority of neighbors. This helps ensure that entities mentioned
    implicitly (via pronouns like "the company") are still linked to all
    relevant chunks.

    Args:
        data_chunks: List of document chunks with their ``contains`` edges
            already populated by LLM extraction.
        entity_nodes: Optional list of Entity objects (not required; entities
            are resolved from existing contains edges on the chunks).
        window_size: Number of positions to look left and right for neighbor
            chunks. Default is 2.

    Returns:
        The modified list of DocumentChunk objects with implicit contains
        edges added where appropriate.
    """
    if not data_chunks:
        return data_chunks

    doc_chunks = _group_chunks_by_document(data_chunks)

    for doc_id, chunks in doc_chunks.items():
        if len(chunks) <= 1:
            continue

        chunks.sort(key=lambda c: c.chunk_index)

        for i, chunk in enumerate(chunks):
            neighbor_counts = _count_neighbor_entities(chunks, i, window_size)

            if not neighbor_counts:
                continue

            num_neighbors = sum(1 for j in range(max(0, i - window_size), min(len(chunks), i + window_size + 1)) if j != i)
            if num_neighbors == 0:
                continue

            existing_entity_names = _get_existing_entity_names(chunk)

            for entity_name, count in neighbor_counts.items():
                if entity_name in existing_entity_names:
                    continue

                if count > num_neighbors / 2:
                    entity_node = _find_entity_by_name(entity_name, data_chunks)
                    if entity_node is None:
                        continue

                    if chunk.contains is None:
                        chunk.contains = []

                    chunk.contains.append(
                        (
                            Edge(
                                relationship_type="contains",
                                edge_text=f"[implicit] Document context suggests this chunk mentions {entity_name}",
                                implicit=True,
                                inference_layer="propagation",
                            ),
                            entity_node,
                        )
                    )

    return data_chunks


def _group_chunks_by_document(data_chunks: List[DocumentChunk]) -> dict:
    """Group chunks by their parent document ID."""
    doc_chunks = {}
    for chunk in data_chunks:
        doc_id = None
        if hasattr(chunk, "is_part_of") and chunk.is_part_of is not None:
            doc_id = getattr(chunk.is_part_of, "id", None)
        if doc_id is None:
            doc_id = getattr(chunk, "document_id", None)
        if doc_id is None:
            doc_id = "__no_document__"

        if doc_id not in doc_chunks:
            doc_chunks[doc_id] = []
        doc_chunks[doc_id].append(chunk)

    return doc_chunks


def _count_neighbor_entities(chunks: List[DocumentChunk], center_index: int, window_size: int) -> dict:
    """Count entity mentions in neighboring chunks within window_size."""
    counts = {}
    start = max(0, center_index - window_size)
    end = min(len(chunks), center_index + window_size + 1)

    for j in range(start, end):
        if j == center_index:
            continue

        neighbor = chunks[j]
        if neighbor.contains is None:
            continue

        for edge, entity in neighbor.contains:
            if getattr(edge, "implicit", False):
                continue

            entity_name = getattr(entity, "name", None)
            if entity_name:
                counts[entity_name] = counts.get(entity_name, 0) + 1

    return counts


def _get_existing_entity_names(chunk: DocumentChunk) -> set:
    """Get the set of entity names already linked to this chunk."""
    existing = set()
    if chunk.contains is None:
        return existing

    for edge, entity in chunk.contains:
        entity_name = getattr(entity, "name", None)
        if entity_name:
            existing.add(entity_name)

    return existing


def _find_entity_by_name(entity_name: str, data_chunks: List[DocumentChunk]) -> Entity | None:
    """Find an Entity object by name from any chunk's contains edges."""
    for chunk in data_chunks:
        if chunk.contains is None:
            continue
        for edge, entity in chunk.contains:
            if getattr(entity, "name", None) == entity_name:
                return entity
    return None
