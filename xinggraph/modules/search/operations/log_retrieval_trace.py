"""Persist structured retrieval traces (e.g. WIKI_COMPLETION) as JSONL.

Each search that produces a retriever trace appends one JSON line to
``logs/retrieval_trace/retrieval_trace.jsonl`` under the project root so the
retrieval chain and the exact LLM context can be inspected offline.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from xinggraph.shared.logging_utils import get_logger

logger = get_logger()

TRACE_LOG_DIR_NAME = "retrieval_trace"
TRACE_LOG_FILE_NAME = "retrieval_trace.jsonl"

# Opt out by setting XINGGRAPH_LOG_RETRIEVAL_TRACE=false
_LOG_ENABLED = os.getenv("XINGGRAPH_LOG_RETRIEVAL_TRACE", "true").lower() in (
    "true",
    "1",
    "yes",
)


def _trace_log_path() -> Path:
    root = Path.cwd()
    return root / "logs" / TRACE_LOG_DIR_NAME / TRACE_LOG_FILE_NAME


async def log_retrieval_trace(
    query: str,
    search_type: Any,
    trace: dict,
    context: Optional[Any] = None,
    completion: Optional[Any] = None,
    dataset_id: Optional[UUID] = None,
) -> None:
    if not _LOG_ENABLED or not trace:
        return

    entry: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "dataset_id": str(dataset_id) if dataset_id else None,
        "search_type": str(getattr(search_type, "value", search_type)),
        "query": query,
        "trace": trace,
        "context": context if isinstance(context, str) else str(context or ""),
        "completion": completion,
    }

    try:
        path = _trace_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
    except Exception as error:  # Never break a search because tracing failed
        logger.debug("Failed to write retrieval trace: %s", error)
