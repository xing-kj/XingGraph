import os
from contextlib import suppress
import importlib.metadata
from pathlib import Path


def get_xinggraph_version() -> str:
    """Returns either the version of installed xinggraph package or the one
    found in nearby pyproject.toml"""
    with suppress(FileNotFoundError, StopIteration):
        with open(
            os.path.join(Path(__file__).parent.parent, "pyproject.toml"), encoding="utf-8"
        ) as pyproject_toml:
            version = (
                next(line for line in pyproject_toml if line.startswith("version"))
                .split("=")[1]
                .strip("'\"\n ")
            )
            # Mark the version as a local XingGraph library by appending “-dev”
            return f"{version}-local"
    try:
        return importlib.metadata.version("xinggraph")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"
