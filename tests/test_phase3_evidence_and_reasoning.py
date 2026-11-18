"""
Phase 3 Evidence Intelligence & Ingredient-Wise Judicial Reasoning — Test Suite.
Covers Sections 24-27:
- Evidence models, canonical witnesses/exhibits, timeline, accused-wise mapping,
  contradiction matrix, recovery chain-of-custody, gated medical/forensic comparison.
- Statutory ingredient checklist, Devil's Advocate scrutiny, bounded revision,
  multi-accused validation, Shabuddin & Jharkhand offline regression benchmarks,
  and Ground Truth isolation.
"""

from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import MagicMock

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_BACKEND = _ROOT / "backend"
for p in (str(_BACKEND), str(_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.agents.evidence_agent import EvidenceAnalysisAgent
from app.agents.judge_agent import JudgeAgent
from app.agents.scrutiny_agent import DevilsAdvocateScrutiny
from app.models.case_models import Charge, Exhibit, ProceedingScope, StructuredCase, WitnessStatement
from app.models.conflict_models import Conflict, ConflictCategory, ConflictReport, ConflictSeverity
from app.models.judgment_models import (
    AccusedFinding,
    DefenseCase,
    Judgment,
    JudicialIssueAnalysis,
    ProsecutionCase,
)
from app.models.legal_models import ApplicableProvision, LegalResearchResult
from app.services.ingredient_checklist import IngredientChecklistBuilder


def _jharkhand_case() -> StructuredCase:
    return StructuredCase(
        case_id="JH-2026-32683",
        case_title="High Court of Jharkhand at Ranchi, Cr. Rev. 1247/2017 with Cr. Rev. 1512/2017",
        accused=["Md. Israful Ansari", "Md. Nasir Ansari", "Israfil Ansari"],
        allegations_summary="Alleged unlawful possession of railway property.",
        connected_proceedings=[
            ProceedingScope(
                proceeding_id="Cr. Revision No. 1247/2017",
                proceeding_type="revision",
                accused_or_petitioners=["Md. Israful Ansari", "Md. Nasir Ansari"],
            ),
            ProceedingScope(
                proceeding_id="Cr. Revision No. 1512/2017",
                proceeding_type="revision",
                accused_or_petitioners=["Israfil Ansari"],
            ),
        ],
        charges=[
            Charge(
                section="Section 3(a)",
                statute="Railway Property (Unlawful Possession) Act, 1966",
                description="Unlawful possession of railway property",
                accused_name="Md. Israful Ansari",
                elements_alleged=["Property is railway property", "Unlawful possession proved"],
                record_status="current",
            ),
            Charge(
                section="Section 3(a)",
                statute="Railway Property (Unlawful Possession) Act, 1966",
                description="Unlawful possession of railway property",
                accused_name="Md. Nasir Ansari",
                elements_alleged=["Property is railway property", "Unlawful possession proved"],
                record_status="current",
            ),
            Charge(
                section="Section 3(a)",
                statute="Railway Property (Unlawful Possession) Act, 1966",
                description="Unlawful possession of railway property",
                accused_name="Israfil Ansari",
                elements_alleged=["Property is railway property", "Unlawful possession proved"],
                record_status="current",
            ),
        ],
        prosecution_facts=[
            "On 26 May 2007 at 5:00 a.m., Md. Israful Ansari and Md. Nasir Ansari were apprehended near Chetar station.",
            "Apprehended persons allegedly named Israfil Ansari as the person who called them to transport scrap.",
        ],
        witnesses=[
            WitnessStatement(
                witness_id="PW-1",
                witness_name="Vijay Kumar Saha",
                witness_type="police_officer",
                testimony_summary="Raiding team member.",
                key_assertions=["Md. Israful Ansari and Md. Nasir Ansari were apprehended at the spot."],
            ),
            WitnessStatement(
                witness_id="PW-1",
                witness_name="Vijay Kumar Saha",
                witness_type="police_officer",
                testimony_summary="Duplicate entry.",
                key_assertions=[],
            ),
            WitnessStatement(
                witness_id="PW-2",
                witness_name="Netaji Subhash",
                witness_type="expert_witness",
                testimony_summary="Inspected seized railway wheels on 11 June 2008.",
                key_assertions=["Seized articles are railway property."],
            ),
        ],
        exhibits=[
            Exhibit(
                exhibit_id="Ex. P-1",
                title="Seizure list",
                exhibit_type="recovery_memo",
                description="Recovery memo of railway wheels attributed to Md. Israful Ansari and Md. Nasir Ansari",
                marked_by="PW-3",
            ),
            Exhibit(
                exhibit_id="Narrative-1",
                title="Oral mention",
                exhibit_type="documentary",
                description="Narrative mention of prior information",
                marked_by="PW-3",
            ),
        ],
        disputed_facts=[
            "Defence disputes the basis for implicating Israfil Ansari.",
            "Minor discrepancy in exact weight estimate of scrap.",
        ],
        missing_or_uncertain_info=["No independent civilian panch witness joined seizure."],
        procedural_history="Trial court convicted on 26 May 2007 incident; appellate court reduced sentence.",
    )


def _shabuddin_case() -> StructuredCase:
    return StructuredCase(
        case_id="SC-3605-2025",
        case_title="Sd. Shabuddin v. The State of Telangana",
        accused=["Shabuddin", "Moulana"],
        decision_subject="Shabuddin",
        proceeding_type="appeal",
        allegations_summary="Recovery of Rs. 25,000 allegedly linked to theft.",
        charges=[
            Charge(
                section="Section 379",
                statute="Indian Penal Code, 1860",
                description="Theft (acquitted)",
                accused_name="Shabuddin",
                record_status="procedural_history",
            ),
            Charge(
                section="Section 411",
                statute="Indian Penal Code, 1860",
                description="Dishonestly receiving stolen property",
                accused_name="Shabuddin",
                elements_alleged=["Property was stolen", "Accused received/retained with knowledge"],
                record_status="current",
            ),
        ],
        prosecution_facts=[
            "On 22 December 2005, deceased M. Narsaiah travelled to Warangal.",
            "Rs. 25,000 was recovered from Shabuddin's house per PW-30.",
        ],
        defense_facts=["Mere possession of cash does not establish stolen property or guilty knowledge."],
        exhibits=[
            Exhibit(
                exhibit_id="MO-3",
                title="Recovered cash Rs. 25,000",
                exhibit_type="physical_object",
                description="Cash recovered from Shabuddin",
                marked_by="PW-30",
            )
        ],
        disputed_facts=["No distinct identifying mark links Rs. 25,000 to deceased."],
    )


def test_canonical_evidence_deduplication_and_exhibit_marking():
    case = _jharkhand_case()
    report = EvidenceAnalysisAgent(llm_service=MagicMock()).analyze_evidence(case=case)

    # PW-1 duplicate removed; PW-1 and PW-2 preserved
    assert len(report.canonical_witnesses) == 2
    ex_map = {e.exhibit_id: e for e in report.canonical_exhibits}
    assert ex_map["Ex. P-1"].is_formally_marked is True
    assert ex_map["Ex. P-1"].verification_status == "formally_marked"
    assert ex_map["Narrative-1"].is_formally_marked is False
    assert ex_map["Narrative-1"].verification_status == "narrative_mention_only"


def test_accused_wise_evidence_mapping_does_not_merge_or_leak():
    case = _jharkhand_case()
    report = EvidenceAnalysisAgent(llm_service=MagicMock()).analyze_evidence(case=case)

    by_name = {m.accused_name: m for m in report.accused_mappings}
    assert set(by_name.keys()) == {"Md. Israful Ansari", "Md. Nasir Ansari", "Israfil Ansari"}
    assert by_name["Md. Israful Ansari"].proceeding_id == "Cr. Revision No. 1247/2017"
    assert by_name["Israfil Ansari"].proceeding_id == "Cr. Revision No. 1512/2017"
    # Recovery memo attributed to Md. Israful & Md. Nasir must NOT leak to Israfil Ansari
    assert len(by_name["Md. Israful Ansari"].recovery_evidence) == 1
    assert len(by_name["Israfil Ansari"].recovery_evidence) == 0


def test_timeline_contradiction_matrix_recovery_and_gated_medical():
    case = _jharkhand_case()
    report = EvidenceAnalysisAgent(llm_service=MagicMock()).analyze_evidence(case=case)

    assert report.timeline is not None
    assert len(report.timeline.events) >= 2
    assert report.contradiction_matrix is not None
    assert report.contradiction_matrix.material_count >= 1
    assert report.contradiction_matrix.minor_count >= 1
    assert len(report.recovery_analyses) >= 1
    assert any("panch" in link.lower() for link in report.recovery_analyses[0].missing_links)

    # PW-2 is expert_witness, so medical_forensic_comparison is available; on Shabuddin (no medical/expert) -> not_available
    assert report.medical_forensic_comparison.status == "available"
    shab_report = EvidenceAnalysisAgent(llm_service=MagicMock()).analyze_evidence(case=_shabuddin_case())
    assert shab_report.medical_forensic_comparison.status == "not_available"
    assert "not_available" in shab_report.medical_forensic_comparison.notes.lower()


def test_timeline_preserves_conflicting_dates():
    case = _shabuddin_case().model_copy(
        update={
            "prosecution_facts": [
                "Conflicting dates in seizure memo: 22/12/2005 vs 24/12/2005 for recovery."
            ]
        }
    )
    report = EvidenceAnalysisAgent(llm_service=MagicMock()).analyze_evidence(case=case)
    assert report.timeline is not None
    assert len(report.timeline.date_conflicts_detected) == 1
    assert report.timeline.events[0].has_date_conflict is True
    assert set(report.timeline.events[0].conflicting_dates) == {"22/12/2005", "24/12/2005"}


def test_ingredient_checklist_builder_maps_verified_statute_and_missing_statute():
    case = _shabuddin_case()
    ev_report = EvidenceAnalysisAgent(llm_service=MagicMock()).analyze_evidence(case=case)
    research = LegalResearchResult(
        research_id="RES-1",
        side="prosecution",
        status="completed",
        question="Section 411 IPC",
        findings="Found",
        applicable_provisions=[
            ApplicableProvision(
                act_name="Indian Penal Code, 1860",
                short_name="IPC",
                section_or_article="Section 411",
                page=10,
                source_file="IPC.pdf",
                chunk_id="ipc_411",
                citation="Indian Penal Code, 1860, Section 411",
                text="Whoever dishonestly receives or retains any stolen property...",
                relevance_reasoning="Governs stolen property.",
                legal_ingredients=["Property must be stolen property", "Dishonest receipt with knowledge"],
            )
        ],
        citations=["Indian Penal Code, 1860, Section 411"],
        reasoning_relevance="Historical IPC applies.",
    )
    checklists = IngredientChecklistBuilder.build(
        case=case,
        evidence_report=ev_report,
        prosecution_legal_research=research,
    )
    assert len(checklists) == 1
    assert checklists[0].charge_key == "Indian Penal Code, 1860, Section 411"
    assert len(checklists[0].ingredients) == 2
    assert checklists[0].ingredients[0].source_citation == "Indian Penal Code, 1860, Section 411"


def test_devils_advocate_scrutiny_flags_defects_and_judge_runs_bounded_revision():
    case = _jharkhand_case()
    ev_report = EvidenceAnalysisAgent(llm_service=MagicMock()).analyze_evidence(case=case)
    conflict_report = ConflictReport(
        case_id=case.case_id,
        total_conflicts=1,
        critical_conflicts_count=1,
        conflicts=[
            Conflict(
                conflict_id="C-1",
                category=ConflictCategory.EVIDENCE_CONTRADICTION,
                statement_a="Seized from Md. Israful Ansari",
                statement_b="No independent panch witness",
                severity=ConflictSeverity.HIGH,
                explanation="Unverified recovery",
                impact_on_case="Affects proof",
            )
        ],
        summary="Critical conflict.",
    )
    pros = ProsecutionCase(case_id=case.case_id, prosecution_theory="Guilty", final_prayer="Convict")
    defn = DefenseCase(case_id=case.case_id, defense_theory="Not proved", alternative_interpretation="Doubt", final_prayer="Acquit")

    # Draft 1 omits accused_findings (high severity scrutiny challenge)
    draft1 = Judgment(
        case_title=case.case_title,
        date_of_decision="2026-11-18",
        case_background="Bg",
        issues_for_determination=["Issue 1"],
        applicable_law=["Section 3(a)"],
        evidence_assessment="PW-1 and Ex. P-1 evaluated.",
        witness_assessment="PW-1 assessed.",
        prosecution_submissions="Pros.",
        defense_submissions="Def.",
        issue_analyses=[
            JudicialIssueAnalysis(
                issue_number=1,
                issue_statement="Issue 1",
                applicable_law="Section 3(a)",
                prosecution_submission_summary="P",
                defense_submission_summary="D",
                evidentiary_evaluation="E",
                judicial_finding="NOT PROVED",
            )
        ],
        findings_per_charge={"Railway Property (Unlawful Possession) Act, 1966, Section 3(a)": "Acquitted"},
        accused_findings=[],
        final_decision="ACQUITTAL",
        reasons="Benefit of doubt due to contradiction.",
        legal_citations=["Section 3(a) of the Railway Property (Unlawful Possession) Act, 1966"],
    )
    revised = draft1.model_copy(
        update={
            "accused_findings": [
                AccusedFinding(accused_name="Md. Israful Ansari", proceeding_id="Cr. Revision No. 1247/2017", finding="ACQUITTAL", reasoning_summary="Doubt"),
                AccusedFinding(accused_name="Md. Nasir Ansari", proceeding_id="Cr. Revision No. 1247/2017", finding="ACQUITTAL", reasoning_summary="Doubt"),
                AccusedFinding(accused_name="Israfil Ansari", proceeding_id="Cr. Revision No. 1512/2017", finding="ACQUITTAL", reasoning_summary="No direct link"),
            ]
        }
    )

    mock_llm = MagicMock()
    mock_llm.generate_structured.side_effect = [draft1, revised]

    judge = JudgeAgent(llm_service=mock_llm, enable_scrutiny=True)
    final_judgment = judge.adjudicate(
        case=case,
        prosecution_case=pros,
        defense_case=defn,
        evidence_report=ev_report,
        conflict_report=conflict_report,
    )
    assert mock_llm.generate_structured.call_count == 2  # 1 draft + 1 bounded scrutiny revision
    assert final_judgment.scrutiny_report is not None
    assert final_judgment.scrutiny_report.requires_revision is True
    assert len(final_judgment.accused_findings) == 3
    assert len(final_judgment.ingredient_checklists) == 3


def test_devils_advocate_catches_burden_reversal():
    case = _shabuddin_case()
    ev_report = EvidenceAnalysisAgent(llm_service=MagicMock()).analyze_evidence(case=case)
    conflict_report = ConflictReport(case_id=case.case_id, total_conflicts=0, summary="None")
    bad_draft = Judgment(
        case_title=case.case_title,
        date_of_decision="2026-11-18",
        case_background="Bg",
        issues_for_determination=["Issue 1"],
        applicable_law=["Section 411 IPC"],
        evidence_assessment="Accused failed to prove his innocence after mere recovery.",
        witness_assessment="PW-30",
        prosecution_submissions="P",
        defense_submissions="D",
        issue_analyses=[
            JudicialIssueAnalysis(
                issue_number=1,
                issue_statement="Issue 1",
                applicable_law="Section 411 IPC",
                prosecution_submission_summary="P",
                defense_submission_summary="D",
                evidentiary_evaluation="E",
                judicial_finding="PROVED",
            )
        ],
        findings_per_charge={"Indian Penal Code, 1860, Section 411": "Convicted"},
        final_decision="CONVICTION",
        reasons="Mere recovery proves guilt.",
        legal_citations=["Section 411 IPC"],
    )
    rep = DevilsAdvocateScrutiny(enable_llm=False).review(
        draft=bad_draft,
        case=case,
        evidence_report=ev_report,
        conflict_report=conflict_report,
        checklists=[],
    )
    cats = {c.category for c in rep.challenges}
    assert "burden_of_proof_reversal" in cats
    assert "unsupported_recovery_inference" in cats
    assert rep.requires_revision is True
