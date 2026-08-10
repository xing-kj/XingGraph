"""Built-in tools registered at import time.

Importing this package registers every built-in tool with the registry.
"""

from xinggraph.modules.tools.builtin import load_skill as _load_skill  # noqa: F401
from xinggraph.modules.tools.builtin import memory_search as _memory_search  # noqa: F401
