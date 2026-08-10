import os
import pathlib
from typing import List
from uuid import UUID, uuid4
from pydantic import BaseModel

import xinggraph
from xinggraph.api.v1.datasets import datasets
from xinggraph.context_global_variables import set_database_global_context_variables
from xinggraph.infrastructure.engine import DataPoint
from xinggraph.modules.data.methods import create_authorized_dataset
from xinggraph.modules.engine.operations.setup import setup
from xinggraph.modules.engine.utils import generate_node_id
from xinggraph.modules.users.models import User
from xinggraph.modules.users.methods import get_default_user
from xinggraph.shared.logging_utils import get_logger
from xinggraph.tasks.storage import add_data_points

logger = get_logger()


async def main():
    data_directory_path = str(
        pathlib.Path(
            os.path.join(pathlib.Path(__file__).parent, ".data_storage/test_delete_custom_graph")
        ).resolve()
    )
    xinggraph.config.data_root_directory(data_directory_path)
    xinggraph_directory_path = str(
        pathlib.Path(
            os.path.join(pathlib.Path(__file__).parent, ".xinggraph_system/test_delete_custom_graph")
        ).resolve()
    )
    xinggraph.config.system_root_directory(xinggraph_directory_path)

    await xinggraph.prune.prune_data()
    await xinggraph.prune.prune_system(metadata=True)
    await setup()

    class Organization(DataPoint):
        name: str
        metadata: dict = {"index_fields": ["name"]}

    class ForProfit(Organization):
        name: str = "For-Profit"
        metadata: dict = {"index_fields": ["name"]}

    class NonProfit(Organization):
        name: str = "Non-Profit"
        metadata: dict = {"index_fields": ["name"]}

    class Person(DataPoint):
        name: str
        works_for: List[Organization]
        metadata: dict = {"index_fields": ["name"]}

    companyA = ForProfit(id=generate_node_id("Company A"), name="Company A")
    companyB = NonProfit(id=generate_node_id("Company B"), name="Company B")

    person1 = Person(id=generate_node_id("John"), name="John", works_for=[companyA, companyB])
    person2 = Person(id=generate_node_id("Jane"), name="Jane", works_for=[companyB])

    user: User = await get_default_user()  # type: ignore

    class CustomData(BaseModel):
        id: UUID

    dataset = await create_authorized_dataset(dataset_name="test_dataset", user=user)
    data1 = CustomData(id=uuid4())
    data2 = CustomData(id=uuid4())

    await set_database_global_context_variables(dataset.id, dataset.owner_id)

    from xinggraph.modules.pipelines.models import PipelineContext

    await add_data_points(
        [person1],
        ctx=PipelineContext(
            user=user,
            dataset=dataset,
            data_item=data1,
        ),
    )

    await add_data_points(
        [person2],
        ctx=PipelineContext(
            user=user,
            dataset=dataset,
            data_item=data2,
        ),
    )

    from xinggraph.infrastructure.databases.graph import get_graph_engine

    graph_engine = await get_graph_engine()

    nodes, edges = await graph_engine.get_graph_data()

    # Initial check — filter out EdgeType nodes created by index_graph_edges
    data_nodes = [n for n in nodes if n[1].get("type") != "EdgeType"]
    assert len(data_nodes) == 4 and len(edges) == 3, (
        f"Expected 4 data nodes and 3 edges, got {len(data_nodes)} and {len(edges)}"
    )

    nodes_by_id = {node[0]: node[1] for node in nodes}

    assert str(generate_node_id("John")) in nodes_by_id, "John node not present in the graph."
    assert str(generate_node_id("Jane")) in nodes_by_id, "Jane node not present in the graph."
    assert str(generate_node_id("Company A")) in nodes_by_id, (
        "Company A node not present in the graph."
    )
    assert str(generate_node_id("Company B")) in nodes_by_id, (
        "Company B node not present in the graph."
    )

    edges_by_ids = {f"{edge[0]}_{edge[2]}_{edge[1]}": edge[3] for edge in edges}

    assert (
        f"{str(generate_node_id('John'))}_works_for_{str(generate_node_id('Company A'))}"
        in edges_by_ids
    ), "Edge between John and Company A not present in the graph."
    assert (
        f"{str(generate_node_id('John'))}_works_for_{str(generate_node_id('Company B'))}"
        in edges_by_ids
    ), "Edge between John and Company A not present in the graph."
    assert (
        f"{str(generate_node_id('Jane'))}_works_for_{str(generate_node_id('Company B'))}"
        in edges_by_ids
    ), "Edge between John and Company A not present in the graph."

    # Second data deletion
    await datasets.delete_data(dataset.id, data1.id, user)

    nodes, edges = await graph_engine.get_graph_data()
    remaining_data_nodes = [n for n in nodes if n[1].get("type") != "EdgeType"]
    assert len(remaining_data_nodes) == 2 and len(edges) == 1, (
        f"Expected 2 data nodes and 1 edge after delete, got {len(remaining_data_nodes)} and {len(edges)}"
    )

    nodes_by_id = {node[0]: node[1] for node in nodes}

    assert str(generate_node_id("Jane")) in nodes_by_id, "Jane node not present in the graph."
    assert str(generate_node_id("Company B")) in nodes_by_id, (
        "Company B node not present in the graph."
    )

    edges_by_ids = {f"{edge[0]}_{edge[2]}_{edge[1]}": edge[3] for edge in edges}

    assert (
        f"{str(generate_node_id('Jane'))}_works_for_{str(generate_node_id('Company B'))}"
        in edges_by_ids
    ), "Edge between John and Company A not present in the graph."

    # Second data deletion
    await datasets.delete_data(dataset.id, data2.id, user)

    nodes, edges = await graph_engine.get_graph_data()
    assert len(nodes) == 0 and len(edges) == 0, "Nodes and edges are not deleted."


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
