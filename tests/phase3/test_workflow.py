"""
Phase 3 Tests: End-to-End Courtroom Workflow Execution.
Verifies complete deterministic graph execution and validates the 12-section AI judgment schema.
"""

from app.graph.workflow import CourtWorkflow, create_court_graph, run_court
from app.models.judgment_models import Judgment
from tests.phase2.test_case_agent import SAMPLE_CASE_PACKET_TEXT


def test_graph_compilation():
    builder = create_court_graph()
    app = builder.compile()
    assert app is not None


def test_end_to_end_court_execution():
    # Execute through high-level run_court entry point
    final_state = run_court(SAMPLE_CASE_PACKET_TEXT)

    # 1. Verify all primary state components populated
    assert final_state.case_analysis is not None
    assert final_state.prosecution is not None
    assert final_state.defense is not None
    assert final_state.evidence_analysis is not None
    assert final_state.conflicts is not None
    assert final_state.judge_input is not None
    assert final_state.judgment is not None

    # 2. Verify all 10 nodes executed
    nodes_executed = {entry.node for entry in final_state.execution_log}
    expected_nodes = {
        "case_understanding",
        "prosecutor",
        "prosecutor_legal_research",
        "prosecutor_web_research",
        "defense",
        "defense_legal_research",
        "defense_web_research",
        "evidence",
        "conflict",
        "judge",
    }
    assert expected_nodes.issubset(nodes_executed)

    # 3. Verify Judgment schema and all 12 judicial framework sections
    judgment: Judgment = final_state.judgment
    assert judgment.judgment_id is not None
    assert "CONVICT" in judgment.final_decision.upper() or "ACQUIT" in judgment.final_decision.upper()

    # Section 1: Case Background
    assert len(judgment.case_background) > 20
    # Section 2: Issues for Determination
    assert len(judgment.issues_for_determination) > 0
    # Section 3: Applicable Law
    assert len(judgment.applicable_law) > 0
    # Section 4: Evidence Assessment
    assert len(judgment.evidence_assessment) > 20
    # Section 5: Witness Assessment
    assert len(judgment.witness_assessment) > 20
    # Section 6: Prosecution Submissions
    assert len(judgment.prosecution_submissions) > 20
    # Section 7: Defense Submissions
    assert len(judgment.defense_submissions) > 20
    # Section 8: Analysis of each issue
    assert len(judgment.issue_analyses) > 0
    # Section 9: Findings per charge
    assert len(judgment.findings_per_charge) > 0
    # Section 10: Final Decision
    assert judgment.final_decision
    # Section 11: Reasons
    assert len(judgment.reasons) > 20
    # Section 12: Legal Citations
    assert len(judgment.legal_citations) > 0
