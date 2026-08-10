import ast
import re
from typing import Any, Dict, Iterator
from uuid import NAMESPACE_OID, uuid5

from .chunk_by_sentence import get_word_size

# Matches a single structured "Doc" block:
#   Doc <index>/<total>: len=<len>, titles=[...]
#   --- 内容开始 ---
#   <content>
#   --- 内容结束 ---
DOC_BLOCK_RE = re.compile(
    r"^Doc\s+(?P<doc_index>\d+)/(?P<total>\d+):\s*len=\d+,\s*titles=(?P<titles>.+?)\s*\n"
    r"^--+\s*内容开始\s*--+\s*\n"
    r"(?P<content>.*?)\n"
    r"^--+\s*内容结束\s*--+\s*$",
    re.MULTILINE | re.DOTALL,
)


def _parse_titles(titles_text: str) -> list:
    """Parse the titles='...' list literal from the Doc header."""
    if not titles_text:
        return []
    titles_text = titles_text.strip()
    if titles_text.startswith("["):
        try:
            parsed = ast.literal_eval(titles_text)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except (ValueError, SyntaxError):
            pass
    return [name.strip() for name in titles_text.strip("[]").split(",") if name.strip()]


def chunk_by_doc_structure(
    data: str,
    max_chunk_size: int,
) -> Iterator[Dict[str, Any]]:
    """
    Chunk text that follows the "parsed PDF" wrapper format, where each semantic
    section is wrapped in:

        Doc <N>/<total>: len=<len>, titles=[<t_1>, <t_2>, ...]
        --- ...内容开始... ---
        <content>
        --- ...内容结束... ---

    Each Doc block becomes exactly one chunk: its text is the block verbatim
    (header line + begin/end markers + content), so chunks can be re-assembled
    and traced back to the original structure. The `titles` hierarchy is carried
    on each chunk dict for downstream metadata.

    Text without the wrapper markers is treated as a single whole-text chunk.

    A message that a single chunk exceeds max_chunk_size is not silently split;
    callers must validate and raise.
    """
    blocks = list(DOC_BLOCK_RE.finditer(data))
    if not blocks:
        yield {
            "text": data,
            "chunk_size": get_word_size(data),
            "chunk_id": uuid5(NAMESPACE_OID, data or "empty"),
            "titles": [],
            "doc_index": None,
            "total_docs": None,
            "cut_type": "doc_structure",
        }
        return

    for match in blocks:
        doc_index = int(match.group("doc_index"))
        total_docs = int(match.group("total"))
        titles = _parse_titles(match.group("titles"))
        block_text = match.group(0) + "\n" if not match.group(0).endswith("\n") else match.group(0)

        yield {
            "text": block_text,
            "chunk_size": get_word_size(block_text),
            "chunk_id": uuid5(NAMESPACE_OID, f"{doc_index}:{block_text}"),
            "titles": titles,
            "doc_index": doc_index,
            "total_docs": total_docs,
            "cut_type": "doc_structure",
        }