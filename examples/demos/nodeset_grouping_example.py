import asyncio
import os

import xinggraph
from xinggraph import visualize_graph
from xinggraph.shared.logging_utils import ERROR, setup_logging

text_a = """
    AI is revolutionizing financial services through intelligent fraud detection
    and automated customer service platforms.
    """

text_b = """
    Advances in AI are enabling smarter systems that learn and adapt over time.
    """

text_c = """
    MedTech startups have seen significant growth in recent years, driven by innovation
    in digital health and medical devices.
    """

node_set_a = ["AI", "FinTech"]
node_set_b = ["AI"]
node_set_c = ["MedTech"]


async def main():
    await xinggraph.forget(everything=True)

    await xinggraph.remember(text_a, node_set=node_set_a, self_improvement=False)
    await xinggraph.remember(text_b, node_set=node_set_b, self_improvement=False)
    await xinggraph.remember(text_c, node_set=node_set_c, self_improvement=False)

    visualization_path = os.path.join(
        os.path.dirname(__file__), ".artifacts", "nodeset_grouping.html"
    )
    await visualize_graph(visualization_path)


if __name__ == "__main__":
    logger = setup_logging(log_level=ERROR)
    asyncio.run(main())
