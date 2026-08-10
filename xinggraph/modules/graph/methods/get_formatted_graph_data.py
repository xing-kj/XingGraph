from uuid import UUID
from xinggraph.infrastructure.databases.graph import get_graph_engine
from xinggraph.context_global_variables import set_database_global_context_variables
from xinggraph.modules.data.exceptions.exceptions import DatasetNotFoundError
from xinggraph.modules.data.methods import get_authorized_dataset
from xinggraph.modules.users.models import User


async def get_formatted_graph_data(dataset_id: UUID, user: User):
    dataset = await get_authorized_dataset(user, dataset_id)
    if not dataset:
        raise DatasetNotFoundError(message="Dataset not found.")

    async with set_database_global_context_variables(dataset_id, dataset.owner_id):
        graph_client = await get_graph_engine()
        (nodes, edges) = await graph_client.get_graph_data(dataset_id=dataset_id)

    return {
        "nodes": list(
            map(
                lambda node: {
                    "id": str(node[0]),
                    "label": node[1]["name"]
                    if ("name" in node[1] and node[1]["name"] != "")
                    else f"{node[1]['type']}_{str(node[0])}",
                    "type": node[1]["type"],
                    "properties": {
                        key: value
                        for key, value in node[1].items()
                        if key not in ["id", "type", "name", "created_at", "updated_at"]
                        and value is not None
                    },
                },
                nodes,
            )
        ),
        "edges": [
            {
                "source": str(edge[0]),
                "target": str(edge[1]),
                "label": str(edge[2]),
                "relationship_type": str(edge[2]),
                **(
                    {k: v for k, v in edge[3].items() if k not in ("source_node_id", "target_node_id")}
                    if isinstance(edge[3], dict)
                    else {}
                ),
                "properties": edge[3] if isinstance(edge[3], dict) else {},
            }
            for edge in edges
        ],
    }
