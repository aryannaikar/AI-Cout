"""
Phase 3 Tests: Individual LangGraph Node Executions.
Verifies all 10 courtroom nodes call their respective Phase-2 agents and produce structured outputs.
"""

import pytest

from app.graph.nodes import (
    case_understanding_node,
    conflict_node,
    defense_legal_research_node,
    defense_node,
    defense_web_research_node,
    evidence_node,
    judge_node,
    prosecutor_legal_research_node,
    prosecutor_node,
    prosecutor_web_research_node,
)
from app.graph.state import CourtState
from tests.phase2.test_case_agent import SAMPLE_CASE_PACKET_TEXT


@pytest.fixture
def base_state():
    return CourtState(case_packet=SAMPLE_CASE_PACKET_TEXT)


def test_case_understanding_node(base_state):
    res = case_understanding_node(base_state)
    assert "case_analysis" in res
    assert res["case_analysis"] is not None
    assert "execution_log" in res
    assert res["execution_log"][0].status == "completed"
    assert res["execution_log"][0].node == "case_understanding"


def test_prosecutor_node(base_state):
    # Prepare state with case_analysis
    case_update = case_understanding_node(base_state)
    state = CourtState(**{**base_state.model_dump(), **case_update})

    res = prosecutor_node(state)
    assert "prosecution" in res
    assert res["prosecution"].prosecution_theory is not None
    assert res["execution_log"][0].node == "prosecutor"
    assert res["execution_log"][0].status == "completed"


def test_prosecutor_legal_and_web_research_nodes(base_state):
    case_update = case_understanding_node(base_state)
    state = CourtState(**{**base_state.model_dump(), **case_update})

    # Legal RAG
    rag_res = prosecutor_legal_research_node(state)
    assert "prosecution_legal_research" in rag_res
    assert len(rag_res["prosecution_legal_research"].applicable_provisions) > 0

    # Web Research
    web_res = prosecutor_web_research_node(state)
    assert "prosecution_web_research" in web_res
    assert len(web_res["prosecution_web_research"].sources) > 0


def test_defense_nodes(base_state):
    case_update = case_understanding_node(base_state)
    state = CourtState(**{**base_state.model_dump(), **case_update})

    # Defense argument
    def_res = defense_node(state)
    assert "defense" in def_res
    assert len(def_res["defense"].reasonable_doubt_grounds) > 0

    # Defense RAG
    rag_res = defense_legal_research_node(state)
    assert "defense_legal_research" in rag_res
    assert rag_res["defense_legal_research"].side == "defense"

    # Defense Web
    web_res = defense_web_research_node(state)
    assert "defense_web_research" in web_res
    assert web_res["defense_web_research"].side == "defense"


def test_evidence_and_conflict_nodes(base_state):
    case_update = case_understanding_node(base_state)
    state = CourtState(**{**base_state.model_dump(), **case_update})

    # Evidence
    ev_res = evidence_node(state)
    assert "evidence_analysis" in ev_res
    assert len(ev_res["evidence_analysis"].evidence_items) > 0

    # Conflict
    state_with_ev = CourtState(**{**state.model_dump(), **ev_res})
    conf_res = conflict_node(state_with_ev)
    assert "conflicts" in conf_res
    assert len(conf_res["conflicts"].conflicts) > 0


def test_judge_node(base_state):
    case_update = case_understanding_node(base_state)
    state = CourtState(**{**base_state.model_dump(), **case_update})

    pros_res = prosecutor_node(state)
    def_res = defense_node(state)
    ev_res = evidence_node(state)
    state = CourtState(**{**state.model_dump(), **pros_res, **def_res, **ev_res})
    conf_res = conflict_node(state)
    state = CourtState(**{**state.model_dump(), **conf_res})

    res = judge_node(state)
    assert "judgment" in res
    assert "judge_input" in res
    assert res["judgment"].judgment_id is not None
    assert "CONVICT" in res["judgment"].final_decision.upper() or "ACQUIT" in res["judgment"].final_decision.upper()
    assert res["execution_log"][0].status == "completed"
