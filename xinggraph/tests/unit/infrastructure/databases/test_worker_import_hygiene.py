"""Guardrail: the DB worker subprocesses must NOT import xinggraph.

This regressed silently in the past (old SubprocessGraphDBWrapper /
SubprocessVectorDBWrapper wrapped xinggraph adapter classes in the child,
dragging the entire ~200 MB xinggraph import graph into every child).

The new design puts worker code under the top-level ``xinggraph_db_workers``
package, which by construction imports only the native DB library (kuzu or
lancedb) + pyarrow + stdlib. This test enforces that invariant by spawning a
clean Python child and verifying ``xinggraph`` is absent from ``sys.modules``.
"""

from __future__ import annotations

import multiprocessing as mp
import sys

import pytest


def _probe_kuzu_worker(result_q):
    # Import the worker; make sure ``xinggraph`` isn't dragged in.
    import xinggraph_db_workers.kuzu_worker  # noqa: F401

    xinggraph_modules = sorted(m for m in sys.modules if m == "xinggraph" or m.startswith("xinggraph."))
    result_q.put(xinggraph_modules)


def _probe_lancedb_worker(result_q):
    import xinggraph_db_workers.lancedb_worker  # noqa: F401

    xinggraph_modules = sorted(m for m in sys.modules if m == "xinggraph" or m.startswith("xinggraph."))
    result_q.put(xinggraph_modules)


def _probe_harness(result_q):
    import xinggraph_db_workers.harness  # noqa: F401

    xinggraph_modules = sorted(m for m in sys.modules if m == "xinggraph" or m.startswith("xinggraph."))
    result_q.put(xinggraph_modules)


def _run_probe(target) -> list:
    ctx = mp.get_context("spawn")
    q = ctx.Queue()
    p = ctx.Process(target=target, args=(q,))
    p.start()
    try:
        return q.get(timeout=30)
    finally:
        p.join(timeout=10)
        if p.is_alive():
            p.terminate()
            p.join(timeout=5)


def test_kuzu_worker_does_not_import_xinggraph():
    modules = _run_probe(_probe_kuzu_worker)
    assert modules == [], (
        f"Kuzu worker pulled xinggraph into the child's sys.modules: {modules}. "
        "Keep the worker module (xinggraph_db_workers.kuzu_worker) free of "
        "xinggraph imports."
    )


def test_lancedb_worker_does_not_import_xinggraph():
    # Skip gracefully if lancedb isn't installed in this environment.
    try:
        import lancedb  # noqa: F401
    except ImportError:
        pytest.skip("lancedb not installed")

    modules = _run_probe(_probe_lancedb_worker)
    assert modules == [], (
        f"LanceDB worker pulled xinggraph into the child's sys.modules: {modules}. "
        "Keep the worker module (xinggraph_db_workers.lancedb_worker) free of "
        "xinggraph imports."
    )


def test_harness_does_not_import_xinggraph():
    modules = _run_probe(_probe_harness)
    assert modules == [], (
        f"Harness pulled xinggraph into the child's sys.modules: {modules}. "
        "Keep xinggraph_db_workers.harness stdlib-only."
    )
