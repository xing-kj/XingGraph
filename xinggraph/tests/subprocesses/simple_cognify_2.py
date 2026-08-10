import asyncio

import xinggraph
from xinggraph.api.v1.search import SearchType
from xinggraph.shared.logging_utils import INFO, setup_logging
from common import configure_xinggraph_for_subprocess


async def main():
    configure_xinggraph_for_subprocess(xinggraph)

    await xinggraph.cognify(datasets=["second_cognify_dataset"])

    query_text = (
        "Tell me what is in the context. Additionally write out 'SECOND_COGNIFY' before your answer"
    )
    search_results = await xinggraph.search(
        query_type=SearchType.GRAPH_COMPLETION,
        query_text=query_text,
        datasets=["second_cognify_dataset"],
    )

    print("Search results:")
    for result_text in search_results:
        print(result_text)


if __name__ == "__main__":
    setup_logging(log_level=INFO)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
