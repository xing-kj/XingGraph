import argparse
import asyncio

from xinggraph.cli.reference import SupportsCliCommand
from xinggraph.cli import DEFAULT_DOCS_URL
import xinggraph.cli.echo as fmt


class ServeCommand(SupportsCliCommand):
    command_string = "serve"
    help_string = "Connect to a XingGraph instance (cloud or local)"
    docs_url = DEFAULT_DOCS_URL
    description = """
Connect the local XingGraph SDK to a XingGraph instance.

Cloud mode (default): authenticates via browser-based device code flow,
discovers your tenant, and connects automatically.

Local mode: connect directly to a running XingGraph backend.

Examples:
  xinggraph serve                              # Cloud (Auth0 device flow)
  xinggraph serve --url http://localhost:8000  # Local instance
  xinggraph serve --url https://my.xinggraph.ai --api-key ck_...
  xinggraph serve --logout                     # Disconnect + clear credentials
    """

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--url",
            help="Direct URL of a XingGraph instance (skips Auth0 + tenant discovery)",
        )
        parser.add_argument(
            "--api-key",
            help="API key for the instance (optional for local, required for cloud instances)",
        )
        parser.add_argument(
            "--management-url",
            help="Override the Management API URL (cloud mode only)",
        )
        parser.add_argument(
            "--logout",
            action="store_true",
            help="Disconnect and clear saved credentials",
        )

    def execute(self, args: argparse.Namespace) -> None:
        if args.logout:
            asyncio.run(_logout())
        else:
            asyncio.run(
                _serve(url=args.url, api_key=args.api_key, management_url=args.management_url)
            )


async def _serve(url=None, api_key=None, management_url=None):
    import xinggraph

    mode = "local" if url else "cloud"
    fmt.note(f"Connecting to XingGraph ({mode})...")
    try:
        client = await xinggraph.serve(url=url, api_key=api_key or "", management_url=management_url)
        fmt.success(f"Connected to {client.service_url}")
    except KeyboardInterrupt:
        fmt.warning("Authentication cancelled.")
    except Exception as e:
        fmt.error(f"Failed to connect: {e}")


async def _logout():
    import xinggraph

    await xinggraph.disconnect(clear_saved=True)
