"""
Unit and Integration Tests for Model #2 (Evidentiary Defect Classifier)
and 5-Link Theft & Recovery Chain Evaluator.
"""

from __future__ import annotations

import re

from app.agents.defense_agent import DefenseAgent
from app.agents.evidence_agent import EvidenceAnalysisAgent
from app.models.case_models import Charge, Exhibit, StructuredCase, WitnessStatement
from app.services.ml_defect_classifier import MLEvidentiaryDefectClassifier


def test_ml_defect_classifier_detects_core_defects_without_false_positives():
    """Verify defect detection on genuine loopholes while suppressing unrelated defects."""
    theft_text = (
        "Police searched the shop without any independent public witness and prepared seizure memo. "
        "Recovered unmarked currency notes without serial numbers or ownership proof. "
        "Witness made dock identification for the first time without prior Test Identification Parade (TIP). "
        "Co-accused confessional statement implicated the petitioner."
    )
    defects = MLEvidentiaryDefectClassifier.detect_defects(theft_text, is_historical=True, top_k=6)
    codes = {d["code"] for d in defects}
    assert "NO_INDEPENDENT_PANCH_WITNESS" in codes
    assert "GENERIC_UNIDENTIFIED_PROPERTY" in codes
    assert "NO_PRIOR_TIP_DOCK_ID" in codes
    assert "CO_ACCUSED_CONFESSION_ONLY" in codes
    # Must NOT hallucinate electronic certificate or firearm sanction issues
    assert "MISSING_ELECTRONIC_CERTIFICATE" not in codes
    assert "MISSING_STATUTORY_SANCTION_OR_FSL" not in codes

    arms_text = (
        "Accused charged under Section 25 Arms Act for illegal firearm without previous sanction "
        "under Section 39 Arms Act and without any ballistic FSL report."
    )
    arms_defects = MLEvidentiaryDefectClassifier.detect_defects(arms_text, is_historical=True, top_k=5)
    assert "MISSING_STATUTORY_SANCTION_OR_FSL" in {d["code"] for d in arms_defects}


def test_theft_recovery_chain_audit_triggers_and_gates_properly():
    """Verify 5-Link audit runs on multi-accused theft/recovery cases and returns [] on non-theft cases."""
    theft_case = StructuredCase(
        case_id="THEFT-5LINK-01",
        case_title="State v. Accused A & Accused B",
        accused=["Accused A", "Accused B"],
        allegations_summary="Unlawful possession of stolen cash without serial numbers; Accused B named in co-accused confession.",
        charges=[
            Charge(
                section="Section 411",
                statute="Indian Penal Code, 1860",
                description="Dishonestly receiving stolen property",
                accused_name="Accused A",
            )
        ],
        prosecution_facts=[
            "Date of incident: 12-08-2005.",
            "Seizure memo prepared without independent local panch witnesses; recovered unmarked currency notes.",
        ],
    )
    audit = MLEvidentiaryDefectClassifier.evaluate_theft_recovery_chain(case=theft_case)
    assert len(audit) == 5
    joined = " ".join(audit)
    assert "Link 1" in joined and "Link 5" in joined
    assert "Section 102" in joined or "Section 114" in joined

    non_theft_case = StructuredCase(
        case_id="DEFAM-01",
        case_title="State v. Editor",
        allegations_summary="Allegation of criminal defamation under Section 499 IPC regarding newspaper editorial.",
        charges=[
            Charge(
                section="Section 500",
                statute="Indian Penal Code, 1860",
                description="Defamation",
                accused_name="Editor",
            )
        ],
        prosecution_facts=["Newspaper published article on 10-05-2023."],
    )
    assert MLEvidentiaryDefectClassifier.evaluate_theft_recovery_chain(case=non_theft_case) == []


def test_evidence_and_defense_agents_integrate_ml_defects_without_fake_ids():
    """Verify EvidenceAnalysisAgent and DefenseAgent integrate Model #2 cleanly without fabricating IDs."""
    case = StructuredCase(
        case_id="THEFT-INTEG-01",
        case_title="State v. Raju",
        accused=["Raju"],
        allegations_summary="Recovery of unmarked cash under Section 411 IPC without independent panch witness.",
        charges=[
            Charge(
                section="Section 411",
                statute="Indian Penal Code, 1860",
                description="Receiving stolen property",
                accused_name="Raju",
            )
        ],
        prosecution_facts=[
            "Date of incident: 15-03-2018.",
            "Police recovered unnumbered currency notes without joining any independent public witness.",
        ],
        witnesses=[
            WitnessStatement(
                witness_id="PW-1",
                witness_name="SI Verma",
                witness_type="police_officer",
                testimony_summary="Effected recovery of currency notes.",
                key_assertions=["Recovered unmarked cash from accused."],
            )
        ],
        exhibits=[
            Exhibit(
                exhibit_id="Ex. P-1",
                title="Seizure Memo",
                exhibit_type="recovery_memo",
                description="Recovery memo of currency notes.",
                marked_by="PW-1",
            )
        ],
        missing_or_uncertain_info=["No independent public witness joined during seizure."],
    )

    ev_report = EvidenceAnalysisAgent().analyze_evidence(case=case)
    assert len(ev_report.ml_detected_defects) >= 1
    assert len(ev_report.theft_recovery_chain_audit) >= 4

    # Strictly verify NO synthetic witness/exhibit IDs (PW-*, DW-*, Ex.*) were generated by ML outputs
    ml_blob = " ".join(ev_report.ml_detected_defects + ev_report.theft_recovery_chain_audit)
    assert not re.search(r"\b(?:PW|DW|EV|MO)[- ]\d+\b|\bEx\.?\s*[A-Z]?[- ]?\d+\b", ml_blob, re.IGNORECASE)

    def_case = DefenseAgent().build_defense(case=case, evidence_report=ev_report)
    grounds_blob = " ".join(def_case.reasonable_doubt_grounds)
    assert any(defect in grounds_blob for defect in ev_report.ml_detected_defects)
