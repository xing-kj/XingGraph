from xinggraph.shared.logging_utils import get_logger
from os.path import basename

from xinggraph.tasks.chunks import chunk_by_doc_structure
from xinggraph.modules.chunking.Chunker import Chunker
from .models.DocumentChunk import DocumentChunk

logger = get_logger()


class StructuredDocChunker(Chunker):
    """
    A Chunker for text in the "parsed PDF" wrapper format.

    The source text is expected to follow:

        Doc <N>/<total>: len=<len>, titles=[<title_1>, <title_2>, ...]
        --- 内容开始 ---
        <content>
        --- 内容结束 ---

    Each Doc block becomes exactly one chunk with its text kept verbatim (header
    line + begin/end markers + content), so chunks reproduce the original
    structure and can be traced back. The titles hierarchy is carried in
    metadata. Text that does not contain the wrapper markers is emitted as a
    single whole-text chunk.
    """

    async def read(self):
        document_id = str(self.document.id)
        document_name = self.document.name or basename(self.document.raw_data_location)

        # get_text is streamed (e.g. 1MB slices), but a single Doc block may
        # span multiple slices, so accumulate the full text before parsing.
        full_text = ""
        async for content_text in self.get_text():
            if content_text is None:
                continue
            full_text += content_text

        if not full_text.strip():
            return

        for chunk_data in chunk_by_doc_structure(full_text, self.max_chunk_size):
            chunk_size = chunk_data["chunk_size"]
            if chunk_size > self.max_chunk_size:
                logger.warning(
                    "StructuredDocChunker: chunk of %d tokens exceeds max_chunk_size %d "
                    "for document %s — yielding oversized chunk instead of failing.",
                    chunk_size, self.max_chunk_size, document_id,
                )

            metadata = {"index_fields": ["text"]}
            if chunk_data.get("titles"):
                metadata["titles"] = chunk_data["titles"]
            if chunk_data.get("doc_index") is not None:
                metadata["doc_index"] = chunk_data["doc_index"]
            if chunk_data.get("total_docs") is not None:
                metadata["total_docs"] = chunk_data["total_docs"]

            yield DocumentChunk(
                id=chunk_data["chunk_id"],
                text=chunk_data["text"],
                chunk_size=chunk_size,
                is_part_of=self.document,
                chunk_index=self.chunk_index,
                cut_type=chunk_data["cut_type"],
                contains=[],
                document_id=document_id,
                document_name=document_name,
                metadata=metadata,
            )
            self.chunk_index += 1