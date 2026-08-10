from xinggraph.modules.graph.xinggraph_graph.XingGraphGraph import XingGraphGraph


async def extract_subgraph(subgraphs: list[XingGraphGraph]):
    for subgraph in subgraphs:
        for edge in subgraph.edges:
            yield edge
