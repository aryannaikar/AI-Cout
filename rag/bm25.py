"""
Pure-Python Okapi BM25 lexical index and Reciprocal Rank Fusion (RRF) for Hybrid Legal RAG.
Preserves exact statutory section/article tokens (e.g. '3(a)', '317', '65b', '411')
and enforces act_filter / act_filters at scoring time.
"""

from __future__ import annotations

import hashlib
import math
import pickle
import re
from collections import Counter
from pathlib import Path
from typing import Any, Optional, Sequence


_STOPWORDS = frozenset({
    "the", "of", "and", "in", "to", "a", "an", "for", "or", "by", "on", "is",
    "are", "was", "were", "be", "been", "with", "that", "this", "as", "at",
    "from", "under", "which", "who", "any", "such", "may", "shall", "not",
    "what", "how", "does", "law", "applies", "about", "regarding",
})


def tokenize_legal_text(text: str) -> list[str]:
    """
    Tokenize legal text while preserving section/article designations such as '3(a)', '65b', '317'.
    """
    lowered = text.lower()
    # Capture section/article numbers including parenthesized sub-clauses like 3(a), 65b, 304b
    raw_tokens = re.findall(r"[a-z0-9]+(?:\([a-z0-9]+\))?", lowered)
    tokens: list[str] = []
    for tok in raw_tokens:
        if tok in _STOPWORDS:
            continue
        tokens.append(tok)
        # Also emit base number if parenthesized, e.g. '3(a)' -> '3'
        if "(" in tok:
            base = tok.split("(", 1)[0]
            if base and base not in _STOPWORDS:
                tokens.append(base)
    return tokens


def extract_query_section_tokens(query: str) -> set[str]:
    """Extract explicit section or article identifiers from a query (e.g. '317', '3(a)', '21')."""
    matches = re.findall(
        r"(?:section|sec\.?|s\.|article|art\.?)\s*(\d+[a-z]?(?:\([a-z0-9]+\))?)",
        query,
        re.IGNORECASE,
    )
    return {m.lower() for m in matches}


class BM25Index:
    """In-memory Okapi BM25 index built over ChromaDB statutory chunks."""

    def __init__(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]],
        k1: float = 1.5,
        b: float = 0.75,
    ):
        # Deduplicate by chunk ID while preserving deterministic order
        seen_ids: set[str] = set()
        dedup_ids: list[str] = []
        dedup_docs: list[str] = []
        dedup_metas: list[dict[str, Any]] = []
        for cid, doc, meta in zip(ids, documents, metadatas):
            if cid in seen_ids:
                continue
            seen_ids.add(cid)
            dedup_ids.append(cid)
            dedup_docs.append(doc)
            dedup_metas.append(meta)

        self.ids = dedup_ids
        self.documents = dedup_docs
        self.metadatas = dedup_metas
        self.k1 = k1
        self.b = b
        self.n_docs = len(dedup_docs)
        self.id_digest = self.compute_id_digest(dedup_ids)

        self.doc_tokens: list[Counter[str]] = []
        self.doc_lens: list[int] = []
        self.df: Counter[str] = Counter()

        for doc, meta in zip(dedup_docs, dedup_metas):
            # Include key metadata fields (section, article, title, act_name) in lexical representation
            meta_prefix = " ".join(
                str(meta.get(k, "")) for k in ("act_name", "short_name", "section", "article", "title") if meta.get(k)
            )
            toks = tokenize_legal_text(f"{meta_prefix} {doc}")
            tf = Counter(toks)
            self.doc_tokens.append(tf)
            self.doc_lens.append(len(toks))
            for term in tf:
                self.df[term] += 1

        self.avg_dl = (sum(self.doc_lens) / self.n_docs) if self.n_docs else 1.0
        self.idf: dict[str, float] = {
            term: math.log((self.n_docs - freq + 0.5) / (freq + 0.5) + 1.0)
            for term, freq in self.df.items()
        }

    @staticmethod
    def compute_id_digest(ids: list[str]) -> str:
        """Compute deterministic digest over sorted chunk IDs for cache invalidation."""
        h = hashlib.sha256()
        for cid in sorted(ids):
            h.update(cid.encode("utf-8", errors="ignore"))
            h.update(b"\n")
        return h.hexdigest()

    def save_cache(self, cache_path: Path) -> None:
        """Persist BM25 index to disk for fast restart."""
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "n_docs": self.n_docs,
            "id_digest": self.id_digest,
            "index": self,
        }
        with open(cache_path, "wb") as f:
            pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)

    @classmethod
    def load_cache(cls, cache_path: Path, expected_count: int, expected_digest: str) -> Optional["BM25Index"]:
        """Load cached BM25 index if count and ID digest match current ChromaDB state."""
        if not cache_path.exists():
            return None
        try:
            with open(cache_path, "rb") as f:
                payload = pickle.load(f)
            if payload.get("n_docs") == expected_count and payload.get("id_digest") == expected_digest:
                idx = payload.get("index")
                if isinstance(idx, cls):
                    return idx
        except Exception:
            return None
        return None

    def search(
        self,
        query: str,
        top_k: int = 20,
        act_filter: Optional[str] = None,
        act_filters: Optional[Sequence[str]] = None,
    ) -> list[tuple[str, float, str, dict[str, Any]]]:
        """
        Return top_k matches as (chunk_id, bm25_score, document, metadata),
        strictly filtered by act_filter / act_filters.
        """
        if not self.n_docs or not query.strip():
            return []

        q_tokens = tokenize_legal_text(query)
        if not q_tokens:
            return []

        allowed_acts: Optional[set[str]] = None
        if act_filters:
            allowed_acts = set(act_filters)
        elif act_filter:
            allowed_acts = {act_filter}

        query_secs = extract_query_section_tokens(query)
        scored: list[tuple[str, float, str, dict[str, Any]]] = []

        for idx in range(self.n_docs):
            meta = self.metadatas[idx]
            if allowed_acts is not None and meta.get("short_name") not in allowed_acts:
                continue

            tf = self.doc_tokens[idx]
            dl = self.doc_lens[idx] or 1
            score = 0.0
            for term in q_tokens:
                if term not in tf:
                    continue
                freq = tf[term]
                idf = self.idf.get(term, 0.0)
                denom = freq + self.k1 * (1.0 - self.b + self.b * (dl / self.avg_dl))
                score += idf * ((freq * (self.k1 + 1.0)) / denom)

            # Exact section/article metadata match boost
            if query_secs:
                prov = str(meta.get("section") or meta.get("article") or "").lower()
                prov_num_match = re.search(r"(\d+[a-z]?(?:\([a-z0-9]+\))?)", prov)
                if prov_num_match and prov_num_match.group(1) in query_secs:
                    score += 5.0

            if score > 0.0:
                scored.append((self.ids[idx], score, self.documents[idx], meta))

        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]


def reciprocal_rank_fusion(
    dense_results: list[Any],
    bm25_results: list[tuple[str, float, str, dict[str, Any]]],
    result_factory: Any,
    rrf_k: int = 60,
    dense_weight: float = 1.0,
    bm25_weight: float = 1.0,
) -> list[Any]:
    """
    Fuse dense and BM25 ranked lists via weighted Reciprocal Rank Fusion (RRF).
    Preserves original dense/bm25 ranks and scores in metadata without conflating scales.
    """
    by_id: dict[str, Any] = {}
    rrf_scores: dict[str, float] = {}
    dense_ranks: dict[str, tuple[int, float]] = {}
    bm25_ranks: dict[str, tuple[int, float]] = {}

    for rank, res in enumerate(dense_results, start=1):
        cid = res.chunk_id
        if cid in dense_ranks:
            continue
        by_id[cid] = res
        dense_ranks[cid] = (rank, float(res.score))
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (dense_weight / (rrf_k + rank))

    for rank, (cid, bm25_score, doc_text, meta) in enumerate(bm25_results, start=1):
        if cid in bm25_ranks:
            continue
        bm25_ranks[cid] = (rank, float(bm25_score))
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (bm25_weight / (rrf_k + rank))
        if cid not in by_id:
            by_id[cid] = result_factory(cid, doc_text, meta, distance=1.0)

    fused: list[Any] = []
    for cid, score in sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True):
        item = by_id[cid]
        item.score = float(score)
        meta = dict(item.metadata)
        meta["rrf_score"] = float(score)
        meta["retrieval_method"] = "hybrid_rrf"
        if cid in dense_ranks:
            meta["dense_rank"] = dense_ranks[cid][0]
            meta["dense_score"] = dense_ranks[cid][1]
        if cid in bm25_ranks:
            meta["bm25_rank"] = bm25_ranks[cid][0]
            meta["bm25_score"] = bm25_ranks[cid][1]
        item.metadata = meta
        fused.append(item)

    return fused
