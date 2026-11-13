"""
Phase 4 Tests: Complete Pipeline and Node Execution (Tests 6-17).
Verifies that all 10 courtroom agents execute in sequence/parallel and their outputs merge at the Judge.
"""

from unittest.mock import patch
from app.graph.workflow import CourtWorkflow
from app.models.legal_models import WebResearchItem, WebResearchResult
from tests.phase2.test_case_agent import SAMPLE_CASE_PACKET_TEXT


def test_6_to_17_full_pipeline_and_all_agents_execute():
    # Mock web search to ensure testing does not depend on live internet
    mock_web_result = WebResearchResult(
        research_id="RES-WEB-001",
        side="prosecution",
        research_question="Mocked precedent query",
        finding="Mocked judicial precedent summary",
        why_it_matters="Grounds legal interpretation of evidentiary standards.",
        sources=[
            WebResearchItem(
                title="State of Haryana v. Bhajan Lal",
                url="https://indiankanoon.org/doc/12345",
                passage_summary="Supreme Court guidelines on criminal investigation.",
                why_source_matters="Relevant to standard of proof.",
            )
        ],
    )

    with patch("app.agents.web_research_agent.WebResearchAgent.research", return_value=mock_web_result):
        workflow = CourtWorkflow()
        final_state = workflow.run(SAMPLE_CASE_PACKET_TEXT)

        # Test 6: Full pipeline executes
        assert final_state is not None

        # Test 7: Case Understanding executes
        assert final_state.case_analysis is not None
        assert len(final_state.case_analysis.accused) > 0
        assert bool(final_state.case_analysis.case_title)

        # Test 8: Prosecutor executes
        assert final_state.prosecution is not None
        assert final_state.prosecution.prosecution_theory

        # Test 9: Defense executes
        assert final_state.defense is not None
        assert len(final_state.defense.reasonable_doubt_grounds) > 0

        # Test 10: Prosecution Legal Research executes
        assert final_state.prosecution_legal_research is not None
        assert len(final_state.prosecution_legal_research.applicable_provisions) > 0

        # Test 11: Defense Legal Research executes
        assert final_state.defense_legal_research is not None
        assert len(final_state.defense_legal_research.applicable_provisions) > 0

        # Test 12: Prosecution Web Research executes
        assert final_state.prosecution_web_research is not None
        assert len(final_state.prosecution_web_research.sources) > 0

        # Test 13: Defense Web Research executes
        assert final_state.defense_web_research is not None

        # Test 14: Evidence Analysis executes
        assert final_state.evidence_analysis is not None
        assert len(final_state.evidence_analysis.evidence_items) > 0

        # Test 15: Conflict Detection executes
        assert final_state.conflicts is not None

        # Test 16: Judge executes
        assert final_state.judgment is not None
        assert final_state.judgment.judgment_id is not None

        # Test 17: Judge receives merged material
        judge_in = final_state.judge_input
        assert judge_in is not None
        assert judge_in.case_analysis == final_state.case_analysis
        assert judge_in.prosecution == final_state.prosecution
        assert judge_in.defense == final_state.defense
        assert judge_in.evidence_analysis == final_state.evidence_analysis
        assert judge_in.conflicts == final_state.conflicts
