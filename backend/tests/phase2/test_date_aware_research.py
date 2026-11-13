"""Offline regression tests for date-aware, source-faithful legal research."""

from app.agents.legal_research_agent import LegalResearchAgent
from app.models.case_models import Charge, StructuredCase
from app.services.legal_transition import detect_case_legal_regime
from rag.retriever import RetrievalResult


def _case(incident: str, statute: str, section: str = "Section 302") -> StructuredCase:
    return StructuredCase(
        case_id="SYNTHETIC", case_title="State v. Test", allegations_summary="Alleged offence.",
        charges=[Charge(section=section, statute=statute, description="Test offence", accused_name="A")],
        prosecution_facts=[f"Date of incident: {incident}."], defense_facts=[],
    )


def _result(short_name: str, act_name: str, section: str) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=f"{short_name}-{section}", text="Whoever commits an act must satisfy the stated requirements.",
        act_name=act_name, short_name=short_name, section=section, article=None,
        title="Test provision", chapter=None, part=None, page=9, source_file=f"{short_name}.pdf",
        score=0.9, distance=0.2, metadata={"short_name": short_name},
    )


class RecordingRetriever:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def retrieve(self, **kwargs):
        self.calls.append(kwargs)
        return self.results


def test_date_cutover_uses_day_level_transition_rule():
    before = detect_case_legal_regime(_case("30-06-2024", "Indian Penal Code, 1860"))
    after = detect_case_legal_regime(_case("01-07-2024", "Bharatiya Nyaya Sanhita, 2023"))
    assert before["regime"] == "historical"
    assert after["regime"] == "modern"


def test_historical_research_never_relabels_a_bsa_chunk_as_indian_evidence_act():
    case = _case("12-08-2005", "Indian Penal Code, 1860")
    retriever = RecordingRetriever([_result("BSA", "Bharatiya Sakshya Adhiniyam, 2023", "Section 63")])
    result = LegalResearchAgent(retriever=retriever).research("electronic evidence", case=case)

    assert result.applicable_provisions == []
    assert result.citations == []
    assert "No modern provision was substituted" in result.findings
    assert set(retriever.calls[0]["act_filters"]) >= {"IPC", "IEA", "CrPC"}


def test_historical_research_preserves_historical_source_and_traceability():
    case = _case("12-08-2005", "Indian Penal Code, 1860")
    retriever = RecordingRetriever([_result("IPC", "Indian Penal Code, 1860", "Section 302")])
    result = LegalResearchAgent(retriever=retriever).research("murder ingredients", case=case)

    provision = result.applicable_provisions[0]
    assert provision.act_name == "Indian Penal Code, 1860"
    assert provision.source_file == "IPC.pdf"
    assert provision.page == 9
    assert provision.applicable_version == "historical"
    assert "Bharatiya" not in provision.citation


def test_modern_research_excludes_historical_statutes():
    case = _case("02-07-2024", "Bharatiya Nyaya Sanhita, 2023")
    retriever = RecordingRetriever([
        _result("IPC", "Indian Penal Code, 1860", "Section 302"),
        _result("BNS", "Bharatiya Nyaya Sanhita, 2023", "Section 103"),
    ])
    result = LegalResearchAgent(retriever=retriever).research("murder ingredients", case=case)

    assert [item.short_name for item in result.applicable_provisions] == ["BNS"]
    assert result.applicable_provisions[0].applicable_version == "modern"
