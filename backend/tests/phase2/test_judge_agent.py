"""Hermetic tests for the structured DeepSeek-backed JudgeAgent."""

import json
from pathlib import Path
import tempfile

import pytest

from app.agents.judge_agent import JudgeAgent
from app.models.case_models import Charge, Exhibit, StructuredCase, WitnessStatement
from app.models.conflict_models import Conflict, ConflictCategory, ConflictReport, ConflictSeverity
from app.models.evidence_models import EvidenceAnalysisReport, EvidenceItemAnalysis, EvidenceType
from app.models.judgment_models import DefenseCase, Judgment, ProsecutionCase
from app.models.legal_models import ApplicableProvision, LegalResearchResult, WebResearchItem, WebResearchResult
from app.services.judgment_writer import JudgmentWriter


def make_record():
    case = StructuredCase(
        case_id="CASE-TEST",
        case_title="State v. Example",
        allegations_summary="The accused allegedly retained a recovered item.",
        charges=[Charge(
            section="Section 317",
            statute="Bharatiya Nyaya Sanhita, 2023",
            description="Dishonestly receiving or retaining stolen property",
            accused_name="Example",
            elements_alleged=["Possession", "Knowledge of stolen nature"],
        )],
        prosecution_facts=["PW-1 identified the item at seizure."],
        defense_facts=["The defense disputes knowledge and challenges identification."],
        witnesses=[WitnessStatement(
            witness_id="PW-1", witness_name="Witness One", witness_type="eye_witness",
            testimony_summary="Identified the item during seizure.",
            key_assertions=["Saw the item"], reliability_indicators=["No cross-check supplied"],
        )],
        exhibits=[Exhibit(
            exhibit_id="Ex. P-1", title="Seizure memo", exhibit_type="documentary",
            description="Record of the seizure.", marked_by="PW-1",
        )],
        legal_issues=["Whether possession and knowledge are proved?"],
        disputed_facts=["Whether the accused knew the item was stolen."],
        missing_or_uncertain_info=["No independent witness is identified in the packet."],
    )
    prosecution = ProsecutionCase(
        case_id=case.case_id,
        prosecution_theory="The seizure and identification establish knowing possession.",
        statutory_elements=["Possession", "Knowledge"],
        supporting_witnesses=["PW-1"],
        supporting_exhibits=["Ex. P-1"],
        final_prayer="Conviction",
    )
    defense = DefenseCase(
        case_id=case.case_id,
        defense_theory="Identification does not prove knowledge.",
        reasonable_doubt_grounds=["Knowledge is disputed."],
        witness_inconsistencies_highlighted=["No independent witness is identified."],
        missing_evidence_highlighted=["No independent seizure witness."],
        alternative_interpretation="Possession could have been innocent.",
        final_prayer="Acquittal",
    )
    evidence = EvidenceAnalysisReport(
        case_id=case.case_id,
        evidence_items=[EvidenceItemAnalysis(
            id="Ex. P-1", type=EvidenceType.DOCUMENTARY, description="Seizure memo",
            source="Marked by PW-1", related_witness="PW-1", supports=["Seizure occurred"],
            limitations=["No independent witness identified"], confidence=0.6,
        )],
        missing_evidence_gaps=["Independent seizure witness not identified."],
        documentary_compliance_assessment="Authentication details are incomplete in the packet.",
        summary="The seizure record is present but has a corroboration gap.",
    )
    conflicts = ConflictReport(
        case_id=case.case_id,
        total_conflicts=1,
        conflicts=[Conflict(
            conflict_id="CONF-1", category=ConflictCategory.PROSECUTION_VS_DEFENSE,
            statement_a="Knowledge is inferred from possession.",
            statement_b="Knowledge is denied.", sources=["Prosecution", "Defense"],
            severity=ConflictSeverity.MEDIUM, explanation="The inference is contested.",
            impact_on_case="Requires assessment of the surrounding proof.",
        )],
        summary="The parties dispute whether possession proves knowledge.",
    )
    legal = LegalResearchResult(
        research_id="RES-1", side="judicial", question="Elements of Section 317",
        findings="Knowledge of stolen nature is material.",
        applicable_provisions=[ApplicableProvision(
            act_name="Bharatiya Nyaya Sanhita, 2023", short_name="BNS",
            section_or_article="Section 317", page=1, source_file="bns.pdf",
            chunk_id="chunk-1", citation="Bharatiya Nyaya Sanhita, 2023, Section 317",
            text="Supplied provision text.", relevance_reasoning="Governs the charge.",
        )],
        citations=["Bharatiya Nyaya Sanhita, 2023, Section 317"], source_pages=[1],
        reasoning_relevance="The retrieved provision governs the charge.",
    )
    return case, prosecution, defense, evidence, conflicts, legal


class JudgeLLMMock:
    def __init__(self, *, fail=False, invent_reference=False):
        self.calls = []
        self.fail = fail
        self.invent_reference = invent_reference

    def generate_structured(self, prompt, response_schema, system_prompt="", fallback_data=None):
        self.calls.append((prompt, response_schema, system_prompt, fallback_data))
        if self.fail:
            raise RuntimeError("OpenRouter quota error")
        dossier = json.loads(prompt.split("LIVE TRIAL DOSSIER (contains no Ground Truth):\n", 1)[1])
        case = dossier["original_case_record"]
        citation = dossier["allowed_citations"][0]
        ref = "PW-88" if self.invent_reference else "PW-1"
        return response_schema.model_validate({
            "case_title": "model-generated title is overwritten",
            "date_of_decision": "1900-01-01",
            "case_background": "Background drawn from the supplied record.",
            "issues_for_determination": case["legal_issues"],
            "applicable_law": [citation],
            "evidence_assessment": f"{ref} and Ex. P-1 are assessed with the limitations recorded.",
            "witness_assessment": "PW-1 is assessed only from the recorded statement and reliability indicators.",
            "prosecution_submissions": "The prosecution argument is assessed as advocacy, not proof.",
            "defense_submissions": "The defense argument is considered independently.",
            "issue_analyses": [{
                "issue_number": 1, "issue_statement": case["legal_issues"][0],
                "applicable_law": citation,
                "prosecution_submission_summary": "The seizure is relied on.",
                "defense_submission_summary": "Knowledge is challenged.",
                "evidentiary_evaluation": f"{ref} and Ex. P-1 require corroboration assessment.",
                "judicial_finding": "NOT PROVED",
            }],
            "findings_per_charge": {citation: "NOT PROVED"},
            "final_decision": "ACQUITTAL",
            "reasons": "The record and its stated gaps are weighed without assuming facts not supplied.",
            "legal_citations": [citation],
        })


def test_judge_calls_openrouter_with_complete_record_and_returns_schema():
    case, prosecution, defense, evidence, conflicts, legal = make_record()
    mock = JudgeLLMMock()
    pros_web = WebResearchResult(
        research_id="WEB-P", side="prosecution", research_question="Burden of proof",
        finding="A precedent may be relevant.",
        sources=[WebResearchItem(
            title="Prosecution precedent", url="https://example.test/pros",
            passage_summary="Provided precedent summary.", why_source_matters="Addresses prosecution issue.",
        )],
        why_it_matters="Relevant to prosecution argument.",
    )
    defense_web = WebResearchResult(
        research_id="WEB-D", side="defense", research_question="Reasonable doubt",
        finding="A defense precedent may be relevant.",
        sources=[WebResearchItem(
            title="Defense precedent", url="https://example.test/defense",
            passage_summary="Provided defense precedent summary.", why_source_matters="Addresses defense issue.",
        )],
        why_it_matters="Relevant to defense argument.",
    )
    judgment = JudgeAgent(llm_service=mock).adjudicate(
        case, prosecution, defense, evidence, conflicts,
        prosecution_legal_research=legal,
        prosecution_web_research=pros_web,
        defense_web_research=defense_web,
    )

    assert isinstance(judgment, Judgment)
    assert len(mock.calls) == 1
    prompt, schema, system_prompt, fallback_data = mock.calls[0]
    assert schema is Judgment and fallback_data is None
    assert prosecution.prosecution_theory in prompt
    assert defense.defense_theory in prompt
    assert evidence.summary in prompt
    assert conflicts.summary in prompt
    assert legal.citations[0] in prompt
    assert "Prosecution precedent" in prompt and "Defense precedent" in prompt
    assert "PW-1" in prompt and "Ex. P-1" in prompt
    assert system_prompt and "Do not invent facts" in system_prompt
    assert judgment.case_title == case.case_title
    assert judgment.judgment_id == f"JUDG-{case.case_id}"
    assert judgment.date_of_decision != "1900-01-01"


def test_judge_rejects_ground_truth_before_llm_call():
    case, prosecution, defense, evidence, conflicts, _ = make_record()
    tainted = case.model_copy(update={"case_title": "Ground Truth Verdict: Convicted"})
    mock = JudgeLLMMock()
    with pytest.raises(PermissionError, match="SECURITY VIOLATION"):
        JudgeAgent(llm_service=mock).adjudicate(tainted, prosecution, defense, evidence, conflicts)
    assert mock.calls == []


def test_judge_rejects_invented_evidence_identifier():
    case, prosecution, defense, evidence, conflicts, legal = make_record()
    mock = JudgeLLMMock(invent_reference=True)
    with pytest.raises(ValueError, match="identifier absent from the record"):
        JudgeAgent(llm_service=mock).adjudicate(
            case, prosecution, defense, evidence, conflicts, prosecution_legal_research=legal
        )


def test_judge_surfaces_provider_failure_without_fabricating_judgment():
    case, prosecution, defense, evidence, conflicts, _ = make_record()
    mock = JudgeLLMMock(fail=True)
    with pytest.raises(RuntimeError, match="quota error"):
        JudgeAgent(llm_service=mock).adjudicate(case, prosecution, defense, evidence, conflicts)
    assert len(mock.calls) == 1


def test_structured_judgment_still_persists_to_json_txt_and_pdf():
    case, prosecution, defense, evidence, conflicts, legal = make_record()
    judgment = JudgeAgent(llm_service=JudgeLLMMock()).adjudicate(
        case, prosecution, defense, evidence, conflicts, prosecution_legal_research=legal
    )
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as out_dir:
        paths = JudgmentWriter().persist_judgment(
            case_id=case.case_id, judgment=judgment, custom_output_dir=out_dir
        )
        assert all(Path(paths[key]).exists() for key in ("json", "txt", "pdf"))
        saved = json.loads(Path(paths["json"]).read_text(encoding="utf-8"))
        assert saved["final_decision"] == judgment.final_decision
