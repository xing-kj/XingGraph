import pytest
from unittest.mock import AsyncMock, patch

from xinggraph.modules.retrieval.wiki_completion_retriever import (
    DisambiguationCheck,
    WikiCompletionRetriever,
)


def make_entry(name, score, role, term=None):
    entry = {"id": f"id_{name}", "name": name, "score": score, "role": role}
    if role == "subject":
        entry["anchor_term"] = term or name
    elif role == "attribute":
        entry["source_term"] = term or name
    return entry


def test_extraction_clarification_skipped_when_subjects_present():
    retriever = WikiCompletionRetriever()
    qe = {
        "subjects": ["双循环制冷系统"],
        "attributes": [{"term": "工作原理", "subject": "双循环制冷系统"}],
        "clarification_request": "请问您指的是哪款设备或产品上的双循环制冷系统？",
    }
    assert retriever._extraction_clarification_response(qe) is None


def test_extraction_clarification_honored_when_nothing_to_anchor():
    retriever = WikiCompletionRetriever()
    qe = {
        "subjects": [],
        "attributes": [],
        "clarification_request": "你想了解哪款冰箱？",
    }
    response = retriever._extraction_clarification_response(qe)
    assert response is not None
    assert response["clarification_request"] == "你想了解哪款冰箱？"
    assert response["entities"] == []


@pytest.fixture
def retriever():
    return WikiCompletionRetriever()


@patch("xinggraph.modules.retrieval.wiki_completion_retriever.LLMGateway")
@pytest.mark.asyncio
async def test_skips_llm_when_scores_above_threshold(mock_gateway, retriever):
    hits = [
        make_entry("生物安全柜", 0.90, "subject", "生物柜"),
        make_entry("生物柜", 0.87, "subject", "生物柜"),
    ]

    result = await retriever._disambiguate_entities("生物柜的安全联锁条件?", hits)

    mock_gateway.acreate_structured_output.assert_not_called()
    assert result == {}


@patch("xinggraph.modules.retrieval.wiki_completion_retriever.LLMGateway")
@pytest.mark.asyncio
async def test_skips_attribute_groups_even_when_low_score(mock_gateway, retriever):
    hits = [
        make_entry("家用电冰箱", 0.30, "attribute", "控温精度"),
        make_entry("植萃净味除菌装置", 0.26, "attribute", "作用"),
    ]

    result = await retriever._disambiguate_entities("双循环系统的控温精度怎么样?", hits)

    mock_gateway.acreate_structured_output.assert_not_called()
    assert result == {}


@patch("xinggraph.modules.retrieval.wiki_completion_retriever.LLMGateway")
@pytest.mark.asyncio
async def test_returns_clarification_when_low_score_not_found(mock_gateway, retriever):
    hits = [
        make_entry("HYR-111", 0.55, "subject", "HYR-999"),
        make_entry("HYR-110", 0.50, "subject", "HYR-999"),
    ]
    mock_gateway.acreate_structured_output = AsyncMock(
        return_value=type(
            "Result",
            (),
            {
                "checks": [
                    DisambiguationCheck(
                        source_term="HYR-999",
                        role="subject",
                        status="not_found",
                        selected_node=None,
                        disambiguation_question="图谱中没有找到 HYR-999，最接近的是 HYR-111。",
                    )
                ]
            },
        )()
    )

    result = await retriever._disambiguate_entities("HYR-999 的启动条件?", hits)

    mock_gateway.acreate_structured_output.assert_awaited_once()
    assert result["clarification_request"].startswith("图谱中没有找到")


@patch("xinggraph.modules.retrieval.wiki_completion_retriever.LLMGateway")
@pytest.mark.asyncio
async def test_verified_selection_narrows_entity_hits(mock_gateway, retriever):
    hits = [
        make_entry("生物安全柜", 0.62, "subject", "生物柜"),
        make_entry("生物柜", 0.58, "subject", "生物柜"),
    ]
    mock_gateway.acreate_structured_output = AsyncMock(
        return_value=type(
            "Result",
            (),
            {
                "checks": [
                    DisambiguationCheck(
                        source_term="生物柜",
                        role="subject",
                        status="verified",
                        selected_node="生物安全柜",
                        disambiguation_question=None,
                    )
                ]
            },
        )()
    )

    result = await retriever._disambiguate_entities("生物柜的启动条件?", hits)
    narrowed = retriever._apply_verified_selection("生物柜的启动条件?", hits, result)

    assert result.get("clarification_request") is None
    names = {entry["name"] for entry in narrowed}
    assert names == {"生物安全柜"}


@patch("xinggraph.modules.retrieval.wiki_completion_retriever.LLMGateway")
@pytest.mark.asyncio
async def test_fail_open_on_llm_error(mock_gateway, retriever):
    hits = [make_entry("生物安全柜", 0.55, "subject", "生物柜")]
    mock_gateway.acreate_structured_output = AsyncMock(side_effect=RuntimeError("boom"))

    result = await retriever._disambiguate_entities("生物柜的启动条件?", hits)

    assert result == {}


@patch("xinggraph.modules.retrieval.wiki_completion_retriever.LLMGateway")
@pytest.mark.asyncio
async def test_verified_keeps_unaffected_groups(mock_gateway, retriever):
    hits = [
        make_entry("生物安全柜", 0.62, "subject", "生物柜"),
        make_entry("生物柜", 0.58, "subject", "生物柜"),
        make_entry("CO2培养箱", 0.30, "attribute", "培养"),
    ]
    mock_gateway.acreate_structured_output = AsyncMock(
        return_value=type(
            "Result",
            (),
            {
                "checks": [
                    DisambiguationCheck(
                        source_term="生物柜",
                        role="subject",
                        status="verified",
                        selected_node="生物安全柜",
                        disambiguation_question=None,
                    )
                ]
            },
        )()
    )

    result = await retriever._disambiguate_entities("生物柜的启动条件?", hits)
    narrowed = retriever._apply_verified_selection("生物柜的启动条件?", hits, result)

    names = {entry["name"] for entry in narrowed}
    assert names == {"生物安全柜", "CO2培养箱"}