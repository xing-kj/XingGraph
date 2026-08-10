"""Unit tests for StructuredDocChunker behavior."""

import pytest
from uuid import uuid4

from xinggraph.modules.chunking.StructuredDocChunker import StructuredDocChunker
from xinggraph.modules.data.processing.document_types import Document

SAMPLE = """=== 解析结果 ===
源文件: D:\\盈康知识库\\dw-86唯一.pdf
Documents: 90

Doc 1/90: len=402, titles=['dw-86唯一']
--- 内容开始 ---
医用低温保存箱
型号：DW-86L100STL
--- 内容结束 ---

Doc 2/90: len=166, titles=['dw-86唯一', '目录']
--- 内容开始 ---
注意事项....1
使用注意事项....4
--- 内容结束 ---
"""


def _make_text_generator(*texts):
    async def gen():
        for text in texts:
            yield text

    return gen


async def _collect(chunker):
    chunks = []
    async for chunk in chunker.read():
        chunks.append(chunk)
    return chunks


def _make_document():
    return Document(
        id=uuid4(),
        name="dw-86唯一.txt",
        raw_data_location="/p/dw-86唯一.txt",
        external_metadata=None,
        mime_type="text/plain",
    )


@pytest.mark.asyncio
async def test_one_chunk_per_doc_block():
    chunker = StructuredDocChunker(
        _make_document(), _make_text_generator(SAMPLE), max_chunk_size=512
    )
    chunks = await _collect(chunker)

    assert len(chunks) == 2, "Each Doc block should become exactly one chunk"


@pytest.mark.asyncio
async def test_text_is_verbatim_and_titles_in_metadata():
    chunker = StructuredDocChunker(
        _make_document(), _make_text_generator(SAMPLE), max_chunk_size=512
    )
    chunks = await _collect(chunker)

    assert chunks[0].text.startswith("Doc 1/90: len=402, titles=['dw-86唯一']")
    assert "--- 内容开始 ---" in chunks[0].text
    assert "型号：DW-86L100STL" in chunks[0].text
    assert chunks[0].text.rstrip().endswith("--- 内容结束 ---")
    assert chunks[0].cut_type == "doc_structure"
    assert chunks[0].metadata["titles"] == ["dw-86唯一"]
    assert chunks[0].metadata["doc_index"] == 1
    assert chunks[0].metadata["total_docs"] == 90


@pytest.mark.asyncio
async def test_chunk_indices_increment_across_blocks():
    chunker = StructuredDocChunker(
        _make_document(), _make_text_generator(SAMPLE), max_chunk_size=512
    )
    chunks = await _collect(chunker)

    assert [c.chunk_index for c in chunks] == [0, 1]


@pytest.mark.asyncio
async def test_text_streamed_across_get_text_slices():
    # A Doc block may span multiple get_text slices; the chunker must accumulate.
    slice1 = SAMPLE[: len(SAMPLE) // 2]
    slice2 = SAMPLE[len(SAMPLE) // 2 :]
    chunker = StructuredDocChunker(
        _make_document(), _make_text_generator(slice1, slice2), max_chunk_size=512
    )
    chunks = await _collect(chunker)

    assert len(chunks) == 2
    assert chunks[1].text.startswith("Doc 2/90:")


@pytest.mark.asyncio
async def test_oversized_block_raises_value_error():
    chunker = StructuredDocChunker(
        _make_document(), _make_text_generator(SAMPLE), max_chunk_size=1
    )

    with pytest.raises(ValueError, match="larger than the maximum chunk size"):
        await _collect(chunker)


@pytest.mark.asyncio
async def test_empty_input_produces_no_chunks():
    chunker = StructuredDocChunker(
        _make_document(), _make_text_generator(""), max_chunk_size=512
    )
    chunks = await _collect(chunker)

    assert len(chunks) == 0
