"""
Reusable Legal Retriever for future AI Court Agents.
Provides semantic search over Indian statutes with citation grounding and metadata preservation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional, Sequence

from rag.bm25 import BM25Index, extract_query_section_tokens, reciprocal_rank_fusion
from rag.config import config
from rag.embeddings import EmbeddingModel
from rag.query_processor import QueryProcessor
from rag.reranker import LegalReranker
from rag.vector_store import LegalVectorStore

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """A grounded legal search result with statutory citation and relevance scoring."""

    chunk_id: str
    text: str
    act_name: str
    short_name: str
    section: Optional[str]
    article: Optional[str]
    title: Optional[str]
    chapter: Optional[str]
    part: Optional[str]
    page: int
    source_file: str
    score: float
    distance: float
    metadata: dict[str, Any]

    def citation(self) -> str:
        """Format an authoritative legal citation for court proceedings."""
        provision = self.section or self.article or "General Provision"
        title_suffix = f" ({self.title})" if self.title and self.title != provision else ""
        return f"{self.act_name}, {provision}{title_suffix} [Page {self.page}, Source: {self.source_file}]"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary matching conceptual specification."""
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "metadata": {
                "act_name": self.act_name,
                "short_name": self.short_name,
                "section": self.section,
                "article": self.article,
                "title": self.title,
                "chapter": self.chapter,
                "part": self.part,
                "page": self.page,
                "source_file": self.source_file,
            },
            "score": round(self.score, 4),
            "distance": round(self.distance, 4),
            "citation": self.citation(),
        }


class LegalRetriever:
    """
    High-level, reusable retriever service. Future AI Court agents (Prosecutor, Defense, Judge)
    can call this to query Indian statutes without coupling to LangGraph or ChromaDB internals.
    """

    _bm25_process_cache: dict[tuple[str, int, str], BM25Index] = {}

    def __init__(
        self,
        vector_store: Optional[LegalVectorStore] = None,
        embedding_model: Optional[EmbeddingModel] = None,
        top_k: Optional[int] = None,
        reranker: Optional[LegalReranker] = None,
        enable_hybrid: bool = True,
        enable_reranker: Optional[bool] = None,
    ):
        self.vector_store = vector_store or LegalVectorStore()
        self.embedding_model = embedding_model or EmbeddingModel()
        self.top_k = top_k or config.retrieval_top_k
        self.query_processor = QueryProcessor()
        self.reranker = reranker or LegalReranker()
        self.enable_hybrid = enable_hybrid
        self.enable_reranker = config.use_reranker if enable_reranker is None else enable_reranker
        self._bm25_index: Optional[BM25Index] = None
        self._bm25_doc_count: int = -1
        self.last_retrieval_method: str = "not_run"
        self.last_reranker_status: str = "not_run"

    def _get_bm25_index(self) -> Optional[BM25Index]:
        """Lazily build/load BM25 index with process cache + disk persistence and invalidation."""
        if not self.enable_hybrid:
            return None
        try:
            current_count = self.vector_store.count() if hasattr(self.vector_store, "count") else -1
            if self._bm25_index is not None and current_count == self._bm25_doc_count:
                return self._bm25_index
            collection = getattr(self.vector_store, "collection", None)
            if collection is None or not hasattr(collection, "get"):
                return None

            col_name = getattr(self.vector_store, "collection_name", config.collection_name)
            persist_dir = getattr(self.vector_store, "persist_directory", config.vectorstore_dir)
            # Fetch IDs first for lightweight cache validation
            id_only = collection.get(include=[])
            ids = id_only.get("ids") or []
            if not ids:
                return None
            digest = BM25Index.compute_id_digest(ids)
            cache_key = (str(persist_dir), len(ids), digest)

            if cache_key in self._bm25_process_cache:
                self._bm25_index = self._bm25_process_cache[cache_key]
                self._bm25_doc_count = current_count
                return self._bm25_index

            from pathlib import Path
            cache_path = Path(persist_dir) / f".bm25_cache_{col_name}.pkl"
            cached = BM25Index.load_cache(cache_path, expected_count=len(ids), expected_digest=digest)
            if cached is not None:
                self._bm25_process_cache[cache_key] = cached
                self._bm25_index = cached
                self._bm25_doc_count = current_count
                return cached

            raw = collection.get(include=["documents", "metadatas"])
            docs = raw.get("documents") or []
            metas = raw.get("metadatas") or []
            if not docs:
                return None
            idx = BM25Index(ids=raw.get("ids") or ids, documents=docs, metadatas=metas)
            try:
                idx.save_cache(cache_path)
            except Exception:
                pass
            self._bm25_process_cache[cache_key] = idx
            self._bm25_index = idx
            self._bm25_doc_count = current_count
            return idx
        except Exception as e:
            logger.debug("BM25 index build skipped: %s", e)
            return None

    @staticmethod
    def _build_result(
        chunk_id: str,
        doc_text: str,
        meta: dict[str, Any],
        distance: float,
    ) -> RetrievalResult:
        score = 1.0 - (float(distance) / 2.0)
        return RetrievalResult(
            chunk_id=chunk_id,
            text=doc_text,
            act_name=meta.get("act_name", "Unknown Statute"),
            short_name=meta.get("short_name", ""),
            section=meta.get("section") or None,
            article=meta.get("article") or None,
            title=meta.get("title") or None,
            chapter=meta.get("chapter") or None,
            part=meta.get("part") or None,
            page=int(meta.get("page", 1)),
            source_file=meta.get("source_file", ""),
            score=score,
            distance=float(distance),
            metadata=dict(meta),
        )

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        act_filter: Optional[str] = None,
        act_filters: Optional[Sequence[str]] = None,
    ) -> list[RetrievalResult]:
        """
        Retrieve the most relevant legal provisions for a given query using
        Hybrid Search (Dense ChromaDB + BM25), Reciprocal Rank Fusion, and Cross-Encoder Reranking.
        """
        k = top_k or self.top_k
        query = query.strip()
        if not query:
            return []

        processed_query = self.query_processor.process(query)
        final_act_filter = act_filter or processed_query.suggested_act

        # Build optional metadata filter strictly before retrieval
        where: Optional[dict] = None
        if act_filters:
            where = {"short_name": {"$in": list(act_filters)}}
        elif final_act_filter:
            where = {"short_name": final_act_filter}

        candidate_k = max(k * 4, config.retrieval_candidate_k) if self.enable_hybrid else k

        # 1. Dense ChromaDB search
        query_vec = self.embedding_model.encode([query])[0]
        search_res = self.vector_store.search(
            query_embedding=query_vec,
            n_results=candidate_k,
            where=where,
        )

        dense_results: list[RetrievalResult] = []
        if search_res and search_res.get("ids") and search_res["ids"][0]:
            ids = search_res["ids"][0]
            documents = search_res["documents"][0]
            metadatas = search_res["metadatas"][0]
            distances = (
                search_res["distances"][0]
                if "distances" in search_res and search_res["distances"]
                else [0.0] * len(ids)
            )
            for chunk_id, doc_text, meta, dist in zip(ids, documents, metadatas, distances):
                dense_results.append(self._build_result(chunk_id, doc_text, meta, float(dist)))

        # 2. BM25 lexical search + 3. Reciprocal Rank Fusion
        bm25_index = self._get_bm25_index()
        if bm25_index is not None:
            bm25_results = bm25_index.search(
                query=query,
                top_k=candidate_k,
                act_filter=None if act_filters else final_act_filter,
                act_filters=act_filters,
            )
            has_section_ref = bool(extract_query_section_tokens(query))
            fused_results = reciprocal_rank_fusion(
                dense_results=dense_results,
                bm25_results=bm25_results,
                result_factory=self._build_result,
                rrf_k=config.hybrid_rrf_k,
                dense_weight=0.7 if has_section_ref else 2.2,
                bm25_weight=1.3 if has_section_ref else 0.4,
            )
            self.last_retrieval_method = "hybrid_rrf"
        else:
            fused_results = dense_results
            for rank, item in enumerate(fused_results, start=1):
                item.metadata = dict(item.metadata)
                item.metadata["dense_rank"] = rank
                item.metadata["dense_score"] = float(item.score)
                item.metadata["retrieval_method"] = "dense_only"
            self.last_retrieval_method = "dense_only"

        if not fused_results:
            self.last_reranker_status = "not_run"
            return []

        # 4. Cross-Encoder Reranking on top candidates
        if self.enable_reranker and self.reranker is not None:
            rerank_pool = fused_results[: max(k * 2, 10)]
            reranked = self.reranker.rerank(query, rerank_pool)
            self.last_reranker_status = self.reranker.last_status
            return reranked[:k]

        self.last_reranker_status = "skipped_disabled"
        for item in fused_results:
            item.metadata["reranker_status"] = "skipped_disabled"
        return fused_results[:k]

    @staticmethod
    def format_context_for_llm(results: list[RetrievalResult]) -> str:
        """
        Helper method to format retrieved results into a structured prompt context
        ready for LLM ingestion by future Courtroom Agents.
        """
        if not results:
            return "No relevant statutory provisions found."

        context_blocks = []
        for i, r in enumerate(results, start=1):
            block = (
                f"### [PROVISION {i}] {r.citation()}\n"
                f"- Act: {r.act_name}\n"
                f"- Provision: {r.section or r.article or 'N/A'}\n"
                f"- Page: {r.page}\n"
                f"```text\n{r.text}\n```"
            )
            context_blocks.append(block)

        return "\n\n".join(context_blocks)
