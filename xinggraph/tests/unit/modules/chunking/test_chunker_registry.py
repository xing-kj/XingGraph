"""Unit tests for the chunker registry."""

import pytest

from xinggraph.modules.chunking.registry import (
    build_chunker,
    register_chunker,
    get_available_chunkers,
)
from xinggraph.modules.chunking.TextChunker import TextChunker
from xinggraph.modules.chunking.StructuredDocChunker import StructuredDocChunker


def test_build_chunker_defaults_to_text():
    assert build_chunker(None) is TextChunker
    assert build_chunker("automatic") is TextChunker
    assert build_chunker("default") is TextChunker


def test_build_chunker_known_names():
    assert build_chunker("text") is TextChunker
    assert build_chunker("structured_doc") is StructuredDocChunker


def test_build_chunker_unknown_raises():
    with pytest.raises(ValueError, match="Unknown chunker"):
        build_chunker("does_not_exist")


def test_register_chunker_round_trip():
    class DummyChunker:
        def read(self):
            yield None

    register_chunker("dummy", DummyChunker)
    assert build_chunker("dummy") is DummyChunker
    assert "dummy" in get_available_chunkers()


def test_register_chunker_rejects_non_class():
    with pytest.raises(ValueError, match="class"):
        register_chunker("bad", "not-a-class")
