import os
import pathlib
import xinggraph
from xinggraph.modules.search.operations import get_history
from xinggraph.modules.users.methods import get_default_user
from xinggraph.shared.logging_utils import get_logger
from xinggraph.modules.search.types import SearchType

logger = get_logger()


async def main():
    data_directory_path = str(
        pathlib.Path(
            os.path.join(pathlib.Path(__file__).parent, ".data_storage/test_library")
        ).resolve()
    )
    xinggraph.config.data_root_directory(data_directory_path)
    xinggraph_directory_path = str(
        pathlib.Path(
            os.path.join(pathlib.Path(__file__).parent, ".xinggraph_system/test_library")
        ).resolve()
    )
    xinggraph.config.system_root_directory(xinggraph_directory_path)

    await xinggraph.prune.prune_data()
    await xinggraph.prune.prune_system(metadata=True)

    await xinggraph.add(["TEST1"], "test1")
    await xinggraph.add(["TEST2"], "test2")

    task_1_config = {
        "vector_db_url": "xinggraph1.test",
        "vector_db_key": "",
        "vector_db_provider": "lancedb",
        "vector_db_name": "",
    }
    task_2_config = {
        "vector_db_url": "xinggraph2.test",
        "vector_db_key": "",
        "vector_db_provider": "lancedb",
        "vector_db_name": "",
    }

    task_1_graph_config = {
        "graph_database_provider": "ladybug",
        "graph_file_path": "ladybug1.db",
    }
    task_2_graph_config = {
        "graph_database_provider": "ladybug",
        "graph_file_path": "ladybug2.db",
    }

    # schedule both cognify calls concurrently
    task1 = asyncio.create_task(
        xinggraph.cognify(
            ["test1"], vector_db_config=task_1_config, graph_db_config=task_1_graph_config
        )
    )
    task2 = asyncio.create_task(
        xinggraph.cognify(
            ["test2"], vector_db_config=task_2_config, graph_db_config=task_2_graph_config
        )
    )

    # wait until both are done (raises first error if any)
    await asyncio.gather(task1, task2)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main(), debug=True)
