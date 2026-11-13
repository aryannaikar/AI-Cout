"""
Pytest configuration and synthetic fixtures for Phase 5 tests.
Provides realistic legal test fixtures for AI Judgment, Real Court Judgment,
and Case Packets across JSON, TXT, and PDF formats.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
import pymupdf

from app.models.judgment_models import Judgment, JudicialIssueAnalysis

REAL_COURT_JUDGMENT_TEXT = """
IN THE HIGH COURT OF DELHI AT NEW DELHI
Crl.A. No. 240/2003
State v. Jai Bhagwan
Date of Decision: 12.04.2005

The appellant Jai Bhagwan was prosecuted for offences punishable under Section 411 of the Indian Penal Code, 1860 and Section 25 of the Arms Act, 1959.
The prosecution case is that on 22.03.2001, the accused was apprehended at a police barricade while driving stolen scooter bearing registration No. DL-1S-4321 and was found in possession of an unlicensed country-made pistol.
The learned trial court framed charges under Section 411 IPC and Section 25 Arms Act.
The prosecution examined PW-1 Head Constable Ram Singh (recovery witness), PW-2 Sub-Inspector Dharam Pal (Investigating Officer), and PW-6 Gurnam Singh (owner of the stolen vehicle).
The prosecution relied on Exhibit P-1 (seizure memo of scooter), Exhibit P-2 (recovery memo of country-made pistol), and Exhibit P-3 (FSL ballistic report).
Points for determination:
1. Whether prosecution proved that the recovered vehicle was stolen property and in conscious possession of the accused under Section 411 IPC?
2. Whether the dock identification of the accused by PW-6 without a prior Test Identification Parade (TIP) is reliable in law?
3. Whether the seizure of the firearm under Section 25 Arms Act is proved beyond reasonable doubt in the absence of independent public witnesses?

Having appreciated the evidence on record, this Court finds:
First, no Test Identification Parade (TIP) was conducted. PW-6 saw the accused for the first time in the dock. Dock identification without prior TIP is inherently weak and cannot sustain conviction.
Second, despite the recovery occurring on a busy public highway, no independent public witnesses were joined in the search and seizure.
Third, the prosecution failed to prove the identity of the recovered vehicle by matching engine and chassis numbers with registration records.
Consequently, the prosecution has failed to establish guilt beyond reasonable doubt. The appellant is entitled to the benefit of doubt.

Operative Order:
The appeal is allowed. The conviction and sentence under Section 411 IPC and Section 25 Arms Act are set aside. The appellant is acquitted of all charges. Bail bonds stand discharged.
""".strip()

SYNTHETIC_AI_JUDGMENT_DATA = {
    "judgment_id": "JUDG-SYNTH-001",
    "case_title": "State v. Jai Bhagwan",
    "presiding_court": "Court of Sessions / AI Court of India",
    "date_of_decision": "2026-10-06",
    "case_background": "The prosecution alleges that the accused was found in possession of stolen property and an unlicensed firearm. The accused pleaded not guilty.",
    "issues_for_determination": [
        "Whether the recovered property constitutes stolen property under Section 317 BNS?",
        "Whether electronic call records are admissible without certificate under Section 63 BSA?",
    ],
    "applicable_law": [
        "Bharatiya Nyaya Sanhita, 2023, Section 317",
        "Bharatiya Sakshya Adhiniyam, 2023, Section 63",
    ],
    "evidence_assessment": "The prosecution produced Exhibit P-1 seizure memo and Exhibit P-9 electronic call detail records. Exhibit P-9 lacks Section 63 BSA certificate.",
    "witness_assessment": "The prosecution examined PW-1 and PW-2. Both were official police personnel.",
    "prosecution_submissions": "State submits that stolen property was recovered from accused.",
    "defense_submissions": "Defense contends that electronic evidence is inadmissible without certificate under Section 63 BSA.",
    "issue_analyses": [
        {
            "issue_number": 1,
            "issue_statement": "Whether the recovered property constitutes stolen property under Section 317 BNS?",
            "applicable_law": "Section 317 BNS",
            "prosecution_submission_summary": "State argues guilt proved.",
            "defense_submission_summary": "Defense argues reasonable doubt.",
            "evidentiary_evaluation": "Evaluating the evidence, chain of custody was not proved.",
            "judicial_finding": "NOT PROVED",
        },
        {
            "issue_number": 2,
            "issue_statement": "Whether electronic call records are admissible without certificate under Section 63 BSA?",
            "applicable_law": "Section 63 BSA",
            "prosecution_submission_summary": "State submitted CDR.",
            "defense_submission_summary": "Defense argued failure to comply with Section 63 BSA.",
            "evidentiary_evaluation": "Absence of mandatory certificate renders electronic evidence inadmissible.",
            "judicial_finding": "NOT PROVED",
        },
    ],
    "findings_per_charge": {
        "Section 317 BNS": "ACQUITTED (Benefit of Doubt)",
    },
    "final_decision": "ACQUITTAL",
    "reasons": "The core evidence relied upon by the prosecution was electronic call records. Because the prosecution failed to produce a certificate under Section 63 BSA, the electronic records are inadmissible. Consequently, the accused is entitled to acquittal on benefit of doubt.",
    "legal_citations": [
        "Bharatiya Nyaya Sanhita, 2023, Section 317",
        "Bharatiya Sakshya Adhiniyam, 2023, Section 63",
    ],
}


@pytest.fixture
def real_court_judgment_text() -> str:
    return REAL_COURT_JUDGMENT_TEXT


@pytest.fixture
def synthetic_ai_judgment() -> Judgment:
    return Judgment.model_validate(SYNTHETIC_AI_JUDGMENT_DATA)


@pytest.fixture
def synthetic_ai_judgment_json() -> str:
    return json.dumps(SYNTHETIC_AI_JUDGMENT_DATA, indent=2)


@pytest.fixture
def real_court_judgment_pdf(tmp_path: Path) -> Path:
    """Generate a realistic synthetic Real Court Judgment PDF."""
    pdf_path = tmp_path / "Real_Court_Judgment.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    y = 50
    for line in REAL_COURT_JUDGMENT_TEXT.split("\n"):
        page.insert_text(pymupdf.Point(50, y), line, fontsize=10, fontname="helv")
        y += 15
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def sample_case_packet_txt() -> str:
    return (
        "CASE PACKET: State v. Jai Bhagwan\n"
        "FIR No. 123/2001, Police Station Kashmere Gate.\n"
        "Allegations: Stolen two-wheeler scooter and recovery of illicit pistol on 22.03.2001.\n"
        "Charges framed: Section 411 IPC, Section 25 Arms Act.\n"
        "Witnesses: PW-1 HC Ram Singh, PW-2 SI Dharam Pal, PW-6 Gurnam Singh.\n"
        "Exhibits: Ex. P-1 seizure memo, Ex. P-2 recovery memo, Ex. P-3 ballistic report.\n"
    )
