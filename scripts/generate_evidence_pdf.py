"""
Generate a clean standardized Evidence PDF for the Jai Bhagwan case.

This script produces Jai_Bhagwan_Evidence_Packet.pdf in data/cases/case_packet/
containing ONLY evidentiary content — no security instructions, no AI blindness
sections, no ground truth metadata.

Sections:
  1. Case Identification
  2. Charges / Allegations
  3. Prosecution Witnesses (PW-1 through PW-8)
  4. Defence Witnesses (none adduced)
  5. Documentary Evidence / Exhibits (Ex.PA through Ex.PK — 14 exhibits)
  6. Physical / Material Evidence
  7. Recovery Evidence
  8. Identification Evidence
  9. Witness Testimony / Claims
 10. Statements / Disclosures
 11. Procedural / Investigation Evidence
 12. Evidence Linkages
 13. Contradictions / Inconsistencies
 14. Missing / Unproduced Evidence
 15. Source / Page Provenance

Run from project root:
    python scripts/generate_evidence_pdf.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is importable
_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

try:
    import pymupdf
except ImportError:
    print("ERROR: pymupdf is not installed. Run: pip install pymupdf")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Evidence page content — clean, no instructional/security text
# ---------------------------------------------------------------------------

PAGE_1 = """
IN THE HIGH COURT OF PUNJAB & HARYANA AT CHANDIGARH

CASE: CRA-S-174-SB-2005

CASE IDENTIFICATION
===================
Case Title : Jai Bhagwan & Ors.  versus  State of Haryana
Court      : In the High Court of Punjab & Haryana at Chandigarh
FIR No.    : 50 / 2002
FIR Date   : 01.07.2002
Police Station : Mohana
Relevant Dates : 01.07.2002, 16.05.2002
Parties    : Jai Bhagwan & Ors. (Appellants), State of Haryana (Respondent)
""".strip()

PAGE_2 = """
CHARGES / ALLEGATIONS
=====================
The FIR No.50 dated 01.07.2002 was lodged in Police Station Mohana for commission
of offences punishable under the following provisions:

  CH-01 : Section 412 of Indian Penal Code
  CH-02 : Section 420 of Indian Penal Code
  CH-03 : Section 468 of Indian Penal Code
  CH-04 : Section 471 of Indian Penal Code
  CH-05 : Section 25 of Arms Act

Allegation: The appellants were alleged to be in possession of a stolen vehicle
(Indica car) bearing a fake registration number, and in possession of a countrymade
pistol, in connection with a reported incident of dacoity.

The car was reported as robbed in connection with FIR No.149 dated 16.05.2002
registered at Police Station Sadar Rohtak.
""".strip()

PAGE_3 = """
PROSECUTION WITNESSES
=====================
Eight witnesses were examined by the prosecution:

  PW-1 : Om Parkash
  PW-2 : HC Umed Singh
  PW-3 : HC Satyawan
  PW-4 : Fateh Singh
  PW-5 : Silak Ram, Reader to District Magistrate Sonepat
  PW-6 : Gurnam Singh
  PW-7 : Inspector Lachman Singh
  PW-8 : ASI Ishwar Singh

DEFENCE WITNESSES
=================
Once the prosecution evidence was recorded, the learned trial Court completed
all the essential formalities enshrined under Section 313 CrPC.
Thereafter, opportunity of defence evidence was afforded to the appellants.
In their defence evidence, no evidence was adduced by the appellants.
No defence witness was examined.
""".strip()

PAGE_4 = """
DOCUMENTARY EVIDENCE / EXHIBITS
================================
The following documents and material objects were proved and marked as exhibits
by the prosecution during trial:

  Ex.PA    - Affidavit of Om Parkash
  Ex.P1    - Number plate (one of two)
  Ex.P2    - Number plate (second of two); Ex.P1 & Ex.P2 — Both the number plates
  Ex.P3    - Pistol, recovered from the appellant, namely Jai Bhagwan
  Ex.PB    - Seizure memo of Indica car and countrymade pistol
  Ex.PB/1  - Sketch of the pistol
  Ex.PC    - The information memo sent to the police station (ruqqa)
  Ex.PC/1  - Copy of First Information Report
  Ex.PC/2  - Endorsement recorded on the information memo
  Ex.PD    - Affidavit of HC Satyawan
  Ex.PE    - Statement of Fateh Singh
  Ex.PG    - Memo of Identification of the car by the PW-6 Gurnam Singh
  Ex.PH    - Release order of car in question
  Ex.PK    - Photocopy of FIR No.149 dated 16.05.2002, Police Station Sadar Rohtak

PHYSICAL / MATERIAL EVIDENCE
=============================
  PE-01  : Indica car bearing fake registration number plate DL3-CP-3753
           (actual registration number determined upon close scrutiny).
           Linked exhibits: Ex.PB, Ex.P1, Ex.P2.

  PE-02  : Countrymade pistol recovered from the appellant Jai Bhagwan.
           Linked exhibits: Ex.P3, Ex.PB/1.

RECOVERY EVIDENCE
=================
  REC-01 : Indica car and countrymade pistol seized pursuant to seizure memo Ex.PB.
           Prosecution claims items were recovered by the police team headed by
           SHO Police Station Mohana, namely SI Lachhman Singh.

IDENTIFICATION EVIDENCE
=======================
  ID-01  : Vehicle identification — Memo of Identification Ex.PG.
           PW-6 Gurnam Singh identified the Indica car.
           Type: vehicle identification.
""".strip()

PAGE_5 = """
WITNESS TESTIMONY / CLAIMS
===========================
  CLM-01 : PW-1 Om Parkash — Deposed on facts within witness knowledge.
           Claim type: observation.
  CLM-02 : PW-2 HC Umed Singh — Deposed as police witness on procedural facts.
           Claim type: procedural.
  CLM-03 : PW-3 HC Satyawan — Affidavit Ex.PD; deposed as police witness.
           Claim type: procedural.
  CLM-04 : PW-4 Fateh Singh — Statement Ex.PE; deposed on facts within knowledge.
           Claim type: observation.
  CLM-05 : PW-5 Silak Ram (Reader to District Magistrate Sonepat) — deposed
           on procedural/administrative matters.
           Claim type: procedural.
  CLM-06 : PW-6 Gurnam Singh — Identified the Indica car (Ex.PG).
           Claim type: identification.
  CLM-07 : PW-7 Inspector Lachman Singh — Led the team that intercepted the
           vehicle; prepared seizure memo and other procedural documents.
           Claim type: procedural.
  CLM-08 : PW-8 ASI Ishwar Singh — Deposed on investigative steps.
           Claim type: procedural.

STATEMENTS / DISCLOSURES
=========================
  STM-01 : Statement of Fateh Singh (Ex.PE) recorded during investigation.
           Type: statement under investigation.

PROCEDURAL / INVESTIGATION EVIDENCE
=====================================
  PROC-01 : FIR Registration — Registration of FIR No.50 dated 01.07.2002
             at Police Station Mohana.
  PROC-02 : Site Inspection — Investigating Officer inspected the spot and
             prepared rough site plan of the place of occurrence.
  PROC-03 : Seizure and Recovery Memo — Seizure memo prepared (Ex.PB).
  PROC-04 : Recording of Statements — Recorded the statement of witnesses
             under Section 161 CrPC.
  PROC-05 : Filing of Final Report — Final report under Section 173 of CrPC
             was filed.
  PROC-06 : Trial Examination of Prosecution Witnesses — As many as eight
             witnesses were examined by the prosecution.
  PROC-07 : Recording Statement of Accused under Section 313 CrPC — All
             essential formalities enshrined under Section 313 CrPC completed.

EVIDENCE LINKAGES
==================
  LNK-01 : PW-6 testified regarding exhibit Ex.PG (Identification memo of car).
  LNK-02 : REC-01 produced seizure exhibit Ex.PB.
  LNK-03 : PW-6 carried out identification under memo Ex.PG.
  LNK-04 : PW-3 testified via affidavit Ex.PD.
  LNK-05 : PW-4 statement recorded as Ex.PE.

CONTRADICTIONS / INCONSISTENCIES
==================================
  CONTR-01 : Vehicle registration number plate discrepancies.
             Statement A: Number plate bearing fake registration number DL3-CP-3753
             was affixed on the intercepted car (Source: FIR / interception memo).
             Statement B: Actual vehicle registration number was different and was
             uncovered upon close scrutiny of engine/chassis numbers
             (Source: Seizure memo Ex.PB and number plates Ex.P1 & Ex.P2).
             Type: documentary.
             Description: Discrepancy between the apparent fake registration plate
             and the actual identity of the vehicle.

MISSING / UNPRODUCED EVIDENCE
===============================
  MISS-01 : No defence evidence or defence witnesses were adduced by the accused.
             Expected source: Defence. Explicitly stated in record. (Page 5)

  MISS-02 : Absence of independent civilian panch witnesses at the time of
             search and seizure of the Indica car and pistol.
             Expected source: Investigating Agency. Explicitly noted in case record.

SOURCE / PAGE PROVENANCE
========================
  Ex.PA  (Ex.PA / Affidavit of Om Parkash)          — Source page: 4
  Ex.PG  (Ex.PG / Identification memo of car)        — Source page: 4
  Ex.PH  (Ex.PH / Release order of car in question) — Source page: 4
  Ex.PK  (Ex.PK / Copy of FIR No.149)               — Source page: 4
  PW-1 through PW-8 depositions                      — Source page: 5
""".strip()


def generate_pdf(output_path: Path) -> None:
    """Write the five-page clean Evidence PDF to output_path."""
    pages_content = [PAGE_1, PAGE_2, PAGE_3, PAGE_4, PAGE_5]

    doc = pymupdf.open()
    for page_text in pages_content:
        page = doc.new_page(width=595, height=842)
        y = 40
        for line in page_text.split("\n"):
            page.insert_text(
                pymupdf.Point(40, y),
                line,
                fontsize=9,
                fontname="helv",
            )
            y += 13
            if y > 820:
                break  # safety — don't overflow page

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    doc.close()
    print(f"[OK] Evidence PDF written to: {output_path}")
    print(f"     Pages: {len(pages_content)}")


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    out = project_root / "data" / "cases" / "case_packet" / "Jai_Bhagwan_Evidence_Packet.pdf"
    generate_pdf(out)
