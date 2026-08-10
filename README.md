<div align="center">
  <a href="https://github.com/xing-kj/xinggraph">
    <h1>XingGraph</h1>
  </a>

  <br />

  XingGraph - The Open-Source AI Memory Platform for Agents

  <p align="center">
  <a href="https://www.youtube.com/watch?v=8hmqS2Y5RVQ&t=13s">Demo</a>
  .
  <a href="https://docs.xinggraph.ai/">Docs</a>
  .
  <a href="https://xinggraph.ai">Learn More</a>
  ·
  <a href="https://discord.gg/NQPKmU5CCg">Join Discord</a>
  ·
  <a href="https://www.reddit.com/r/AIMemory/">Join r/AIMemory</a>
  .
  <a href="https://github.com/xing-kj/xinggraph-community">Community Plugins & Add-ons</a>
  </p>


  [![GitHub forks](https://img.shields.io/github/forks/xing-kj/xinggraph.svg?style=social&label=Fork&maxAge=2592000)](https://GitHub.com/xing-kj/xinggraph/network/)
  [![GitHub stars](https://img.shields.io/github/stars/xing-kj/xinggraph.svg?style=social&label=Star&maxAge=2592000)](https://GitHub.com/xing-kj/xinggraph/stargazers/)
  [![GitHub commits](https://badgen.net/github/commits/xing-kj/xinggraph)](https://GitHub.com/xing-kj/xinggraph/commit/)
  [![GitHub tag](https://badgen.net/github/tag/xing-kj/xinggraph)](https://github.com/xing-kj/xinggraph/tags/)
  [![Downloads](https://static.pepy.tech/badge/xinggraph)](https://pepy.tech/project/xinggraph)
  [![License](https://img.shields.io/github/license/xing-kj/xinggraph?colorA=00C586&colorB=000000)](https://github.com/xing-kj/xinggraph/blob/main/LICENSE)
  [![Contributors](https://img.shields.io/github/contributors/xing-kj/xinggraph?colorA=00C586&colorB=000000)](https://github.com/xing-kj/xinggraph/graphs/contributors)
  <a href="https://github.com/sponsors/xing-kj"><img src="https://img.shields.io/badge/Sponsor-❤️-ff69b4.svg" alt="Sponsor"></a>

<p>
  <a href="https://trendshift.io/repositories/13955" target="_blank" style="display:inline-block;">
    <img src="https://trendshift.io/api/badge/repositories/13955" alt="xing-kj%2Fxinggraph | Trendshift" width="250" height="55" />
  </a>
</p>

XingGraph is the open-source AI memory platform that gives AI agents persistent long-term memory across sessions. Ingest data in any format, build a self-hosted knowledge graph, and let every agent recall, connect, and act with full context

  <p align="center">
  🌐 This README is also available in:
  :
  <!-- Keep these links. Translations will automatically update with the README. -->
  <a href="https://www.readme-i18n.com/xing-kj/xinggraph?lang=de">Deutsch</a> |
  <a href="https://www.readme-i18n.com/xing-kj/xinggraph?lang=es">Español</a> |
  <a href="https://www.readme-i18n.com/xing-kj/xinggraph?lang=fr">Français</a> |
  <a href="https://www.readme-i18n.com/xing-kj/xinggraph?lang=ja">日本語</a> |
  <a href="README_ko.md">한국어</a> |
  <a href="https://www.readme-i18n.com/xing-kj/xinggraph?lang=pt">Português</a> |
  <a href="https://www.readme-i18n.com/xing-kj/xinggraph?lang=ru">Русский</a> |
  <a href="https://www.readme-i18n.com/xing-kj/xinggraph?lang=zh">中文</a>
  </p>

<p align="center">
  <img src="assets/memory-graph.png" alt="XingGraph Memory Graph" width="80%" />
</p>
</div>

📄 Read the research paper: [Optimizing the Interface Between Knowledge Graphs and LLMs for Complex Reasoning](https://arxiv.org/abs/2505.24478) — XingGraph Contributors et al., 2025


## About XingGraph

XingGraph is an open-source AI memory platform for AI Agents. Ingest data in any format, and XingGraph continuously builds a self-hosted knowledge graph that gives your agents persistent long-term memory across sessions. XingGraph combines vector embeddings, graph reasoning, and cognitive-science-grounded ontology generation to make documents both searchable by meaning and connected by relationships that evolve as your knowledge does.

:star: _Help us reach more developers and grow the xinggraph community. Star this repo!_

:books: _Check our detailed [documentation](https://docs.xinggraph.ai/getting-started/installation#environment-configuration) for setup and configuration._

:crab: _Available as a plugin for your OpenClaw — [xinggraph-openclaw](https://www.npmjs.com/package/@xinggraph/xinggraph-openclaw)_

✴️ _Available as a plugin for your Claude Code — [claude-code-plugin](https://github.com/xing-kj/xinggraph-integrations/tree/main/integrations/claude-code)_

🦀 _Available as a Rust client — [xinggraph-rs](https://github.com/xing-kj/xinggraph-rs)_

🟦 _Available as a TypeScript client — [@xinggraph/xinggraph-ts](https://www.npmjs.com/package/@xinggraph/xinggraph-ts)_



### Why use XingGraph:

- Easily Build Company Brain - unify data from various sources in one place and enable Agents with your domain knowledge
- Knowledge infrastructure — unified ingestion, graph/vector search, runs locally, ontology grounding, multimodal
- Persistent and Learning Agents - learn from feedback, context management, cross-agent knowledge sharing
- Reliable and Trustworthy Agents - agentic user/tenant isolation, traceability, OTEL collector, audit traits

### How it Works

<p align="center">
  <img src="assets/remember.svg" alt="XingGraph Products" width="80%" />
</p>

<p align="center">
  <img src="assets/recall.svg" alt="XingGraph Recall" width="80%" />
</p>

## Basic Usage & Feature Guide

To learn more, [check out this short, end-to-end Colab walkthrough](https://colab.research.google.com/drive/1HRrzIvzcbwrESVfX76wJLKmtIg00SUga?usp=sharing) of XingGraph's core features.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1HRrzIvzcbwrESVfX76wJLKmtIg00SUga?usp=sharing)

## Quickstart

Let’s try XingGraph in just a few lines of code.

### Prerequisites

- Python 3.10 to 3.14

### Step 1: Install XingGraph

You can install XingGraph with **pip**, **poetry**, **uv**, or your preferred Python package manager.

```bash
uv pip install xinggraph
```

### Step 2: Configure the LLM
```python
import os
os.environ["LLM_API_KEY"] = "YOUR OPENAI_API_KEY"
```
Alternatively, create a `.env` file using our [template](https://github.com/xing-kj/xinggraph/blob/main/.env.template).

To integrate other LLM providers, see our [LLM Provider Documentation](https://docs.xinggraph.ai/setup-configuration/llm-providers).

### Step 3: Run the Pipeline

XingGraph's API gives you four operations — `remember`, `recall`, `forget`, and `improve`:

```python
import xinggraph
import asyncio


async def main():
    # Store permanently in the knowledge graph (runs add + cognify + improve)
    await xinggraph.remember("XingGraph turns documents into AI memory.")

    # Store in session memory (fast cache, syncs to graph in background)
    await xinggraph.remember("User prefers detailed explanations.", session_id="chat_1")

    # Query with auto-routing (picks best search strategy automatically)
    results = await xinggraph.recall("What does XingGraph do?")
    for result in results:
        print(result)

    # Query session memory first, fall through to graph if needed
    results = await xinggraph.recall("What does the user prefer?", session_id="chat_1")
    for result in results:
        print(result)

    # Delete when done
    await xinggraph.forget(dataset="main_dataset")


if __name__ == '__main__':
    asyncio.run(main())

```

### Use the XingGraph CLI

```bash
xinggraph-cli remember "XingGraph turns documents into AI memory."

xinggraph-cli recall "What does XingGraph do?"

xinggraph-cli forget --all
```

To open the local UI, run:
```bash
xinggraph-cli -ui
```

> **Note:** The MCP server launched by `xinggraph-cli -ui` runs inside a Docker container.
> Docker Desktop, Colima, or any OCI-compatible runtime with a working `docker` CLI is
> required. See [Docker & Colima Setup](docs/docker-colima-setup.md) for details.

## Run with Docker

Prefer containers? XingGraph publishes prebuilt images to Docker Hub on every push to `main`:
[`xinggraph/xinggraph`](https://hub.docker.com/r/xinggraph/xinggraph) (the API server) and
[`xinggraph/xinggraph-mcp`](https://hub.docker.com/r/xinggraph/xinggraph-mcp) (the MCP server).

### Option A — Docker Compose (build from source)

Clone the repo, create a `.env` with at least `LLM_API_KEY`, then:

```bash
cp .env.template .env   # then edit .env and set LLM_API_KEY

# Start the API server (http://localhost:8000)
docker compose up

# Optional profiles (combine as needed):
docker compose --profile ui up        # + frontend on http://localhost:3000
docker compose --profile mcp up       # + MCP server on http://localhost:8001
docker compose --profile postgres up  # + Postgres/PGVector
docker compose --profile neo4j up     # + Neo4j
```

> The `xinggraph` and `xinggraph-mcp` services publish different host ports (`8000` vs `8001`),
> so you can run both at once.

### Option B — Pull the prebuilt image (no clone required)

```bash
# Create a minimal .env in the current directory
echo 'LLM_API_KEY="YOUR_OPENAI_API_KEY"' > .env

# API server
docker run --env-file ./.env -p 8000:8000 --rm -it xinggraph/xinggraph:main

# MCP server (HTTP transport)
docker pull xinggraph/xinggraph-mcp:main
docker run -e TRANSPORT_MODE=http --env-file ./.env -p 8000:8000 --rm -it xinggraph/xinggraph-mcp:main
```

See the [MCP server README](xinggraph-mcp/README.md) for SSE/stdio transports, optional
extras, and MCP client configuration.

## Use with AI Agents

### Claude Code

Install the [XingGraph memory plugin](https://github.com/xing-kj/xinggraph-integrations/tree/main/integrations/claude-code) to give Claude Code persistent memory across sessions. The plugin captures prompts, tool traces, and assistant responses into session memory, injects relevant context on every prompt, and syncs session memory into the permanent knowledge graph at session end.

**Install** from the Claude Code marketplace. The recommended way is from your shell, *before* launching Claude Code, so the first `claude` launch is a clean session that bootstraps memory automatically:

```bash
# Add the marketplace and install the plugin (one-time, user-scoped)
claude plugin marketplace add xing-kj/xinggraph-integrations
claude plugin install xinggraph-memory@xinggraph

# Set env vars for your mode (see below), then launch
export LLM_API_KEY="sk-..."   # local mode; or XINGGRAPH_BASE_URL + XINGGRAPH_API_KEY for cloud
claude
```

**Local mode** (default) — the plugin bootstraps a local XingGraph API at `http://localhost:8011`. Only `LLM_API_KEY` is required; the XingGraph API key is auto-minted if absent:

```bash
export LLM_API_KEY="sk-..."
```

**XingGraph Cloud or a remote server** — set both:

```bash
export XINGGRAPH_BASE_URL="https://your-instance.xinggraph.ai"
export XINGGRAPH_API_KEY="ck_..."
```

On startup you should see a "XingGraph Memory Connected" system message.

The plugin hooks into Claude Code's lifecycle — `SessionStart` selects mode and sets up identity, `UserPromptSubmit` injects dataset-scoped context, `PostToolUse` captures tool traces, `Stop` writes the assistant's answer, `PreCompact` preserves memory across context resets, and `SessionEnd` triggers the final sync into the permanent graph.

See the [plugin README](https://github.com/xing-kj/xinggraph-integrations/tree/main/integrations/claude-code) for sessions, datasets, and full configuration.

### Connect to XingGraph Cloud

Point any Python agent at a managed XingGraph instance — all SDK calls route to the cloud:

```python
import xinggraph

await xinggraph.serve(url="https://your-instance.xinggraph.ai", api_key="ck_...")

await xinggraph.remember("important context")
results = await xinggraph.recall("what happened?")

await xinggraph.disconnect()
```

## Examples

Browse more examples in the [`examples/`](examples/) folder — demos, guides, custom pipelines, and database configurations.

**Use Case 1 — Customer Support Agent**

```python
Goal: Resolve customer issues using their personal data across finance, support, and product history.

User: "My invoice looks wrong and the issue is still not resolved."

XingGraph tracks: past interactions, failed actions, resolved cases, product history

# Agent response:
Agent: "I found 2 similar billing cases resolved last month.
        The issue was caused by a sync delay between payment
        and invoice systems — a fix was applied on your account."

# What happens under the hood:
- Unifies data sources from various company channels
- Reconstructs the interaction timeline and tracks outcomes
- Retrieves similar resolved cases
- Maps to the best resolution strategy
- Updates memory after execution so the agent never repeats the same mistake
```

**Use Case 2 — Expert Knowledge Distillation (SQL Copilot)**

```python
Goal: Help junior analysts solve tasks by reusing expert-level queries, patterns, and reasoning.

User: "How do I calculate customer retention for this dataset?"

XingGraph tracks: expert SQL queries, workflow patterns, schema structures, successful implementations

# Agent response:
Agent: "Here's how senior analysts solved a similar retention query.
        XingGraph matched your schema to a known structure and adapted
        the expert's logic to fit your dataset."

# What happens under the hood:
- Extracts and stores patterns from expert SQL queries and workflows
- Maps the current schema to previously seen structures
- Retrieves similar tasks and their successful implementations
- Adapts expert reasoning to the current context
- Updates memory with new successful patterns so junior analysts perform at near-expert level
```

## Run the Whole Memory Layer on Postgres

Graph memory traditionally means operating a stack — a graph database for relationships, a vector database for embeddings, Redis for sessions, and a relational database for metadata — all deployed, secured, and paid for before an agent remembers anything. In xinggraph 1.0 you can run the entire memory layer on a single Postgres instance.

| Memory layer | Traditional stack | xinggraph on Postgres |
| --- | --- | --- |
| Relationships | Neo4j or another graph database | xinggraph's Postgres graph backend |
| Embeddings | Dedicated vector database | pgvector |
| Sessions | Redis | SQL session-cache backend |
| Metadata | Relational database | same Postgres |

The graph still exists — it just lives inside the same Postgres-backed memory layer as the text, metadata, and embeddings, so retrieval moves between similarity and structure without crossing service boundaries. In our CI benchmarks, Postgres search ran ~10% faster than the separate graph-plus-vector setup.

Postgres is the default we recommend for most deployments, but you can still swap in dedicated backends when a workload needs them (Neo4j and Neptune for graphs, Redis for sessions, pgvector and LanceDB for vectors, plus Qdrant, ChromaDB, Weaviate, and Milvus via community adapters). Local development stays fully embedded — SQLite, LanceDB, and Kuzudb — with no extra services to stand up.

```bash
pip install "xinggraph[postgres]"
```

```bash
DB_PROVIDER=postgres
VECTOR_DB_PROVIDER=pgvector
GRAPH_DATABASE_PROVIDER=postgres
CACHE_BACKEND=postgres

DB_HOST=localhost
DB_PORT=5432
DB_USERNAME=xinggraph
DB_PASSWORD=xinggraph
DB_NAME=xinggraph_db
```

## Deploy XingGraph

Use [XingGraph Cloud](https://www.xinggraph.ai) for a fully managed experience, or self-host with one of the 1-click deployment configurations below.

| Platform | Best For | Command |
|----------|----------|---------|
| **XingGraph Cloud** | Managed service, no infrastructure to maintain | [Sign up](https://www.xinggraph.ai) or `await xinggraph.serve()` |
| **Modal** | Serverless, auto-scaling, GPU workloads | `bash distributed/deploy/modal-deploy.sh` |
| **Railway** | Simplest PaaS, native Postgres | `railway init && railway up` |
| **Fly.io** | Edge deployment, persistent volumes | `bash distributed/deploy/fly-deploy.sh` |
| **Render** | Simple PaaS with managed Postgres | Deploy to Render button |
| **Daytona** | Cloud sandboxes (SDK or CLI) | See `distributed/deploy/daytona_sandbox.py` |
| **Islo** | Isolated cloud sandboxes (SDK) | See `distributed/deploy/islo_sandbox.py` |

See the [`distributed/`](distributed/) folder for deploy scripts, worker configurations, and additional details.

## Use XingGraph in Other Languages

Prefer something other than Python? XingGraph also ships official clients for Rust and TypeScript.

### Getting Started with Rust

Use the [xinggraph-rs](https://github.com/xing-kj/xinggraph-rs) crate to add, cognify, and search from Rust.

```bash
cargo add xinggraph
```

See the [xinggraph-rs repository](https://github.com/xing-kj/xinggraph-rs) for full setup and examples.

### Getting Started with TypeScript

Use the [@xinggraph/xinggraph-ts](https://www.npmjs.com/package/@xinggraph/xinggraph-ts) package to add, cognify, and search from Node.js or the browser.

```bash
npm install @xinggraph/xinggraph-ts
```

See the [@xinggraph/xinggraph-ts package](https://www.npmjs.com/package/@xinggraph/xinggraph-ts) for full setup and examples.

## Benchmarks

We ran xinggraph against [BEAM](https://github.com/mohammadtavakoli78/BEAM), a long-context benchmark that tests whether a system can keep track of a long conversation as it changes — a more useful test for agent memory than typical needle-in-a-haystack benchmarks. Using only xinggraph's default settings and standard open-source features (no custom models, no BEAM-specific pipelines), we beat the previous state of the art at the 100K-token setting and matched it at 10M tokens.

| Benchmark | Setting | xinggraph | Previous SOTA | Obsidian / RAG baseline |
|-----------|---------|--------|---------------|--------------------------|
| BEAM | 100K tokens | **0.79** (>0.8 with per-question routing) | 0.735 | ~0.33 |
| BEAM | 10M tokens | **0.67** | 0.641 | ~0.33 |

These numbers are a directional signal rather than a definitive measure — see the [BEAM preliminary report](xinggraph/eval_framework/beam/REPORT.md) for the full methodology, caveats, and what the results actually mean.

## Latest News

[![Watch Demo](https://img.youtube.com/vi/8hmqS2Y5RVQ/maxresdefault.jpg)](https://www.youtube.com/watch?v=8hmqS2Y5RVQ&t=13s)


## Community & Support

### Contributing
We welcome contributions from the community! Your input helps make XingGraph better for everyone. See [`CONTRIBUTING.md`](CONTRIBUTING.md) to get started.

### Code of Conduct

We're committed to fostering an inclusive and respectful community. Read our [Code of Conduct](https://github.com/xing-kj/xinggraph/blob/main/CODE_OF_CONDUCT.md) for guidelines.

## Research & Citation

We recently published a research paper on optimizing knowledge graphs for LLM reasoning:

```bibtex
@misc{xinggraph2025optimizinginterfaceknowledgegraphs,
      title={Optimizing the Interface Between Knowledge Graphs and LLMs for Complex Reasoning},
      author={XingGraph Contributors},
      year={2025},
      eprint={2505.24478},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2505.24478},
}
```
