"""
Reusable Legal Retriever for future AI Court Agents.
Provides semantic search over Indian statutes with citation grounding and metadata preservation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional, Sequence

from rag.config import config
from rag.embeddings import EmbeddingModel
from rag.vector_store import LegalVectorStore
from rag.query_processor import QueryProcessor

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

    def __init__(
        self,
        vector_store: Optional[LegalVectorStore] = None,
        embedding_model: Optional[EmbeddingModel] = None,
        top_k: Optional[int] = None,
    ):
        self.vector_store = vector_store or LegalVectorStore()
        self.embedding_model = embedding_model or EmbeddingModel()
        self.top_k = top_k or config.retrieval_top_k
        self.query_processor = QueryProcessor()

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        act_filter: Optional[str] = None,
        act_filters: Optional[Sequence[str]] = None,
    ) -> list[RetrievalResult]:
        """
        Retrieve the most relevant legal provisions for a given query.

        Args:
            query: Natural language query (e.g. "What law applies to stolen property?").
            top_k: Number of results to return (overrides default).
            act_filter: Optional statute filter (e.g. "BNS", "BSA", "IT_Act", "Constitution").
            act_filters: Optional set of permitted statutes. This is applied at
                retrieval time, not after ranking, so incompatible statutes
                cannot enter a historical case's research result.

        Returns:
            List of RetrievalResult objects sorted by descending relevance.
        """
        k = top_k or self.top_k
        query = query.strip()
        if not query:
            return []

        # Generate dense query embedding
        query_vec = self.embedding_model.encode([query])[0]

        # Build optional metadata filter
        where: Optional[dict] = None
        
        # Process query
        processed_query = self.query_processor.process(query)
        
        # Use provided filter, or fall back to suggested act if any
        final_act_filter = act_filter or processed_query.suggested_act
        
        if act_filters:
            where = {"short_name": {"$in": list(act_filters)}}
        elif final_act_filter:
            where = {"short_name": final_act_filter}

        # Query ChromaDB
        search_res = self.vector_store.search(
            query_embedding=query_vec,
            n_results=k,
            where=where,
        )

        results: list[RetrievalResult] = []

        if not search_res or not search_res.get("ids") or not search_res["ids"][0]:
            return results

        ids = search_res["ids"][0]
        documents = search_res["documents"][0]
        metadatas = search_res["metadatas"][0]
        distances = search_res["distances"][0] if "distances" in search_res and search_res["distances"] else [0.0] * len(ids)

        for chunk_id, doc_text, meta, dist in zip(ids, documents, metadatas, distances):
            # Chroma default metric is squared L2 distance.
            # For L2 normalized vectors, squared L2 = 2 * (1 - cosine_similarity).
            # Therefore, cosine_similarity = 1.0 - (dist / 2.0).
            score = 1.0 - (float(dist) / 2.0)

            sec = meta.get("section") or None
            art = meta.get("article") or None

            res = RetrievalResult(
                chunk_id=chunk_id,
                text=doc_text,
                act_name=meta.get("act_name", "Unknown Statute"),
                short_name=meta.get("short_name", ""),
                section=sec,
                article=art,
                title=meta.get("title") or None,
                chapter=meta.get("chapter") or None,
                part=meta.get("part") or None,
                page=int(meta.get("page", 1)),
                source_file=meta.get("source_file", ""),
                score=score,
                distance=float(dist),
                metadata=meta,
            )
            results.append(res)

        return results

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
