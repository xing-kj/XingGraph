"""Tests for the CQL literal keyword layer in WikiCompletionRetriever."""

import pytest
from unittest.mock import AsyncMock, patch

from xinggraph.modules.retrieval.wiki_completion_retriever import WikiCompletionRetriever


class _GraphConn:
    def __init__(self, rows):
        self.query = AsyncMock(return_value=rows)


class _Engine:
    def __init__(self, conn):
        self.graph = conn


def _retriever_with(conn):
    retriever = WikiCompletionRetriever()
    retriever._unified_engine = _Engine(conn)
    return retriever


@pytest.mark.asyncio
async def test_keyword_layer_returns_exact_and_substring_hits():
    conn = _GraphConn(
        [
            {"id": "2509e38d-ef45-5980-a13a-72318d6da22f", "name": "双循环制冷系统", "description": "desc"},
            {"id": "8d2702e0", "name": "海尔", "description": "中国品牌"},
        ]
    )
    retriever = _retriever_with(conn)
    with patch("xinggraph.modules.retrieval.wiki_completion_retriever.current_dataset_id") as ds:
        ds.get.return_value = None
        rows = await retriever._collect_entities_by_keyword("双循环制冷系统")

    assert len(rows) == 2
    assert rows[0]["name"] == "双循环制冷系统"
    assert rows[0]["id"] == "2509e38d-ef45-5980-a13a-72318d6da22f"
    assert rows[1]["name"] == "海尔"


@pytest.mark.asyncio
async def test_keyword_layer_forwards_dataset_id_and_builds_clause():
    conn = _GraphConn([])
    retriever = _retriever_with(conn)
    with patch("xinggraph.modules.retrieval.wiki_completion_retriever.current_dataset_id") as ds:
        ds.get.return_value = "ds-1"
        await retriever._collect_entities_by_keyword("海尔")

    cql, params = conn.query.await_args.args
    assert "toLower(e.name) = toLower($term)" in cql
    assert "$dataset_id IN coalesce(e.source_dataset_ids, [])" in cql
    assert params == {"term": "海尔", "dataset_id": "ds-1"}


@pytest.mark.asyncio
async def test_keyword_layer_fails_open_on_query_error():
    conn = _GraphConn([])
    conn.query = AsyncMock(side_effect=RuntimeError("boom"))
    retriever = _retriever_with(conn)
    with patch("xinggraph.modules.retrieval.wiki_completion_retriever.current_dataset_id") as ds:
        ds.get.return_value = None
        rows = await retriever._collect_entities_by_keyword("海尔")

    assert rows == []


def test_keyword_anchor_outranks_same_name_candidate_in_dedup():
    retriever = WikiCompletionRetriever()
    keyword = {
        "id": "k1",
        "name": "海尔",
        "role": "subject",
        "anchor_term": "海尔双循环系统",
        "score": 1.0,
        "match_mode": "keyword",
    }
    candidate = {
        "id": "c1",
        "name": "海尔",
        "role": "sentence",
        "coherence": 1,
        "score": 0.42,
    }
    merged = retriever._dedupe_rank_entities([candidate, keyword], limit=1)

    assert len(merged) == 1
    assert merged[0]["name"] == "海尔"
    assert merged[0]["match_mode"] == "keyword"
    assert merged[0]["score"] == 1.0