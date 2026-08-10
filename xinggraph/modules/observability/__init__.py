from typing import Optional
from contextlib import contextmanager

from .trace_context import (
    enable_tracing,
    disable_tracing,
    is_tracing_enabled,
    get_last_trace,
    get_all_traces,
    clear_traces,
)
from .tracing import (
    XingGraphTrace,
    redact_secrets,
    get_tracer,
    XINGGRAPH_DB_SYSTEM,
    XINGGRAPH_DB_QUERY,
    XINGGRAPH_DB_ROW_COUNT,
    XINGGRAPH_LLM_MODEL,
    XINGGRAPH_LLM_PROVIDER,
    XINGGRAPH_SEARCH_TYPE,
    XINGGRAPH_SEARCH_QUERY,
    XINGGRAPH_PIPELINE_TASK_NAME,
    XINGGRAPH_VECTOR_COLLECTION,
    XINGGRAPH_VECTOR_RESULT_COUNT,
    XINGGRAPH_SPAN_CATEGORY,
    XINGGRAPH_PIPELINE_NAME,
    XINGGRAPH_RESULT_SUMMARY,
    XINGGRAPH_RESULT_COUNT,
    # V2 attributes
    XINGGRAPH_DATASET_NAME,
    XINGGRAPH_SESSION_ID,
    XINGGRAPH_SESSION_ENTRY_COUNT,
    XINGGRAPH_DATA_SIZE_BYTES,
    XINGGRAPH_DATA_ITEM_COUNT,
    XINGGRAPH_OPERATION_MODE,
    XINGGRAPH_RECALL_SCOPE,
    XINGGRAPH_RECALL_SOURCE,
    XINGGRAPH_FORGET_TARGET,
    XINGGRAPH_IMPROVE_STAGES,
    XINGGRAPH_GRAPH_EDGES_SYNCED,
)


try:
    from opentelemetry.trace import StatusCode as OtelStatusCode
except ImportError:

    class _StatusCodeFallback:
        ERROR = "ERROR"
        OK = "OK"
        UNSET = "UNSET"

    OtelStatusCode = _StatusCodeFallback  # type: ignore[misc, assignment]


class _NullSpan:
    """No-op span used when tracing is disabled."""

    def __getattr__(self, name):
        return lambda *args, **kwargs: None


def get_tracer_if_enabled() -> Optional[object]:
    """Return the OTEL tracer if tracing is enabled, None otherwise."""
    if is_tracing_enabled():
        return get_tracer()
    return None


@contextmanager
def new_span(name: str):
    """Context manager that creates an OTEL span if tracing is enabled, or yields None."""
    if is_tracing_enabled():
        tracer = get_tracer()
        if tracer is not None:
            with tracer.start_as_current_span(name) as span:
                yield span
                return
    yield _NullSpan()
