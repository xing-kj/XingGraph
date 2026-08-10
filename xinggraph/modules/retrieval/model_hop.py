"""Model-directed hop: travel ONLY along the product-model path.

This is a self-contained, single-purpose retrieval helper. It deliberately
walks the product-model edges of the graph:

    (cat:Entity)-[:is_product]->(m:Entity)-[:is_a]->(EntityType:PRODUCT_MODEL)

so that, once category entities are wired to their model variants with
``is_product`` edges, a retriever anchored on a category can pull back exactly
those models and their subject-document chunks without spreading into generic
edges (``Rel``, ``develops``, ``produces``, ...) that the full
``get_neighborhood`` traversal walks.

Priority order when ``seed_entity_ids`` are provided:

1. ``is_product`` — any seed carrying outgoing ``is_product`` edges (a
   category, e.g. the medical low-temperature preservation box) returns all of
   its linked model entities.
2. Self-model — a seed that is itself tagged ``is_a -> PRODUCT_MODEL`` (an
   anchored concrete model) returns only itself, so a query for one model never
   expands to sibling models.
3. Fallback — only when neither applies (seeds that are neither a category nor
   a model) does the hop walk the original ``contains`` path over the subject
   documents.

This module is intentionally independent from ``WikiCompletionRetriever``'s main
step-2 traversal: it is mounted as an additional branch and its chunk ids are
merged (deduped) into the pipeline's chunk pool. It never opens a write
transaction; all queries are read-only.
"""

from typing import Any, Dict, List, Optional

import logging

logger = logging.getLogger("model_hop")


async def _model_chunks(
    graph,
    model_ids: List[str],
    doc_ids: Optional[List[str]] = None,
    dataset_id: Optional[str] = None,
) -> List[str]:
    """Return the ``DocumentChunk`` ids that contain any of ``model_ids``.

    Optional ``doc_ids`` / ``dataset_id`` restrict the chunks to the subject
    documents / dataset. Fail-open: on error returns an empty list.
    """
    params: Dict[str, Any] = {"mids": list(model_ids)}
    where = []
    if doc_ids:
        params["docs"] = list(doc_ids)
        where.append("c.document_id IN $docs")
    if dataset_id:
        params["dataset_id"] = str(dataset_id)
        where.append("$dataset_id IN coalesce(c.source_dataset_ids, [])")
    where_clause = (" AND " + " AND ".join(where)) if where else ""
    cql = f"""
    MATCH (m:Entity)-[r:contains]-(c:DocumentChunk)
    WHERE m.id IN $mids {where_clause}
    RETURN collect(DISTINCT c.id) AS chunk_ids
    """
    try:
        rows = await graph.query(cql, params)
    except Exception as error:  # noqa: BLE001
        logger.warning("model_directed_hop chunk query failed: %s", error, exc_info=True)
        return []
    if not rows:
        return []
    return list(dict.fromkeys(x for x in (rows[0].get("chunk_ids") or []) if x))


async def _fallback_contains(
    graph,
    doc_ids: Optional[List[str]] = None,
    dataset_id: Optional[str] = None,
    max_hops: int = 5,
) -> Dict[str, Any]:
    """Original behavior: walk ``contains`` over the subject-document chunks.

    Used only when the seed anchors are neither a category (no ``is_product``
    out-edge) nor a model themselves, keeping backward compatibility.
    """
    params: Dict[str, Any] = {}
    doc_clause = ""
    if doc_ids:
        params["docs"] = list(doc_ids)
        doc_clause = "AND c.document_id IN $docs"
    dataset_clause = ""
    if dataset_id:
        params["dataset_id"] = str(dataset_id)
        dataset_clause = "AND $dataset_id IN coalesce(c.source_dataset_ids, [])"

    cql = f"""
    MATCH (c:DocumentChunk)-[r:contains*1..{max_hops}]->(m:Entity)
          -[:is_a]->(t:EntityType {{name: 'PRODUCT_MODEL'}})
    WHERE TRUE {doc_clause} {dataset_clause}
    RETURN collect(DISTINCT m.id) AS model_ids, collect(DISTINCT c.id) AS chunk_ids
    """
    try:
        rows = await graph.query(cql, params)
    except Exception as error:  # noqa: BLE001
        logger.warning("model_directed_hop fallback query failed: %s", error, exc_info=True)
        return {"model_entity_ids": [], "model_chunk_ids": [], "entity_type": "PRODUCT_MODEL"}

    if not rows:
        return {"model_entity_ids": [], "model_chunk_ids": [], "entity_type": "PRODUCT_MODEL"}

    row = rows[0]
    model_ids = list(dict.fromkeys(x for x in (row.get("model_ids") or []) if x))
    chunk_ids = list(dict.fromkeys(x for x in (row.get("chunk_ids") or []) if x))
    return {
        "model_entity_ids": model_ids,
        "model_chunk_ids": chunk_ids,
        "entity_type": "PRODUCT_MODEL",
        "mode": "fallback",
    }


async def model_directed_hop(
    graph,
    doc_ids: Optional[List[str]] = None,
    dataset_id: Optional[str] = None,
    max_hops: int = 5,
    seed_entity_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Return the model-bearing chunks reachable from the given documents.

    Parameters
    ----------
    graph:
        The unified graph adapter exposing an async ``query(cql, params)``.
    doc_ids:
        Subject-document ids to restrict the hop to. ``None`` = no doc filter.
    dataset_id:
        Optional dataset id to scope entities/chunks to (source_dataset_ids).
    max_hops:
        Upper bound for the variable-length ``contains`` walk along the model
        path (fallback branch only). Because a model entity is directly
        ``contains``-linked to its spec/table chunks, the default is 1 hop; the
        parameter only guards against future nested layouts.
    seed_entity_ids:
        Entity ids the retriever anchored on (Step 0/1 subjects). When present,
        the hop prefers ``is_product`` out-edges; a seed with no such out-edge
        that is itself a model returns only itself.

    Returns a dict with ``model_entity_ids``, ``model_chunk_ids`` (both lists,
    deduped) and ``entity_type`` name. Fails open: any error yields empty lists
    and never raises.
    """
    empty = {"model_entity_ids": [], "model_chunk_ids": [], "entity_type": "PRODUCT_MODEL"}

    if graph is None or not hasattr(graph, "query"):
        return empty

    if seed_entity_ids:
        model_ids: List[str] = []
        # 1. Preferred: seeds with is_product out-edges (categories) -> their models.
        try:
            rows = await graph.query(
                """
                MATCH (seed:Entity)-[:is_product]->(m:Entity)
                WHERE seed.id IN $seeds
                RETURN collect(DISTINCT m.id) AS model_ids
                """,
                {"seeds": list(seed_entity_ids)},
            )
            if rows and rows[0].get("model_ids"):
                model_ids.extend(x for x in rows[0]["model_ids"] if x)
        except Exception as error:  # noqa: BLE001
            logger.warning("model_directed_hop is_product query failed: %s", error, exc_info=True)
            return empty

        # 2. Seeds that are models themselves (no is_product out-edge) -> only themselves.
        try:
            rows = await graph.query(
                """
                MATCH (seed:Entity)
                WHERE seed.id IN $seeds
                  AND NOT EXISTS((seed)-[:is_product]->(:Entity))
                MATCH (seed)-[:is_a]->(t:EntityType {name: 'PRODUCT_MODEL'})
                RETURN collect(DISTINCT seed.id) AS model_ids
                """,
                {"seeds": list(seed_entity_ids)},
            )
            if rows and rows[0].get("model_ids"):
                model_ids.extend(x for x in rows[0]["model_ids"] if x)
        except Exception as error:  # noqa: BLE001
            logger.warning("model_directed_hop self-model query failed: %s", error, exc_info=True)
            return empty

        model_ids = list(dict.fromkeys(x for x in model_ids if x))
        if model_ids:
            chunk_ids = await _model_chunks(graph, model_ids, doc_ids, dataset_id)
            return {
                "model_entity_ids": model_ids,
                "model_chunk_ids": chunk_ids,
                "entity_type": "PRODUCT_MODEL",
                "mode": "is_product",
            }

    # 3. Fallback: seeds are neither category nor model (or none provided).
    return await _fallback_contains(graph, doc_ids, dataset_id, max_hops)
