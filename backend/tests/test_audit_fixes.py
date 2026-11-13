"""
Unit and Integration Tests for Audit Fixes:
1. Historical statute selection (IPC/IEA vs BNS/BSA)
2. Shared SentenceTransformer singleton caching
3. OpenRouter client reuse, request counting, and usage tracking
4. API failure handling (no silent mock substitution)
5. Missing agent output detection in judge_node
6. Judge 12-section generation and document persistence
7. Authoritative web research precedent retrieval
"""

import json
from pathlib import Path
import tempfile
import pytest
from unittest.mock import MagicMock, patch

from app.core.llm_provider import LLMProvider, OpenRouterLLMClient
from app.graph.nodes import judge_node
from app.graph.state import CourtState
from app.models.case_models import Charge, StructuredCase
from app.models.conflict_models import ConflictReport
from app.models.evidence_models import EvidenceAnalysisReport
from app.models.judgment_models import DefenseCase, ProsecutionCase
from app.agents.judge_agent import JudgeAgent
from app.services.judgment_writer import JudgmentWriter
from app.services.legal_transition import (
    detect_case_legal_regime,
    get_defense_legal_research_query,
    get_prosecutor_legal_research_query,
    map_provision_to_historical,
)
from app.services.web_search_service import WebSearchService
from rag.embeddings import EmbeddingModel


def test_historical_statute_selection_2005_shabuddin():
    """Verify that a 2005 / IPC case is identified as historical and queries IPC / Evidence Act."""
    case = StructuredCase(
        case_id="SHABUDDIN-2005",
        case_title="Sd. Shabuddin v. State of Telangana",
        court_identifier="FIR No. 344/2005, PS City",
        allegations_summary="Accused committed murder using lethal weapon.",
        charges=[
            Charge(
                section="Section 302",
                statute="Indian Penal Code, 1860",
                description="Punishment for murder",
                accused_name="Sd. Shabuddin",
            )
        ],
        prosecution_facts=["Incident occurred on 12-08-2005.", "Recovery made on 15-08-2005."],
        defense_facts=["False implication, lack of eye-witnesses."],
    )

    regime = detect_case_legal_regime(case)
    assert regime["is_historical"] is True
    assert regime["penal_statute"] == "Indian Penal Code, 1860"
    assert regime["evidence_statute"] == "Indian Evidence Act, 1872"
    assert regime["procedure_statute"] == "Code of Criminal Procedure, 1973"

    # Defense query must reference Indian Evidence Act, NOT BSA
    def_query = get_defense_legal_research_query(case)
    assert "Indian Evidence Act 1872" in def_query
    assert "Bharatiya Sakshya Adhiniyam" not in def_query

    # Prosecution query must reference IPC
    pros_query = get_prosecutor_legal_research_query(case)
    assert "Section 302" in pros_query
    assert "Indian Penal Code" in pros_query

    # Judge adjudicating historical case
    agent = JudgeAgent()
    pros_case = ProsecutionCase(
        case_id="SHABUDDIN-2005",
        prosecution_theory="Accused committed homicidal act.",
        final_prayer="Conviction under Section 302 IPC.",
    )
    def_case = DefenseCase(
        case_id="SHABUDDIN-2005",
        defense_theory="Accused was not present; circumstantial chain broken.",
        alternative_interpretation="Third party acted alone without accused's involvement.",
        final_prayer="Acquittal on benefit of doubt.",
        reasonable_doubt_grounds=["Uncorroborated recovery"],
    )
    ev_report = EvidenceAnalysisReport(
        case_id="SHABUDDIN-2005",
        summary="Analysis of recovered weapon.",
        documentary_compliance_assessment="Recovery memo marked without independent civilian witness.",
        missing_evidence_gaps=["No independent public witnesses"],
    )
    conf_report = ConflictReport(
        case_id="SHABUDDIN-2005",
        summary="Contradictions noted.",
        total_conflicts=1,
        critical_conflicts_count=1,
    )

    judgment = agent.adjudicate(
        case=case,
        prosecution_case=pros_case,
        defense_case=def_case,
        evidence_report=ev_report,
        conflict_report=conf_report,
    )

    # Applicable law must cite Indian Evidence Act and IPC, not BSA
    assert any("Indian Evidence Act" in law for law in judgment.applicable_law)
    assert not any("Bharatiya Sakshya Adhiniyam" in law for law in judgment.applicable_law)


def test_modern_statute_selection_2024_bns():
    """Verify that a 2024+ BNS case uses Bharatiya Nyaya Sanhita & Bharatiya Sakshya Adhiniyam."""
    case = StructuredCase(
        case_id="CASE-2024-999",
        case_title="State v. New Accused",
        court_identifier="FIR No. 12/2024 (Dated 15-08-2024), PS Central",
        allegations_summary="Accused found in possession of stolen property.",
        charges=[
            Charge(
                section="Section 317",
                statute="Bharatiya Nyaya Sanhita, 2023",
                description="Receiving stolen property",
                accused_name="Accused",
            )
        ],
        prosecution_facts=["Seizure conducted on 16-08-2024."],
        defense_facts=["No conscious possession."],
    )

    regime = detect_case_legal_regime(case)
    assert regime["is_historical"] is False
    assert regime["penal_statute"] == "Bharatiya Nyaya Sanhita, 2023"
    assert regime["evidence_statute"] == "Bharatiya Sakshya Adhiniyam, 2023"

    def_query = get_defense_legal_research_query(case)
    assert "Bharatiya Sakshya Adhiniyam" in def_query


def test_provision_historical_mapping():
    """Test transition mapping from BSA/BNS sections to IEA/IPC."""
    act, sec = map_provision_to_historical("Bharatiya Sakshya Adhiniyam, 2023", "Section 104")
    assert act == "Indian Evidence Act, 1872"
    assert "101" in sec

    act, sec = map_provision_to_historical("Bharatiya Sakshya Adhiniyam, 2023", "Section 23")
    assert act == "Indian Evidence Act, 1872"
    assert "27" in sec

    act, sec = map_provision_to_historical("Bharatiya Nyaya Sanhita, 2023", "Section 103")
    assert act == "Indian Penal Code, 1860"
    assert "302" in sec


def test_shared_embedding_model_singleton():
    """Verify that SentenceTransformer model is shared across instances without duplicate loading."""
    e1 = EmbeddingModel()
    e2 = EmbeddingModel()
    m1 = e1.model
    m2 = e2.model
    assert m1 is m2
    assert id(m1) == id(m2)


def test_openrouter_client_reuse_and_request_counter():
    """Verify centralized LLMProvider returns cached OpenRouter client and tracks requests."""
    client1 = LLMProvider.get("openrouter")
    client2 = LLMProvider.get("openrouter")
    assert client1 is client2

    assert isinstance(client1, OpenRouterLLMClient)
    init_count = client1.request_count

    # Simulate tracked request
    client1._track_request("test_agent", {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150})
    assert client1.request_count == init_count + 1
    assert client1.agent_request_counts["test_agent"] >= 1
    summary = client1.get_usage_summary()
    assert summary["total_requests"] >= 1
    assert summary["total_tokens_used"] >= 150


def test_openrouter_api_failure_raises_explicit_error():
    """Verify that API errors raise RuntimeError and never silently return mock data."""
    client = OpenRouterLLMClient(api_key="sk-or-test-fake")

    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 402
        mock_resp.text = "Insufficient credits in account"
        mock_post.return_value = mock_resp

        with pytest.raises(RuntimeError) as exc_info:
            client.generate_structured(
                prompt="Test prompt",
                response_schema=StructuredCase,
                fallback_data={"case_id": "FALLBACK"},
            )
        assert "quota error (HTTP 402)" in str(exc_info.value) or "insufficient credits" in str(exc_info.value).lower()


def test_judge_node_missing_inputs_detected():
    """Verify that judge_node detects missing trial components and marks execution failed."""
    state = CourtState(
        case_packet="dummy.pdf",
        case_analysis=StructuredCase(
            case_id="TEST-001",
            case_title="State v. Test",
            allegations_summary="Test allegation",
        ),
        # Missing prosecution, defense, evidence_analysis, conflicts
    )

    result = judge_node(state)
    assert result.get("judgment") is None
    assert "errors" in result
    assert result["errors"][0].agent == "judge"
    assert "missing essential trial components" in result["errors"][0].error.lower()
    assert result["execution_log"][0].status == "failed"


def test_judge_12_sections_and_persistence():
    """Verify that Judge renders all 12 sections and persists complete artifacts."""
    case = StructuredCase(
        case_id="AUDIT-CASE-001",
        case_title="State v. Ramu",
        court_identifier="Sessions Case No. 42/2023",
        allegations_summary="Allegation of robbery under Section 392 IPC.",
        charges=[
            Charge(
                section="Section 392",
                statute="Indian Penal Code, 1860",
                description="Robbery",
                accused_name="Ramu",
            )
        ],
    )
    pros_case = ProsecutionCase(
        case_id="AUDIT-CASE-001",
        prosecution_theory="Guilt proved by direct evidence.",
        final_prayer="Conviction and maximum statutory penalty.",
    )
    def_case = DefenseCase(
        case_id="AUDIT-CASE-001",
        defense_theory="Innocence plea, doubts raised.",
        alternative_interpretation="Accused was a bystander with no involvement.",
        final_prayer="Complete acquittal.",
    )
    ev_report = EvidenceAnalysisReport(
        case_id="AUDIT-CASE-001",
        summary="Physical recovery memo.",
        documentary_compliance_assessment="Recovery memo strictly compliant with procedural requirements.",
    )
    conf_report = ConflictReport(
        case_id="AUDIT-CASE-001",
        summary="Minor conflict in timing.",
        total_conflicts=0,
        critical_conflicts_count=0,
    )

    agent = JudgeAgent()
    judgment = agent.adjudicate(
        case=case,
        prosecution_case=pros_case,
        defense_case=def_case,
        evidence_report=ev_report,
        conflict_report=conf_report,
    )

    # 12 Sections check
    assert judgment.case_background
    assert len(judgment.issues_for_determination) >= 1
    assert len(judgment.applicable_law) >= 1
    assert judgment.evidence_assessment
    assert judgment.witness_assessment
    assert judgment.prosecution_submissions
    assert judgment.defense_submissions
    assert len(judgment.issue_analyses) >= 1
    assert len(judgment.findings_per_charge) >= 1
    assert judgment.final_decision in ["CONVICTION", "ACQUITTAL"]
    assert judgment.reasons
    assert len(judgment.legal_citations) >= 1

    # Persistence check
    with tempfile.TemporaryDirectory() as tmpdir:
        writer = JudgmentWriter(base_output_dir=tmpdir)
        paths = writer.persist_judgment("AUDIT-CASE-001", judgment)

        assert Path(paths["json"]).exists()
        assert Path(paths["txt"]).exists()
        assert Path(paths["pdf"]).exists()

        # Verify JSON content matches
        data = json.loads(Path(paths["json"]).read_text(encoding="utf-8"))
        assert data["case_title"] == "State v. Ramu"
        assert data["final_decision"] == judgment.final_decision

        # Verify TXT contains 12 sections
        txt_content = Path(paths["txt"]).read_text(encoding="utf-8")
        for i in range(1, 13):
            assert f"SECTION {i}:" in txt_content


def test_authoritative_web_research_homicide_and_circumstantial():
    """Verify that WebSearchService returns authoritative Supreme Court precedents."""
    search = WebSearchService()
    results = search.search_legal("Supreme Court precedent on Section 302 IPC murder")
    assert len(results) >= 1
    assert any("Rayavarapu Punnayya" in r.title or "Virsa Singh" in r.title for r in results)
    assert any("indiankanoon.org" in r.url or "sci.gov.in" in r.url for r in results)

    circ_results = search.search_legal("circumstantial evidence and benefit of doubt")
    assert len(circ_results) >= 1
    assert any("Sharad Birdhichand Sarda" in r.title or "Kali Ram" in r.title for r in circ_results)
