"""Unit tests for the structured-doc extraction prompt."""

from xinggraph.infrastructure.llm.prompts import render_prompt


def test_structured_doc_prompt_renders():
    prompt = render_prompt("generate_graph_prompt_structured_doc.txt", {})

    assert prompt is not None
    assert len(prompt.strip()) > 0


def test_structured_doc_prompt_contains_structure_rules():
    prompt = render_prompt("generate_graph_prompt_structured_doc.txt", {})

    # #0 block-structure section must be present (titles + content boundaries)
    assert "Input Chunk Structure" in prompt
    assert "titles" in prompt
    assert "内容开始" in prompt
    assert "内容结束" in prompt

    # wrapper-only text must not be extracted as entities
    assert "wrapper" in prompt


def test_structured_doc_prompt_keeps_general_graph_rules():
    prompt = render_prompt("generate_graph_prompt_structured_doc.txt", {})

    # Original general extraction rules must be preserved
    assert "Labeling Nodes" in prompt
    assert "PRODUCT_MODEL" in prompt
    assert "is_product" in prompt
    assert "Coreference" in prompt
