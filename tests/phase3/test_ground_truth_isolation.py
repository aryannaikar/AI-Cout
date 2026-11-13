"""
Phase 3 Tests: Comprehensive Blind-Evaluation and Ground Truth Isolation.
Enforces the 5 critical security requirements:
1. Ground_Truth_Verdict.pdf cannot enter initial state.
2. A state containing a forbidden ground-truth field is rejected.
3. Ground-truth content cannot be propagated between nodes.
4. Judge node receives no ground-truth data.
5. Execution log contains no ground-truth information.
"""

from pathlib import Path
import pytest

from app.graph.nodes import case_understanding_node, judge_node
from app.graph.state import CourtState
from app.graph.validation import BlindEvaluationViolation
from app.graph.workflow import CourtWorkflow
from tests.phase2.test_case_agent import SAMPLE_CASE_PACKET_TEXT


def test_1_ground_truth_file_cannot_enter_initial_state(tmp_path: Path):
    gt_path = tmp_path / "Ground_Truth_Verdict.pdf"
    gt_path.write_bytes(b"%PDF-1.4 Fake verdict")

    workflow = CourtWorkflow()
    with pytest.raises(BlindEvaluationViolation):
        workflow.run(gt_path)

    with pytest.raises(BlindEvaluationViolation):
        CourtState(case_packet=str(gt_path))


def test_2_state_containing_forbidden_ground_truth_fields_rejected():
    forbidden_fields = [
        "ground_truth",
        "real_verdict",
        "actual_judgment",
        "correct_verdict",
        "actual_reasoning",
    ]
    for field in forbidden_fields:
        with pytest.raises(BlindEvaluationViolation):
            CourtState(**{"case_packet": "Case_Packet.pdf", field: "State won"})


def test_3_ground_truth_content_cannot_be_propagated_between_nodes():
    tainted_text = (
        "IN THE COURT OF SESSIONS\n"
        "State v. Accused\n"
        "Ground Truth Verdict: The accused is hereby convicted under BNS 317.\n"
    )
    with pytest.raises(BlindEvaluationViolation):
        CourtState(case_packet=tainted_text)

    state = CourtState(case_packet=SAMPLE_CASE_PACKET_TEXT)
    # Tainting case packet text causes case_understanding_node to catch or reject
    state_tainted = CourtState(case_packet="Normal text")
    state_tainted.case_packet = tainted_text
    res = case_understanding_node(state_tainted)
    assert "errors" in res
    assert res["execution_log"][0].status == "failed"


def test_4_judge_node_receives_no_ground_truth_data():
    workflow = CourtWorkflow()
    final_state = workflow.run(SAMPLE_CASE_PACKET_TEXT)

    judge_in = final_state.judge_input
    assert judge_in is not None

    # Audit judge input serialization
    dumped = judge_in.model_dump_json().lower()
    for forbidden in ["ground_truth", "real_verdict", "actual_judgment", "correct_verdict"]:
        assert forbidden not in dumped


def test_5_execution_log_contains_no_ground_truth():
    workflow = CourtWorkflow()
    final_state = workflow.run(SAMPLE_CASE_PACKET_TEXT)

    for entry in final_state.execution_log:
        entry_text = f"{entry.node} {entry.status} {entry.error or ''}".lower()
        assert "ground_truth" not in entry_text
        assert "real_verdict" not in entry_text
