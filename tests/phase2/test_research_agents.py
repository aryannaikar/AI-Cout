"""
Phase 2 Tests: Legal Research and Web Research Agents.
Verifies integration with Phase 1 LegalRetriever, citation grounding, and web query blindness guardrails.
"""

import pytest
from app.agents.legal_research_agent import LegalResearchAgent
from app.agents.web_research_agent import WebResearchAgent
from app.models.legal_models import LegalResearchResult, WebResearchResult
from rag.retriever import LegalRetriever


def test_legal_research_agent_prosecution_calls_retriever():
    agent = LegalResearchAgent(side="prosecution")
    result = agent.research("What constitutes dishonestly receiving stolen property under BNS?")

    assert isinstance(result, LegalResearchResult)
    assert result.side == "prosecution"
    assert len(result.applicable_provisions) > 0

    # Must preserve statutory citations and page numbers
    assert len(result.citations) > 0
    assert len(result.source_pages) > 0
    assert all(isinstance(p, int) for p in result.source_pages)

    # Top provision should be BNS Section 317
    top_p = result.applicable_provisions[0]
    assert "317" in top_p.section_or_article or "BNS" in top_p.short_name
    assert "Bharatiya Nyaya Sanhita" in top_p.act_name
    assert len(top_p.text) > 20
    assert len(top_p.relevance_reasoning) > 10


def test_legal_research_agent_defense_perspective():
    agent = LegalResearchAgent(side="defense")
    result = agent.research("What are the mandatory conditions for admissibility of electronic records?")

    assert isinstance(result, LegalResearchResult)
    assert result.side == "defense"
    assert len(result.applicable_provisions) > 0

    # Should retrieve BSA electronic provisions (Section 61/63) or IT Act
    found_electronic = any(
        "electronic" in p.text.lower() or "61" in p.section_or_article or "63" in p.section_or_article
        for p in result.applicable_provisions
    )
    assert found_electronic
    assert len(result.applicable_provisions[0].relevance_reasoning) > 10


def test_web_research_agent_output_schema():
    agent = WebResearchAgent(side="prosecution")
    result = agent.research("Supreme court precedent on electronic evidence certificate under Indian law")

    assert isinstance(result, WebResearchResult)
    assert result.side == "prosecution"
    assert len(result.sources) > 0

    top_src = result.sources[0]
    assert top_src.title
    assert top_src.url.startswith("http")
    assert top_src.passage_summary
    assert top_src.is_current is True


def test_web_research_blindness_guardrail_rejects_verdict_search():
    agent = WebResearchAgent(side="defense")

    # Trying to search for the hidden evaluation verdict must be blocked!
    with pytest.raises(PermissionError, match="BLIND EVALUATION VIOLATION"):
        agent.research("Jai Bhagwan v State of Haryana final judgment outcome")

    with pytest.raises(PermissionError, match="BLIND EVALUATION VIOLATION"):
        agent.research("What was the verdict in this case?")

    with pytest.raises(PermissionError, match="BLIND EVALUATION VIOLATION"):
        agent.research("actual court decision convicted or acquitted")
