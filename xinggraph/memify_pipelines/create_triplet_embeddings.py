from typing import Any

from xinggraph import memify
from xinggraph.context_global_variables import (
    set_database_global_context_variables,
)
from xinggraph.exceptions import XingGraphValidationError
from xinggraph.modules.data.methods import get_authorized_existing_datasets
from xinggraph.shared.logging_utils import get_logger
from xinggraph.modules.pipelines.tasks.task import Task
from xinggraph.modules.users.models import User
from xinggraph.tasks.memify.get_triplet_datapoints import get_triplet_datapoints
from xinggraph.tasks.storage import index_data_points

logger = get_logger("create_triplet_embeddings")


async def create_triplet_embeddings(
    user: User,
    dataset: str = "main_dataset",
    run_in_background: bool = False,
    triplets_batch_size: int = 100,
) -> dict[str, Any]:
    dataset_to_write = await get_authorized_existing_datasets(
        user=user, datasets=[dataset], permission_type="write"
    )

    if not dataset_to_write:
        raise XingGraphValidationError(
            message=f"User does not have write access to dataset: {dataset}",
            log=False,
        )

    async with set_database_global_context_variables(
        dataset_to_write[0].id, dataset_to_write[0].owner_id
    ):
        extraction_tasks = [Task(get_triplet_datapoints, triplets_batch_size=triplets_batch_size)]

        enrichment_tasks = [
            Task(index_data_points, task_config={"batch_size": triplets_batch_size}),
        ]

        result = await memify(
            extraction_tasks=extraction_tasks,
            enrichment_tasks=enrichment_tasks,
            dataset=dataset_to_write[0].id,
            data=[{}],
            user=user,
            run_in_background=run_in_background,
        )

    return result
