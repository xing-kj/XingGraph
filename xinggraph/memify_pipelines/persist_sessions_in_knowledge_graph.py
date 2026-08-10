from typing import Optional, List

from xinggraph import memify
from xinggraph.context_global_variables import (
    set_database_global_context_variables,
    set_session_user_context_variable,
)
from xinggraph.exceptions import XingGraphValidationError
from xinggraph.modules.data.methods import get_authorized_existing_datasets
from xinggraph.shared.logging_utils import get_logger
from xinggraph.modules.pipelines.tasks.task import Task
from xinggraph.modules.users.models import User
from xinggraph.tasks.memify import extract_user_sessions, cognify_session


logger = get_logger("persist_sessions_in_knowledge_graph")


async def persist_sessions_in_knowledge_graph_pipeline(
    user: User,
    session_ids: Optional[List[str]] = None,
    dataset: str = "main_dataset",
    run_in_background: bool = False,
):
    """
    Persist user sessions into the knowledge graph via memify pipeline.

    Reads session data via SessionManager (caching must be enabled). Each session
    is cognified and added to the graph with node_set "user_sessions_from_cache".

    Args:
        user: Authenticated user with write access to the dataset.
        session_ids: Optional list of session IDs to persist. If None, no sessions
            are extracted (caller must specify which sessions to persist).
        dataset: Dataset name for write access. Defaults to "main_dataset".
        run_in_background: If True, runs memify asynchronously and returns immediately.
    """
    await set_session_user_context_variable(user)
    dataset_to_write = await get_authorized_existing_datasets(
        user=user, datasets=[dataset], permission_type="write"
    )

    if not dataset_to_write:
        raise XingGraphValidationError(
            message=f"User (id: {str(user.id)}) does not have write access to dataset: {dataset}",
            log=False,
        )

    async with set_database_global_context_variables(
        dataset_to_write[0].id, dataset_to_write[0].owner_id
    ):
        extraction_tasks = [Task(extract_user_sessions, session_ids=session_ids)]

        enrichment_tasks = [
            Task(cognify_session, dataset_id=dataset_to_write[0].id, user=user),
        ]

        result = await memify(
            extraction_tasks=extraction_tasks,
            enrichment_tasks=enrichment_tasks,
            dataset=dataset_to_write[0].id,
            user=user,
            data=[{}],
            run_in_background=run_in_background,
        )

    logger.info("Session persistence pipeline completed")
    return result
