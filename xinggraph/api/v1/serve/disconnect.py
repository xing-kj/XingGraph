"""Disconnect from XingGraph Cloud and revert to local mode."""

from xinggraph.shared.logging_utils import get_logger

logger = get_logger("serve.disconnect")


async def disconnect(clear_saved: bool = False) -> None:
    """Disconnect from XingGraph Cloud and revert to local mode.

    After calling this, all V2 operations (remember, recall, improve,
    forget) will execute locally again.

    Args:
        clear_saved: If True, also delete the saved credentials at
            ``~/.xinggraph/cloud_credentials.json``. By default credentials
            are preserved so ``xinggraph.serve()`` can reconnect without
            re-authenticating.
    """
    from xinggraph.api.v1.serve.state import get_remote_client, set_remote_client

    client = get_remote_client()
    if client:
        await client.close()
        set_remote_client(None)
        logger.info("Disconnected from XingGraph Cloud")
        print("  Disconnected from XingGraph Cloud. Operations now run locally.")
    else:
        print("  Not connected to XingGraph Cloud.")

    if clear_saved:
        from xinggraph.api.v1.serve.credentials import clear_credentials

        clear_credentials()
        print("  Saved credentials cleared.")
