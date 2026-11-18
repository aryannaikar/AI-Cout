"""
Phase 1 Foundation Fixes — Regression Test Suite.
Covers:
1. Shabuddin historical law and Section 379 / 411 distinction.
2. Jharkhand three distinct persons and two connected revisions.
3. Correct Section 3(a) Railway Property (Unlawful Possession) Act, 1966 identification
   without inferring an Act from section number alone.
4. Charge-wise judgment coverage and Judge legal-authority validation.
5. Explicit missing/failed legal research representation.
6. Ground Truth isolation.
7. Phase 5 issue extraction and verdict comparison.
8. LegalRetriever end-to-end retrieval without dependency/DLL failures.
"""

from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import MagicMock

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_BACKEND = _ROOT / "backend"
for p in (str(_BACKEND), str(_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.agents.case_agent import CaseUnderstandingAgent
from app.agents.judge_agent import JudgeAgent
from app.agents.legal_research_agent import LegalResearchAgent
from app.agents.prosecutor_agent import ProsecutorAgent
from app.comparison.extractor import JudgmentNormalizer
from app.comparison.schemas import OperativeVerdict
from app.graph import nodes
from app.graph.state import CourtState
from app.models.case_models import Charge, ProceedingScope, StructuredCase
from app.models.conflict_models import ConflictReport
from app.models.evidence_models import EvidenceAnalysisReport
from app.models.judgment_models import (
    AccusedFinding,
    DefenseCase,
    Judgment,
    JudicialIssueAnalysis,
    ProsecutionCase,
)
from app.models.legal_models import LegalResearchResult
from app.services.legal_transition import get_prosecutor_legal_research_query


def _make_jharkhand_case() -> StructuredCase:
    return StructuredCase(
        case_id="JH-2026-32683",
        case_title="High Court of Jharkhand at Ranchi, Cr. Rev. 1247/2017 with Cr. Rev. 1512/2017",
        court_identifier="2026:JHHC:32683",
        accused=["Md. Israful Ansari", "Md. Nasir Ansari", "Israfil Ansari"],
        allegations_summary="Unlawful possession of railway property between Chetar and Richugota stations on 26 May 2007.",
        proceeding_type="revision",
        connected_proceedings=[
            ProceedingScope(
                proceeding_id="Cr. Revision No. 1247/2017",
                proceeding_type="revision",
                accused_or_petitioners=["Md. Israful Ansari", "Md. Nasir Ansari"],
                role_summary="Apprehended at spot; recovery attributed to them.",
            ),
            ProceedingScope(
                proceeding_id="Cr. Revision No. 1512/2017",
                proceeding_type="revision",
                accused_or_petitioners=["Israfil Ansari"],
                role_summary="Named by co-accused as person who called them to transport scrap.",
            ),
        ],
        charges=[
            Charge(
                section="Section 3(a)",
                statute="Railway Property (Unlawful Possession) Act, 1966",
                description="Unlawful possession of railway property",
                accused_name="Md. Israful Ansari",
                record_status="current",
            ),
            Charge(
                section="Section 3(a)",
                statute="Railway Property (Unlawful Possession) Act, 1966",
                description="Unlawful possession of railway property",
                accused_name="Md. Nasir Ansari",
                record_status="current",
            ),
            Charge(
                section="Section 3(a)",
                statute="Railway Property (Unlawful Possession) Act, 1966",
                description="Unlawful possession of railway property",
                accused_name="Israfil Ansari",
                record_status="current",
            ),
        ],
        procedural_history="Registered on 26 May 2007 under Section 3 of R.P.(U.P.) Act.",
    )


def _make_shabuddin_case() -> StructuredCase:
    return StructuredCase(
        case_id="SC-3605-2025",
        case_title="Sd. Shabuddin v. The State of Telangana",
        court_identifier="Criminal Appeal No. 3605 of 2025",
        accused=["Shabuddin", "Moulana"],
        decision_subject="Shabuddin",
        proceeding_type="appeal",
        allegations_summary="Recovery of Rs. 25,000 allegedly linked to theft of cash from deceased on 22 December 2005.",
        charges=[
            Charge(
                section="Section 302",
                statute="Indian Penal Code, 1860",
                description="Murder",
                accused_name="Moulana",
                record_status="other_accused",
            ),
            Charge(
                section="Section 379",
                statute="Indian Penal Code, 1860",
                description="Theft (acquitted by Trial Court)",
                accused_name="Shabuddin",
                record_status="procedural_history",
            ),
            Charge(
                section="Section 411",
                statute="Indian Penal Code, 1860",
                description="Dishonestly receiving stolen property",
                accused_name="Shabuddin",
                record_status="current",
            ),
        ],
        procedural_history="Trial court acquitted under Sections 302, 201, 379 IPC on 22 December 2005 incident; convicted under Section 411 IPC.",
    )


def test_jharkhand_three_distinct_persons_and_two_revisions():
    """Connected revisions must preserve all three persons without merging Md. Israful Ansari and Israfil Ansari."""
    case = _make_jharkhand_case()
    subjects = case.distinct_decision_subjects()
    assert len(subjects) == 3
    assert "Md. Israful Ansari" in subjects
    assert "Md. Nasir Ansari" in subjects
    assert "Israfil Ansari" in subjects
    assert len(case.connected_proceedings) == 2


def test_section_3a_railway_property_act_not_overwritten_as_ipc(monkeypatch):
    """Historical regime must NOT turn Section 3(a) Railway Property Act into Indian Penal Code."""
    case = _make_jharkhand_case()
    query = get_prosecutor_legal_research_query(case)
    assert "Railway Property (Unlawful Possession) Act, 1966" in query
    assert "Indian Penal Code" not in query

    captured_queries: list[str] = []

    class FakeWebAgent:
        def __init__(self, side="prosecution"):
            self.side = side

        def research(self, question: str):
            captured_queries.append(question)
            return None

    monkeypatch.setattr(nodes, "WebResearchAgent", FakeWebAgent)
    state = CourtState(case_packet="dummy.pdf", case_analysis=case)
    nodes.prosecutor_web_research_node(state)

    assert len(captured_queries) == 1
    assert "Railway Property (Unlawful Possession) Act, 1966" in captured_queries[0]
    assert "Indian Penal Code" not in captured_queries[0]


def test_heuristic_parse_never_infers_act_from_section_alone():
    """Heuristic parser must only extract explicit Act + Section pairs and never fall back to BNS 317."""
    agent = CaseUnderstandingAgent(llm_service=MagicMock())
    text = (
        "High Court of Jharkhand\n"
        "Statutory provision stated: Section 3(a) of the Railway Property (Unlawful Possession) Act, 1966."
    )
    parsed = agent._heuristic_parse(text, "Jharkhand_Case_Packet.pdf")
    assert len(parsed["charges"]) == 1
    assert parsed["charges"][0]["statute"] == "Railway Property (Unlawful Possession) Act, 1966"
    assert parsed["charges"][0]["section"] == "Section 3(a)"

    # Text with only a bare section number and no Act must not guess BNS 317
    bare = agent._heuristic_parse("Allegation mentions Section 420 without naming an act.", "Bare_Case_Packet.pdf")
    assert bare["charges"] == []


def test_shabuddin_charge_separation_and_prosecutor_consistency():
    """Only current charges for decision_subject should drive active statutory elements."""
    case = _make_shabuddin_case()
    current = case.current_charges()
    assert len(current) == 1
    assert current[0].section == "Section 411"
    assert current[0].accused_name == "Shabuddin"

    pros = ProsecutorAgent(llm_service=MagicMock()).build_case(case=case)
    assert len(pros.statutory_elements) == 1
    assert "Section 411" in pros.statutory_elements[0]
    assert "Section 302" not in pros.statutory_elements[0]


def test_judge_citation_validation_normalized_but_strict():
    """Judge validation accepts formatted variants of verified charges while rejecting ungrounded sections."""
    case = _make_shabuddin_case()
    dossier = {
        "research_citations": ["Kali Ram v. State of Himachal Pradesh, (1973) 2 SCC 808"],
        "verified_charges": [
            {"statute": "Indian Penal Code, 1860", "section": "Section 411", "charge_key": "Indian Penal Code, 1860, Section 411"}
        ],
    }
    base_judgment = Judgment(
        case_title=case.case_title,
        date_of_decision="2026-11-18",
        case_background="Background.",
        issues_for_determination=["Whether Section 411 IPC is proved?"],
        applicable_law=["Indian Penal Code, 1860, Section 411"],
        evidence_assessment="Assessment.",
        witness_assessment="Witnesses.",
        prosecution_submissions="Prosecution.",
        defense_submissions="Defense.",
        issue_analyses=[
            JudicialIssueAnalysis(
                issue_number=1,
                issue_statement="Whether Section 411 IPC is proved?",
                applicable_law="Section 411 IPC",
                prosecution_submission_summary="Pros.",
                defense_submission_summary="Def.",
                evidentiary_evaluation="Eval.",
                judicial_finding="NOT PROVED",
            )
        ],
        findings_per_charge={"Indian Penal Code, 1860, Section 411": "Acquitted / Not proved"},
        final_decision="ACQUITTAL",
        reasons="Reasons.",
        legal_citations=["Section 411 IPC", "Kali Ram v. State of Himachal Pradesh"],
    )
    validated = JudgeAgent._validate_output(base_judgment, case, dossier)
    assert validated.final_decision == "ACQUITTAL"

    # Ungrounded section (e.g., Section 420 IPC) must still be rejected
    bad_judgment = base_judgment.model_copy(update={"legal_citations": ["Section 420 IPC"]})
    with pytest.raises(ValueError, match="absent from supplied research or charges"):
        JudgeAgent._validate_output(bad_judgment, case, dossier)


def test_jharkhand_multi_accused_findings_coverage():
    """Connected proceedings sharing Section 3(a) must not fail findings_per_charge deduplication."""
    case = _make_jharkhand_case()
    dossier = {
        "research_citations": [],
        "verified_charges": [
            {
                "statute": "Railway Property (Unlawful Possession) Act, 1966",
                "section": "Section 3(a)",
                "charge_key": "Railway Property (Unlawful Possession) Act, 1966, Section 3(a)",
            }
        ],
    }
    judgment = Judgment(
        case_title=case.case_title,
        date_of_decision="2026-11-18",
        case_background="Background.",
        issues_for_determination=["Whether Section 3(a) R.P.(U.P.) Act is proved?"],
        applicable_law=["Railway Property (Unlawful Possession) Act, 1966, Section 3(a)"],
        evidence_assessment="Assessment.",
        witness_assessment="Witnesses.",
        prosecution_submissions="Prosecution.",
        defense_submissions="Defense.",
        issue_analyses=[
            JudicialIssueAnalysis(
                issue_number=1,
                issue_statement="Whether Section 3(a) R.P.(U.P.) Act is proved?",
                applicable_law="Section 3(a) R.P.(U.P.) Act",
                prosecution_submission_summary="Pros.",
                defense_submission_summary="Def.",
                evidentiary_evaluation="Eval.",
                judicial_finding="NOT PROVED",
            )
        ],
        findings_per_charge={"Railway Property (Unlawful Possession) Act, 1966, Section 3(a)": "Acquitted / Not proved"},
        accused_findings=[
            AccusedFinding(
                accused_name="Md. Israful Ansari",
                proceeding_id="Cr. Revision No. 1247/2017",
                charges_decided=["Section 3(a) R.P.(U.P.) Act"],
                finding="ACQUITTAL",
                reasoning_summary="Independent witness/ownership proof missing.",
            ),
            AccusedFinding(
                accused_name="Md. Nasir Ansari",
                proceeding_id="Cr. Revision No. 1247/2017",
                charges_decided=["Section 3(a) R.P.(U.P.) Act"],
                finding="ACQUITTAL",
                reasoning_summary="Independent witness/ownership proof missing.",
            ),
            AccusedFinding(
                accused_name="Israfil Ansari",
                proceeding_id="Cr. Revision No. 1512/2017",
                charges_decided=["Section 3(a) R.P.(U.P.) Act"],
                finding="ACQUITTAL",
                reasoning_summary="Only implicated on co-accused statement.",
            ),
        ],
        final_decision="ACQUITTAL",
        reasons="Reasons.",
        legal_citations=["Section 3(a) of the Railway Property (Unlawful Possession) Act, 1966"],
    )
    validated = JudgeAgent._validate_output(judgment, case, dossier)
    assert len(validated.accused_findings) == 3


def test_missing_or_failed_legal_research_explicit_status(monkeypatch):
    """Failed or empty legal research must return explicit status, never None or silent completed."""
    agent = LegalResearchAgent(side="prosecution", retriever=MagicMock(retrieve=lambda **kw: []))
    empty_res = agent.research(question="Section 3(a) Railway Property Act", is_historical=True)
    assert empty_res.status == "empty"
    assert empty_res.applicable_provisions == []

    class BrokenRetriever:
        def retrieve(self, **kw):
            raise RuntimeError("Vector store offline")

    monkeypatch.setattr(nodes, "LegalResearchAgent", lambda side="prosecution": LegalResearchAgent(side=side, retriever=BrokenRetriever()))
    state = CourtState(case_packet="dummy.pdf", case_analysis=_make_jharkhand_case())
    out = nodes.prosecutor_legal_research_node(state)
    res = out["prosecution_legal_research"]
    assert isinstance(res, LegalResearchResult)
    assert res.status == "failed"
    assert "Vector store offline" in (res.error_message or "")


def test_ground_truth_isolation():
    """Ground truth markers and verdict filenames must be rejected."""
    with pytest.raises(PermissionError, match="SECURITY VIOLATION"):
        CaseUnderstandingAgent._validate_case_file(Path("Ground_Truth_Verdict.pdf"))

    case = _make_shabuddin_case().model_copy(update={"allegations_summary": "ground truth verdict: ACQUITTAL"})
    pros = ProsecutionCase(case_id=case.case_id, prosecution_theory="T", final_prayer="P")
    defn = DefenseCase(case_id=case.case_id, defense_theory="T", alternative_interpretation="A", final_prayer="P")
    with pytest.raises(PermissionError, match="SECURITY VIOLATION"):
        JudgeAgent._validate_blindness(case, pros, defn)


def test_phase5_shabuddin_verdict_and_issue_normalization():
    """Phase 5 normalizer extracts clean ACQUITTAL and judicial issues from Shabuddin Ground Truth."""
    sample = """
AI COURT OF INDIA
Ground Truth – Real Court Verdict
Sd. Shabuddin v. The State of Telangana
Criminal Appeal No. 3605 of 2025 | Supreme Court of India | 19 August 2025
1. Operative Verdict
ACQUITTAL
The appeal was allowed and the appellant was acquitted of all charges.
2. Issues Decided
• Issue I – Reverse burden of proof: prosecution bore the burden beyond reasonable doubt.
• Issue II – Section 411 IPC after acquittal under Section 379 IPC.
"""
    norm = JudgmentNormalizer.normalize_real_judgment(sample)
    assert norm.verdict == OperativeVerdict.ACQUITTAL
    assert len(norm.legal_issues) >= 2


def test_legal_retriever_works_end_to_end():
    """LegalRetriever must retrieve provisions from ChromaDB without HF/DLL errors."""
    from rag.retriever import LegalRetriever

    retriever = LegalRetriever(top_k=2)
    results = retriever.retrieve("burden of proof", top_k=2)
    assert len(results) >= 1
