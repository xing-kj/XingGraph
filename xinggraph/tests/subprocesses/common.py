import os


def configure_xinggraph_for_subprocess(xinggraph):
    data_root_directory = os.getenv("XINGGRAPH_TEST_DATA_ROOT")
    system_root_directory = os.getenv("XINGGRAPH_TEST_SYSTEM_ROOT")

    if data_root_directory:
        xinggraph.config.data_root_directory(data_root_directory)
    if system_root_directory:
        xinggraph.config.system_root_directory(system_root_directory)


def get_kuzu_db_path() -> str:
    return os.getenv("XINGGRAPH_TEST_KUZU_DB_PATH", "test.db")
