from typing import List

from xinggraph.modules.engine.models import Entity
from xinggraph.infrastructure.context.BaseContextProvider import (
    BaseContextProvider,
)


class DummyContextProvider(BaseContextProvider):
    """Simple context getter that returns a constant context."""

    async def get_context(self, entities: List[Entity], query: str) -> str:
        return "Albert Einstein was a theoretical physicist."
