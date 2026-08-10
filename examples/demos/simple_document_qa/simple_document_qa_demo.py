# ruff: noqa: E402
import asyncio
import os

# By default xinggraph uses OpenAI's gpt-5-mini LLM model
# Provide your OpenAI LLM API KEY, in case you did not set it in the .env file
# Set this before importing XingGraph so XingGraph reads the example value instead of defaults or .env settings.
# os.environ["LLM_API_KEY"] = ""

import xinggraph


async def xinggraph_demo():
    # Get file path to document to process
    from pathlib import Path

    current_directory = Path(__file__).resolve().parent
    file_path = os.path.join(current_directory, "data", "alice_in_wonderland.txt")

    await xinggraph.forget(everything=True)

    # Call XingGraph to process document
    await xinggraph.remember(file_path, self_improvement=False)

    # Query XingGraph for information from provided document
    answer = await xinggraph.recall("List me all the important characters in Alice in Wonderland.")
    print(answer)

    answer = await xinggraph.recall("How did Alice end up in Wonderland?")
    print(answer)

    answer = await xinggraph.recall("Tell me about Alice's personality.")
    print(answer)


# XingGraph is an async library, it has to be called in an async context
if __name__ == "__main__":
    asyncio.run(xinggraph_demo())
