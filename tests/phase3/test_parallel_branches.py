"""
Phase 3 Tests: Parallel Branch Execution and State Independence.
Verifies Prosecution and Defense branches execute independently without collision or mutual interference.
"""

from app.graph.nodes import (
    case_understanding_node,
    defense_legal_research_node,
    defense_node,
    defense_web_research_node,
    prosecutor_legal_research_node,
    prosecutor_node,
    prosecutor_web_research_node,
)
from app.graph.state import CourtState
from app.graph.workflow import CourtWorkflow
from tests.phase2.test_case_agent import SAMPLE_CASE_PACKET_TEXT


def test_independent_branch_execution_no_collision():
    initial_state = CourtState(case_packet=SAMPLE_CASE_PACKET_TEXT)
    case_res = case_understanding_node(initial_state)
    state = CourtState(**{**initial_state.model_dump(), **case_res})

    # Execute Prosecution branch
    p_case = prosecutor_node(state)
    p_rag = prosecutor_legal_research_node(state)
    p_web = prosecutor_web_research_node(state)

    # Execute Defense branch
    d_case = defense_node(state)
    d_rag = defense_legal_research_node(state)
    d_web = defense_web_research_node(state)

    # Combine into state
    combined_state = CourtState(
        **{
            **state.model_dump(),
            **p_case,
            **p_rag,
            **p_web,
            **d_case,
            **d_rag,
            **d_web,
        }
    )

    # Assert mutual independence and non-empty outputs
    assert combined_state.prosecution is not None
    assert combined_state.defense is not None
    assert combined_state.prosecution.prosecution_theory != combined_state.defense.defense_theory

    assert combined_state.prosecution_legal_research.side == "prosecution"
    assert combined_state.defense_legal_research.side == "defense"

    assert combined_state.prosecution_web_research.side == "prosecution"
    assert combined_state.defense_web_research.side == "defense"


def test_graph_parallel_branch_execution_logs():
    workflow = CourtWorkflow()
    final_state = workflow.run(SAMPLE_CASE_PACKET_TEXT)

    node_names = [entry.node for entry in final_state.execution_log]
    # Both prosecution and defense pipeline nodes must be present in execution log
    assert "prosecutor" in node_names
    assert "defense" in node_names
    assert "prosecutor_legal_research" in node_names
    assert "defense_legal_research" in node_names
    assert "prosecutor_web_research" in node_names
    assert "defense_web_research" in node_names
