from unittest.mock import patch
import sys

from xinggraph.tasks.chunks import chunk_by_doc_structure

chunk_by_sentence_module = sys.modules.get("xinggraph.tasks.chunks.chunk_by_sentence")


def mock_get_embedding_engine():
    class MockTokenizer:
        def count_tokens(self, text):
            # deterministic proxy: count of whitespace-separated tokens
            return len(text.split())

    class MockEngine:
        tokenizer = MockTokenizer()

    return MockEngine()


SAMPLE = """=== 解析结果 ===
源文件: D:\\盈康知识库\\dw-86唯一.pdf
Documents: 90
Chunks: 93

Doc 1/90: len=402, titles=['dw-86唯一']
--- 内容开始 ---
医用低温保存箱
使用说明书
型号：DW-86L100STL
--- 内容结束 ---

Doc 2/90: len=166, titles=['dw-86唯一', '目录']
--- 内容开始 ---
注意事项....1
使用注意事项....4
--- 内容结束 ---

Doc 3/90: len=581, titles=['dw-86唯一', '技术数据']
--- 内容开始 ---
<table><tr><td>型号</td><td>温度范围(°C)</td></tr><tr><td>DW-86L100STL</td><td>-20~-86</td></tr></table>
--- 内容结束 ---
"""


@patch.object(
    chunk_by_sentence_module, "get_embedding_engine", side_effect=mock_get_embedding_engine
)
def test_chunks_are_split_by_doc_blocks(_):
    chunks = list(chunk_by_doc_structure(SAMPLE, max_chunk_size=1024))

    assert len(chunks) == 3, "Each Doc block should become exactly one chunk"


@patch.object(
    chunk_by_sentence_module, "get_embedding_engine", side_effect=mock_get_embedding_engine
)
def test_chunk_text_is_verbatim_block(_):
    chunks = list(chunk_by_doc_structure(SAMPLE, max_chunk_size=1024))

    # Doc 1 text must reproduce the whole block including header and markers
    assert chunks[0]["text"].startswith("Doc 1/90: len=402, titles=['dw-86唯一']")
    assert "--- 内容开始 ---" in chunks[0]["text"]
    assert "型号：DW-86L100STL" in chunks[0]["text"]
    assert "--- 内容结束 ---" in chunks[0]["text"]


@patch.object(
    chunk_by_sentence_module, "get_embedding_engine", side_effect=mock_get_embedding_engine
)
def test_titles_and_doc_index_metadata(_):
    chunks = list(chunk_by_doc_structure(SAMPLE, max_chunk_size=1024))

    assert chunks[0]["titles"] == ["dw-86唯一"]
    assert chunks[1]["titles"] == ["dw-86唯一", "目录"]
    assert chunks[2]["titles"] == ["dw-86唯一", "技术数据"]
    assert chunks[0]["doc_index"] == 1
    assert chunks[2]["total_docs"] == 90
    assert chunks[0]["cut_type"] == "doc_structure"


@patch.object(
    chunk_by_sentence_module, "get_embedding_engine", side_effect=mock_get_embedding_engine
)
def test_table_content_preserved_in_chunk(_):
    chunks = list(chunk_by_doc_structure(SAMPLE, max_chunk_size=1024))

    assert "<table>" in chunks[2]["text"]
    assert "</table>" in chunks[2]["text"]


@patch.object(
    chunk_by_sentence_module, "get_embedding_engine", side_effect=mock_get_embedding_engine
)
def test_unstructured_text_becomes_single_chunk(_):
    text = "no wrapper markers at all, just a normal paragraph."
    chunks = list(chunk_by_doc_structure(text, max_chunk_size=1024))

    assert len(chunks) == 1
    assert chunks[0]["text"] == text
    assert chunks[0]["titles"] == []
    assert chunks[0]["cut_type"] == "doc_structure"
