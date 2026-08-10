from xinggraph.modules.graph.xinggraph_graph.XingGraphGraph import XingGraphGraph


async def extract_subgraph_chunks(subgraphs: list[XingGraphGraph]):
    """
    Get all Document Chunks from subgraphs and forward to next task in pipeline
    """
    for subgraph in subgraphs:
        for node in subgraph.nodes.values():
            if node.attributes["type"] == "DocumentChunk":
                yield node.attributes["text"]
