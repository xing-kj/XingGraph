import json
from typing import Optional

from xinggraph.context_global_variables import session_user
from xinggraph.exceptions import XingGraphSystemError
from xinggraph.infrastructure.session.get_session_manager import get_session_manager
from xinggraph.modules.users.models import User
from xinggraph.shared.logging_utils import get_logger

logger = get_logger("extract_agent_trace_feedbacks")


def _normalize_trace_content(value) -> Optional[str]:
    """Convert raw trace content into a non-empty string suitable for memify payloads."""
    if value is None:
        return None
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    if isinstance(value, (bool, int, float)):
        return str(value)

    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True)
    normalized = serialized.strip()
    return normalized or None


async def extract_agent_trace_feedbacks(
    data,
    session_ids: Optional[list[str]] = None,
    raw_trace_content: bool = False,
    last_n_steps: Optional[int] = None,
):
    """
    Extract step-level agent trace content for the current user.

    Retrieves either stored ``session_feedback`` values or raw ``method_return_value``
    values from agent trace sessions and yields one formatted text blob per session.
    Only non-empty entries are included.

    Args:
        data: Data passed from memify. If empty dict ({}), no external data is provided.
        session_ids: Optional list of specific session IDs to extract.
        raw_trace_content: When True, persist raw ``method_return_value`` values instead
            of ``session_feedback`` summaries.
        last_n_steps: Optional number of most recent trace steps to extract per
            session. When None, all stored steps are used.

    Yields:
        String containing the session ID and all non-empty extracted entries.

    Raises:
        XingGraphSystemError: If SessionManager is unavailable or extraction fails.
    """
    try:
        if not data or data == [{}]:
            logger.info("Fetching agent trace feedback for current user")

        user: User = session_user.get()
        if not user:
            raise XingGraphSystemError(message="No authenticated user found in context", log=False)

        user_id = str(user.id)

        session_manager = get_session_manager()
        if not session_manager.is_available:
            raise XingGraphSystemError(
                message=(
                    "SessionManager not available for agent trace feedback extraction, "
                    "please enable caching in order to have sessions to save"
                ),
                log=False,
            )

        if not isinstance(raw_trace_content, bool):
            raise XingGraphSystemError(
                message="raw_trace_content must be a boolean",
                log=False,
            )

        if session_ids:
            for session_id in session_ids:
                try:
                    content_label = (
                        "method_return_value" if raw_trace_content else "session_feedback"
                    )
                    if not raw_trace_content:
                        trace_values = await session_manager.get_agent_trace_feedback(
                            user_id=user_id,
                            session_id=session_id,
                            last_n=last_n_steps,
                        )
                    else:
                        trace_session = await session_manager.get_agent_trace_session(
                            user_id=user_id,
                            session_id=session_id,
                            last_n=last_n_steps,
                        )
                        trace_values = [entry.method_return_value for entry in trace_session]

                    normalized_trace_values = [
                        normalized
                        for value in trace_values
                        if (normalized := _normalize_trace_content(value)) is not None
                    ]
                    if normalized_trace_values:
                        logger.info(
                            "Extracted session %s via SessionManager with %d %s entries",
                            session_id,
                            len(normalized_trace_values),
                            content_label,
                        )
                        yield f"Session ID: {session_id}\n\n" + "\n".join(normalized_trace_values)
                except Exception as error:
                    logger.warning(
                        "Failed to extract agent trace %s for session %s: %s",
                        content_label,
                        session_id,
                        error,
                    )
                    continue
        else:
            logger.info(
                "No specific session_ids provided. Please specify which sessions to extract."
            )

    except XingGraphSystemError:
        raise
    except Exception as error:
        logger.error("Error extracting agent trace feedbacks: %s", error)
        raise XingGraphSystemError(
            message=f"Failed to extract agent trace feedbacks: {error}",
            log=False,
        )
