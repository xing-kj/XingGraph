from typing import List, Optional

from xinggraph.context_global_variables import session_user
from xinggraph.exceptions import XingGraphValidationError
from xinggraph.infrastructure.databases.cache.models import SessionQAEntry
from xinggraph.infrastructure.databases.exceptions import DatabaseNotCreatedError
from xinggraph.infrastructure.session.get_session_manager import get_session_manager
from xinggraph.modules.users.exceptions.exceptions import UserNotFoundError
from xinggraph.modules.users.methods import get_default_user
from xinggraph.modules.users.models import User
from xinggraph.shared.logging_utils import get_logger

logger = get_logger("session_api_sdk")


async def _resolve_user(user: Optional[User]) -> User:
    if user is not None:
        if getattr(user, "id", None) is None:
            raise XingGraphValidationError(
                message="Session user must have an id.",
                name="SessionPreconditionError",
            )
        return user
    ctx_user = session_user.get()
    if ctx_user is not None and getattr(ctx_user, "id", None) is not None:
        return ctx_user
    try:
        return await get_default_user()
    except (DatabaseNotCreatedError, UserNotFoundError) as error:
        raise XingGraphValidationError(
            message=(
                "Session prerequisites not met: no default user found. "
                "Initialize XingGraph before using session APIs by running "
                "`await xinggraph.add(...)` followed by `await xinggraph.cognify()`."
            ),
            name="SessionPreconditionError",
        ) from error


async def get_session(
    session_id: str = "default_session",
    last_n: Optional[int] = None,
    user: Optional[User] = None,
) -> List[SessionQAEntry]:
    resolved_user = await _resolve_user(user)
    user_id = str(resolved_user.id)

    try:
        sm = get_session_manager()
        raw = await sm.get_session(
            user_id=user_id,
            session_id=session_id,
            last_n=last_n,
            formatted=False,
        )
    except Exception as e:
        logger.warning("get_session: error from SessionManager: %s", e)
        return []

    if not raw:
        return []

    result: List[SessionQAEntry] = []
    for entry in raw:
        if isinstance(entry, dict):
            try:
                result.append(SessionQAEntry.model_validate(entry))
            except Exception as e:
                logger.warning("get_session: skip invalid entry: %s", e)
        elif isinstance(entry, SessionQAEntry):
            result.append(entry)
        else:
            logger.warning("get_session: skip non-dict non-SessionQAEntry entry: %s", type(entry))
    return result


async def add_feedback(
    session_id: str,
    qa_id: str,
    feedback_text: Optional[str] = None,
    feedback_score: Optional[int] = None,
    user: Optional[User] = None,
) -> bool:
    resolved_user = await _resolve_user(user)
    user_id = str(resolved_user.id)

    try:
        sm = get_session_manager()
        return await sm.add_feedback(
            user_id=user_id,
            session_id=session_id,
            qa_id=qa_id,
            feedback_text=feedback_text,
            feedback_score=feedback_score,
        )
    except Exception as e:
        logger.warning("add_feedback: error from SessionManager: %s", e)
        return False


async def add_frequency_weights(
    session_id: str,
    qa_id: str,
    node_ids: Optional[list[str]] = None,
    edge_ids: Optional[list[str]] = None,
    user: Optional[User] = None,
) -> bool:
    """Add or update frequency weight data for a QA entry.

    This function stores the graph elements (node_ids and edge_ids) that were used
    in generating the answer for a QA entry. This data is later processed by
    apply_frequency_weights to increment the frequency weights of those elements.

    The frequency_weights_applied flag is reset to False so the entry will be
    reprocessed by the apply_frequency_weights pipeline.

    Args:
        session_id: Session identifier.
        qa_id: QA entry identifier.
        node_ids: List of node IDs used in generating the answer.
        edge_ids: List of edge IDs used in generating the answer.
        user: User that owns the session. If None, uses session/context user or default user.

    Returns:
        True if updated, False if QA not found or cache unavailable.
    """
    from xinggraph.tasks.memify.frequency_weights_constants import (
        MEMIFY_METADATA_FREQUENCY_WEIGHTS_APPLIED_KEY,
    )

    resolved_user = await _resolve_user(user)
    user_id = str(resolved_user.id)

    used_graph_element_ids: dict[str, list[str]] = {}
    if node_ids:
        used_graph_element_ids["node_ids"] = node_ids
    if edge_ids:
        used_graph_element_ids["edge_ids"] = edge_ids

    try:
        sm = get_session_manager()
        return await sm.update_qa(
            user_id=user_id,
            session_id=session_id,
            qa_id=qa_id,
            used_graph_element_ids=used_graph_element_ids if used_graph_element_ids else None,
            memify_metadata={MEMIFY_METADATA_FREQUENCY_WEIGHTS_APPLIED_KEY: False},
        )
    except Exception as e:
        logger.warning("add_frequency_weights: error from SessionManager: %s", e)
        return False


async def delete_feedback(
    session_id: str,
    qa_id: str,
    user: Optional[User] = None,
) -> bool:
    """
    Clear feedback for a QA entry (sets feedback_text and feedback_score to None).

    When user is None, uses session context or default user.

    Args:
        session_id: Session identifier.
        qa_id: QA entry identifier to clear feedback for.
        user: User that owns the session. If None, uses session/context user or default user.

    Returns:
        True if feedback was cleared, False if QA not found or cache unavailable.
    """
    resolved_user = await _resolve_user(user)
    user_id = str(resolved_user.id)

    try:
        sm = get_session_manager()
        return await sm.delete_feedback(
            user_id=user_id,
            session_id=session_id,
            qa_id=qa_id,
        )
    except Exception as e:
        logger.warning("delete_feedback: error from SessionManager: %s", e)
        return False
