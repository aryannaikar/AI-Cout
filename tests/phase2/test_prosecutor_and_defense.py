"""
Phase 2 Tests: Prosecutor Agent and Defense Agent.
Verifies adversarial case construction and epistemic categorization:
FACT, EVIDENCE, LEGAL_RULE, INFERENCE, and ARGUMENT.
"""

from app.agents.case_agent import CaseUnderstandingAgent
from app.agents.defense_agent import DefenseAgent
from app.agents.evidence_agent import EvidenceAnalysisAgent
from app.agents.legal_research_agent import LegalResearchAgent
from app.agents.prosecutor_agent import ProsecutorAgent
from app.models.judgment_models import (
    DefenseCase,
    ProsecutionCase,
    StatementType,
)
from tests.phase2.test_case_agent import SAMPLE_CASE_PACKET_TEXT


def test_prosecutor_agent():
    case = CaseUnderstandingAgent().parse_case_text(SAMPLE_CASE_PACKET_TEXT)
    ev_report = EvidenceAnalysisAgent().analyze_evidence(case)
    legal_res = LegalResearchAgent(side="prosecution").research("punishment for stolen property BNS Section 317")

    prosecutor = ProsecutorAgent()
    pros_case = prosecutor.build_case(case, ev_report, legal_res)

    assert isinstance(pros_case, ProsecutionCase)
    assert pros_case.case_id == case.case_id
    assert len(pros_case.statutory_elements) > 0
    assert len(pros_case.legal_citations) > 0
    assert len(pros_case.addressed_weaknesses) > 0

    # Verify statement type classifications
    stmt_types = [comp.statement_type for comp in pros_case.argument_components]
    assert StatementType.FACT in stmt_types
    assert StatementType.EVIDENCE in stmt_types
    assert StatementType.LEGAL_RULE in stmt_types
    assert StatementType.INFERENCE in stmt_types
    assert StatementType.ARGUMENT in stmt_types


def test_defense_agent():
    case = CaseUnderstandingAgent().parse_case_text(SAMPLE_CASE_PACKET_TEXT)
    ev_report = EvidenceAnalysisAgent().analyze_evidence(case)
    legal_res = LegalResearchAgent(side="defense").research("burden of proof presumption of innocence BSA")

    defense = DefenseAgent()
    def_case = defense.build_defense(case, ev_report, legal_res)

    assert isinstance(def_case, DefenseCase)
    assert def_case.case_id == case.case_id
    assert len(def_case.reasonable_doubt_grounds) > 0
    assert len(def_case.missing_evidence_highlighted) > 0
    assert len(def_case.legal_citations) > 0
    assert len(def_case.alternative_interpretation) > 20

    # Verify statement type classifications
    stmt_types = [comp.statement_type for comp in def_case.argument_components]
    assert StatementType.FACT in stmt_types
    assert StatementType.EVIDENCE in stmt_types
    assert StatementType.LEGAL_RULE in stmt_types
    assert StatementType.INFERENCE in stmt_types
    assert StatementType.ARGUMENT in stmt_types
