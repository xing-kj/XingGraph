import xinggraph
from xinggraph.shared.logging_utils import get_logger, ERROR
from typing import Optional, Tuple, List, Dict, Union, Any, Callable, Awaitable

from xinggraph.eval_framework.benchmark_adapters.benchmark_adapters import BenchmarkAdapter
from xinggraph.modules.chunking.TextChunker import TextChunker
from xinggraph.modules.pipelines.tasks.task import Task
from xinggraph.modules.pipelines import run_pipeline

logger = get_logger(level=ERROR)


class CorpusBuilderExecutor:
    def __init__(
        self,
        benchmark: Union[str, Any] = "Dummy",
        task_getter: Callable[..., Awaitable[List[Task]]] = None,
    ) -> None:
        if isinstance(benchmark, str):
            try:
                adapter_enum = BenchmarkAdapter(benchmark)
            except ValueError:
                raise ValueError(f"Unsupported benchmark: {benchmark}")
            self.adapter = adapter_enum.adapter_class()
        else:
            self.adapter = benchmark

        self.raw_corpus = None
        self.questions = None
        self.task_getter = task_getter

    def load_corpus(
        self,
        limit: Optional[int] = None,
        load_golden_context: bool = False,
        instance_filter: Optional[Union[str, List[str], List[int]]] = None,
    ) -> Tuple[List[Dict], List[str]]:
        self.raw_corpus, self.questions = self.adapter.load_corpus(
            limit=limit, load_golden_context=load_golden_context, instance_filter=instance_filter
        )
        return self.raw_corpus, self.questions

    async def build_corpus(
        self,
        limit: Optional[int] = None,
        chunk_size=1024,
        chunker=TextChunker,
        load_golden_context: bool = False,
        instance_filter: Optional[Union[str, List[str], List[int]]] = None,
    ) -> List[str]:
        await self.adapter.prepare_corpus()
        self.load_corpus(
            limit=limit, load_golden_context=load_golden_context, instance_filter=instance_filter
        )
        await self.run_xinggraph(chunk_size=chunk_size, chunker=chunker)
        return self.questions

    async def run_xinggraph(self, chunk_size=1024, chunker=TextChunker) -> None:
        await xinggraph.prune.prune_data()
        await xinggraph.prune.prune_system(metadata=True)

        # Benchmarks such as HotpotQA can repeat the same context passage across
        # multiple questions. Deduplicate before ingestion to avoid racing inserts
        # of the same deterministic Data.id during batched add() processing.
        unique_corpus = list(dict.fromkeys(self.raw_corpus))

        await xinggraph.add(unique_corpus)

        tasks = await self.task_getter(chunk_size=chunk_size, chunker=chunker)
        pipeline_run = run_pipeline(tasks=tasks)

        async for run_info in pipeline_run:
            print(run_info)
