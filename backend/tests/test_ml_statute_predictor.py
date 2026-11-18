"""
Unit and Integration Tests for Stage-0 ML Statutory & Companion-Section Predictor.
"""

from __future__ import annotations

from app.agents.case_agent import CaseUnderstandingAgent
from app.agents.legal_research_agent import LegalResearchAgent
from app.models.case_models import Charge, StructuredCase
from app.services.ml_statute_predictor import MLStatutePredictor


def test_ml_statute_predictor_murder_and_custody_recovery():
    """Verify murder + custody recovery text predicts IPC 302, IPC 34, IEA 27, IEA 102."""
    text = (
        "The deceased was murdered in broad daylight by multiple assailants using sharp cutting weapons "
        "and country made pistol. The accused were apprehended and on their disclosure statement under police custody, "
        "the weapon and blood stained clothes were recovered."
    )
    preds = MLStatutePredictor.predict_statutes(text, top_k=6, threshold=0.35)
    codes = {p["code"] for p in preds}
    assert "IPC_302" in codes
    assert "IPC_34" in codes
    assert "IEA_27" in codes
    assert "IEA_102" in codes


def test_ml_statute_predictor_theft_and_search_without_murder_false_positive():
    """Verify theft/search facts trigger theft/search/evidence rules and suppress false-positive IPC 302."""
    text = (
        "The railway protection force searched the scrap godown of the accused and recovered railway track iron plates. "
        "The accused failed to produce receipt or lawful permit for possession of stolen railway material. "
        "Search conducted without joining independent local witnesses."
    )
    preds = MLStatutePredictor.predict_statutes(text, top_k=6, threshold=0.35)
    codes = {p["code"] for p in preds}
    assert "IPC_379" in codes
    assert "IEA_102" in codes
    assert "CRPC_100" in codes
    assert "IPC_302" not in codes


def test_ml_statute_predictor_cheating_and_forgery():
    """Verify fraud/forgery text predicts cheating, forgery, and conspiracy companion statutes."""
    text = (
        "The accused impersonated as company director, fabricated loan application and forged board resolutions "
        "dishonestly inducing the bank to disburse loan of Rs. 2 crores."
    )
    preds = MLStatutePredictor.predict_statutes(text, top_k=6, threshold=0.35)
    codes = {p["code"] for p in preds}
    assert "IPC_420" in codes
    assert "IPC_468" in codes
    assert "IPC_471" in codes
    assert "IPC_120B" in codes


def test_case_understanding_post_process_populates_ml_predicted_statutes():
    """Verify CaseUnderstandingAgent._post_process_case populates ml_predicted_statutes."""
    case = StructuredCase(
        case_id="ML-TEST-001",
        case_title="State v. Test Accused",
        allegations_summary="Murder with sharp weapon and custody recovery.",
        charges=[
            Charge(
                section="Section 302",
                statute="Indian Penal Code, 1860",
                description="Murder",
                accused_name="Test Accused",
            )
        ],
    )
    raw_text = (
        "State v. Test Accused. FIR 102/2005 dated 12-08-2005. "
        "The deceased was killed with knives and iron rods. Disclosure statement made in police custody "
        "led to recovery of the murder weapon."
    )
    processed = CaseUnderstandingAgent._post_process_case(case, raw_text)
    assert len(processed.ml_predicted_statutes) >= 1
    assert any("IPC" in item or "IEA" in item for item in processed.ml_predicted_statutes)


def test_legal_research_agent_uses_ml_predictions_respecting_special_act_boundaries():
    """Verify LegalResearchAgent enriches IPC cases with companion laws while keeping RP(UP) special-act isolated."""
    # 1. Historical IPC case gets companion provisions (IPC 34, IEA 27, IEA 102, etc.)
    ipc_case = StructuredCase(
        case_id="IPC-HIST-2005",
        case_title="State v. Accused",
        allegations_summary="Murder and custody disclosure recovery of knife.",
        charges=[
            Charge(
                section="Section 302",
                statute="Indian Penal Code, 1860",
                description="Murder",
                accused_name="Accused",
            )
        ],
        prosecution_facts=[
            "Incident occurred on 12-08-2005.",
            "Accused made disclosure statement in police custody leading to recovery of weapon.",
        ],
    )
    ipc_res = LegalResearchAgent(side="defense").research(
        question="Ingredients of Section 302 IPC and evidentiary value of custody recovery",
        case=ipc_case,
        top_k=8,
    )
    ipc_citations = " ".join(ipc_res.citations)
    assert "Indian Penal Code, 1860, Section 302" in ipc_citations
    assert "Indian Evidence Act, 1872" in ipc_citations

    # 2. Pure Special-Act (RPUP) case gets IEA/CrPC companions without spurious IPC sections
    rpup_case = StructuredCase(
        case_id="RPUP-2007",
        case_title="State v. Scrap Dealer",
        allegations_summary="Possession of stolen railway track angle plates recovered during search without panchas.",
        charges=[
            Charge(
                section="Section 3(a)",
                statute="Railway Property (Unlawful Possession) Act, 1966",
                description="Unlawful possession of railway property",
                accused_name="Scrap Dealer",
            )
        ],
        prosecution_facts=[
            "Date of incident: 26-05-2007.",
            "RPF searched the scrap godown without joining independent local witnesses.",
        ],
    )
    rpup_res = LegalResearchAgent(side="defense").research(
        question="Standards of proof for Section 3(a) Railway Property (Unlawful Possession) Act, 1966",
        case=rpup_case,
        top_k=8,
    )
    rpup_cits = " ".join(rpup_res.citations)
    assert "Railway Property (Unlawful Possession) Act, 1966" in rpup_cits
    assert "Indian Evidence Act, 1872" in rpup_cits
    assert "Indian Penal Code, 1860" not in rpup_cits
