<p align="center">
  <img src="assets/banner.svg" width="100%" alt="XingGraph — Knowledge-Graph RAG" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-6b4fb0?logo=python&logoColor=white&style=for-the-badge" alt="Python"/>
  <img src="https://img.shields.io/badge/Neo4j-GraphDB-4f7bdd?logo=neo4j&logoColor=white&style=for-the-badge" alt="Neo4j"/>
  <img src="https://img.shields.io/badge/GraphRAG-Knowledge--Graph-a974ff?style=for-the-badge" alt="GraphRAG"/>
  <img src="https://img.shields.io/badge/Ontology-RDF%2FOWL-a974ff?style=for-the-badge" alt="Ontology"/>
  <img src="https://img.shields.io/badge/MCP-Model--Context--Protocol-6b4fb0?logo=modelcontextprotocol&logoColor=white&style=for-the-badge" alt="MCP"/>
  <img src="https://img.shields.io/badge/FastAPI-API-4f7bdd?logo=fastapi&logoColor=white&style=for-the-badge" alt="FastAPI"/>
</p>

<p align="center">
  <img src="assets/principles-ring.svg" width="100%" alt="XingGraph 七项设计原则" />
</p>

# XingGraph

知识图谱驱动的 AI 记忆与检索系统 — 让 LLM 从「文档堆」进化到「会回答、会对比、会溯源，还给你看证据」。
_AI memory & retrieval engine built on a knowledge graph — from raw documents to answers that compare, cross-reference, and show their sources._

> 核心亮点 / Highlights
>
> - **WIKI 多主体渐进式检索** (`WIKI_COMPLETION`)：把一句"软件测评式"提问自动拆成多个主体，实体锚定 → 图遍历 → Wiki 汇总 → LLM 筛选 → 回答，支持跨主体横向对比。
> - **structured_doc 结构化建图**：按 PDF 解析后的 `Doc N/total` 结构切块入图，保留标题层级；回答时自动启用**标题归因** prompt，引用来源章节而非原始 wrapper 头。
> - **model_hop 产品型号定向跳转**：只沿 `is_product → is_a PRODUCT_MODEL` 走，问一个型号绝不扩散到姊妹型号。
> - **`search_type: null` 自动路由** + 会话缓存 / 多租户隔离 / 全程检索 trace。

---

## 目录 / Contents

- [七项设计原则](#七项设计原则--seven-design-principles)
- [核心特性](#核心特性--core-features)
- [一个例子看懂它](#一个例子看懂它--one-example-to-see-it)
- [工作原理](#工作原理--how-it-works)
- [为什么比 GraphRAG / 纯 LLM-wiki 更优](#为什么比-graphrag--纯-llm-wiki-更优--why-its-better-than-graphrag-and-vectorless-llmwiki)
- [安装](#安装--installation)
- [快速开始（CLI）](#快速开始cli--quickstart)
- [⭐ WIKI 多主体搜索](#-wiki-多主体搜索--wiki-multi-subject-search)
- [⭐ structured_doc 建图与标题归因](#-structured_doc-建图与标题归因--graph-building-with-title-attribution)
- [API 速查](#api-速查--api-reference)
- [项目结构](#项目结构--project-structure)
- [开发命令](#开发命令--development)

---

## 七项设计原则 / Seven Design Principles

| Principle | What it means |
|---|---|
| 🔍 可观测 | 每步检索写入结构化 trace，可实时盯住跳转路径 |
| 📌 可回溯 | 回答带标题归因 + references，指回原文章节 |
| 🎛 可控制 | 路由 / scope / 节点过滤 / 开关全可接管 |
| 🧩 可扩展 | RDF/OWL 本体即扩展点，业务术语可扩充 |
| 🌱 可进化 | 自建提示词与切分方式 + 反馈影响检索权重 |
| 💰 省 token | subject 文档白名单硬过滤，他文不入上下文 |
| 🛡 少幻觉 | 答案绑定原文 chunk，回传参考片段 |

---

## 核心特性 / Core Features

| 能力 | 说明 | 入口 |
|---|---|---|
| **WIKI 多主体搜索** | Step0 LLM 抽取主体+属性 → Step1 实体锚定 → Step2 `Entity→Chunk→Wiki` 图遍历 → Step3 Wiki 向量扩展 → Step4 LLM 筛选 → Step5 回答。多主体查询自动放宽 `top_k`，支持横向对比。 | `search_type=WIKI_COMPLETION` |
| **structured_doc 建图** | 识别 PDF 解析 wrapper（`Doc N/total ... titles=[...]`）逐块入库，标题层级写入 chunk 元数据。 | `--chunker structured_doc` |
| **标题归因回答** | 检测到数据集用 structured_doc 建图后，自动切换专用 system prompt，回答引用文档小标题而非 wrapper 头。 | 自动，无需手工配置 |
| **model_hop** | 沿产品→型号边定向跳转，型号自锚定时只返回自身，避免扩展到兄弟型号。 | WIKI 检索内置分支 |
| **自动路由** | `search_type: null` 时按查询内容选最优策略；会话命中时短路图搜索。 | `xinggraph.recall` 默认行为 |
| **会话/多租户** | `--user-id` 多 agent 隔离，session 缓存、trace 全程记录。 | CLI / API |

---

## 一个例子看懂它 / One Example to See It

把一份**医院智慧药房投标文档**（PDF → 结构化解析 → 入图），然后问一句多主体对比问题。

```
Q: 对比 A 型号储药发药一体机 与 B 型号 的差异，以及与现有 HIS 系统的对接方式
```

**纯文本检索（无向量 LLM-wiki 类）** 只会答到：*"A 型号储药发药一体机是 …"* — 丢了 B、丢了 HIS，没有对比。

**XingGraph WIKI 渐进式检索**：

1. **Step0 拆主体** → `subjects: [A, B, HIS]`，`attributes: [差异, 对接方式]` → 多主体自动把 `top_k` 从 8 提到 `max(15, 3×5)=15`
2. **Step1 实体锚定** → 三个主体各自在图里找到锚点，subject 永不过滤
3. **Step2 图遍历** → 沿 `Entity→Chunk→Wiki` 把三者的章节级摘要拉进来
4. **Step4 LLM 筛选** → 只留真正能回答差异/对接的 wiki
5. **Step5 回答** → 输出结构化的对比 + 每条引用章节小标题

**你实际看到的图谱**（示意）：
<!-- TODO: 替换为你的图谱截图，路径 assets/demo/graph-demo.png -->
<img src="assets/demo/graph-demo.png" alt="知识图谱效果图" width="720px"/>

**一次真实问答的链路**（示意）：
<!-- TODO: 替换为你的问答截图，路径 assets/demo/qa-demo.png -->
<img src="assets/demo/qa-demo.png" alt="问答链路效果图" width="720px"/>

> 中文备注：上图是你贴效果图的位置。README 渲染时 GitHub 会自动按 `assets/demo/*.png` 的相对路径展示；把两张截图放进该目录即可。

---

## 工作原理 / How It Works

### 建图管线 / Graph construction

```mermaid
flowchart LR
    subgraph INGEST[Ingest 数据入图]
        A[文档 / 投标文件 PDF] --> B[PDF 结构化解析 wrap 成 Doc 块]
        B --> C[xinggraph.add / remember];
        C --> D[xinggraph.cognify];
        D --> E{chunker 策略};
        E -->|--chunker structured_doc| F[StructuredDocChunker];
        E -->|TextChunker 等| G[常规切块];
        F --> H["逐块入库 · 保留标题层级 metadata"];
        G --> I[实体抽取 Entity · 关系建边];
        H --> J[(Neo4j / 图存储)];
        I --> J;
    end
    subgraph GRAPH[Knowledge Graph]
        J --> K[Entity · DocumentChunk · Wiki 节点与边];
    end
```

结构化 PDF 的 wrapper 格式（由 PDF 解析器产生）：

```
Doc 1/5: len=4123, titles=[第一章 总体设计, 1.1 系统架构]
--- 内容开始 ---
<章节正文>
--- 内容结束 ---
```

`StructuredDocChunker` 每块逐字保留 wrapper 原文，`titles` 层级、`doc_index`、`total_docs` 全部进入元数据，回答阶段可据此做精确标题归因。

### WIKI 渐进式检索 / Progressive retrieval pipeline

```mermaid
flowchart TB
    Q["用户提问<br/>(多主体对比)"] --> S0;
    subgraph STEP0_1[Step 0–1 · 理解与锚定]
        S0["Step 0 LLM 抽取<br/>subjects + attributes<br/>(属性绑定主体)"];
        S0 --> S1["Step 1 实体锚定<br/>subject 永不过滤 + 句子级匹配"];
        S1 -.可并行分支.-> MH["model_hop<br/>产品→型号定向跳转"];
        MH -.合并去重.-> S2;
    end
    S1 --> S2["Step 2 图遍历<br/>Entity → Chunk → Wiki"];
    subgraph STEP2_5[Step 2–5 · 检索与回答]
        S2 --> S3["Step 3 Wiki 向量扩展(可选)"];
        S3 --> S4["Step 4 LLM Wiki 筛选<br/>只留能答的"];
        S4 --> S5["Step 5 回答生成<br/>结构化对比 + 标题归因引用"];
    end
    S5 --> out["输出 trace + 引用来源"];
```

- 多主体查询（`subjects > 1`）自动把 `entity_top_k` 从 `8` 提至 `max(15, n×5)`，每个主体都有独立候选池，不会"只答到最大主体"。
- 每个 retrieval 回传结构化 `trace`：`step0_llm_entities`（subjects/attributes）可被会话缓存复用，实现二次检索短路。

---

## 为什么比 GraphRAG / 纯 LLM-wiki 更优 / Why It's Better

| 维度 | 纯 GraphRAG（微软式社区摘要） | 无向量 LLM-wiki 检索 | :star: xinggraph WIKI 渐进式 |
|---|---|---|---|
| **成本** | 全库 LLM 抽取 + 社区检测，一次可能烧大量 token | 低，但只做字面匹配 | 按需渐进，LLM 只在筛选/回答阶段使用，省 token |
| **多主体对比** | 社区摘要易漏主体，对比全靠碰运气 | 纯文本匹配，无法横向对比 | **显式 subjects+attributes 抽取**，top_k 按主体数自动放大，结构化输出对比 |
| **归因溯源** | 社区摘要，指不到具体章节 | 无结构，无法给出来源层级 | structured_doc 保留标题层级 → 回答引用「第一章/1.3」级标题 |
| **语义一跳** | 有社区跳转，但粒度粗 | 无图，无多跳关系 | 实体锚定 + `model_hop` 精确沿产品→型号边走，型号自锚定不扩散 |
| **可观测性** | 弱，黑盒 | 无 trace | **全流程结构化 trace**（step0 主体/属性 → 每步命中） |
| **语义召回** | 向量 | 仅字面 | 实体向量锚定 + Wiki 向量扩展（可选），字面+语义双保险 |

一段话总结：

> 纯 GraphRAG 用"全局离线摘要"换全局问题能力，代价是贵、慢、难溯源；无向量 LLM-wiki 用"省事"换掉多跳与对比能力，容易漏主体、答不齐。
> XingGraph 取中间路线：**实体锚定 + 图遍历 + Wiki 向量扩展 + LLM 筛选** 走有向的、可观测的、按需加深的检索路径 —— 问得越具体，路走得越省；问得越宽（多主体），自动加深加宽，还能把每一步的证据链还给你。

---

## 安装 / Installation

要求 Python >= 3.10 且 < 3.14，推荐 `uv`：

```bash
uv sync --dev --all-extras --reinstall
```

> 中文备注：LLM service 配置（api_key / model / endpoint）在你的配置文件或环境变量里设置；按仓库里的配置模板初始化后即可启动。

---

## 快速开始（CLI）/ Quickstart

```bash
uv run xinggraph-cli add "XingGraph turns documents into AI memory."
uv run xinggraph-cli cognify
uv run xinggraph-cli search "What does xinggraph do?"
uv run xinggraph-cli recall "Compare platform A vs B" --search-type WIKI_COMPLETION
```

常用子命令：`add` / `remember` / `cognify` / `search` / `recall` / `memify` / `forget` / `delete` / `serve`。

> 中文备注：`search` 是通用检索；`recall` 是面向记忆的回答式入口，`search_type` 留空时自动选最优策略。

---

## ⭐ WIKI 多主体搜索 / Wiki Multi-subject Search

对"多主体、要对比、要溯源"的问题最有效。HTTP 直接指定：

```bash
curl -X POST http://localhost:8000/v1/recall \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "search_type": "WIKI_COMPLETION",
    "query": "对比 A 卡奥斯工业互联网平台 与 B 卡奥斯的差异,以及与 C 的关系",
    "top_k": 15,
    "include_references": true
  }'
```

Python SDK：

```python
import asyncio
import xinggraph


async def main():
    results = await xinggraph.recall(
        query="对比三家企业的多智能体体系差异",
        search_type="WIKI_COMPLETION",
        top_k=15,
        include_references=True,
    )
    for r in results:
        print(r.answer[:500])


asyncio.run(main())
```

> 中文备注：`"search_type": null` 触发自动路由；显式写 `WIKI_COMPLETION` 则绕过 selector 直走 WIKI 管线。

### 检索 trace

```json
{
  "retriever": "WikiCompletionRetriever",
  "retrieval_mode": "wiki_first",
  "step0_llm_entities": {
    "subjects": ["A", "B", "C"],
    "attributes": [{"term": "多智能体体系", "subject": "A"}]
  }
}
```

多主体查询自动放大 `entity_top_k`（见工作原理解释），保证每个主体都有独立候选池，避免"只答到最大主体"。

---

## ⭐ structured_doc 建图与标题归因 / Graph Building with Title Attribution

### 建图

```bash
uv run xinggraph-cli add --path ./parsed_manual.pdf
uv run xinggraph-cli cognify --chunker structured_doc --chunk-size 2048
```

```python
import asyncio
import xinggraph


async def main():
    await xinggraph.add("parsed_manual.pdf")   # 支持 PDF 解析 wrapper 源文件
    await xinggraph.cognify(
        chunker="structured_doc",             # 逐 Doc 块入库，保留标题层级
        chunk_size=2048,
    )


asyncio.run(main())
```

### 标题归因

用 structured_doc 建图的数据集在推理时**自动**使用专用 prompt
（`answer_simple_question_structured_doc.txt`），回答会带上原始文档小标题作为来源：

```
Q: 系统架构里哪一层负责鉴权？
A: 详见「第一章 总体设计」中的「1.3 安全设计」：鉴权层由 ……（引用自该节）
```

无需手工配置 — `get_search_type_retriever_instance` 按数据集实际 chunker 自动切换
`system_prompt` 与 `system_prompt_path`。

---

## API 速查 / API Reference

| 端点 | 用途 | 关键参数 |
|---|---|---|
| `POST /v1/remember` | 记一条内容并建图 | `text`, `dataset` |
| `POST /v1/add` | 添加文档/文件 | `document`, `dataset` |
| `POST /v1/cognify` | 执行切块+实体抽取+建图 | `chunker`, `chunk_size` |
| `POST /v1/search` | 通用检索 | `search_type`, `query` |
| `POST /v1/recall` | 面向记忆的回答式召回 | `search_type(WIKI_COMPLETION)`, `query`, `include_references` |
| `GET  /v1/recall` | 检索历史 | — |

`search_type` 可用值（节选）：`SUMMARIES`、`CHUNKS`、`RAG_COMPLETION`、`HYBRID_COMPLETION`、
`TRIPLET_COMPLETION`、`GRAPH_COMPLETION`、`GRAPH_COMPLETION_DECOMPOSITION`、
`AGENTIC_COMPLETION`、`WIKI_COMPLETION`。

---

## 项目结构 / Project Structure

```
xinggraph/                     # 核心 Python 库
  api/                         # FastAPI 版本化路由
  cli/                         # CLI 入口与子命令
  infrastructure/              # 数据库 / LLM / embeddings / storage
  modules/
    chunking/                  # 切分器（含 StructuredDocChunker）
    retrieval/                 # 检索器（含 WikiCompletionRetriever）
    search/                    # 搜索类型路由
    ontology/  users/          # 本体 / 用户与权限
  tasks/                       # 可复用任务（chunks 等）
  tests/                       # 单测 / 集成 / CLI / E2E
xinggraph-mcp/                 # MCP 服务（stdio / SSE / HTTP）
xinggraph-frontend/            # Next.js 本地演示 UI
examples/                      # 公开 API 示例脚本
```

---

## 开发命令 / Development

```bash
uv run pytest xinggraph/tests/unit/ -v
uv run pytest xinggraph/tests/integration/ -v
uv run ruff check .
uv run ruff format .
uv run python -m xinggraph.api.client  # 启动 FastAPI server
```

> 中文备注：新增公开 API 时请同步在 `examples/python/` 补示例；CI 与本机命令一致。