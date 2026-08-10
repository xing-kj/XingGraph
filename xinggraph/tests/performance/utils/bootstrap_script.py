# Importing locust at module top monkey-patches socket/time via gevent, which
# makes asyncio + async sqlite hot-spin at 100% CPU. Run bootstrap in a fresh
# interpreter that never imports locust.

import asyncio
import sys

import xinggraph
from xinggraph.modules.engine.operations.setup import setup
from xinggraph.modules.users.api_key.create_api_key import create_api_key
from xinggraph.modules.users.methods import create_default_user


async def main(out_path: str) -> None:
    await xinggraph.prune.prune_data()
    await xinggraph.prune.prune_system(metadata=True)
    await setup()
    user = await create_default_user()
    api_key_obj = await create_api_key(user, name="locust-loadtest")
    with open(out_path, "w") as f:
        f.write(api_key_obj.api_key)


asyncio.run(main(sys.argv[1]))
