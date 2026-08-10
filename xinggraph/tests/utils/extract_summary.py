from uuid import uuid5
from xinggraph.modules.chunking.models import DocumentChunk
from xinggraph.shared.data_models import SummarizedContent
from xinggraph.tasks.summarization.models import TextSummary


def extract_summary(document_chunk: DocumentChunk, summary=SummarizedContent) -> TextSummary:
    return TextSummary(
        id=uuid5(document_chunk.id, "TextSummary"),
        text=summary.summary,
        made_from=document_chunk,
        source_chunk_id=str(document_chunk.id),
        belongs_to_set=document_chunk.belongs_to_set,
    )
