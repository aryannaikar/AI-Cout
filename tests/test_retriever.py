"""
Integration tests for the LegalRetriever using realistic legal queries.
Tests realistic legal questions:
- stolen property
- forged documents
- electronic evidence
- constitutional provisions
"""

from pathlib import Path
import pytest

from rag.chunker import LegalAwareChunker
from rag.embeddings import EmbeddingModel
from rag.loader import PDFLoader
from rag.retriever import LegalRetriever
from rag.vector_store import LegalVectorStore
from rag.config import config


@pytest.fixture(scope="module")
def populated_test_retriever():
    """
    Use the persistent legal vector store for retrieval testing.
    """
    store = LegalVectorStore()
    emb_model = EmbeddingModel()
    if store.count() == 0:
        from rag.ingest import run_ingestion
        run_ingestion()
    return LegalRetriever(vector_store=store, embedding_model=emb_model, top_k=5)


def test_retrieval_stolen_property(populated_test_retriever):
    retriever = populated_test_retriever
    query = "What law applies to possession or receiving of stolen property?"
    results = retriever.retrieve(query=query, top_k=5)

    assert len(results) > 0
    top_result = results[0]
    assert top_result.score > 0.2

    # Must find BNS Section 317 or IT Act Section 66B (stolen computer resource)
    found_stolen_prov = any(
        "317" in (r.section or "") or "66B" in (r.section or "") or "stolen property" in r.text.lower()
        for r in results
    )
    assert found_stolen_prov, "Failed to retrieve Section 317 or stolen property provisions"

    # Verify citation format
    assert top_result.citation() is not None
    assert "Page" in top_result.citation()
    assert top_result.source_file.endswith(".pdf")


def test_retrieval_electronic_evidence(populated_test_retriever):
    retriever = populated_test_retriever
    query = "What provisions govern the admissibility of electronic records and digital evidence?"
    results = retriever.retrieve(query=query, top_k=5)

    assert len(results) > 0
    # Must retrieve BSA Section 61 or Section 63
    found_electronic = any(
        "bsa" in r.short_name.lower() and ("61" in (r.section or "") or "63" in (r.section or "") or "electronic" in r.text.lower())
        for r in results
    )
    assert found_electronic, "Failed to retrieve BSA electronic evidence provisions (Section 61/63)"


def test_retrieval_computer_tampering_and_hacking(populated_test_retriever):
    retriever = populated_test_retriever
    query = "What law deals with tampering with computer source code or unauthorized computer damage?"
    results = retriever.retrieve(query=query, top_k=5)

    assert len(results) > 0
    # Must retrieve IT Act Section 65 or 66
    found_it_act = any(
        "it_act" in r.short_name.lower() and any(sec in (r.section or "") for sec in ["65", "66", "43"])
        for r in results
    )
    assert found_it_act, "Failed to retrieve IT Act Section 65/66/43"


def test_retrieval_constitutional_liberty(populated_test_retriever):
    retriever = populated_test_retriever
    query = "What constitutional provision protects the right to life and personal liberty?"
    results = retriever.retrieve(query=query, top_k=5)

    assert len(results) > 0
    # Must retrieve Article 21
    found_art_21 = any(
        "21" in (r.article or "") or "personal liberty" in r.text.lower()
        for r in results
    )
    assert found_art_21, "Failed to retrieve Constitution Article 21"


def test_retrieval_act_filter(populated_test_retriever):
    retriever = populated_test_retriever
    query = "What punishment is given for murder?"
    results = retriever.retrieve(query=query, top_k=3, act_filter="BNS")

    assert len(results) > 0
    for r in results:
        assert r.short_name == "BNS"
        assert r.act_name == "Bharatiya Nyaya Sanhita, 2023"


def test_retrieval_empty_query(populated_test_retriever):
    retriever = populated_test_retriever
    assert retriever.retrieve("") == []
    assert retriever.retrieve("    ") == []


def test_retrieval_admissibility_of_evidence(populated_test_retriever):
    retriever = populated_test_retriever
    query = "What law governs admissibility of evidence?"
    results = retriever.retrieve(query=query, top_k=5)
    
    assert len(results) > 0
    # Must prioritize BSA Act
    assert results[0].short_name == "BSA", f"Expected BSA, got {results[0].short_name}"
    
    found_141 = any("141" in (r.section or "") for r in results)
    assert found_141, "Expected Section 141 to be retrieved"


def test_retrieval_relevant_evidence(populated_test_retriever):
    retriever = populated_test_retriever
    query = "Which provision determines whether evidence is relevant?"
    results = retriever.retrieve(query=query, top_k=5)
    
    assert len(results) > 0
    # Should prioritize BSA over BNS for relevance queries
    assert results[0].short_name == "BSA"


def test_retrieval_fabricating_false_evidence(populated_test_retriever):
    retriever = populated_test_retriever
    query = "What is the punishment for fabricating false evidence?"
    results = retriever.retrieve(query=query, top_k=5)
    
    assert len(results) > 0
    # Should prioritize BNS over BSA for punishment queries
    assert results[0].short_name == "BNS"
    # Section 229, 230, etc. deal with false evidence in BNS
    found_false_evidence = any("false evidence" in r.text.lower() for r in results)
    assert found_false_evidence, "Expected to retrieve false evidence provisions"
