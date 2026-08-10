"""Minimal subprocess-side machinery for running native DB clients (kuzu,
lancedb) in a dedicated child process without importing xinggraph.

This package must stay free of xinggraph imports so that a spawned worker has
a small memory footprint (just the native DB library + stdlib).
"""
