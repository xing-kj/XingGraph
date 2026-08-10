#!/usr/bin/env python3
"""
Minimal CLI entry point for xinggraph that avoids early initialization
"""

import sys
import os
from typing import Any, Sequence

# CRITICAL: Prevent verbose logging initialization for CLI-only usage
# This must be set before any xinggraph imports to be effective
os.environ["XINGGRAPH_MINIMAL_LOGGING"] = "true"
os.environ["XINGGRAPH_CLI_MODE"] = "true"


def get_version() -> str:
    """Get xinggraph version without importing the main package"""
    try:
        # Try to get version from pyproject.toml first (for development)
        from pathlib import Path

        pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
        if pyproject_path.exists():
            with open(pyproject_path, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("version"):
                        version = line.split("=")[1].strip("'\"\n ")
                        return f"{version}-local"

        # Fallback to installed package version
        import importlib.metadata

        return importlib.metadata.version("xinggraph")
    except Exception:
        return "unknown"


def get_command_info() -> dict:
    """Get command information without importing xinggraph"""
    return {
        "add": "Add data to XingGraph for knowledge graph processing",
        "search": "Search and query the knowledge graph for insights, information, and connections",
        "cognify": "Transform ingested data into a structured knowledge graph",
        "delete": "Delete data from xinggraph knowledge base",
        "config": "Manage xinggraph configuration settings",
    }


def print_help() -> None:
    """Print help message with dynamic command descriptions"""
    commands = get_command_info()
    command_list = "\n".join(f"    {cmd:<12} {desc}" for cmd, desc in commands.items())

    print(f"""
usage: xinggraph [-h] [--version] [--debug] {{{"|".join(commands.keys())}}} ...

XingGraph CLI - Manage your knowledge graphs and cognitive processing pipelines.

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  --debug               Enable debug mode to show full stack traces on exceptions

Available commands:
  {{{",".join(commands.keys())}}}
{command_list}

For more information on each command, use: xinggraph <command> --help
""")


def main() -> int:
    """Minimal CLI main function"""
    # Handle help and version without any imports - purely static
    if len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] in ["-h", "--help"]):
        print_help()
        return 0

    if len(sys.argv) == 2 and sys.argv[1] == "--version":
        print(f"xinggraph {get_version()}")
        return 0

    # For actual commands, import the full CLI with minimal logging
    try:
        from xinggraph.cli._xinggraph import main as full_main

        return full_main()
    except Exception as e:
        if "--debug" in sys.argv:
            raise
        print(f"Error: {e}")
        print("Use --debug for full stack trace")
        return 1


if __name__ == "__main__":
    sys.exit(main())
