"""Generate ChunkWiki from a document chunk using LLM analysis."""

from typing import Optional

from xinggraph.infrastructure.llm.LLMGateway import LLMGateway
from xinggraph.infrastructure.llm.prompts import render_prompt
from xinggraph.shared.data_models import ChunkWiki

WIKI_PROMPT_PATH = "generate_chunk_wiki.txt"


async def generate_chunk_wiki(
    chunk_text: str,
    chunk_id: str,
    neighbor_entities: Optional[list[str]] = None,
    custom_prompt: Optional[str] = None,
    **kwargs,
) -> ChunkWiki:
    """Generate a wiki summary for a document chunk.

    Args:
        chunk_text: The raw text of the document chunk.
        chunk_id: The ID of the document chunk.
        neighbor_entities: Optional list of entity names from neighboring chunks,
            used to help resolve pronouns and references.
        custom_prompt: Optional custom system prompt to override the default.
        **kwargs: Additional arguments passed to LLMGateway.acreate_structured_output.

    Returns:
        ChunkWiki with summary, key_topics, key_entities, and content_type.
    """
    neighbor_entities = neighbor_entities or []
    neighbor_text = ", ".join(neighbor_entities) if neighbor_entities else "None"

    system_prompt = custom_prompt or render_prompt(
        WIKI_PROMPT_PATH,
        {"chunk_text": chunk_text, "neighbor_entities": neighbor_text},
    )

    wiki = await LLMGateway.acreate_structured_output(
        text_input=chunk_text,
        system_prompt=system_prompt,
        response_model=ChunkWiki,
        **kwargs,
    )

    wiki.chunk_id = chunk_id

    return wiki
