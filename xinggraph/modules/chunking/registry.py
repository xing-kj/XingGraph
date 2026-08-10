from typing import Callable

from xinggraph.modules.chunking.Chunker import Chunker
from xinggraph.modules.chunking.TextChunker import TextChunker
from xinggraph.modules.chunking.StructuredDocChunker import StructuredDocChunker

# Map of chunker name -> chunker class. The classes are constructed by the
# document layer as: chunker_cls(document, max_chunk_size=..., get_text=...),
# so we register classes (not instances). LangchainChunker/CsvChunker are
# loaded lazily to avoid importing their optional heavy dependencies unless
# they are actually requested.
_REGISTERED_CHUNKERS: dict[str, type[Chunker]] = {
    "text": TextChunker,
    "structured_doc": StructuredDocChunker,
}


def _lazy_import(name: str) -> type[Chunker]:
    if name == "langchain":
        from xinggraph.modules.chunking.LangchainChunker import LangchainChunker

        return LangchainChunker
    if name == "csv":
        from xinggraph.modules.chunking.CsvChunker import CsvChunker

        return CsvChunker
    raise ValueError(f"Unknown chunker '{name}'. Available: {sorted(_REGISTERED_CHUNKERS)}")


def register_chunker(name: str, chunker_class: type[Chunker]) -> None:
    """Register a chunker class under a name for the cognify pipeline."""
    if not (isinstance(chunker_class, type) and hasattr(chunker_class, "read")):
        raise ValueError(f"Chunker {chunker_class} must be a class with a 'read' method")
    _REGISTERED_CHUNKERS[name] = chunker_class


def build_chunker(name: str | None) -> type[Chunker]:
    """Resolve a registered chunker by name. Defaults to the plain TextChunker."""
    if not name or name in ("automatic", "default"):
        return TextChunker
    if name in _REGISTERED_CHUNKERS:
        return _REGISTERED_CHUNKERS[name]
    return _lazy_import(name)


def get_available_chunkers() -> list[str]:
    """Names of all registered chunkers, for the frontend selector."""
    return sorted([*_REGISTERED_CHUNKERS.keys(), "langchain", "csv"])