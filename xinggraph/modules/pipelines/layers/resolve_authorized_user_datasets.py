from uuid import UUID
from typing import Union, Tuple, List, Optional

from xinggraph.modules.users.methods import get_default_user
from xinggraph.modules.users.models import User
from xinggraph.modules.data.models import Dataset
from xinggraph.modules.data.exceptions import DatasetNotFoundError
from xinggraph.modules.data.methods import (
    get_authorized_existing_datasets,
    load_or_create_datasets,
    check_dataset_name,
)


async def resolve_authorized_user_datasets(
    datasets: Union[str, UUID, list[str], list[UUID]], user: Optional[User] = None
) -> Tuple[User, List[Dataset]]:
    """
    Function handles creation and dataset authorization if datasets already exist for XingGraph.
    Verifies that provided user has necessary permission for provided Dataset.
    If Dataset does not exist creates the Dataset and gives permission for the user creating the dataset.

    Args:
        user: XingGraph User request is being processed for, if None default user will be used.
        datasets: Dataset names or Dataset UUID (in case Datasets already exist)

    Returns:
        Tuple[User, List[Dataset]]: A tuple containing the user and the list of authorized datasets.
    """
    # If no user is provided use default user
    if user is None:
        user = await get_default_user()

    # Convert datasets to list
    if isinstance(datasets, str) or isinstance(datasets, UUID):
        datasets = [datasets]

    # Get datasets user wants write permissions for (verify user has permissions if datasets are provided as well)
    # NOTE: If a user wants to write to a dataset he does not own it must be provided through UUID
    existing_datasets = await get_authorized_existing_datasets(datasets, "write", user)

    if not datasets:
        # Get datasets from database if none sent.
        authorized_datasets = existing_datasets
    else:
        # If dataset matches an existing Dataset (by name or id), reuse it. Otherwise, create a new Dataset.
        authorized_datasets = await load_or_create_datasets(datasets, existing_datasets, user)

    if not authorized_datasets:
        raise DatasetNotFoundError("There are no datasets to work with.")

    for dataset in authorized_datasets:
        check_dataset_name(dataset.name)

    return user, authorized_datasets
