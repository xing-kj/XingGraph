import asyncio
import os
from dataclasses import dataclass
from typing import Any, List, Dict, Optional

from dotenv import load_dotenv
import xinggraph
from xinggraph.api.v1.search import SearchType

from .qa_benchmark_base import QABenchmarkRAG, QABenchmarkConfig
from xinggraph.eval_framework.benchmark_adapters.hotpot_qa_adapter import HotpotQAAdapter
from xinggraph.eval_framework.corpus_builder.corpus_builder_executor import CorpusBuilderExecutor
from xinggraph.eval_framework.answer_generation.answer_generation_executor import (
    retriever_options,
)
from xinggraph.eval_framework.corpus_builder.task_getters.TaskGetters import TaskGetters

load_dotenv()


@dataclass
class XingGraphConfig(QABenchmarkConfig):
    """Configuration for XingGraph QA benchmark using eval framework."""

    # Dataset parameters
    dataset_name: str = "hotpot_qa_dataset"

    # Eval framework parameters
    benchmark: str = "HotPotQA"
    qa_engine: str = "xinggraph_graph_completion"
    task_getter_type: str = "Default"
    chunk_size: int = 1024
    top_k: int = 5
    system_prompt_path: str = "answer_simple_question_benchmark2.txt"

    # Search parameters (fallback if not using eval framework)
    search_type: SearchType = SearchType.GRAPH_COMPLETION

    # Clean slate on initialization
    clean_start: bool = True

    # Default results file
    results_file: str = "hotpot_qa_xinggraph_results.json"


class QABenchmarkXingGraph(QABenchmarkRAG):
    """XingGraph implementation of QA benchmark using eval framework components."""

    def __init__(self, corpus, qa_pairs, config: XingGraphConfig):
        super().__init__(corpus, qa_pairs, config)
        self.config: XingGraphConfig = config
        self.corpus_builder = None
        self.retriever = None

    @classmethod
    def from_jsons(
        cls, qa_pairs_file: str, instance_filter_file: str, config: XingGraphConfig
    ) -> "QABenchmarkXingGraph":
        """Create benchmark instance using HotpotQA adapter instead of raw JSON loading."""
        print("Loading data using HotpotQA adapter...")

        # Use HotpotQA adapter to load corpus and questions
        adapter = HotpotQAAdapter()

        # Load instance filter
        import json

        with open(instance_filter_file, "r") as f:
            instance_filter = json.load(f)

        # Load corpus with proper limits and instance filter
        corpus_limit = config.corpus_limit
        qa_limit = config.qa_limit

        corpus, qa_pairs = adapter.load_corpus(
            limit=max(corpus_limit, qa_limit)
            if corpus_limit and qa_limit
            else (corpus_limit or qa_limit),
            load_golden_context=True,  # Include golden context for evaluation
            instance_filter=instance_filter,
        )

        print(f"Loaded {len(corpus)} documents and {len(qa_pairs)} QA pairs from HotpotQA adapter")

        return cls(corpus, qa_pairs, config)

    async def initialize_rag(self) -> Any:
        """Initialize XingGraph system with eval framework components."""
        if self.config.clean_start:
            # Create a clean slate for xinggraph
            await xinggraph.prune.prune_data()
            await xinggraph.prune.prune_system(metadata=True)

        # Initialize corpus builder
        try:
            task_getter = TaskGetters(self.config.task_getter_type).getter_func
        except KeyError:
            raise ValueError(f"Invalid task getter type: {self.config.task_getter_type}")

        self.corpus_builder = CorpusBuilderExecutor(
            benchmark=self.config.benchmark,
            task_getter=task_getter,
        )

        # Initialize retriever
        self.retriever = retriever_options[self.config.qa_engine](
            top_k=self.config.top_k, system_prompt_path=self.config.system_prompt_path
        )

        print(
            f"Initialized XingGraph with {self.config.qa_engine} retriever (top_k={self.config.top_k}, system_prompt={self.config.system_prompt_path})"
        )
        return "xinggraph_initialized"

    async def cleanup_rag(self) -> None:
        """Clean up resources."""
        pass

    async def insert_document(self, document: str, document_id: int) -> None:
        """Insert document into XingGraph via corpus builder."""
        # Documents are handled in bulk by load_corpus_to_rag method
        pass

    async def load_corpus_to_rag(self) -> None:
        """Load corpus data into XingGraph using eval framework's corpus builder."""
        if not self.corpus_builder:
            raise RuntimeError("Corpus builder not initialized. Call initialize_rag() first.")

        print(f"Building corpus using eval framework with {len(self.corpus)} documents...")

        # Set the corpus data in the builder
        self.corpus_builder.raw_corpus = self.corpus
        self.corpus_builder.questions = self.qa_pairs

        # Run xinggraph pipeline to process documents
        await self.corpus_builder.run_xinggraph(chunk_size=self.config.chunk_size)

        print("Corpus building completed using eval framework")

    async def query_rag(self, question: str) -> str:
        """Query XingGraph using eval framework's retriever."""
        if not self.retriever:
            raise RuntimeError("Retriever not initialized. Call initialize_rag() first.")

        try:
            # Get completion (retriever handles context internally)
            search_results = await self.retriever.get_completion(question)

            # Return the first result (main answer)
            if search_results and len(search_results) > 0:
                return str(search_results[0])
            else:
                return "No relevant information found."

        except Exception as e:
            print(f"Error during retrieval: {e}")
            return f"Error: {str(e)}"

    @property
    def system_name(self) -> str:
        """Return system name."""
        return f"XingGraph-{self.config.qa_engine}"


if __name__ == "__main__":
    # Example usage
    config = XingGraphConfig(
        corpus_limit=5,  # Small test
        qa_limit=3,
        qa_engine="xinggraph_graph_completion",
        task_getter_type="Default",
        print_results=True,
        clean_start=True,
    )

    benchmark = QABenchmarkXingGraph.from_jsons(
        qa_pairs_file="hotpot_qa_24_qa_pairs.json",  # HotpotQA adapter will load data
        instance_filter_file="hotpot_qa_24_instance_filter.json",  # Instance filter for specific questions
        config=config,
    )

    results = benchmark.run()
