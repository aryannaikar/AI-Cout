"""
Phase 3 Tests: Explicit Error Handling and Fault Tolerance.
Verifies errors are captured, logged, not silently swallowed, and do not fabricate fake replacement data.
"""

from unittest.mock import patch
from app.graph.nodes import (
    case_understanding_node,
    prosecutor_web_research_node,
    defense_web_research_node,
    judge_node,
    prosecutor_node,
    defense_node,
    evidence_node,
    conflict_node,
)
from app.graph.state import CourtState
from tests.phase2.test_case_agent import SAMPLE_CASE_PACKET_TEXT


def test_research_node_captures_recoverable_error():
    base_state = CourtState(case_packet=SAMPLE_CASE_PACKET_TEXT)
    case_update = case_understanding_node(base_state)
    state = CourtState(**{**base_state.model_dump(), **case_update})

    with patch("app.agents.web_research_agent.WebResearchAgent.research", side_effect=ConnectionError("Simulated network outage")):
        res = prosecutor_web_research_node(state)

        # Output research must be None (no fabrication)
        assert res["prosecution_web_research"] is None

        # Must record explicit error
        assert len(res["errors"]) == 1
        err = res["errors"][0]
        assert err.agent == "prosecutor_web_research"
        assert "network outage" in err.error
        assert err.recoverable is True

        # Execution log must record failed status
        assert len(res["execution_log"]) == 1
        log = res["execution_log"][0]
        assert log.node == "prosecutor_web_research"
        assert log.status == "failed"
        assert "network outage" in log.error


def test_judge_proceeds_with_missing_optional_research():
    base_state = CourtState(case_packet=SAMPLE_CASE_PACKET_TEXT)
    case_update = case_understanding_node(base_state)
    state = CourtState(**{**base_state.model_dump(), **case_update})

    # Run core nodes without web research
    pros = prosecutor_node(state)
    defs = defense_node(state)
    ev = evidence_node(state)
    state = CourtState(**{**state.model_dump(), **pros, **defs, **ev})
    conf = conflict_node(state)
    state = CourtState(**{**state.model_dump(), **conf})

    # Both web research items are None
    assert state.prosecution_web_research is None
    assert state.defense_web_research is None

    # Judge must still be able to adjudicate with the factual and evidence record
    judge_res = judge_node(state)
    assert "judgment" in judge_res
    assert "CONVICT" in judge_res["judgment"].final_decision.upper() or "ACQUIT" in judge_res["judgment"].final_decision.upper()
    assert judge_res["execution_log"][0].status == "completed"
