"""
Phase 2 Hybrid Legal RAG — Test Suite.
Validates:
1. Legal-aware BM25 tokenization and exact section/article matching.
2. Reciprocal Rank Fusion (RRF) of dense + BM25 results.
3. Strict act_filter / act_filters enforcement across both dense and BM25.
4. Cross-encoder reranker integration and graceful fallback.
5. End-to-end Hybrid LegalRetriever on the live ChromaDB statutory corpus.
"""

from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import MagicMock

_ROOT = Path(__file__).resolve().parents[1]
_BACKEND = _ROOT / "backend"
for p in (str(_ROOT), str(_BACKEND)):
    if p not in sys.path:
        sys.path.insert(0, p)

from rag.bm25 import BM25Index, extract_query_section_tokens, reciprocal_rank_fusion, tokenize_legal_text
from rag.reranker import LegalReranker
from rag.retriever import LegalRetriever, RetrievalResult


def test_legal_tokenizer_preserves_section_numbers():
    tokens = tokenize_legal_text("Section 3(a) of Railway Property Act and Section 65B")
    assert "3(a)" in tokens
    assert "3" in tokens
    assert "65b" in tokens
    secs = extract_query_section_tokens("ingredients of Section 317 BNS and Section 3(a)")
    assert "317" in secs
    assert "3(a)" in secs


def test_bm25_act_filters_prevent_era_leakage():
    ids = ["bns_317", "bsa_63", "const_21"]
    docs = [
        "Whoever dishonestly receives or retains any stolen property shall be punished.",
        "Electronic record admissibility certificate requirements.",
        "Protection of life and personal liberty.",
    ]
    metas = [
        {"short_name": "BNS", "act_name": "Bharatiya Nyaya Sanhita, 2023", "section": "Section 317"},
        {"short_name": "BSA", "act_name": "Bharatiya Sakshya Adhiniyam, 2023", "section": "Section 63"},
        {"short_name": "Constitution", "act_name": "Constitution of India", "article": "Article 21"},
    ]
    idx = BM25Index(ids=ids, documents=docs, metadatas=metas)

    # Historical act_filters must exclude BNS and BSA
    hist_hits = idx.search("stolen property Section 317", top_k=5, act_filters=("IPC", "IEA", "Constitution"))
    assert all(hit[3]["short_name"] not in {"BNS", "BSA"} for hit in hist_hits)

    # Exact section boost ranks BNS 317 first when BNS is permitted
    bns_hits = idx.search("Section 317 stolen property", top_k=5, act_filter="BNS")
    assert len(bns_hits) == 1
    assert bns_hits[0][0] == "bns_317"


def test_reciprocal_rank_fusion_combines_dense_and_bm25():
    dense = [
        RetrievalResult(
            chunk_id="c1", text="Dense top", act_name="BNS", short_name="BNS",
            section="Section 303", article=None, title=None, chapter=None, part=None,
            page=1, source_file="bns.pdf", score=0.9, distance=0.2, metadata={},
        ),
        RetrievalResult(
            chunk_id="c2", text="Both hit", act_name="BNS", short_name="BNS",
            section="Section 317", article=None, title=None, chapter=None, part=None,
            page=2, source_file="bns.pdf", score=0.8, distance=0.4, metadata={},
        ),
    ]
    bm25 = [
        ("c2", 8.5, "Both hit", {"act_name": "BNS", "short_name": "BNS", "section": "Section 317", "page": 2, "source_file": "bns.pdf"}),
        ("c3", 6.0, "BM25 only", {"act_name": "BNS", "short_name": "BNS", "section": "Section 318", "page": 3, "source_file": "bns.pdf"}),
    ]
    fused = reciprocal_rank_fusion(
        dense_results=dense,
        bm25_results=bm25,
        result_factory=LegalRetriever._build_result,
        rrf_k=60,
    )
    assert [r.chunk_id for r in fused][0] == "c2"
    assert len(fused) == 3
    assert "rrf_score" in fused[0].metadata


def test_reranker_graceful_fallback_and_scoring():
    results = [
        RetrievalResult(
            chunk_id="a", text="Low relevance", act_name="BNS", short_name="BNS",
            section="Section 1", article=None, title=None, chapter=None, part=None,
            page=1, source_file="bns.pdf", score=0.9, distance=0.2, metadata={},
        ),
        RetrievalResult(
            chunk_id="b", text="High relevance stolen property", act_name="BNS", short_name="BNS",
            section="Section 317", article=None, title=None, chapter=None, part=None,
            page=2, source_file="bns.pdf", score=0.5, distance=1.0, metadata={},
        ),
    ]
    reranker = LegalReranker(model_name="mock-reranker")
    reranker._model_cache["mock-reranker"] = MagicMock(predict=lambda pairs: [0.1, 0.95])
    reranked = reranker.rerank("stolen property", results)
    assert reranked[0].chunk_id == "b"
    assert reranked[0].score == 0.95
    assert reranker.last_status == "applied"
    assert reranked[0].metadata["reranker_status"] == "applied"

    # Explicit fallback when reranker fails or is unavailable
    broken_reranker = LegalReranker(model_name="nonexistent-local-model-xyz")
    broken_reranker._load_failed = True
    broken_reranker.last_status = "fallback_unavailable"
    fallback_res = broken_reranker.rerank("stolen property", results)
    assert broken_reranker.last_status == "fallback_unavailable"
    assert all(r.metadata["reranker_status"] == "fallback_unavailable" for r in fallback_res)


def test_rrf_mathematical_correctness_and_rank_preservation():
    """Verify exact RRF formula: w_d/(k+r_d) + w_b/(k+r_b) and metadata rank preservation."""
    dense = [
        RetrievalResult(
            chunk_id="d1", text="D1", act_name="BNS", short_name="BNS",
            section="Section 10", article=None, title=None, chapter=None, part=None,
            page=1, source_file="bns.pdf", score=0.95, distance=0.1, metadata={},
        ),
        RetrievalResult(
            chunk_id="d2", text="D2", act_name="BNS", short_name="BNS",
            section="Section 20", article=None, title=None, chapter=None, part=None,
            page=2, source_file="bns.pdf", score=0.80, distance=0.4, metadata={},
        ),
    ]
    bm25 = [
        ("d2", 12.0, "D2", {"act_name": "BNS", "short_name": "BNS", "section": "Section 20", "page": 2, "source_file": "bns.pdf"}),
        ("d3", 9.0, "D3", {"act_name": "BNS", "short_name": "BNS", "section": "Section 30", "page": 3, "source_file": "bns.pdf"}),
    ]
    fused = reciprocal_rank_fusion(
        dense_results=dense,
        bm25_results=bm25,
        result_factory=LegalRetriever._build_result,
        rrf_k=60,
        dense_weight=1.0,
        bm25_weight=1.0,
    )
    # d2 appears at dense rank 2 (1/62) + bm25 rank 1 (1/61) = 0.0325225...
    # d1 appears at dense rank 1 only (1/61) = 0.0163934...
    # d3 appears at bm25 rank 2 only (1/62) = 0.0161290...
    assert [r.chunk_id for r in fused] == ["d2", "d1", "d3"]
    assert abs(fused[0].score - (1.0 / 62 + 1.0 / 61)) < 1e-9
    assert fused[0].metadata["dense_rank"] == 2
    assert fused[0].metadata["bm25_rank"] == 1
    assert fused[0].metadata["retrieval_method"] == "hybrid_rrf"


def test_bm25_cache_persistence_and_invalidation(tmp_path):
    """BM25 cache loads on matching digest and invalidates when chunk IDs change."""
    ids = ["c1", "c2", "c1"]  # includes duplicate ID to verify deduplication
    docs = ["Theft of property", "Dishonestly receiving stolen property", "Duplicate"]
    metas = [
        {"short_name": "BNS", "section": "Section 303"},
        {"short_name": "BNS", "section": "Section 317"},
        {"short_name": "BNS", "section": "Section 303"},
    ]
    idx = BM25Index(ids=ids, documents=docs, metadatas=metas)
    assert idx.n_docs == 2

    cache_file = tmp_path / "bm25_cache.pkl"
    idx.save_cache(cache_file)
    loaded = BM25Index.load_cache(cache_file, expected_count=2, expected_digest=idx.id_digest)
    assert loaded is not None
    assert loaded.n_docs == 2

    # Invalidation on changed count or digest
    assert BM25Index.load_cache(cache_file, expected_count=3, expected_digest=idx.id_digest) is None
    assert BM25Index.load_cache(cache_file, expected_count=2, expected_digest="wrong-digest") is None


def test_legal_research_agent_surfaces_retrieval_and_reranker_status():
    """LegalResearchAgent propagates retrieval_method, reranker_status, and source_type."""
    from app.agents.legal_research_agent import LegalResearchAgent

    mock_hit = RetrievalResult(
        chunk_id="bsa_63",
        text="Any information contained in an electronic record shall be deemed a document...",
        act_name="Bharatiya Sakshya Adhiniyam, 2023",
        short_name="BSA",
        section="Section 63",
        article=None,
        title="Admissibility of electronic records",
        chapter=None,
        part=None,
        page=18,
        source_file="BSA.pdf",
        score=0.88,
        distance=0.24,
        metadata={"retrieval_method": "hybrid_rrf", "reranker_status": "applied"},
    )
    mock_retriever = MagicMock()
    mock_retriever.last_retrieval_method = "hybrid_rrf"
    mock_retriever.last_reranker_status = "applied"
    mock_retriever.retrieve.return_value = [mock_hit]

    agent = LegalResearchAgent(side="prosecution", retriever=mock_retriever)
    res = agent.research(question="Section 63 BSA electronic record", is_historical=False)
    assert res.status == "completed"
    assert res.retrieval_method == "hybrid_rrf"
    assert res.reranker_status == "applied"
    assert res.applicable_provisions[0].source_type == "verified_statute"


def test_live_hybrid_retriever_exact_sections():
    """Live hybrid retrieval against ChromaDB must surface exact sections cleanly."""
    retriever = LegalRetriever(top_k=5, enable_hybrid=True, enable_reranker=False)
    results = retriever.retrieve("Section 317 stolen property", top_k=5, act_filter="BNS")
    assert len(results) >= 1
    assert any((r.section or "").lower().endswith("317") or "317" in r.text for r in results)
    assert all("rrf_score" in r.metadata for r in results)
