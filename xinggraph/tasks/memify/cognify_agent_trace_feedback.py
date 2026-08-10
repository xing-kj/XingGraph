from typing import Optional
from uuid import UUID

import xinggraph

from xinggraph.exceptions import XingGraphSystemError, XingGraphValidationError
from xinggraph.modules.users.models import User
from xinggraph.shared.logging_utils import get_logger

logger = get_logger("cognify_agent_trace_feedback")


async def cognify_agent_trace_feedback(
    data: str,
    dataset_id: Optional[UUID | str] = None,
    node_set_name: str = "agent_trace_feedbacks",
    user: Optional[User] = None,
) -> None:
    """
    Process and cognify agent trace session text into the knowledge graph.

    Args:
        data: Agent trace text for a single session. Depending on the extractor
            configuration, this may contain either session feedback summaries or
            raw method return values.
        dataset_id: Dataset identifier to write to.
        node_set_name: Node-set name used when adding the trace text.
        user: User the add/cognify calls run as. Without it they fall back to
            the default user, which has no write ACL on multi-tenant deployments.

    Raises:
        XingGraphValidationError: If data is None or empty.
        XingGraphSystemError: If xinggraph operations fail.
    """
    try:
        if not data or (isinstance(data, str) and not data.strip()):
            logger.warning(
                "Empty agent trace content provided to cognify_agent_trace_feedback task, skipping"
            )
            raise XingGraphValidationError(
                message="Agent trace content cannot be empty",
                log=False,
            )

        logger.info("Processing agent trace content for cognification")

        await xinggraph.add(data, dataset_id=dataset_id, node_set=[node_set_name], user=user)
        logger.debug(
            "Agent trace content added to xinggraph with node_set: %s",
            node_set_name,
        )
        await xinggraph.cognify(datasets=[dataset_id], user=user)
        logger.info("Agent trace content successfully cognified")

    except XingGraphValidationError:
        raise
    except Exception as error:
        logger.error("Error cognifying agent trace content: %s", error)
        raise XingGraphSystemError(
            message=f"Failed to cognify agent trace content: {error}",
            log=False,
        )
