import asyncio
import xinggraph

DATASET = "demo_dataset"
SESSION = "demo_session"


async def main():
    await xinggraph.forget(everything=True)

    await xinggraph.remember(
        "Einstein developed general relativity.",
        dataset_name=DATASET,
        self_improvement=False,
    )

    await xinggraph.remember(
        "Niels Bohr worked on atomic structure.",
        dataset_name=DATASET,
        session_id=SESSION,
        self_improvement=False,
    )

    answer_before_improve = await xinggraph.recall(
        "What did Bohr work on?",
        datasets=[DATASET],
    )

    await xinggraph.improve(dataset=DATASET, session_ids=[SESSION])

    answer_after_improve = await xinggraph.recall(
        "What did Bohr work on?",
        datasets=[DATASET],
    )
    print("Before improve:", answer_before_improve)

    print("After improve:", answer_after_improve)


if __name__ == "__main__":
    asyncio.run(main())
