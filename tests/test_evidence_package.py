"""
Tests for Standardized Evidence PDF Ingestion and Representation Layer.

Covers all 25 specific test areas:
1. Evidence PDF loads.
2. Case information extracted.
3. Multiple witnesses extracted.
4. Multiple exhibits extracted.
5. Physical evidence extracted.
6. Recovery evidence extracted.
7. Identification evidence extracted.
8. Testimony claims extracted.
9. Statements extracted.
10. Procedural evidence extracted.
11. Evidence linkages created.
12. Contradictions represented.
13. Missing evidence represented.
14. Page provenance preserved.
15. Prosecution and defence evidence remain distinguishable.
16. Claims are not converted into facts.
17. Ground Truth PDF rejected.
18. Real Verdict PDF rejected.
19. Ground Truth content cannot enter EvidencePackage.
20. Evidence Agent consumes EvidencePackage.
21. Judge receives EvidencePackage/EvidenceAnalysis.
22. No guilt/innocence decision is made by extraction.
23. Parser works with variable witness/exhibit counts.
24. Empty sections are handled correctly.
25. Malformed Evidence PDF produces structured error.
+ Real Case Validation against supplied case evidence (PW-1..PW-8, Ex.PA..Ex.PK).
"""

from pathlib import Path
import pytest
import pymupdf

from app.agents.evidence_agent import EvidenceAnalysisAgent
from app.agents.judge_agent import JudgeAgent
from app.graph.state import CourtState, JudgeInput
from app.ingestion.evidence_extractor import EvidenceExtractor
from app.ingestion.evidence_loader import (
    EvidencePDFLoader,
    GroundTruthLeakageError,
    MalformedEvidencePDFError,
)
from app.models.case_models import StructuredCase
from app.models.conflict_models import ConflictReport
from app.models.evidence_models import EvidenceAnalysisReport
from app.models.evidence_package_models import (
    ClaimType,
    EvidenceItem,
    EvidencePackage,
    Witness,
)
from app.models.judgment_models import DefenseCase, ProsecutionCase
from rag.loader import PDFPage


REAL_CASE_EVIDENCE_TEXT = """
[Page 1]
IN THE HIGH COURT OF PUNJAB & HARYANA AT CHANDIGARH
CRA-S-174-SB-2005
Jai Bhagwan & Ors. ..... Appellants
VERSUS
State of Haryana ..... Respondent

[Page 2]
The FIR No.50 dated 01.07.2002 was lodged in Police Station Mohana for commission
of offence punishable under Sections 412, 420, 468, 471 of Indian Penal Code and Section 25 of Arms Act.

[Page 3]
A team headed by SHO Police Station Mohana, namely SI Lachhman Singh, intercepted an Indica car.
The registration number plate was bearing No.DL3-CP-3753, but on close scrutiny actual number was different.

[Page 4]
the car was robbed in an incident of dacoity, and that with regard to such incident the FIR No.149 dated 16.05.2002
was registered in Police Station Sadar Rohtak. As per prosecution, during the course of further investigation,
the Investigating Officer inspected the spot, prepared rough site plan of the place of occurrence,
recorded the statement of witnesses under Section 161 CrPC, and completed other usual formalities of investigation.
Thereafter, the final report under Section 173 of CrPC was filed.

5. To discharge its burden of proving the charges against the appellants, the prosecution in the instant case
had relied upon oral as well as documentary evidence, both. The documents proved and marked with exhibits,
by the prosecution were:-
Ex.PA - Affidavit of Om Parkash
Ex.P1 & Ex.P2 - Both the number plates
Ex.P3 - Pistol, recovered from the appellant, namely Jai Bhagwan
Ex.PB - Seizure memo of Indica car and countrymade pistol
Ex.PB/1 - Sketch of the pistol
Ex.PC - The information memo sent to the police station (ruqqa)
Ex.PC/1 - Copy of First Information Report
Ex.PC/2 - Endorsement recorded on the information memo
Ex.PD - Affidavit of HC Satyawan
Ex.PE - Statement of Fateh Singh
Ex.PG - Memo of Identification of the car by the PW-6 Gurnam Singh
Ex.PH - Release order of car in question
Ex.PK - Photocopy of FIR No.149 dated 16.05.2002, Police Station Sadar Rohtak

[Page 5]
6. To provide support and corroboration to the above-mentioned documentary evidence, as many as eight witnesses
were examined by the prosecution. They were:-
PW-1 - Om Parkash
PW-2 - HC Umed Singh
PW-3 - HC Satyawan
PW-4 - Fateh Singh
PW-5 - Silak Ram, Reader to District Magistrate Sonepat
PW-6 - Gurnam Singh
PW-7 - Inspector Lachman Singh
PW-8 - ASI Ishwar Singh

7. Once the prosecution evidence was recorded, the learned trial Court completed all the essential formalities,
enshrined under Section 313 CrPC. Thereafter, opportunity of defence evidence was afforded to the appellants.
In their defence evidence, no evidence was adduced by the appellants.
"""


@pytest.fixture
def evidence_pdf_fixture(tmp_path: Path) -> Path:
    """Generate a realistic synthetic Evidence_Packet.pdf with pages 1-5."""
    pdf_path = tmp_path / "Evidence_Packet.pdf"
    doc = pymupdf.open()
    pages_raw = REAL_CASE_EVIDENCE_TEXT.strip().split("[Page ")
    for p_block in pages_raw:
        if not p_block.strip():
            continue
        lines = p_block.split("]\n", 1)
        p_content = lines[1] if len(lines) > 1 else lines[0]
        page = doc.new_page(width=595, height=842)
        y = 50
        for line in p_content.strip().split("\n"):
            page.insert_text(pymupdf.Point(40, y), line.strip(), fontsize=9, fontname="helv")
            y += 14
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


# -----------------------------------------------------------------------------
# 1. Evidence PDF loads
# -----------------------------------------------------------------------------
def test_1_evidence_pdf_loads(evidence_pdf_fixture: Path):
    loader = EvidencePDFLoader()
    pages = loader.load_pdf(evidence_pdf_fixture)
    assert len(pages) == 5
    assert all(isinstance(p, PDFPage) for p in pages)
    assert pages[3].page_number == 4
    assert "Ex.PA" in pages[3].text


# -----------------------------------------------------------------------------
# 2. Case information extracted
# -----------------------------------------------------------------------------
def test_2_case_information_extracted(evidence_pdf_fixture: Path):
    loader = EvidencePDFLoader()
    pages = loader.load_pdf(evidence_pdf_fixture)
    extractor = EvidenceExtractor()
    pkg = extractor.extract(pages, source_filename="Evidence_Packet.pdf")

    assert pkg.case_identification is not None
    assert "State" in (pkg.case_identification.case_title or "") or "Jai Bhagwan" in (pkg.case_identification.case_title or "")
    assert pkg.case_identification.police_station is not None
    assert len(pkg.case_identification.relevant_dates) > 0
    # Verify missing fields are None or empty, not invented
    assert isinstance(pkg.case_identification.parties, list)


# -----------------------------------------------------------------------------
# 3. Multiple witnesses extracted
# -----------------------------------------------------------------------------
def test_3_multiple_witnesses_extracted(evidence_pdf_fixture: Path):
    loader = EvidencePDFLoader()
    pages = loader.load_pdf(evidence_pdf_fixture)
    extractor = EvidenceExtractor()
    pkg = extractor.extract(pages)

    assert len(pkg.prosecution_witnesses) == 8
    pw_ids = [w.witness_id for w in pkg.prosecution_witnesses]
    for i in range(1, 9):
        assert f"PW-{i}" in pw_ids
    # Verify name and side preservation
    pw6 = next(w for w in pkg.prosecution_witnesses if w.witness_id == "PW-6")
    assert "Gurnam Singh" in pw6.name
    assert pw6.side == "Prosecution"


# -----------------------------------------------------------------------------
# 4. Multiple exhibits extracted
# -----------------------------------------------------------------------------
def test_4_multiple_exhibits_extracted(evidence_pdf_fixture: Path):
    loader = EvidencePDFLoader()
    pages = loader.load_pdf(evidence_pdf_fixture)
    extractor = EvidenceExtractor()
    pkg = extractor.extract(pages)

    assert len(pkg.exhibits) >= 14
    ex_nums = [e.exhibit_number for e in pkg.exhibits]
    expected = ["Ex.PA", "Ex.P1", "Ex.P2", "Ex.P3", "Ex.PB", "Ex.PB/1", "Ex.PC", "Ex.PC/1", "Ex.PC/2", "Ex.PD", "Ex.PE", "Ex.PG", "Ex.PH", "Ex.PK"]
    for exp in expected:
        assert exp in ex_nums, f"Expected exhibit {exp} to be present in extracted exhibits."


# -----------------------------------------------------------------------------
# 5. Physical evidence extracted
# -----------------------------------------------------------------------------
def test_5_physical_evidence_extracted(evidence_pdf_fixture: Path):
    loader = EvidencePDFLoader()
    pages = loader.load_pdf(evidence_pdf_fixture)
    extractor = EvidenceExtractor()
    pkg = extractor.extract(pages)

    assert len(pkg.physical_evidence) > 0
    items = [pe.item_description.lower() for pe in pkg.physical_evidence]
    has_weapon = any("pistol" in it or "weapon" in it for it in items)
    has_plates = any("plate" in it for it in items)
    assert has_weapon
    assert has_plates


# -----------------------------------------------------------------------------
# 6. Recovery evidence extracted
# -----------------------------------------------------------------------------
def test_6_recovery_evidence_extracted(evidence_pdf_fixture: Path):
    loader = EvidencePDFLoader()
    pages = loader.load_pdf(evidence_pdf_fixture)
    extractor = EvidenceExtractor()
    pkg = extractor.extract(pages)

    assert len(pkg.recoveries) > 0
    rec = pkg.recoveries[0]
    assert rec.recovery_id.startswith("REC-")
    assert rec.prosecution_claim is not None
    assert "prosecution claims" in rec.prosecution_claim.lower()


# -----------------------------------------------------------------------------
# 7. Identification evidence extracted
# -----------------------------------------------------------------------------
def test_7_identification_evidence_extracted(evidence_pdf_fixture: Path):
    loader = EvidencePDFLoader()
    pages = loader.load_pdf(evidence_pdf_fixture)
    extractor = EvidenceExtractor()
    pkg = extractor.extract(pages)

    assert len(pkg.identifications) > 0
    ident = pkg.identifications[0]
    assert ident.identification_type in ["vehicle identification", "document or object identification"]
    assert "Ex.PG" in (ident.identification_memo or "")


# -----------------------------------------------------------------------------
# 8. Testimony claims extracted
# -----------------------------------------------------------------------------
def test_8_testimony_claims_extracted(evidence_pdf_fixture: Path):
    loader = EvidencePDFLoader()
    pages = loader.load_pdf(evidence_pdf_fixture)
    extractor = EvidenceExtractor()
    pkg = extractor.extract(pages)

    assert len(pkg.testimony_claims) >= 8
    claim_types = {c.claim_type for c in pkg.testimony_claims}
    valid_types = {ct.value for ct in ClaimType}
    for ct in claim_types:
        assert ct.value in valid_types


# -----------------------------------------------------------------------------
# 9. Statements extracted
# -----------------------------------------------------------------------------
def test_9_statements_extracted(evidence_pdf_fixture: Path):
    loader = EvidencePDFLoader()
    pages = loader.load_pdf(evidence_pdf_fixture)
    extractor = EvidenceExtractor()
    pkg = extractor.extract(pages)

    assert len(pkg.statements) > 0
    stm = pkg.statements[0]
    assert "Fateh Singh" in stm.person
    assert "Ex.PE" in stm.related_evidence


# -----------------------------------------------------------------------------
# 10. Procedural evidence extracted
# -----------------------------------------------------------------------------
def test_10_procedural_evidence_extracted(evidence_pdf_fixture: Path):
    loader = EvidencePDFLoader()
    pages = loader.load_pdf(evidence_pdf_fixture)
    extractor = EvidenceExtractor()
    pkg = extractor.extract(pages)

    assert len(pkg.procedural_records) >= 3
    types = [pr.procedure_type for pr in pkg.procedural_records]
    assert "FIR registration" in types or "site inspection" in types or "final report" in types


# -----------------------------------------------------------------------------
# 11. Evidence linkages created
# -----------------------------------------------------------------------------
def test_11_evidence_linkages_created(evidence_pdf_fixture: Path):
    loader = EvidencePDFLoader()
    pages = loader.load_pdf(evidence_pdf_fixture)
    extractor = EvidenceExtractor()
    pkg = extractor.extract(pages)

    assert len(pkg.evidence_links) > 0
    link_types = [l.relation_type for l in pkg.evidence_links]
    assert any(lt in ["testified_about", "produced", "identified"] for lt in link_types)


# -----------------------------------------------------------------------------
# 12. Contradictions represented
# -----------------------------------------------------------------------------
def test_12_contradictions_represented(evidence_pdf_fixture: Path):
    loader = EvidencePDFLoader()
    pages = loader.load_pdf(evidence_pdf_fixture)
    extractor = EvidenceExtractor()
    pkg = extractor.extract(pages)

    assert len(pkg.contradictions) > 0
    c = pkg.contradictions[0]
    assert c.statement_a
    assert c.statement_b
    assert c.source_a
    assert c.source_b


# -----------------------------------------------------------------------------
# 13. Missing evidence represented
# -----------------------------------------------------------------------------
def test_13_missing_evidence_represented(evidence_pdf_fixture: Path):
    loader = EvidencePDFLoader()
    pages = loader.load_pdf(evidence_pdf_fixture)
    extractor = EvidenceExtractor()
    pkg = extractor.extract(pages)

    assert len(pkg.missing_evidence) > 0
    m = pkg.missing_evidence[0]
    assert m.explicitly_stated is True
    assert "defence" in m.description.lower() or "panch" in m.description.lower()


# -----------------------------------------------------------------------------
# 14. Page provenance preserved
# -----------------------------------------------------------------------------
def test_14_page_provenance_preserved(evidence_pdf_fixture: Path):
    loader = EvidencePDFLoader()
    pages = loader.load_pdf(evidence_pdf_fixture)
    extractor = EvidenceExtractor()
    pkg = extractor.extract(pages, source_filename="Evidence_Packet.pdf")

    # Check exhibit page provenance
    ex_pa = next(e for e in pkg.exhibits if e.exhibit_number == "Ex.PA")
    assert ex_pa.source_page == 4
    assert ex_pa.source.page == 4
    assert ex_pa.source.source_file == "Evidence_Packet.pdf"

    # Check witness page provenance
    pw1 = next(w for w in pkg.prosecution_witnesses if w.witness_id == "PW-1")
    assert pw1.source_page == 5
    assert pw1.source.page == 5


# -----------------------------------------------------------------------------
# 15. Prosecution and defence evidence remain distinguishable
# -----------------------------------------------------------------------------
def test_15_prosecution_and_defence_remain_distinguishable(evidence_pdf_fixture: Path):
    loader = EvidencePDFLoader()
    pages = loader.load_pdf(evidence_pdf_fixture)
    extractor = EvidenceExtractor()
    pkg = extractor.extract(pages)

    # In this fixture, all 8 witnesses are prosecution witnesses, defence is empty
    assert len(pkg.prosecution_witnesses) == 8
    assert len(pkg.defence_witnesses) == 0
    assert all(w.side == "Prosecution" for w in pkg.prosecution_witnesses)


# -----------------------------------------------------------------------------
# 16. Claims are not converted into facts
# -----------------------------------------------------------------------------
def test_16_claims_not_converted_into_facts(evidence_pdf_fixture: Path):
    loader = EvidencePDFLoader()
    pages = loader.load_pdf(evidence_pdf_fixture)
    extractor = EvidenceExtractor()
    pkg = extractor.extract(pages)

    for rec in pkg.recoveries:
        if rec.prosecution_claim:
            assert "claims" in rec.prosecution_claim.lower() or "alleged" in rec.prosecution_claim.lower()

    for ch in pkg.charges:
        assert "allegation" in ch.allegation_description.lower() or "alleged" in ch.allegation_description.lower()


# -----------------------------------------------------------------------------
# 17. Ground Truth PDF rejected
# -----------------------------------------------------------------------------
def test_17_ground_truth_pdf_rejected(tmp_path: Path):
    loader = EvidencePDFLoader()
    gt_file = tmp_path / "Ground_Truth_Verdict.pdf"
    gt_file.write_text("Conviction and final judgment outcome.")

    with pytest.raises(GroundTruthLeakageError, match="SECURITY VIOLATION"):
        loader.load_pdf(gt_file)


# -----------------------------------------------------------------------------
# 18. Real Verdict PDF rejected
# -----------------------------------------------------------------------------
def test_18_real_verdict_pdf_rejected(tmp_path: Path):
    loader = EvidencePDFLoader()
    verdict_file = tmp_path / "real_verdict_appeal.pdf"
    verdict_file.write_text("Final decision of the high court.")

    with pytest.raises(GroundTruthLeakageError, match="SECURITY VIOLATION"):
        loader.load_pdf(verdict_file)


# -----------------------------------------------------------------------------
# 19. Ground Truth content cannot enter EvidencePackage
# -----------------------------------------------------------------------------
def test_19_ground_truth_content_cannot_enter_evidence_package():
    loader = EvidencePDFLoader()
    tainted_text = "Case evidence. Final verdict: convicted. Ground truth is guilty."

    with pytest.raises(GroundTruthLeakageError, match="SECURITY VIOLATION"):
        loader.load_text(tainted_text)


# -----------------------------------------------------------------------------
# 20. Evidence Agent consumes EvidencePackage
# -----------------------------------------------------------------------------
def test_20_evidence_agent_consumes_evidence_package(evidence_pdf_fixture: Path):
    loader = EvidencePDFLoader()
    pages = loader.load_pdf(evidence_pdf_fixture)
    pkg = EvidenceExtractor().extract(pages)

    agent = EvidenceAnalysisAgent()
    report = agent.analyze_evidence(evidence_package=pkg)

    assert isinstance(report, EvidenceAnalysisReport)
    assert len(report.evidence_items) >= 14
    assert len(report.corroboration_links) > 0
    assert report.documentary_compliance_assessment


# -----------------------------------------------------------------------------
# 21. Judge receives EvidencePackage/EvidenceAnalysis
# -----------------------------------------------------------------------------
def test_21_judge_receives_evidence_package_and_analysis(evidence_pdf_fixture: Path):
    loader = EvidencePDFLoader()
    pages = loader.load_pdf(evidence_pdf_fixture)
    pkg = EvidenceExtractor().extract(pages)
    report = EvidenceAnalysisAgent().analyze_evidence(evidence_package=pkg)

    dummy_case = StructuredCase(
        case_id="CASE-REAL",
        case_title="State v. Accused",
        allegations_summary="Theft and illegal possession of arms.",
    )
    pros_case = ProsecutionCase(
        case_id="CASE-REAL",
        prosecution_theory="Accused was in conscious possession of stolen vehicle and unlicensed pistol.",
        final_prayer="The prosecution prays for conviction of the accused under all charged sections.",
    )
    def_case = DefenseCase(
        case_id="CASE-REAL",
        defense_theory="Planting of recovery without independent witnesses.",
        alternative_interpretation="The accused had no conscious possession and the recovery was fabricated.",
        final_prayer="The defense prays for complete acquittal of the accused.",
    )
    conflicts = ConflictReport(
        case_id="CASE-REAL",
        total_conflicts=0,
        summary="No irreconcilable conflicts observed.",
    )

    judge_in = JudgeInput(
        case_analysis=dummy_case,
        prosecution=pros_case,
        defense=def_case,
        evidence_analysis=report,
        conflicts=conflicts,
        evidence_package=pkg,
    )
    assert judge_in.evidence_package == pkg

    judge = JudgeAgent()
    judgment = judge.adjudicate(
        case=judge_in.case_analysis,
        prosecution_case=judge_in.prosecution,
        defense_case=judge_in.defense,
        evidence_report=judge_in.evidence_analysis,
        conflict_report=judge_in.conflicts,
        evidence_package=judge_in.evidence_package,
    )
    assert "CASE-REAL" in judgment.judgment_id
    assert judgment.final_decision in ["CONVICTION", "ACQUITTAL", "PARTIAL CONVICTION"]
    assert judgment.reasons


# -----------------------------------------------------------------------------
# 22. No guilt/innocence decision is made by extraction
# -----------------------------------------------------------------------------
def test_22_no_guilt_innocence_decision_by_extraction(evidence_pdf_fixture: Path):
    loader = EvidencePDFLoader()
    pages = loader.load_pdf(evidence_pdf_fixture)
    pkg = EvidenceExtractor().extract(pages)

    # Check raw dumped dict to ensure no verdict determinations were added
    pkg_dump = pkg.model_dump()
    assert "verdict" not in pkg_dump
    assert "guilt_status" not in pkg_dump
    assert "final_decision" not in pkg_dump


# -----------------------------------------------------------------------------
# 23. Parser works with variable witness/exhibit counts
# -----------------------------------------------------------------------------
def test_23_variable_witness_and_exhibit_counts():
    extractor = EvidenceExtractor()

    # Case A: 2 witnesses, 1 exhibit
    text_a = """
    [Page 1]
    State v. John Doe
    FIR No. 10/2023
    WITNESSES:
    PW-1: Alice
    PW-2: Bob
    EXHIBITS:
    Ex.P1: Gold ring
    """
    pkg_a = extractor.extract([PDFPage(page_number=1, text=text_a, source_file="a.pdf")])
    assert len(pkg_a.prosecution_witnesses) == 2
    assert len(pkg_a.exhibits) == 1

    # Case B: 0 witnesses, 0 exhibits
    text_b = """
    [Page 1]
    State v. Unknown
    FIR No. 99/2024
    Inquiry on unclaimed property.
    """
    pkg_b = extractor.extract([PDFPage(page_number=1, text=text_b, source_file="b.pdf")])
    assert len(pkg_b.prosecution_witnesses) == 0
    assert len(pkg_b.exhibits) == 0


# -----------------------------------------------------------------------------
# 24. Empty sections are handled correctly
# -----------------------------------------------------------------------------
def test_24_empty_sections_handled_correctly():
    pkg = EvidencePackage()
    assert pkg.defence_witnesses == []
    assert pkg.exhibits == []
    assert pkg.recoveries == []
    assert pkg.contradictions == []
    assert pkg.missing_evidence == []


# -----------------------------------------------------------------------------
# 25. Malformed Evidence PDF produces structured error
# -----------------------------------------------------------------------------
def test_25_malformed_evidence_pdf_produces_structured_error(tmp_path: Path):
    loader = EvidencePDFLoader()

    # Empty text
    with pytest.raises(MalformedEvidencePDFError):
        loader.load_text("   ")

    # Non-existent file
    with pytest.raises(FileNotFoundError):
        loader.load_pdf(tmp_path / "non_existent.pdf")

    # Invalid non-pdf file
    txt_file = tmp_path / "case.txt"
    txt_file.write_text("Hello world")
    with pytest.raises(MalformedEvidencePDFError):
        loader.load_pdf(txt_file)


# -----------------------------------------------------------------------------
# REAL CASE VALIDATION: Pages 4–5 of Supplied Case Document
# -----------------------------------------------------------------------------
def test_real_case_validation_pw1_to_pw8_and_14_exhibits():
    """
    Validates that the parser extracts:
    - PW-1 through PW-8
    - Ex.PA, Ex.P1, Ex.P2, Ex.P3, Ex.PB, Ex.PB/1, Ex.PC, Ex.PC/1, Ex.PC/2,
      Ex.PD, Ex.PE, Ex.PG, Ex.PH, Ex.PK
    without any hardcoded case logic.
    """
    # Load from the real case text fixture
    loader = EvidencePDFLoader()
    pages = loader.load_text(REAL_CASE_EVIDENCE_TEXT, source_filename="Supplied_Case_Evidence.pdf")
    extractor = EvidenceExtractor()
    pkg = extractor.extract(pages, source_filename="Supplied_Case_Evidence.pdf")

    # 1. Verify all 8 witnesses in order
    assert len(pkg.prosecution_witnesses) == 8
    expected_witnesses = [
        ("PW-1", "Om Parkash"),
        ("PW-2", "HC Umed Singh"),
        ("PW-3", "HC Satyawan"),
        ("PW-4", "Fateh Singh"),
        ("PW-5", "Silak Ram"),
        ("PW-6", "Gurnam Singh"),
        ("PW-7", "Inspector Lachman Singh"),
        ("PW-8", "ASI Ishwar Singh"),
    ]
    for exp_id, exp_name in expected_witnesses:
        match = next((w for w in pkg.prosecution_witnesses if w.witness_id == exp_id), None)
        assert match is not None, f"Expected witness {exp_id} to be found"
        assert exp_name in match.name, f"Expected {exp_name} in {match.name}"

    # 2. Verify all 14 exhibits
    expected_exhibits = [
        "Ex.PA",
        "Ex.P1",
        "Ex.P2",
        "Ex.P3",
        "Ex.PB",
        "Ex.PB/1",
        "Ex.PC",
        "Ex.PC/1",
        "Ex.PC/2",
        "Ex.PD",
        "Ex.PE",
        "Ex.PG",
        "Ex.PH",
        "Ex.PK",
    ]
    extracted_exhibits = [e.exhibit_number for e in pkg.exhibits]
    for exp_ex in expected_exhibits:
        assert exp_ex in extracted_exhibits, f"Exhibit {exp_ex} missing from extracted exhibits: {extracted_exhibits}"

    # 3. Check page numbers for exhibits on page 4 and witnesses on page 5
    ex_pk = next(e for e in pkg.exhibits if e.exhibit_number == "Ex.PK")
    assert ex_pk.source_page == 4

    pw_8 = next(w for w in pkg.prosecution_witnesses if w.witness_id == "PW-8")
    assert pw_8.source_page == 5
