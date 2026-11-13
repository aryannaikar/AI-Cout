"""
Phase 4 Tests: Pipeline Isolation and Guardrails (Tests 25-26).
Verifies that:
- Web research remains strictly blind to case outcomes
- Legal RAG operates independently against the statutory corpus without Ground Truth
"""

import pytest
from app.agents.web_research_agent import WebResearchAgent
from rag.retriever import LegalRetriever


def test_25_web_research_remains_blind():
    """Verify that WebResearchAgent rejects queries attempting to discover the actual case verdict."""
    agent = WebResearchAgent(side="prosecution")

    forbidden_queries = [
        "What was the real verdict in State v Ramesh Kumar?",
        "actual judgment outcome Ramesh Kumar trial",
        "did the court convict Ramesh Kumar in 2024?",
        "ground truth verdict State of Maharashtra v Ramesh",
    ]

    for q in forbidden_queries:
        with pytest.raises(PermissionError):
            agent.validate_query(q)


def test_26_rag_remains_independent_and_functional():
    """Verify LegalRetriever queries statutory provisions directly and returns genuine law."""
    retriever = LegalRetriever()
    results = retriever.retrieve("receiving stolen property", top_k=3)

    assert len(results) > 0
    # Must retrieve statutory sections
    found_statute = False
    for res in results:
        meta = res.metadata
        assert "ground_truth" not in str(meta).lower()
        if "BNS" in meta.get("act_name", "") or "Bharatiya" in meta.get("act_name", ""):
            found_statute = True
    assert found_statute, "RAG failed to retrieve relevant statutory law"
