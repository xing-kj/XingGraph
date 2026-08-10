"""Wiki-first progressive retriever: entity → chunk → wiki → LLM screening → answer."""

import asyncio
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from pydantic import BaseModel, Field

from xinggraph.context_global_variables import current_dataset_id, session_user
from xinggraph.infrastructure.databases.cache.config import CacheConfig
from xinggraph.infrastructure.databases.unified import get_unified_engine
from xinggraph.infrastructure.llm.LLMGateway import LLMGateway
from xinggraph.infrastructure.llm.prompts import render_prompt
from xinggraph.modules.retrieval.base_retriever import BaseRetriever
from xinggraph.modules.retrieval.exceptions.exceptions import QueryValidationError
from xinggraph.modules.retrieval.model_hop import model_directed_hop
from xinggraph.modules.retrieval.hybrid.chunks import search_collection
from xinggraph.modules.retrieval.hybrid.results import result_id, payload
from xinggraph.modules.retrieval.utils.completion import generate_completion
from xinggraph.modules.retrieval.utils.validate_queries import validate_retriever_input
from xinggraph.shared.logging_utils import get_logger

logger = get_logger("WikiCompletionRetriever")

WIKI_SCREENING_PROMPT = """You are a retrieval quality assistant. Given a user question and a list of wiki summaries from document chunks, determine which summaries contain enough information to answer the question.

Rules:
1. Return ONLY the wiki_ids (one per line) that are sufficient to answer the question.
2. If NO summary is sufficient, return the single line "INSUFFICIENT".
3. Do not explain your reasoning.
4. Be conservative: only select a wiki if it directly addresses the question.

User question: {query}

Wiki summaries:
{wiki_list}
"""


QUERY_ENTITY_EXTRACTION_PROMPT = """把一个用户问题拆成"主体(subjects)"和"属性(attributes)"，并且每个属性标注它属于哪个主体。

判定规则：
1. subjects：问题真正围绕的具体对象/型号，通常是产品型号、品牌、具体事物名（如 HYR-111）。最多 5 个；如果问题没有这样的明确主体，就返回空数组。
2. attributes：围绕主体提出的关注点、话题或属性（如 温度、清洁维护、噪音）。最多 6 个，去重。
3. 每个属性必须用 subject 字段指明它属于哪个主体：
   - 属性明显只针对某个主体时，subject 用那个主体的准确名字；
   - 属性对所有主体都通用（如"紫外灯功能"在对比三款设备时），则 subject 留空字符串；
   - 属性无法归属到任何具体主体时，subject 用空字符串。
4. 当问题涉及多个主体且某个属性是这些主体共有的（例如"紫外灯"在三款设备对比中），
   该属性的 term 只写属性本身（如"紫外灯启动"），subject 留空。
   系统会自动把该属性搜索词应用到所有主体。
   不要写"紫外灯→生物安全柜"这种复合 term。
5. subjects 里的名字不要重复出现在 attributes 的 term 里。
6. 只输出符合结构的 JSON，不要任何解释。
7. 绝对不要输出 <think>...</think>、<thinking> 或任何推理过程。不要 markdown 代码块。只输出纯 JSON。
8. 如果你无法从问题中识别出具体的主体对象，或者问题非常模糊以至于你无法提取出有意义的 subjects，
   不要猜测，不要编造。你应该设置 clarification_request 为一个简短的澄清问题，用中文询问用户。

示例：
问题：这三款设备（生物安全柜，加温箱，冷链运输箱）都提到了"紫外灯"功能。请对比它们在启动紫外灯时的安全联锁条件有何不同？
输出：
{{
  "subjects": ["生物安全柜", "加温箱", "冷链运输箱"],
  "attributes": [
    {{"term": "紫外灯启动", "subject": ""}},
    {{"term": "安全联锁条件", "subject": "生物安全柜"}},
    {{"term": "安全联锁条件", "subject": "加温箱"}},
    {{"term": "安全联锁条件", "subject": "冷链运输箱"}},
    {{"term": "允许启动条件", "subject": "生物安全柜"}},
    {{"term": "允许启动条件", "subject": "加温箱"}},
    {{"term": "允许启动条件", "subject": "冷链运输箱"}},
    {{"term": "禁止启动条件", "subject": "生物安全柜"}},
    {{"term": "禁止启动条件", "subject": "加温箱"}},
    {{"term": "禁止启动条件", "subject": "冷链运输箱"}}
  ]
}}

用户问题：
{query}
"""


class AttributeRef(BaseModel):
    term: str
    subject: Optional[str] = None


class QueryEntities(BaseModel):
    subjects: List[str] = []
    attributes: List[AttributeRef] = []
    clarification_request: Optional[str] = Field(
        default=None,
        description="当查询模糊/有歧义/无法识别主体时，向用户提出的澄清问题。",
    )


class WikiCompletionRetriever(BaseRetriever):
    """Completion retriever using wiki-first progressive retrieval.

    Pipeline:
      0. LLM entity extraction from the query
      1. Entity retrieval (LLM per-entity match + whole-sentence match, dedup, rank)
      2. Graph traversal (Entity → Chunk → Wiki)
      3. Wiki vector expansion (optional)
      4. LLM wiki screening
      5. Answer generation (wiki-only or progressive full-text recall)
    """

    def __init__(
        self,
        entity_top_k: int = 8,
        entity_per_term_k: int = 2,
        subject_per_term_k: int = 3,
        attribute_pool_k: int = 10,
        wiki_top_k: int = 8,
        max_context_chunks: int = 8,
        max_context_entities: int = 15,
        max_hops: int = 2,
        model_hop_hops: int = 5,
        wiki_screening_timeout: int = 10,
        entity_extraction_timeout: int = 20,
        system_prompt_path: str = "answer_simple_question.txt",
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
        response_model: Type = str,
        user_prompt_path: str = "hybrid_context_for_question.txt",
        include_references: bool = False,
        dataset_id: Optional[str] = None,
    ):
        self.entity_top_k = entity_top_k
        self.entity_per_term_k = entity_per_term_k
        self.subject_per_term_k = subject_per_term_k
        self.attribute_pool_k = attribute_pool_k
        self.wiki_top_k = wiki_top_k
        self.max_context_chunks = max_context_chunks
        self.max_context_entities = max_context_entities
        self.max_hops = max_hops
        self.model_hop_hops = model_hop_hops
        self.wiki_screening_timeout = wiki_screening_timeout
        self.entity_extraction_timeout = entity_extraction_timeout
        self.system_prompt_path = system_prompt_path
        self.system_prompt = system_prompt
        self.session_id = session_id
        self.response_model = response_model
        self.user_prompt_path = user_prompt_path
        self.include_references = include_references
        self.dataset_id = dataset_id

        # Structured retrieval trace collected across the 5 pipeline steps.
        # Populated only when retrieval actually runs; None otherwise.
        self.trace: Optional[Dict[str, Any]] = None

    def _use_session_cache(self) -> bool:
        user = session_user.get()
        user_id = getattr(user, "id", None)
        return bool(user_id and CacheConfig().caching)

    async def get_retrieved_objects(
        self, query: Optional[str] = None, query_batch: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        _reject_query_batch(query_batch)
        validate_retriever_input(query, None, self._use_session_cache())

        # Eagerly initialise the trace so Step 0 / Step 1 writes are never dropped.
        self.trace = {"retriever": "WikiCompletionRetriever"}
        self._model_entity_ids: set = set()
        self._all_model_entity_ids: set = set()

        self._unified_engine = await get_unified_engine()
        query_embeddings = await self._unified_engine.vector.embedding_engine.embed_text([query])
        query_vector = query_embeddings[0]

        dataset_id = current_dataset_id.get()  # noqa: F841

        # Step 0: LLM extraction — subjects + attributes (each attribute bound to a subject).
        qe = await self._extract_query_entities(query)
        self.trace["step0_llm_entities"] = {
            "subjects": qe["subjects"],
            "attributes": [{"term": a["term"], "subject": a["subject"]} for a in qe["attributes"]],
        }

        clarification = qe.get("clarification_request")
        if clarification:
            return {
                "entities": [],
                "chunks": [],
                "wikis": [],
                "retrieval_mode": "wiki_first",
                "clarification_request": clarification,
            }

        subjects_count = len(qe.get("subjects") or [])
        entity_top_k = 8 if subjects_count <= 1 else max(15, subjects_count * 5)

        # Step 1a: anchor/subject match — these are the figuresheads, never filtered.
        anchor_terms = qe["subjects"] or [query]
        anchor_embeddings = await self._unified_engine.vector.embedding_engine.embed_text(
            anchor_terms
        )
        anchor_entries: List[Dict[str, Any]] = []
        for term, term_vector in zip(anchor_terms, anchor_embeddings):
            anchor_hits = await search_collection(
                self._unified_engine.vector,
                "Entity_name",
                term,
                self.subject_per_term_k,
                None,
                "OR",
                query_vector=term_vector,
            )
            for hit in anchor_hits:
                entry = self._trace_entity(hit)
                entry["role"] = "subject"
                entry["source_term"] = term
                entry["anchor_term"] = term
                anchor_entries.append(entry)
        anchor_entries = self._dedupe_rank_entities(anchor_entries, entity_top_k)

        # Step 1b: attribute match — each candidate tagged with the bound subject term.
        candidate_entries: List[Dict[str, Any]] = []
        attr_meta = []
        attr_terms = qe["attributes"]
        if attr_terms:
            attr_texts = [a["term"] for a in attr_terms]
            attr_embeddings = await self._unified_engine.vector.embedding_engine.embed_text(
                attr_texts
            )
            for a, term_vector in zip(attr_terms, attr_embeddings):
                attr_hits = await search_collection(
                    self._unified_engine.vector,
                    "Entity_name",
                    a["term"],
                    self.attribute_pool_k,
                    None,
                    "OR",
                    query_vector=term_vector,
                )
                attr_meta.append(
                    {"term": a["term"], "subject": a["subject"], "hits": len(attr_hits)}
                )
                for hit in attr_hits:
                    entry = self._trace_entity(hit)
                    entry["role"] = "attribute"
                    entry["source_term"] = a["term"]
                    entry["bound_subject"] = a.get("subject") or None
                    candidate_entries.append(entry)

        # Step 1c: whole-sentence fallback hits (role=sentence, no bound subject).
        sentence_hits = await search_collection(
            self._unified_engine.vector,
            "Entity_name",
            query,
            entity_top_k,
            None,
            "OR",
            query_vector=query_vector,
        )
        sentence_entries = [self._trace_entity(hit) for hit in sentence_hits]
        for entry in sentence_entries:
            entry["role"] = "sentence"
        candidate_entries.extend(sentence_entries)

        # Step 1d: source-document coherence gate — keep entities sharing a source
        # document with their bound subject (or any subject) so unrelated documents
        # (e.g. a different product manual) do not leak into the seed set.
        kept, dropped, subject_docs = await self._filter_by_subject_documents(
            anchor_entries, candidate_entries
        )

        # Merge anchors + kept candidates, rank, and fill if short.
        entity_hits = self._dedupe_rank_entities(anchor_entries + kept, entity_top_k)
        if len(entity_hits) < entity_top_k:
            kept_names = {e.get("name") for e in entity_hits}
            remaining = [e for e in candidate_entries if e.get("name") not in kept_names]
            fill = self._dedupe_rank_entities(remaining, entity_top_k - len(entity_hits))
            entity_hits = self._dedupe_rank_entities(entity_hits + fill, entity_top_k)

        self.trace["step1_dedup"] = {
            "raw": len(anchor_entries) + len(candidate_entries),
            "anchors": [
                {"name": e.get("name"), "term": e.get("anchor_term")} for e in anchor_entries
            ],
            "attribute_meta": attr_meta,
            "sentence_hits": len(sentence_entries),
            "kept": [e.get("name") for e in kept],
            "dropped": dropped,
            "subject_docs": subject_docs,
            "unique": len(entity_hits),
        }

        if not entity_hits:
            subjects_list = qe.get("subjects") or []
            clarification_msg = (
                f"未找到与「{', '.join(subjects_list)}」相关的实体。"
                "请确认设备名称是否正确，或尝试其他关键词。"
                if subjects_list
                else "我无法从您的问题中识别出具体的主体对象。请明确您想了解哪款设备？"
            )
            return {
                "entities": [],
                "chunks": [],
                "wikis": [],
                "retrieval_mode": "wiki_first",
                "clarification_request": clarification_msg,
            }

        entity_ids = [entry["id"] for entry in entity_hits if entry.get("id")]
        if not entity_ids:
            self._record_trace(
                entities=entity_hits,
                traversal={
                    "entity_ids_queried": 0,
                    "entity_nodes": 0,
                    "chunk_nodes": 0,
                    "wiki_nodes": 0,
                    "chunk_wiki_pairs": 0,
                    "max_hops": self.max_hops,
                },
                wiki_expansion={"enabled": self.wiki_top_k > 0, "added": 0},
            )
            self.trace["step4_screening"] = {
                "considered": 0,
                "sufficient": [],
                "outcome": "no_wikis",
            }
            self.trace["step5_answer_mode"] = "no_entities"
            self.trace["context"] = ""
            return {"entities": [], "chunks": [], "wikis": [], "retrieval_mode": "wiki_first"}

        # Step 2: Graph traversal (depth=2 to reach ChunkWiki via DocumentChunk)
        try:
            nodes, edges = await self._unified_engine.graph.get_neighborhood(
                entity_ids,
                depth=self.max_hops,
            )
        except Exception as error:
            logger.warning("Neighborhood retrieval failed: %s", error)
            nodes, edges = [], []

        # Separate nodes by type
        entity_nodes = []
        chunk_nodes = []
        wiki_nodes = []
        nodes_by_id = {}
        for node in nodes or []:
            node_id = str(node[0])
            props = node[1] if isinstance(node, (list, tuple)) and len(node) > 1 else {}
            nodes_by_id[node_id] = {"id": node_id, **props}
            node_type = props.get("type", "")
            if node_type == "Entity":
                entity_nodes.append(nodes_by_id[node_id])
            elif node_type == "DocumentChunk":
                chunk_nodes.append(nodes_by_id[node_id])
            elif node_type == "ChunkWiki":
                wiki_nodes.append(nodes_by_id[node_id])

        # ── Subjects from Step 0 (moved up so chunk filtering can use it) ──
        subjects = (
            (self.trace or {}).get("step0_llm_entities", {}).get("subjects", [])
            if self.trace
            else []
        )

        # Step 2b (upstream enhancement): stabilise the subject whitelist by
        # scanning the graph for entities whose name literally contains a subject
        # word and unioning in their documents. This removes the run-to-run
        # jitter from re-deriving subject docs off whichever vector-hit anchor
        # entity happened to be selected. Pure literal match (no synonym/semantic
        # expansion per user decision); foreign docs are left for the chunk-level
        # filter below to drop.
        name_subject_docs = await self._collect_subject_docs_by_name(subjects)
        if name_subject_docs:
            for subj, docs in name_subject_docs.items():
                if not docs:
                    continue
                key = subj
                if key in subject_docs:
                    subject_docs[key] |= set(docs)
                else:
                    subject_docs[key] = set(docs)
            logger.info(
                "SUBJECT_DOCS_MERGED subjects=%s name_sources=%d total_doc_keys=%d",
                subjects,
                len([d for d in name_subject_docs.values() if d]),
                len(subject_docs),
            )

        # Step 2b: narrow traversal to the subjects' source documents so a
        # multi-document entity (e.g. a generic attribute that also appears in an
        # unrelated manual) does not drag foreign-document chunks/wikis into context.
        # Multi-doc subjects get a relaxed whitelist (all their docs pass through)
        # but are still gated by a subject-mention check so foreign products that
        # happen to share a document are excluded; single-doc subjects keep the
        # stricter per-document filter.
        multi_doc_union = {
            d for docs in (subject_docs or {}).values() if len(docs) > 1 for d in docs
        }
        single_doc_union = {
            d for docs in (subject_docs or {}).values() if len(docs) == 1 for d in docs
        }
        subject_lower = [s for s in subjects if s]

        def _chunk_mentions_subject(text) -> bool:
            if not subject_lower:
                return True
            t = (text or "").lower()
            return any(s.lower() in t for s in subject_lower)

        # Hard whitelist: only chunks belonging to a subject document survive.
        # The graph traversal (get_neighborhood depth=2) is document-agnostic and
        # pulls in foreign chunks that merely share a synthetic entity (factory
        # name, welcome page, company footer, generic attribute) with the subject
        # docs (e.g. other Haier products: warming cabinet / bio safety cabinet /
        # CO2 incubator). Those must never leak into retrieval, so anything whose
        # document is not in the subject-doc union is dropped regardless of the
        # single/multi membership (previous elif short-circuited on an empty
        # single_doc_union and let foreign chunks through).
        allowed_docs = multi_doc_union | single_doc_union
        filtered_chunk_nodes = []
        chunks_dropped = []
        for chunk in chunk_nodes:
            doc = chunk.get("document_id") or chunk.get("document_name")
            doc_str = str(doc) if doc else ""
            if not doc_str or doc_str in allowed_docs:
                filtered_chunk_nodes.append(chunk)
            else:
                chunks_dropped.append(
                    {
                        "chunk_id": chunk.get("id"),
                        "document": doc,
                        "reason": f"document not in subject docs (allowed={sorted(allowed_docs)})",
                    }
                )
        chunk_nodes = filtered_chunk_nodes

        if chunks_dropped:
            for drop in chunks_dropped[:50]:
                logger.info(
                    "CHUNK_DROPPED chunk_id=%s document=%s reason=%s",
                    drop.get("chunk_id"),
                    drop.get("document"),
                    drop.get("reason", "not-in-union"),
                )

        # ── Step 2c (independent branch): model-directed hop ──
        # Walks the product-model path, preferring ``is_product`` edges from the
        # anchored subject entities: a category (e.g. the medical low-temperature
        # preservation box) returns all its linked models; an anchored concrete
        # model has no ``is_product`` out-edge so it returns only itself, never
        # expanding to sibling models. Falls back to the legacy ``contains`` walk
        # over the subject documents only when the seeds are neither category
        # nor model. The hop is additive: it tops up chunks the generic
        # depth-limited neighborhood may have missed.
        try:
            model_hop = await model_directed_hop(
                self._unified_engine.graph,
                doc_ids=list(allowed_docs) if allowed_docs else None,
                dataset_id=self.dataset_id,
                max_hops=self.model_hop_hops,
                seed_entity_ids=[str(e.get("id")) for e in anchor_entries if e.get("id")],
            )
            self._model_entity_ids = {
                str(eid) for eid in (model_hop.get("model_entity_ids") or []) if eid
            }
            # All PRODUCT_MODEL entity ids in the graph (for filtering sibling
            # models that generic traversal pulls in via a shared model-table
            # chunk but that the model hop did NOT return).
            try:
                all_model_rows = await self._unified_engine.graph.query(
                    """
                    MATCH (m:Entity)-[:is_a]->(t:EntityType {name: 'PRODUCT_MODEL'})
                    RETURN collect(DISTINCT m.id) AS ids
                    """,
                    {},
                )
                self._all_model_entity_ids = {
                    str(x) for x in (all_model_rows[0].get("ids") or []) if x
                }
            except Exception:  # noqa: BLE001
                self._all_model_entity_ids = set()
            model_chunk_ids = model_hop.get("model_chunk_ids") or []
            if model_chunk_ids:
                existing_ids = {str(c.get("id")) for c in chunk_nodes if c.get("id")}
                new_ids = [cid for cid in set(model_chunk_ids) if str(cid) not in existing_ids]
                hop_chunks = []
                if new_ids:
                    hop_nodes = await self._unified_engine.graph.get_nodes(new_ids)
                    hop_chunks = [
                        {"id": n.get("id"), **n} for n in hop_nodes
                        if n.get("id") and n.get("type") == "DocumentChunk"
                    ]
                    if allowed_docs:
                        allow = {str(a) for a in allowed_docs}
                        hop_chunks = [
                            c for c in hop_chunks
                            if str(c.get("document_id") or c.get("document_name") or "") in allow
                        ]
                chunk_nodes.extend(hop_chunks)
                logger.info(
                    "MODEL_HOP merged=%d unique=%d entity_type=%s max_hops=%d",
                    len(hop_chunks),
                    len(set(model_chunk_ids)),
                    model_hop.get("entity_type"),
                    self.model_hop_hops,
                )
            self.trace["step2c_model_hop"] = {
                "enabled": True,
                "mode": model_hop.get("mode", "fallback"),
                "model_entities": len(model_hop.get("model_entity_ids") or []),
                "model_chunks": len(model_chunk_ids),
                "merged_into_pool": len(hop_chunks) if model_chunk_ids else 0,
                "max_hops": self.model_hop_hops,
            }
        except Exception as error:  # noqa: BLE001
            logger.warning("Model-directed hop failed: %s", error, exc_info=True)
            self._model_entity_ids = set()
            self.trace["step2c_model_hop"] = {
                "enabled": False,
                "error": str(error),
            }

        # ── Rank chunks by relevance to the query ──
        # One vector search over the chunk-text collection produces a score for
        # every candidate; we just look up by id (no per-chunk embedding calls).
        # Sorting replaces the raw graph-traversal order so a later document is
        # not silently truncated away downstream. Fail-open: on any error fall
        # back to the traversal order without breaking existing behaviour.
        chunk_score: Dict[str, float] = {}
        if chunk_nodes:
            try:
                chunk_hits = await search_collection(
                    self._unified_engine.vector,
                    "DocumentChunk_text",
                    query,
                    100,
                    None,
                    "OR",
                    query_vector=query_vector,
                )
                for hit in chunk_hits:
                    cid = result_id(hit)
                    score = getattr(hit, "score", None)
                    if cid and isinstance(score, (int, float)):
                        # Vector hits carry cosine distance; expose similarity (higher is better).
                        chunk_score[cid] = round(1 - float(score), 4)
            except Exception as error:
                logger.debug("Chunk relevance ranking skipped: %s", error)
                chunk_score = {}

        # Mix query relevance (primary) with a subject-mention tie-breaker.
        chunk_nodes.sort(
            key=lambda c: (
                chunk_score.get(c.get("id"), float("-inf")),
                1 if _chunk_mentions_subject(c.get("text")) else 0,
            ),
            reverse=True,
        )

        # Round-robin across documents so no subject document is crowded out of
        # the leading positions by several high-scoring chunks from one doc.
        # Hard guard: only subject documents may participate (foreign docs were
        # already dropped above, this is belt-and-braces).
        doc_groups: Dict[str, List[Dict[str, Any]]] = {}
        for c in chunk_nodes:
            c_doc = str(c.get("document_id") or c.get("document_name") or "")
            if allowed_docs and c_doc and c_doc not in allowed_docs:
                continue
            doc_groups.setdefault(c_doc, []).append(c)
        interleaved = []
        while doc_groups:
            for key in list(doc_groups.keys()):
                if doc_groups[key]:
                    interleaved.append(doc_groups[key].pop(0))
                else:
                    del doc_groups[key]
        chunk_nodes = interleaved

        # ── Build entity↔chunk subject mappings ──
        subject_name_by_norm = {self._norm_key(s): s for s in subjects}

        entity_to_subjects: Dict[str, List[str]] = {}

        # 1. subject role: anchor_term 是 Step 1a 检索该 entity 时用的 subject 原文
        for entry in entity_hits:
            eid = entry.get("id")
            if not eid:
                continue
            role = entry.get("role")
            if role == "subject":
                term = entry.get("anchor_term")
                if term:
                    entity_to_subjects.setdefault(eid, [])
                    if term not in entity_to_subjects[eid]:
                        entity_to_subjects[eid].append(term)
            elif role == "attribute":
                bound = entry.get("bound_subject")
                if bound:
                    entity_to_subjects.setdefault(eid, [])
                    if bound not in entity_to_subjects[eid]:
                        entity_to_subjects[eid].append(bound)

        # 2. sentence role fallback: 绑定到所有 subjects
        all_subjects = list(subjects)
        for entry in sentence_entries:
            eid = entry.get("id")
            if eid and eid not in entity_to_subjects:
                entity_to_subjects[eid] = list(all_subjects)

        # 3. graph entity_nodes fallback: 仅对未在 entity_hits 出现的 graph entity
        for ent in entity_nodes:
            eid = ent.get("id", "")
            if not eid or eid in entity_to_subjects:
                continue
            ename = ent.get("name", "")
            norm = self._norm_key(ename)
            if norm in subject_name_by_norm:
                canonical = subject_name_by_norm[norm]
                entity_to_subjects.setdefault(eid, [])
                if canonical not in entity_to_subjects[eid]:
                    entity_to_subjects[eid].append(canonical)

        chunk_id_set = {c["id"] for c in chunk_nodes if c.get("id")}
        entity_id_set = {e["id"] for e in entity_nodes if e.get("id")}

        entity_chunks: Dict[str, List[str]] = {}
        chunk_entities: Dict[str, List[str]] = {}
        for edge in edges or []:
            src, tgt, etype = edge[0], edge[1], edge[2]
            if etype != "contains":
                continue
            cid, eid = None, None
            if src in chunk_id_set and tgt in entity_id_set:
                cid, eid = src, tgt
            elif tgt in chunk_id_set and src in entity_id_set:
                cid, eid = tgt, src
            if cid and eid:
                entity_chunks.setdefault(eid, []).append(cid)
                chunk_entities.setdefault(cid, []).append(eid)

        chunk_by_id = {c["id"]: c for c in chunk_nodes if c.get("id")}
        for cid, c in chunk_by_id.items():
            related_eids = chunk_entities.get(cid, [])
            subjects_for_chunk = set()
            for eid in related_eids:
                for subj in entity_to_subjects.get(eid, []):
                    subjects_for_chunk.add(subj)
            c["subjects"] = list(subjects_for_chunk) if subjects_for_chunk else []

        # Keep only entities that were actually used: an entity counts as used
        # when it is contained in at least one kept chunk (post doc-whitelist +
        # model-hop merge). Chunks merged in by the model hop carry model
        # entities that are not present in the traversal ``contains`` edges, so
        # their product-model ids are unioned in explicitly.
        used_entity_ids = {eid for eids in chunk_entities.values() for eid in eids}
        used_entity_ids |= {eid for eid in self._model_entity_ids if eid in entity_id_set}
        # Do not let sibling models leak back in: the generic depth-limited
        # traversal pulls in every model sharing a model-table chunk, but only
        # the models the model hop actually returned (via is_product / self-model
        # anchor, or the legacy contains fallback) belong to this retrieval.
        # When the hop resolved a concrete set, restrict model entities to it.
        if self._model_entity_ids and self._all_model_entity_ids:
            used_entity_ids = {
                eid for eid in used_entity_ids
                if eid not in self._all_model_entity_ids or eid in self._model_entity_ids
            }
        filtered_entities = [
            e for e in entity_nodes if str(e.get("id")) in used_entity_ids
        ]
        if len(filtered_entities) != len(entity_nodes):
            logger.info(
                "ENTITIES_FILTERED kept=%d dropped=%d kept_names=%d",
                len(filtered_entities),
                len(entity_nodes) - len(filtered_entities),
                len({e.get("name") for e in filtered_entities if e.get("name")}),
            )
            entity_nodes = filtered_entities

        # Structured "relevant entities" surface: every entity actually used in
        # this retrieval, tagged with whether it is a product model. The UI
        # renders this as a card (models first, others collapsible) instead of
        # parsing the markdown context block.
        self.trace["relevant_entities"] = [
            {
                "name": e.get("name"),
                "description": e.get("description") or "",
                "is_model": str(e.get("id")) in self._model_entity_ids,
            }
            for e in entity_nodes
            if e.get("name")
        ]

        # Build chunk → wiki mapping from edges
        chunk_wiki_map = {}
        for edge in edges or []:
            source_id = str(edge[0])
            target_id = str(edge[1])
            edge_type = edge[2] if len(edge) > 2 else ""
            if edge_type == "has_wiki":
                chunk_wiki_map.setdefault(source_id, []).append(target_id)

        # Attach wikis to chunks
        chunk_wiki_pairs = []
        for chunk in chunk_nodes:
            chunk_id = chunk["id"]
            wiki_ids = chunk_wiki_map.get(chunk_id, [])
            chunk_wikis = [nodes_by_id.get(wid) for wid in wiki_ids if wid in nodes_by_id]
            chunk_wiki_pairs.append((chunk, chunk_wikis))

        # Tag each wiki with subjects inherited from its source chunks.
        for wiki in wiki_nodes:
            wiki_id = wiki.get("id", "")
            source_cids = [src for src, tgts in (chunk_wiki_map or {}).items() if wiki_id in tgts]
            wiki_subjects = set()
            for cid in source_cids:
                for subj in chunk_by_id.get(cid, {}).get("subjects", []):
                    wiki_subjects.add(subj)
            wiki["subjects"] = list(wiki_subjects)

        # Step 3: Wiki vector expansion (optional supplement)
        if self.wiki_top_k > 0 and entity_nodes:
            try:
                wiki_hits = await search_collection(
                    self._unified_engine.vector,
                    "ChunkWiki_text",
                    query,
                    self.wiki_top_k,
                    None,
                    "OR",
                    query_vector=query_vector,
                )
                for hit in wiki_hits:
                    hit_id = result_id(hit)
                    if hit_id and hit_id not in [w["id"] for w in wiki_nodes]:
                        hit_payload = payload(hit)
                        blob = " ".join(
                            [
                                hit_payload.get("summary", "") or "",
                                *(hit_payload.get("key_entities", []) or []),
                                *(hit_payload.get("key_topics", []) or []),
                            ]
                        ).lower()
                        # Drop wikis that mention none of the subjects (e.g. a
                        # foreign product that shares a document) to stop them
                        # leaking into general context.
                        if subject_lower and not any(
                            s.lower() in blob for s in subject_lower
                        ):
                            continue
                        new_wiki = {
                            "id": hit_id,
                            "type": "ChunkWiki",
                            **hit_payload,
                        }
                        # Inherit subjects from source chunks via has_wiki edges.
                        source_cids = [
                            src
                            for src, tgts in (chunk_wiki_map or {}).items()
                            if hit_id in tgts
                        ]
                        wiki_subjects = set()
                        for cid in source_cids:
                            for subj in chunk_by_id.get(cid, {}).get("subjects", []):
                                wiki_subjects.add(subj)
                        if wiki_subjects:
                            new_wiki["subjects"] = list(wiki_subjects)
                        wiki_nodes.append(new_wiki)
            except Exception as error:
                logger.debug("Wiki vector expansion skipped: %s", error)

        traversal = {
            "entity_ids_queried": len(entity_ids),
            "entity_nodes": len(entity_nodes),
            "chunk_nodes": len(chunk_nodes),
            "wiki_nodes": len(wiki_nodes),
            "chunk_wiki_pairs": len(chunk_wiki_pairs),
            "max_hops": self.max_hops,
        }
        traversal["chunk_ranking"] = [
            {
                "chunk_id": c.get("id"),
                "score": chunk_score.get(c.get("id")),
                "document_id": c.get("document_id"),
            }
            for c in chunk_nodes[:20]
        ]
        for rank, c in enumerate(chunk_nodes[:20], start=1):
            logger.info(
                "CHUNK_RANKED rank=%d chunk_id=%s score=%s document_id=%s has_subject=%s",
                rank,
                c.get("id"),
                chunk_score.get(c.get("id")),
                c.get("document_id"),
                1 if _chunk_mentions_subject(c.get("text")) else 0,
            )
        traversal["paths"] = self._build_paths(
            edges,
            chunk_nodes,
            entity_nodes,
            chunk_wiki_pairs,
        )

        self._record_trace(
            entities=entity_hits,
            traversal=traversal,
            wiki_expansion={
                "enabled": self.wiki_top_k > 0 and bool(entity_nodes),
                "added": len(wiki_nodes),
            },
        )

        return {
            "entities": entity_nodes,
            "chunks": chunk_nodes,
            "chunk_wiki_pairs": chunk_wiki_pairs,
            "wikis": wiki_nodes,
            "retrieval_mode": "wiki_first",
            "subject_docs_size": len(allowed_docs),
        }

    async def get_context_from_objects(
        self,
        query: Optional[str] = None,
        query_batch: Optional[List[str]] = None,
        retrieved_objects: Any = None,
    ) -> str:
        _reject_query_batch(query_batch)
        if not retrieved_objects:
            return ""

        subjects = (self.trace or {}).get("step0_llm_entities", {}).get("subjects", [])

        chunks = retrieved_objects.get("chunks", [])
        wikis = retrieved_objects.get("wikis", [])

        subject_chunks: Dict[str, List] = {}
        subject_wikis: Dict[str, List] = {}
        unassigned_chunks, unassigned_wikis = [], []

        for chunk in chunks:
            s = chunk.get("subjects", [])
            if s:
                for subj in s:
                    subject_chunks.setdefault(subj, []).append(chunk)
            else:
                unassigned_chunks.append(chunk)

        for wiki in wikis:
            s = wiki.get("subjects", [])
            if s:
                for subj in s:
                    subject_wikis.setdefault(subj, []).append(wiki)
            else:
                unassigned_wikis.append(wiki)

        sections = []

        for idx, subj in enumerate(subjects, 1):
            parts = []
            w = subject_wikis.get(subj, [])[: self.wiki_top_k]
            c = subject_chunks.get(subj, [])[: self.max_context_chunks]

            if w:
                wiki_texts = []
                for wiki in w:
                    summary = wiki.get("summary", "")
                    topics = wiki.get("key_topics", [])
                    entities = wiki.get("key_entities", [])
                    if summary:
                        wiki_texts.append(
                            f"[{wiki.get('id', '?')}]: {summary}\n"
                            f"Topics: {', '.join(topics)}\n"
                            f"Entities: {', '.join(entities)}"
                        )
                if wiki_texts:
                    parts.append("### Wiki 摘要\n" + "\n---\n".join(wiki_texts))

            if c:
                chunk_texts = []
                for chunk in c:
                    text = chunk.get("text", "")
                    if text:
                        chunk_texts.append(text)
                if chunk_texts:
                    parts.append("### 原文片段\n" + "\n---\n".join(chunk_texts))

            if parts:
                sections.append(f"ENTITY {idx}: {subj}\n" + "\n".join(parts))

        if unassigned_wikis or unassigned_chunks:
            subject_lower = [s for s in subjects if s]

            def _mentions(text) -> bool:
                if not subject_lower:
                    return True
                return any(s.lower() in (text or "").lower() for s in subject_lower)

            parts = []
            if unassigned_wikis:
                wiki_texts = []
                for wiki in unassigned_wikis[: self.wiki_top_k]:
                    summary = wiki.get("summary", "")
                    blob = " ".join(
                        [
                            summary or "",
                            *(wiki.get("key_entities", []) or []),
                            *(wiki.get("key_topics", []) or []),
                        ]
                    )
                    if not _mentions(blob):
                        continue
                    if summary:
                        wiki_texts.append(f"[{wiki.get('id', '?')}]: {summary}")
                if wiki_texts:
                    parts.append("### Wiki 摘要\n" + "\n---\n".join(wiki_texts))
            if unassigned_chunks:
                chunk_texts = [
                    c.get("text", "")
                    for c in unassigned_chunks[: self.max_context_chunks]
                    if c.get("text") and _mentions(c.get("text"))
                ]
                if chunk_texts:
                    parts.append("### 原文片段\n" + "\n---\n".join(chunk_texts))
            if parts:
                sections.append(
                    "GENERAL CONTEXT (not bound to any specific entity)\n" + "\n".join(parts)
                )

        entities = retrieved_objects.get("entities", [])
        if entities:
            # Show every entity that was actually used during retrieval, no
            # truncation. Product-model entities (from the model hop, e.g. the
            # 24 freezer model codes) are listed first, then the remaining used
            # entities — deduped by name so multi-document duplicates collapse.
            model_ids = self._model_entity_ids
            seen_names: set = set()
            models, others = [], []
            for entity in entities:
                name = entity.get("name", "")
                if not name or name in seen_names:
                    continue
                seen_names.add(name)
                bucket = models if str(entity.get("id")) in model_ids else others
                bucket.append(entity)
            entity_texts = [
                f"- {name}: {desc}" if (desc := entity.get("description", "")) else f"- {name}"
                for entity in models + others
                if (name := entity.get("name", ""))
            ]
            if entity_texts:
                sections.append("## Relevant entities\n" + "\n".join(entity_texts))

        context_text = f"\n{'=' * 60}\n".join(sections)
        if self.trace is not None:
            self.trace["context"] = context_text
        return context_text

    async def get_completion_from_context(
        self,
        query: Optional[str] = None,
        query_batch: Optional[List[str]] = None,
        retrieved_objects: Any = None,
        context: Any = None,
    ) -> Union[List[str], List[dict]]:
        _reject_query_batch(query_batch)

        if not context or not retrieved_objects:
            if self.trace is not None:
                self.trace.setdefault(
                    "step4_screening",
                    {
                        "considered": 0,
                        "sufficient": [],
                        "outcome": "no_content",
                    },
                )
                self.trace["step5_answer_mode"] = "empty"
            return [""]

        # Step 4: LLM Wiki screening
        wikis = retrieved_objects.get("wikis", [])
        sufficient_wiki_ids = await self._screen_wikis(query, wikis)
        if self.trace is not None:
            screening = dict(self.trace.get("step4_screening") or {})
            screening["considered"] = len(wikis[: self.wiki_top_k])
            screening["sufficient"] = sufficient_wiki_ids
            screening.setdefault("outcome", "sufficient" if sufficient_wiki_ids else "insufficient")
            # Attach the wiki summaries that were screened, for trace display.
            screening["wikis"] = [
                {
                    "id": wiki.get("id"),
                    "summary": wiki.get("summary", ""),
                    "key_topics": wiki.get("key_topics", []),
                }
                for wiki in wikis[: self.wiki_top_k]
            ]
            self.trace["step4_screening"] = screening

        # Step 5: Answer generation
        if sufficient_wiki_ids:
            completion = await self._generate_wiki_answer(query, context, sufficient_wiki_ids)
        else:
            completion = await self._generate_fulltext_answer(query, retrieved_objects)

        if self.trace is not None:
            self.trace["step5_answer_mode"] = (
                "wiki_answer" if sufficient_wiki_ids else "fulltext_fallback"
            )
        return completion

    async def _screen_wikis(self, query: str, wikis: list) -> list:
        """Use LLM to determine which wikis are sufficient to answer the query."""
        if not wikis:
            return []

        wiki_list_text = "\n\n".join(
            f"[{wiki.get('id', 'unknown')}]: {wiki.get('summary', '')}\n"
            f"  Topics: {', '.join(wiki.get('key_topics', []))}\n"
            f"  Entities: {', '.join(wiki.get('key_entities', []))}"
            for wiki in wikis[: self.wiki_top_k]
        )

        prompt = WIKI_SCREENING_PROMPT.format(query=query, wiki_list=wiki_list_text)

        try:
            result = await asyncio.wait_for(
                LLMGateway.acreate_structured_output(
                    text_input=prompt,
                    system_prompt="You are a retrieval quality assistant. Return only wiki IDs or INSUFFICIENT.",
                    response_model=str,
                ),
                timeout=self.wiki_screening_timeout,
            )
            result = result.strip()
            if result == "INSUFFICIENT":
                self._record_screening({}, "insufficient")
                return []
            selected = [line.strip() for line in result.split("\n") if line.strip()]
            self._record_screening(selected, "sufficient")
            return selected
        except asyncio.TimeoutError:
            logger.warning("Wiki screening timed out; treating all wikis as sufficient")
            selected = [wiki.get("id") for wiki in wikis[: self.wiki_top_k]]
            self._record_screening(selected, "timeout")
            return selected
        except Exception as error:
            logger.warning("Wiki screening failed: %s", error)
            self._record_screening([], "failed")
            return []

    async def _generate_wiki_answer(self, query: str, context: str, wiki_ids: list) -> list:
        """Generate answer based on wiki context only."""
        wiki_context = self._filter_context_by_wiki_ids(context, wiki_ids)
        prompt = wiki_context or context

        result = await generate_completion(
            query=query,
            context=prompt,
            user_prompt_path=self.user_prompt_path,
            system_prompt_path=self.system_prompt_path,
            system_prompt=self.system_prompt,
            response_model=self.response_model,
        )
        return [result] if isinstance(result, str) else result

    async def _generate_fulltext_answer(self, query: str, retrieved_objects: dict) -> list:
        """Progressive full-text recall: retrieve original chunks and generate answer."""
        chunks = retrieved_objects.get("chunks", [])
        chunk_texts = [chunk.get("text", "") for chunk in chunks if chunk.get("text")]

        allowed_size = retrieved_objects.get("subject_docs_size") or 0
        # 1 份 doc 保持 14；多份 doc 按 4 chunk/doc 平均扩，上限 264 保安全
        # （含型号跳转合并进的型号表 chunk，避免把型号表截在全文扫描之外）。
        limit = max(14, allowed_size * 4) if allowed_size else 14
        limit = min(limit, 264, len(chunk_texts)) if chunk_texts else limit
        fulltext_context = "\n\n".join(chunk_texts[:limit])

        if chunk_texts:
            from collections import Counter

            doc_counts = Counter(
                c.get("document_id") or c.get("document_name") or "?"
                for c in chunks[:limit]
            )
            logger.info(
                "FULLTEXT_CONTEXT total_chunks=%d used=%d limit=%d subject_docs=%d doc_distribution=%s",
                len(chunk_texts),
                min(len(chunk_texts), limit),
                limit,
                allowed_size,
                dict(doc_counts),
            )

        if not fulltext_context:
            return [""]

        result = await generate_completion(
            query=query,
            context=fulltext_context,
            user_prompt_path=self.user_prompt_path,
            system_prompt_path=self.system_prompt_path,
            system_prompt=self.system_prompt,
            response_model=self.response_model,
        )
        return [result] if isinstance(result, str) else result

    def _filter_context_by_wiki_ids(self, context: str, wiki_ids: list) -> str:
        """Filter context to only include sections for selected wiki IDs."""
        if not wiki_ids:
            return context
        # Simple implementation: return full context
        # A more sophisticated version would parse and filter by wiki_id
        return context

    def _record_screening(self, sufficient: list, outcome: str) -> None:
        if self.trace is None:
            self.trace = {"retriever": "WikiCompletionRetriever"}
        screening = dict(self.trace.get("step4_screening") or {})
        screening["sufficient"] = sufficient
        screening["outcome"] = outcome
        self.trace["step4_screening"] = screening

    def _record_trace(
        self,
        *,
        entities: Optional[list] = None,
        traversal: Optional[Dict[str, Any]] = None,
        wiki_expansion: Optional[Dict[str, Any]] = None,
    ) -> None:
        if self.trace is None:
            self.trace = {"retriever": "WikiCompletionRetriever"}
        if entities is not None:
            self.trace["step1_entities"] = entities
        if traversal is not None:
            self.trace["step2_traversal"] = traversal
        if wiki_expansion is not None:
            self.trace["step3_wiki_expansion"] = wiki_expansion

    def _trace_entity(self, hit: Any) -> Dict[str, Any]:
        """Best-effort map a vector hit to a compact trace entity.

        The Entity_name vector collection stores the entity name under ``text``
        (``text=getattr(dp, index_fields[0])``); fall back to ``name`` if absent.
        """
        entry: Dict[str, Any] = {"id": result_id(hit) if result_id(hit) else None}
        try:
            hit_payload = payload(hit)
            entry["name"] = hit_payload.get("text") or hit_payload.get("name")
        except Exception:
            pass
        try:
            score = hit.score if hasattr(hit, "score") else None
            if isinstance(score, (int, float)):
                # Vector hits carry cosine distance; expose similarity (higher is better).
                entry["score"] = round(1 - float(score), 4)
        except Exception:
            pass
        return entry

    async def _extract_query_entities(self, query: str) -> Dict[str, Any]:
        """LLM: split query into ``subjects`` + ``attributes``, each attribute bound
        to the subject it belongs to.

        Falls back to the whole sentence as a single subject anchor on timeout/failure.
        Returns ``{"subjects": [...], "attributes": [{"term", "subject"}]}``.
        """
        prompt = QUERY_ENTITY_EXTRACTION_PROMPT.format(query=query)
        try:
            result = await asyncio.wait_for(
                LLMGateway.acreate_structured_output(
                    text_input=prompt,
                    system_prompt="你是实体抽取助手。把用户问题拆成主体与属性，并绑定每个属性归属的主体。",
                    response_model=QueryEntities,
                ),
                timeout=self.entity_extraction_timeout,
            )
            subjects = [str(s).strip() for s in getattr(result, "subjects", []) if str(s).strip()]
            subjects = list(dict.fromkeys(subjects))[:5]
            attributes = []
            for ref in getattr(result, "attributes", []) or []:
                term = (getattr(ref, "term", "") or "").strip()
                if not term:
                    continue
                bound = (getattr(ref, "subject", "") or "").strip() or None
                if bound is None and subjects:
                    bound = subjects[0]
                attributes.append({"term": term, "subject": bound})
            clarification = (getattr(result, "clarification_request", None) or "").strip() or None
            return {
                "subjects": subjects,
                "attributes": attributes,
                "clarification_request": clarification,
            }
        except Exception as error:
            logger.warning("Query entity extraction failed (attempt 1): %s", error, exc_info=True)
            try:
                retry_prompt = QUERY_ENTITY_EXTRACTION_PROMPT.format(query=query) + (
                    "\n\n重要：你的前一次输出包含了解释性文字或思考过程，"
                    "系统无法解析。请严格遵守规则 6，只输出纯 JSON，"
                    "不要任何解释、不要 markdown 代码块、不要 <think> 标签。"
                )
                result = await asyncio.wait_for(
                    LLMGateway.acreate_structured_output(
                        text_input=retry_prompt,
                        system_prompt="你是实体抽取助手。只输出 JSON，不要任何额外内容。",
                        response_model=QueryEntities,
                    ),
                    timeout=self.entity_extraction_timeout,
                )
                subjects = [
                    str(s).strip() for s in getattr(result, "subjects", []) if str(s).strip()
                ]
                subjects = list(dict.fromkeys(subjects))[:5]
                attributes = []
                for ref in getattr(result, "attributes", []) or []:
                    term = (getattr(ref, "term", "") or "").strip()
                    if not term:
                        continue
                    bound = (getattr(ref, "subject", "") or "").strip() or None
                    attributes.append({"term": term, "subject": bound})
                clarification = (
                    getattr(result, "clarification_request", None) or ""
                ).strip() or None
                return {
                    "subjects": subjects,
                    "attributes": attributes,
                    "clarification_request": clarification,
                }
            except Exception as retry_error:
                logger.warning(
                    "Query entity extraction retry also failed: %s", retry_error, exc_info=True
                )
                return {"subjects": [], "attributes": []}

    @staticmethod
    def _norm_key(value: Optional[str]) -> str:
        """Normalise a subject string so ``HYR-111`` == ``hyr111`` for binding lookups."""
        if not value:
            return ""
        return "".join(ch.lower() for ch in str(value) if ch.isalnum())

    async def _source_context(self, entity_id: Optional[str]) -> Optional[Tuple[set, set]]:
        """Collect the source context of an entity's chunks via a depth-2 neighborhood.

        Returns ``(source_keys, chunk_ids)`` where ``source_keys`` is the set of
        document keys the entity is attached to (a chunk's ``document_id`` /
        ``document_name`` field plus the id of its parent Document node) and
        ``chunk_ids`` is the set of directly connected chunk ids. Two entities
        count as co-document when their ``source_keys`` intersect, and as
        co-chunk when their ``chunk_ids`` intersect. Returns ``None`` when the
        graph lookup failed so callers can fail-open.
        """
        ids = [str(entity_id)] if entity_id else []
        if not ids:
            return set(), set()
        try:
            nodes, _ = await self._unified_engine.graph.get_neighborhood(ids, depth=2)
        except Exception as error:
            logger.debug("Source-context lookup for entity failed: %s", error)
            return None
        source_keys: set = set()
        chunk_ids: set = set()
        for node in nodes or []:
            props = node[1] if isinstance(node, (list, tuple)) and len(node) > 1 else {}
            node_type = props.get("type", "")
            node_id = str(props.get("id") or (node[0] if node else ""))
            if node_type == "DocumentChunk":
                chunk_ids.add(node_id)
                doc = props.get("document_id") or props.get("document_name")
                if doc:
                    source_keys.add(str(doc))
            elif node_type not in ("Entity", "ChunkWiki"):
                # Parent Document node (TextDocument/PdfDocument/...); its id is the
                # same value chunks reference via document_id.
                if node_id:
                    source_keys.add(node_id)
        return source_keys, chunk_ids

    async def _filter_by_subject_documents(
        self,
        anchor_entries: List[Dict[str, Any]],
        candidate_entries: List[Dict[str, Any]],
    ) -> tuple:
        """Keep only candidates that share a source document with their bound subject
        (or with any subject when unbound). Returns ``(kept, dropped, subject_docs)``.

        ``subject_docs`` maps each anchor entity name to its source keys; the
        candidate's ``bound_subject`` is normalised to pick the matching anchor set.
        A candidate is kept when it shares at least one source key (same document)
        or chunk id (same chunk) with the target; each kept entry gets a
        ``coherence`` bit (1 = shares a chunk, 0 = shares only a document) used to
        rank same-name entities. Fail-open: any failed graph lookup keeps the
        candidate instead of dropping it.
        """
        anchor_by_key = {}
        subject_docs: Dict[str, list] = {}
        subject_chunks: Dict[str, list] = {}
        anchor_lookup_ok: Dict[str, bool] = {}
        for anchor in anchor_entries:
            anchor_key = self._norm_key(anchor.get("anchor_term"))
            if anchor_key and anchor_key not in anchor_by_key:
                anchor_by_key[anchor_key] = anchor
            term = anchor.get("anchor_term") or anchor.get("name")
            if not term:
                continue
            anchor_name = anchor.get("name", "")
            term_lower = term.lower()
            name_lower = anchor_name.lower()
            if term_lower not in name_lower and name_lower not in term_lower:
                continue
            context = await self._source_context(anchor.get("id"))
            anchor_lookup_ok[term] = context is not None
            docs, chunks = context or (set(), set())
            if term not in subject_docs:
                subject_docs[term] = set()
                subject_chunks[term] = set()
            subject_docs[term] |= set(docs)
            subject_chunks[term] |= set(chunks)

        all_keys = set()
        all_chunks = set()
        for docs, chunks in zip(subject_docs.values(), subject_chunks.values()):
            all_keys |= set(docs)
            all_chunks |= set(chunks)

        kept: List[Dict[str, Any]] = []
        dropped: List[Dict[str, Any]] = []
        for cand in candidate_entries:
            context = await self._source_context(cand.get("id"))
            if context is None:
                kept.append(cand)
                continue
            cand_keys, cand_chunks = context
            bound = cand.get("bound_subject")
            anchor = anchor_by_key.get(self._norm_key(bound)) if bound else None
            if anchor is not None:
                subject_key = anchor.get("anchor_term") or anchor.get("name")
                if anchor_lookup_ok.get(subject_key):
                    target = set(subject_docs.get(subject_key, []))
                    if not target:
                        kept.append(cand)
                        continue
                    shared_chunks = cand_chunks & set(subject_chunks.get(subject_key, []))
                    shared_keys = cand_keys & target
                    multi_doc = len(target) > 1
                    if multi_doc:
                        broader_keys = cand_keys & all_keys
                        if shared_chunks or shared_keys or broader_keys:
                            cand["coherence"] = 1 if shared_chunks else (0 if shared_keys else -1)
                            cand["related_subject"] = anchor.get("name")
                            kept.append(cand)
                        else:
                            dropped.append(
                                {
                                    "name": cand.get("name"),
                                    "reason": f"source-doc mismatch vs subject {anchor.get('name')}",
                                }
                            )
                    else:
                        if shared_chunks or shared_keys:
                            cand["coherence"] = 1 if shared_chunks else 0
                            cand["related_subject"] = anchor.get("name")
                            kept.append(cand)
                        else:
                            dropped.append(
                                {
                                    "name": cand.get("name"),
                                    "reason": f"source-doc mismatch vs subject {anchor.get('name')}",
                                }
                            )
                    continue
            shared_chunks = cand_chunks & all_chunks
            shared_keys = cand_keys & all_keys
            if shared_chunks or shared_keys:
                cand["coherence"] = 1 if shared_chunks else 0
                if bound:
                    cand["related_subject"] = bound
                kept.append(cand)
            else:
                dropped.append(
                    {"name": cand.get("name"), "reason": "no source-doc overlap with any subject"}
                )
        return kept, dropped, subject_docs

    async def _collect_subject_docs_by_name(
        self, subjects: List[str]
    ) -> Dict[str, set]:
        """Collect subject document ids by literal (substring) entity-name match.

        This is the stable upstream source for the Step-2b subject whitelist.
        Instead of re-deriving subject documents from whichever entity vector
        hits happened to be selected (which jitters run-to-run), we scan the
        graph for every Entity whose ``name`` literally contains the LLM-extracted
        subject word and take the union of the documents those entities belong to.

        Pure literal matching (no synonym/semantic expansion): user said "find
        what literally matches". Foreign-product documents that happen to share a
        subject-mentioning entity are intentionally NOT excluded here — the
        existing chunk-level Step-2b filter drops them downstream.

        Returns ``{subject_word: {document_id, ...}}``; fails open to empty.
        """
        if not subjects:
            return {}
        graph = getattr(self, "_unified_engine", None)
        if graph is None or not hasattr(graph, "graph"):
            return {}
        graph_conn = graph.graph
        if graph_conn is None or not hasattr(graph_conn, "query"):
            return {}

        dataset_id = current_dataset_id.get()
        result: Dict[str, set] = {}
        dataset_clause = (
            "AND $dataset_id IN coalesce(e.source_dataset_ids, [])"
            if dataset_id
            else ""
        )
        cql = (
            "MATCH (e:Entity) "
            "WHERE e.name CONTAINS $subj "
            f"{dataset_clause} "
            "OPTIONAL MATCH (c:DocumentChunk)-[:contains]->(e) "
            "RETURN collect(DISTINCT c.document_id) AS all_docs, "
            "       collect(DISTINCT e.name) AS matched_names"
        )
        for subj in subjects:
            if not subj:
                continue
            try:
                params: Dict[str, Any] = {"subj": subj}
                if dataset_id:
                    params["dataset_id"] = str(dataset_id)
                rows = await graph_conn.query(cql, params)
                docs = set()
                names = set()
                for row in rows or []:
                    if not isinstance(row, dict):
                        continue
                    for v in row.get("all_docs") or []:
                        if v:
                            docs.add(v)
                    for n in row.get("matched_names") or []:
                        if n:
                            names.add(n)
                result[subj] = docs
                if docs:
                    logger.info(
                        "SUBJECT_DOCS_BY_NAME subject=%s docs=%d names=%s",
                        subj,
                        len(docs),
                        sorted(names),
                    )
            except Exception as error:
                logger.warning(
                    "Subject-doc-by-name lookup failed for '%s': %s", subj, error
                )
                result[subj] = set()
        return result

    def _dedupe_rank_entities(
        self, entries: List[Dict[str, Any]], limit: int
    ) -> List[Dict[str, Any]]:
        """Merge entity hits: dedupe by name (keep best coherence, then similarity),
        rank by (coherence desc, similarity desc)."""

        def _key(entry: Dict[str, Any]) -> tuple:
            coherence = entry.get("coherence", 0)
            if not isinstance(coherence, (int, float)):
                coherence = 0
            score = entry.get("score")
            if not isinstance(score, (int, float)):
                score = float("-inf")
            return (coherence, score)

        best_by_name: Dict[str, Dict[str, Any]] = {}
        ordered: List[str] = []
        for entry in entries:
            name = entry.get("name")
            if not name:
                continue
            if name not in best_by_name:
                best_by_name[name] = dict(entry)
                ordered.append(name)
            elif _key(entry) > _key(best_by_name[name]):
                best_by_name[name] = dict(entry)
        ranked = sorted(
            (best_by_name[name] for name in ordered),
            key=_key,
            reverse=True,
        )
        return ranked[:limit]

    def _build_paths(self, edges, chunk_nodes, entity_nodes, chunk_wiki_pairs) -> list:
        """Compact representative 2-hop paths (Entity → Chunk → Wiki) for trace.

        Uses ``contains`` edges (defensively, either direction) to map each chunk
        to its entity names, then takes up to 5 chunk_wiki_pairs that actually have
        wikis. Never raises: any failure degrades to an empty path list.
        """
        try:
            entity_id_by_name = {str(node.get("id")): node.get("name") for node in entity_nodes}
            chunk_entities: Dict[str, list] = {}
            chunk_id_set = {str(node.get("id")) for node in chunk_nodes}
            for edge in edges or []:
                if len(edge) < 3:
                    continue
                source_id, target_id, edge_type = str(edge[0]), str(edge[1]), edge[2]
                if edge_type != "contains":
                    continue
                # Entity --contains--> Chunk, or the chunk-side variant
                if target_id in chunk_id_set:
                    name = entity_id_by_name.get(source_id)
                    if name:
                        chunk_entities.setdefault(target_id, []).append(name)
                elif source_id in chunk_id_set:
                    name = entity_id_by_name.get(target_id)
                    if name:
                        chunk_entities.setdefault(source_id, []).append(name)

            paths = []
            for chunk, wikis in chunk_wiki_pairs:
                if not wikis:
                    continue
                chunk_id = str(chunk.get("id"))
                text = chunk.get("text") or ""
                paths.append(
                    {
                        "chunk_id": chunk_id,
                        "chunk_snippet": text[:80] if isinstance(text, str) else "",
                        "document_name": chunk.get("document_name"),
                        "entities": list(dict.fromkeys(chunk_entities.get(chunk_id, [])))[:6],
                        "wikis": [
                            {
                                "id": wiki.get("id"),
                                "summary": (wiki.get("summary") or "")[:120],
                            }
                            for wiki in wikis
                        ][:5],
                    }
                )
                if len(paths) >= 5:
                    break
            return paths
        except Exception as error:
            logger.debug("Failed to build trace paths: %s", error)
            return []


def _reject_query_batch(query_batch):
    if query_batch:
        raise QueryValidationError("Batch queries are not supported for WikiCompletionRetriever")
