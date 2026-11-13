"""
Phase 2 Tests: Judge Agent, 12-Section Judicial Framework, and Ground Truth Isolation.
"""

import pytest
from app.agents.case_agent import CaseUnderstandingAgent
from app.agents.conflict_agent import ConflictDetectionAgent
from app.agents.defense_agent import DefenseAgent
from app.agents.evidence_agent import EvidenceAnalysisAgent
from app.agents.judge_agent import JudgeAgent
from app.agents.legal_research_agent import LegalResearchAgent
from app.agents.prosecutor_agent import ProsecutorAgent
from app.models.judgment_models import Judgment
from tests.phase2.test_case_agent import SAMPLE_CASE_PACKET_TEXT


def test_judge_agent_renders_12_section_judgment():
    case = CaseUnderstandingAgent().parse_case_text(SAMPLE_CASE_PACKET_TEXT)
    ev_report = EvidenceAnalysisAgent().analyze_evidence(case)
    conflict_report = ConflictDetectionAgent().detect_conflicts(case, ev_report)

    pros_legal = LegalResearchAgent(side="prosecution").research("punishment for stolen property BNS Section 317")
    def_legal = LegalResearchAgent(side="defense").research("mandatory conditions for electronic evidence Section 63 BSA")

    pros_case = ProsecutorAgent().build_case(case, ev_report, pros_legal)
    def_case = DefenseAgent().build_defense(case, ev_report, def_legal)

    judge = JudgeAgent()
    judgment = judge.adjudicate(
        case=case,
        prosecution_case=pros_case,
        defense_case=def_case,
        evidence_report=ev_report,
        conflict_report=conflict_report,
        prosecution_legal_research=pros_legal,
        defense_legal_research=def_legal,
    )

    assert isinstance(judgment, Judgment)

    # 1. Case background
    assert judgment.case_background
    assert case.case_title in judgment.case_background

    # 2. Issues for determination
    assert len(judgment.issues_for_determination) > 0

    # 3. Applicable law
    assert len(judgment.applicable_law) > 0

    # 4. Evidence assessment
    assert judgment.evidence_assessment
    assert "evidence" in judgment.evidence_assessment.lower()

    # 5. Witness assessment
    assert judgment.witness_assessment
    assert "witness" in judgment.witness_assessment.lower()

    # 6. Prosecution submissions
    assert judgment.prosecution_submissions

    # 7. Defense submissions
    assert judgment.defense_submissions

    # 8. Analysis of each issue
    assert len(judgment.issue_analyses) == len(judgment.issues_for_determination)
    for issue in judgment.issue_analyses:
        assert issue.judicial_finding in ["PROVED", "NOT PROVED", "DISPROVED"]

    # 9. Findings per charge
    assert len(judgment.findings_per_charge) > 0

    # 10. Final decision
    assert judgment.final_decision in ["CONVICTION", "ACQUITTAL", "PARTIAL CONVICTION"]

    # 11. Reasons
    assert len(judgment.reasons) > 50

    # 12. Legal citations
    assert len(judgment.legal_citations) > 0


def test_judge_rejects_ground_truth_leakage():
    case = CaseUnderstandingAgent().parse_case_text(SAMPLE_CASE_PACKET_TEXT)
    ev_report = EvidenceAnalysisAgent().analyze_evidence(case)
    conflict_report = ConflictDetectionAgent().detect_conflicts(case, ev_report)
    pros_legal = LegalResearchAgent(side="prosecution").research("Section 317 BNS")
    def_legal = LegalResearchAgent(side="defense").research("Section 63 BSA")

    pros_case = ProsecutorAgent().build_case(case, ev_report, pros_legal)
    def_case = DefenseAgent().build_defense(case, ev_report, def_legal)

    # Taint case with Ground Truth leak
    tainted_case = case.model_copy(update={"case_title": "State v. Ramesh Kumar [Ground Truth Verdict: Convicted]"})

    judge = JudgeAgent()
    with pytest.raises(PermissionError, match="SECURITY VIOLATION"):
        judge.adjudicate(
            case=tainted_case,
            prosecution_case=pros_case,
            defense_case=def_case,
            evidence_report=ev_report,
            conflict_report=conflict_report,
        )
