import warnings
import sys


def _load_server_main():
    """Import the heavy server module lazily.

    Importing server eagerly at package-import time pulls in the MCP SDK
    and uvicorn/starlette, which aren't available in environments that
    only depend on the core xinggraph library (e.g. the unit-tests CI job).
    Deferring the import lets `import src.xinggraph_client` succeed without
    those dependencies.
    """
    try:
        from .server import main as server_main
    except ImportError:
        from server import main as server_main
    return server_main


def main():
    """Deprecated main entry point for the package."""
    import asyncio

    deprecation_notice = """
DEPRECATION NOTICE
The CLI entry-point used to start the XingGraph MCP service has been renamed from
"xinggraph" to "xinggraph-mcp". Calling the old entry-point will stop working in a
future release.

WHAT YOU NEED TO DO:
Locate every place where you launch the MCP process and replace the final
argument xinggraph → xinggraph-mcp.

For the example mcpServers block from Cursor shown below the change is:
{
  "mcpServers": {
    "XingGraph": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/xinggraph-mcp",
        "run",
        "xinggraph"              // <-- CHANGE THIS to "xinggraph-mcp"
      ]
    }
  }
}

Continuing to use the old "xinggraph" entry-point will result in failures once it
is removed, so please update your configuration and any shell scripts as soon
as possible.
"""

    warnings.warn(
        "The 'xinggraph' command for xinggraph-mcp is deprecated and will be removed in a future version. "
        "Please use 'xinggraph-mcp' instead to avoid conflicts with the main xinggraph library.",
        DeprecationWarning,
        stacklevel=2,
    )

    print("⚠️  DEPRECATION WARNING", file=sys.stderr)
    print(deprecation_notice, file=sys.stderr)

    asyncio.run(_load_server_main()())


def main_mcp():
    """Clean main entry point for xinggraph-mcp command."""
    import asyncio

    asyncio.run(_load_server_main()())
