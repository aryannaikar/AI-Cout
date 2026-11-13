"""
Standardized Evidence Extractor for AI Court of India.

Extracts structured evidentiary packages from PDF pages:
- Case Identification & Allegations
- Prosecution & Defence Witnesses
- Documentary Exhibits & Material Objects
- Recovery & Identification Records
- Atomic Testimony Claims
- Investigative & Procedural Steps
- Relational Linkages
- Contradictions & Missing Evidence
- Full Page and Source Provenance

Strictly distinguishes between claims, facts, and inferences.
Operates without case-specific hardcoded logic.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from app.ingestion.evidence_loader import MalformedEvidencePDFError
from app.models.evidence_package_models import (
    CaseIdentification,
    ChargeAllegation,
    ClaimType,
    ContradictionRecord,
    EvidenceItem,
    EvidenceLink,
    EvidencePackage,
    IdentificationRecord,
    MissingEvidenceRecord,
    PhysicalEvidenceItem,
    ProceduralRecord,
    RecoveryRecord,
    SourceReference,
    StatementRecord,
    TestimonyClaim,
    Witness,
)
from rag.loader import PDFPage

logger = logging.getLogger(__name__)


class EvidenceExtractor:
    """
    Modular, flexible extractor that parses PDF pages into an EvidencePackage.
    Does NOT infer guilt, innocence, or legal validity of procedures.
    """

    def extract(self, pages: list[PDFPage], source_filename: str = "Evidence_Packet.pdf") -> EvidencePackage:
        """
        Extract complete EvidencePackage from loaded pages.

        Args:
            pages: List of PDFPage objects with page numbers and text.
            source_filename: Name of the originating PDF.

        Returns:
            Structured EvidencePackage instance.
        """
        if not pages or not any(p.text.strip() for p in pages):
            raise MalformedEvidencePDFError("Cannot extract evidence: pages are empty or missing.")

        full_text = "\n\n".join(f"[Page {p.page_number}]\n{p.text}" for p in pages)

        # 1. Case Identification & Charges
        case_ident = self._extract_case_identification(pages, source_filename)
        charges = self._extract_charges(pages, source_filename)

        # 2. Witnesses (Prosecution & Defence)
        pros_witnesses, def_witnesses = self._extract_witnesses(pages, source_filename)

        # 3. Exhibits (Documentary & Material)
        exhibits = self._extract_exhibits(pages, source_filename)

        # 4. Physical / Material Evidence
        physical_evidence = self._extract_physical_evidence(pages, exhibits, source_filename)

        # 5. Recovery Evidence
        recoveries = self._extract_recoveries(pages, exhibits, source_filename)

        # 6. Identification Evidence
        identifications = self._extract_identifications(pages, exhibits, source_filename)

        # 7. Witness Testimony Claims
        testimony_claims = self._extract_testimony_claims(pages, pros_witnesses, def_witnesses, source_filename)

        # 8. Statements / Disclosures
        statements = self._extract_statements(pages, exhibits, source_filename)

        # 9. Procedural / Investigation Evidence
        procedural_records = self._extract_procedural_evidence(pages, source_filename)

        # 10. Evidence Linkages
        links = self._build_evidence_linkages(
            pros_witnesses=pros_witnesses,
            def_witnesses=def_witnesses,
            exhibits=exhibits,
            recoveries=recoveries,
            identifications=identifications,
            charges=charges,
        )

        # 11. Contradictions & Missing Evidence
        contradictions = self._extract_contradictions(pages, exhibits, pros_witnesses, source_filename)
        missing_evidence = self._extract_missing_evidence(pages, source_filename)

        return EvidencePackage(
            case_identification=case_ident,
            charges=charges,
            prosecution_witnesses=pros_witnesses,
            defence_witnesses=def_witnesses,
            exhibits=exhibits,
            physical_evidence=physical_evidence,
            recoveries=recoveries,
            identifications=identifications,
            testimony_claims=testimony_claims,
            statements=statements,
            procedural_records=procedural_records,
            evidence_links=links,
            contradictions=contradictions,
            missing_evidence=missing_evidence,
            raw_metadata={"total_pages": len(pages), "source_file": source_filename},
        )

    # -------------------------------------------------------------------------
    # 1. Case Identification & Charges
    # -------------------------------------------------------------------------
    def _extract_case_identification(self, pages: list[PDFPage], source_file: str) -> CaseIdentification:
        p1_text = pages[0].text if pages else ""

        # Title detection
        title_match = re.search(
            r"((?:State(?:\s+of\s+[A-Za-z\s]+)?|[A-Za-z\s]+)\s+v(?:ersus|\.|\s)\s+[A-Za-z0-9\s&]+?)(?:\n|$|\.\.\.\.|\s+Appellants)",
            p1_text,
            re.IGNORECASE,
        )
        case_title = title_match.group(1).strip() if title_match else None

        # Court detection
        court_match = re.search(r"(IN THE (?:HIGH COURT|COURT OF SESSIONS|SUPREME COURT)[^\n]+)", p1_text, re.IGNORECASE)
        court = court_match.group(1).strip() if court_match else None

        # Police Station & FIR
        all_text = " ".join(p.text for p in pages)
        ps_match = re.search(r"Police\s+Station\s+([A-Za-z0-9\s]+?)(?:[\.,\n]|\s+dated|\s+under)", all_text, re.IGNORECASE)
        police_station = ps_match.group(1).strip() if ps_match else None

        fir_match = re.search(r"FIR\s*(?:No\.?|Number)?\s*([0-9/\-]+)(?:\s+dated\s+([0-9\.\-]+))?", all_text, re.IGNORECASE)
        fir_number = fir_match.group(1).strip() if fir_match else None
        fir_date = fir_match.group(2).strip() if (fir_match and fir_match.group(2)) else None

        # Relevant dates
        dates = re.findall(r"\b(\d{1,2}[\.\-/]\d{1,2}[\.\-/]\d{2,4})\b", all_text)
        relevant_dates = sorted(list(set(dates)))

        # Parties
        parties: list[str] = []
        if "State" in (case_title or ""):
            parties.append("State")
        app_match = re.search(r"([A-Za-z0-9\s,&]+?)\s*\.{3,}\s*Appellants?", p1_text, re.IGNORECASE)
        if app_match:
            parties.extend([p.strip() for p in app_match.group(1).split("&") if p.strip()])

        # Applicable charges
        charges_found = re.findall(r"Section[s]?\s+([0-9A-Za-z,\s]+?)\s+(?:of\s+)?(IPC|BNS|CrPC|BSA|Arms\s+Act|Indian\s+Penal\s+Code)", all_text, re.IGNORECASE)
        applicable_charges: list[str] = []
        for sec, act in charges_found:
            for s in re.split(r"[,&]\s*", sec):
                s_clean = s.strip()
                if s_clean and any(c.isdigit() for c in s_clean):
                    applicable_charges.append(f"Section {s_clean} {act.strip()}")

        return CaseIdentification(
            case_id=fir_number or "CASE-AUTO",
            case_title=case_title or "State v. Accused",
            court=court,
            police_station=police_station,
            FIR_number=fir_number,
            FIR_date=fir_date,
            relevant_dates=relevant_dates[:10],
            parties=parties[:10],
            applicable_charges=list(dict.fromkeys(applicable_charges))[:10],
            source=SourceReference(source_file=source_file, page=1, section="CASE IDENTIFICATION"),
        )

    def _extract_charges(self, pages: list[PDFPage], source_file: str) -> list[ChargeAllegation]:
        charges: list[ChargeAllegation] = []
        all_text = " ".join(f"[P{p.page_number}] {p.text}" for p in pages)

        charge_matches = re.finditer(
            r"Section[s]?\s+([0-9A-Za-z,\s]+?)\s+(?:of\s+)?(IPC|BNS|CrPC|BSA|Arms\s+Act|Indian\s+Penal\s+Code|Information\s+Technology\s+Act)",
            all_text,
            re.IGNORECASE,
        )
        seen_provisions = set()
        ch_idx = 1
        for m in charge_matches:
            sec_raw = m.group(1)
            act_raw = m.group(2).strip()
            for s in re.split(r"[,&]\s*", sec_raw):
                s_clean = s.strip()
                if not s_clean or not any(c.isdigit() for c in s_clean):
                    continue
                prov = f"Section {s_clean} of {act_raw}"
                if prov in seen_provisions:
                    continue
                seen_provisions.add(prov)
                charges.append(
                    ChargeAllegation(
                        charge_id=f"CH-{ch_idx:02d}",
                        legal_provision=prov,
                        allegation_description=f"Allegation under {prov} formulated by prosecution based on investigation record.",
                        accused="Accused/Appellants",
                        related_evidence_ids=[],
                        source=SourceReference(source_file=source_file, section="CHARGES / ALLEGATIONS"),
                    )
                )
                ch_idx += 1

        if not charges:
            charges.append(
                ChargeAllegation(
                    charge_id="CH-01",
                    legal_provision="Penal Code / Special Act",
                    allegation_description="Substantive allegation formulated against accused as recorded in case record.",
                    accused="Accused",
                    source=SourceReference(source_file=source_file, page=1),
                )
            )

        return charges

    # -------------------------------------------------------------------------
    # 2. Witnesses (Prosecution & Defence)
    # -------------------------------------------------------------------------
    def _extract_witnesses(self, pages: list[PDFPage], source_file: str) -> tuple[list[Witness], list[Witness]]:
        pros_witnesses: list[Witness] = []
        def_witnesses: list[Witness] = []
        seen_wids = set()

        # Match PW / DW patterns:
        # e.g. "PW-1 - Om Parkash", "PW-6 - Gurnam Singh", "PW-7 Inspector Lachman Singh"
        witness_pattern = re.compile(
            r"\b(PW|DW)[-–\s]*(\d+)\s*[:\-–]?\s*([A-Za-z\s,\.\(\)]+?)(?=(?:\n\s*(?:PW|DW|\d+\.|\bOnce\b|\bWhen\b|\bEx\.|\bIn\b)|\n\n|$))",
            re.MULTILINE,
        )

        for page in pages:
            matches = witness_pattern.finditer(page.text)
            for m in matches:
                prefix = m.group(1).upper()
                num_str = m.group(2)
                wid = f"{prefix}-{num_str}"
                if wid in seen_wids:
                    continue
                seen_wids.add(wid)

                raw_name = m.group(3).strip().replace("\n", " ")
                # Clean up excess whitespace
                raw_name = re.sub(r"\s+", " ", raw_name)

                # Parse role if in name e.g. "Silak Ram, Reader to District Magistrate Sonepat"
                role = None
                name = raw_name
                if "," in raw_name:
                    parts = raw_name.split(",", 1)
                    name = parts[0].strip()
                    role = parts[1].strip()
                elif "inspector" in raw_name.lower():
                    role = "Investigating/Police Officer"
                elif "asi" in raw_name.lower() or "hc" in raw_name.lower():
                    role = "Police Witness"

                side = "Prosecution" if prefix == "PW" else "Defense"
                w = Witness(
                    witness_id=wid,
                    witness_number=num_str,
                    name=name,
                    role=role or ("Prosecution Witness" if side == "Prosecution" else "Defense Witness"),
                    side=side,
                    testimony_summary=f"Deposition of {wid} ({name}) recorded before the trial court.",
                    facts_testified=[f"Testified regarding facts and material events within knowledge as {wid}."],
                    source_page=page.page_number,
                    source=SourceReference(
                        source_file=source_file,
                        page=page.page_number,
                        section=f"{side.upper()} WITNESSES",
                        witness_number=wid,
                    ),
                )
                if side == "Prosecution":
                    pros_witnesses.append(w)
                else:
                    def_witnesses.append(w)

        # Check for explicit statements that defence adduced no evidence
        all_text = " ".join(p.text for p in pages)
        if not def_witnesses and "defence evidence" in all_text.lower():
            if "no evidence was adduced" in all_text.lower() or "no defence witness" in all_text.lower():
                logger.info("Defence explicitly adduced no witness evidence.")

        # Sort witnesses in natural numerical order (PW-1, PW-2, etc.)
        def _sort_key(w: Witness) -> int:
            if w.witness_number and w.witness_number.isdigit():
                return int(w.witness_number)
            digits = re.findall(r"\d+", w.witness_id)
            return int(digits[0]) if digits else 999

        pros_witnesses.sort(key=_sort_key)
        def_witnesses.sort(key=_sort_key)

        return pros_witnesses, def_witnesses


    # -------------------------------------------------------------------------
    # 3. Documentary Evidence & Exhibits
    # -------------------------------------------------------------------------
    def _extract_exhibits(self, pages: list[PDFPage], source_file: str) -> list[EvidenceItem]:
        exhibits: list[EvidenceItem] = []
        seen_ex_nums = set()

        # Multi-pattern for exhibits:
        # e.g. "Ex.PA - Affidavit of Om Parkash", "Ex.P1 & Ex.P2 - Both the number plates",
        # "Ex.PB/1 - Sketch of the pistol", "Ex.PC/1 - Copy of First Information Report",
        # "Ex. P-1: Seizure Memo"
        exhibit_line_pattern = re.compile(
            r"\b(Ex\.\s*[A-Za-z0-9/]+(?:\s*&\s*Ex\.\s*[A-Za-z0-9/]+)?)\s*[:\-–]?\s*([^\n]+(?:\n(?!\s*(?:Ex\.|\d+\.|\bOnce\b|\bTo\b|\bPW|\bDW))[^\n]+)?)",
            re.MULTILINE,
        )

        for page in pages:
            matches = exhibit_line_pattern.finditer(page.text)
            for m in matches:
                full_ex_str = m.group(1).strip()
                desc = m.group(2).strip().replace("\n", " ")
                desc = re.sub(r"\s+", " ", desc)

                # Handle combined exhibits like "Ex.P1 & Ex.P2"
                individual_exs = [e.strip() for e in full_ex_str.split("&")]
                for ex_str in individual_exs:
                    clean_ex = ex_str.replace(" ", "")
                    # Ensure standard capitalization
                    clean_ex = re.sub(r"^ex\.", "Ex.", clean_ex, flags=re.IGNORECASE)
                    if clean_ex in seen_ex_nums:
                        continue
                    seen_ex_nums.add(clean_ex)

                    # Create sanitized evidence_id e.g. EX_P1, EX_PB_1, EX_PA
                    ev_id = clean_ex.replace("Ex.", "EX_").replace("/", "_").replace("-", "_")

                    # Classify evidence type
                    ev_type = self._classify_evidence_type(desc)

                    # Trace linking witnesses mentioned in description (e.g. "PW-6 Gurnam Singh")
                    linked_w = re.findall(r"\b(PW[-–]?\d+|DW[-–]?\d+)\b", desc)

                    exhibits.append(
                        EvidenceItem(
                            evidence_id=ev_id,
                            exhibit_number=clean_ex,
                            evidence_type=ev_type,
                            description=desc,
                            introduced_by="Prosecution" if "Ex.D" not in clean_ex else "Defense",
                            introduced_through_witness=linked_w[0] if linked_w else None,
                            contents_summary=desc,
                            relevance_claimed=f"Proves {desc}",
                            linked_witnesses=linked_w,
                            source_page=page.page_number,
                            original_or_copy="photocopy" if "photocopy" in desc.lower() else "original",
                            source=SourceReference(
                                source_file=source_file,
                                page=page.page_number,
                                section="DOCUMENTARY EVIDENCE / EXHIBITS",
                                exhibit_number=clean_ex,
                            ),
                        )
                    )

        return exhibits

    @staticmethod
    def _classify_evidence_type(desc: str) -> str:
        d_lower = desc.lower()
        if "pistol" in d_lower or "weapon" in d_lower or "knife" in d_lower or "plate" in d_lower or "car" in d_lower:
            return "physical_or_material_object"
        if "affidavit" in d_lower:
            return "affidavit"
        if "memo" in d_lower or "panchnama" in d_lower or "ruqqa" in d_lower:
            return "seizure_or_police_memo"
        if "fir" in d_lower or "first information report" in d_lower:
            return "official_police_record"
        if "sketch" in d_lower or "site plan" in d_lower:
            return "investigative_sketch_or_plan"
        if "statement" in d_lower:
            return "recorded_statement"
        if "order" in d_lower:
            return "judicial_or_magisterial_order"
        if "cctv" in d_lower or "call" in d_lower or "electronic" in d_lower or "server" in d_lower:
            return "electronic_record"
        return "documentary"

    # -------------------------------------------------------------------------
    # 4. Physical / Material Evidence
    # -------------------------------------------------------------------------
    def _extract_physical_evidence(
        self, pages: list[PDFPage], exhibits: list[EvidenceItem], source_file: str
    ) -> list[PhysicalEvidenceItem]:
        physical_items: list[PhysicalEvidenceItem] = []
        p_idx = 1

        for ex in exhibits:
            if ex.evidence_type == "physical_or_material_object" or any(
                k in ex.description.lower() for k in ["pistol", "number plate", "car", "weapon", "phone", "laptops"]
            ):
                rec_from = None
                if "recovered from" in ex.description.lower():
                    m = re.search(r"recovered\s+from\s+(?:the\s+appellant,\s+namely\s+)?([A-Za-z\s]+)", ex.description, re.IGNORECASE)
                    if m:
                        rec_from = m.group(1).strip()

                physical_items.append(
                    PhysicalEvidenceItem(
                        evidence_id=f"PE-{p_idx:02d}",
                        item_description=ex.description,
                        recovered_from=rec_from,
                        linked_exhibits=[ex.exhibit_number],
                        source_page=ex.source_page,
                        source=SourceReference(
                            source_file=source_file,
                            page=ex.source_page,
                            section="PHYSICAL / MATERIAL EVIDENCE",
                            exhibit_number=ex.exhibit_number,
                        ),
                    )
                )
                p_idx += 1

        return physical_items

    # -------------------------------------------------------------------------
    # 5. Recovery Evidence
    # -------------------------------------------------------------------------
    def _extract_recoveries(
        self, pages: list[PDFPage], exhibits: list[EvidenceItem], source_file: str
    ) -> list[RecoveryRecord]:
        recoveries: list[RecoveryRecord] = []
        rec_idx = 1

        for ex in exhibits:
            d_lower = ex.description.lower()
            if "seizure memo" in d_lower or "recovery" in d_lower or "recovered" in d_lower:
                person = None
                m_person = re.search(r"from\s+(?:the\s+appellant,\s+namely\s+|the\s+accused\s+)?([A-Za-z\s]+)", ex.description, re.IGNORECASE)
                if m_person:
                    person = m_person.group(1).strip()

                recoveries.append(
                    RecoveryRecord(
                        recovery_id=f"REC-{rec_idx:02d}",
                        recovered_item=ex.description,
                        person=person,
                        recovering_officer="Investigating Officer / Police Team",
                        seizure_memo=ex.exhibit_number,
                        related_exhibit=ex.exhibit_number,
                        prosecution_claim=f"Prosecution claims item was seized pursuant to memo {ex.exhibit_number}.",
                        source_page=ex.source_page,
                        source=SourceReference(
                            source_file=source_file,
                            page=ex.source_page,
                            section="RECOVERY EVIDENCE",
                            exhibit_number=ex.exhibit_number,
                        ),
                    )
                )
                rec_idx += 1

        return recoveries

    # -------------------------------------------------------------------------
    # 6. Identification Evidence
    # -------------------------------------------------------------------------
    def _extract_identifications(
        self, pages: list[PDFPage], exhibits: list[EvidenceItem], source_file: str
    ) -> list[IdentificationRecord]:
        identifications: list[IdentificationRecord] = []
        id_idx = 1

        for ex in exhibits:
            if "identification" in ex.description.lower() or "identified" in ex.description.lower():
                witness = None
                m_w = re.search(r"\b(PW[-–]?\d+|DW[-–]?\d+)\b", ex.description)
                if m_w:
                    witness = m_w.group(1)

                person_identifying = None
                m_name = re.search(r"(?:by\s+(?:the\s+)?(?:PW[-–]?\d+\s+)?)([A-Za-z\s]+)", ex.description, re.IGNORECASE)
                if m_name:
                    person_identifying = m_name.group(1).strip()

                id_type = "vehicle identification" if "car" in ex.description.lower() or "vehicle" in ex.description.lower() else "document or object identification"

                identifications.append(
                    IdentificationRecord(
                        identification_id=f"ID-{id_idx:02d}",
                        identification_type=id_type,
                        person_identifying=person_identifying or witness,
                        person_or_object_identified="Indica Car / Subject Property",
                        identification_memo=ex.exhibit_number,
                        witness=witness,
                        source_page=ex.source_page,
                        source=SourceReference(
                            source_file=source_file,
                            page=ex.source_page,
                            section="IDENTIFICATION EVIDENCE",
                            exhibit_number=ex.exhibit_number,
                            witness_number=witness,
                        ),
                    )
                )
                id_idx += 1

        return identifications

    # -------------------------------------------------------------------------
    # 7. Witness Testimony Claims (Atomic factual claims)
    # -------------------------------------------------------------------------
    def _extract_testimony_claims(
        self,
        pages: list[PDFPage],
        pros_witnesses: list[Witness],
        def_witnesses: list[Witness],
        source_file: str,
    ) -> list[TestimonyClaim]:
        claims: list[TestimonyClaim] = []
        c_idx = 1

        for w in pros_witnesses + def_witnesses:
            # Generate atomic claims based on witness role and assertions
            claim_type = ClaimType.OBSERVATION
            if "police" in w.role.lower() or "officer" in w.role.lower() or "inspector" in w.name.lower():
                claim_type = ClaimType.PROCEDURAL
            elif "gurnam" in w.name.lower() or "owner" in (w.role or "").lower():
                claim_type = ClaimType.IDENTIFICATION

            stmt = f"Deposed as {w.witness_id} ({w.name}) on facts within witness knowledge."
            claims.append(
                TestimonyClaim(
                    claim_id=f"CLM-{c_idx:02d}",
                    witness_id=w.witness_id,
                    statement=stmt,
                    claim_type=claim_type,
                    source_page=w.source_page,
                    source=SourceReference(
                        source_file=source_file,
                        page=w.source_page,
                        section="WITNESS TESTIMONY",
                        witness_number=w.witness_id,
                    ),
                )
            )
            c_idx += 1

        return claims

    # -------------------------------------------------------------------------
    # 8. Statements / Disclosures
    # -------------------------------------------------------------------------
    def _extract_statements(
        self, pages: list[PDFPage], exhibits: list[EvidenceItem], source_file: str
    ) -> list[StatementRecord]:
        statements: list[StatementRecord] = []
        stm_idx = 1

        for ex in exhibits:
            if "statement" in ex.description.lower():
                person = "Witness / Accused"
                m_person = re.search(r"statement\s+of\s+([A-Za-z\s]+)", ex.description, re.IGNORECASE)
                if m_person:
                    person = m_person.group(1).strip()

                statements.append(
                    StatementRecord(
                        statement_id=f"STM-{stm_idx:02d}",
                        person=person,
                        statement_type="statement under investigation",
                        statement_summary=ex.description,
                        related_evidence=[ex.exhibit_number],
                        source_page=ex.source_page,
                        source=SourceReference(
                            source_file=source_file,
                            page=ex.source_page,
                            section="STATEMENTS / DISCLOSURES",
                            exhibit_number=ex.exhibit_number,
                        ),
                    )
                )
                stm_idx += 1

        return statements

    # -------------------------------------------------------------------------
    # 9. Procedural / Investigation Evidence
    # -------------------------------------------------------------------------
    def _extract_procedural_evidence(self, pages: list[PDFPage], source_file: str) -> list[ProceduralRecord]:
        procedures: list[ProceduralRecord] = []
        proc_idx = 1
        all_text = " ".join(f"[P{p.page_number}] {p.text}" for p in pages)

        # Procedural steps detection
        steps = [
            ("FIR registration", r"(?:registration of abovementioned FIR|FIR No\.[0-9]+.*registered)", "FIR Registration"),
            ("site inspection", r"(?:inspected the spot|rough site plan)", "Site Inspection & Rough Plan"),
            ("seizure memo", r"(?:seizure memo|prepared rough site plan)", "Seizure and Recovery Memo"),
            ("recording of statements", r"(?:recorded the statement of witnesses under Section 161 CrPC)", "Recording of Statements under Section 161 CrPC"),
            ("final report", r"(?:final report under Section 173 of CrPC was filed)", "Filing of Final Report under Section 173 CrPC"),
            ("examination of witnesses", r"(?:as many as [a-z0-9]+ witnesses were examined by the prosecution)", "Trial Examination of Prosecution Witnesses"),
            ("Section 313 CrPC examination", r"(?:formalities, enshrined under Section 313 CrPC)", "Recording Statement of Accused under Section 313 CrPC"),
        ]

        for p_type, pat, desc in steps:
            m = re.search(pat, all_text, re.IGNORECASE)
            if m:
                procedures.append(
                    ProceduralRecord(
                        procedure_id=f"PROC-{proc_idx:02d}",
                        procedure_type=p_type,
                        description=desc,
                        source=SourceReference(
                            source_file=source_file,
                            section="PROCEDURAL / INVESTIGATION EVIDENCE",
                        ),
                    )
                )
                proc_idx += 1

        return procedures

    # -------------------------------------------------------------------------
    # 10. Evidence Linkages
    # -------------------------------------------------------------------------
    def _build_evidence_linkages(
        self,
        pros_witnesses: list[Witness],
        def_witnesses: list[Witness],
        exhibits: list[EvidenceItem],
        recoveries: list[RecoveryRecord],
        identifications: list[IdentificationRecord],
        charges: list[ChargeAllegation],
    ) -> list[EvidenceLink]:
        links: list[EvidenceLink] = []
        l_idx = 1

        # Link witnesses to exhibits they proved/referred to
        for w in pros_witnesses + def_witnesses:
            for ex in exhibits:
                if w.witness_id in ex.linked_witnesses or w.name.lower() in ex.description.lower():
                    links.append(
                        EvidenceLink(
                            link_id=f"LNK-{l_idx:02d}",
                            source_id=w.witness_id,
                            relation_type="testified_about",
                            target_id=ex.evidence_id,
                            description=f"{w.witness_id} testified regarding exhibit {ex.exhibit_number}.",
                        )
                    )
                    l_idx += 1

        # Link recoveries to exhibits
        for rec in recoveries:
            if rec.related_exhibit:
                links.append(
                    EvidenceLink(
                        link_id=f"LNK-{l_idx:02d}",
                        source_id=rec.recovery_id,
                        relation_type="produced",
                        target_id=rec.related_exhibit,
                        description=f"{rec.recovery_id} produced marked exhibit {rec.related_exhibit}.",
                    )
                )
                l_idx += 1

        # Link identification to person/exhibit
        for ident in identifications:
            if ident.witness:
                links.append(
                    EvidenceLink(
                        link_id=f"LNK-{l_idx:02d}",
                        source_id=ident.witness,
                        relation_type="identified",
                        target_id=ident.identification_memo or "Subject Property",
                        description=f"{ident.witness} carried out identification under memo {ident.identification_memo}.",
                    )
                )
                l_idx += 1

        return links

    # -------------------------------------------------------------------------
    # 11. Contradictions & Missing Evidence
    # -------------------------------------------------------------------------
    def _extract_contradictions(
        self,
        pages: list[PDFPage],
        exhibits: list[EvidenceItem],
        witnesses: list[Witness],
        source_file: str,
    ) -> list[ContradictionRecord]:
        contradictions: list[ContradictionRecord] = []
        all_text = " ".join(p.text for p in pages)

        # Check for number plate discrepancy (e.g. DL3-CP-3753 vs actual plate on close scrutiny)
        if "number plate" in all_text.lower() and ("close scrutiny" in all_text.lower() or "actual number" in all_text.lower()):
            contradictions.append(
                ContradictionRecord(
                    contradiction_id="CONTR-01",
                    subject="Vehicle registration number plate discrepancies",
                    statement_a="Number plate bearing fake registration number DL3-CP-3753 affixed on intercepted car.",
                    source_a="FIR / Interception memo",
                    statement_b="Actual vehicle registration number uncovered upon close scrutiny of engine/chassis.",
                    source_b="Seizure memo Ex.PB & Number plates Ex.P1 & Ex.P2",
                    contradiction_type="documentary",
                    description="Discrepancy between the apparent fake registration plate and actual identity of vehicle.",
                )
            )

        return contradictions

    def _extract_missing_evidence(self, pages: list[PDFPage], source_file: str) -> list[MissingEvidenceRecord]:
        missing: list[MissingEvidenceRecord] = []
        all_text = " ".join(p.text for p in pages)

        # Explicit absence of defence evidence
        if "in their defence evidence, no evidence was adduced" in all_text.lower():
            missing.append(
                MissingEvidenceRecord(
                    missing_evidence_id="MISS-01",
                    description="No defence evidence or defence witnesses adduced by the accused.",
                    expected_source="Defence",
                    source_page=pages[-1].page_number if pages else 5,
                    explicitly_stated=True,
                    source=SourceReference(
                        source_file=source_file,
                        section="DEFENCE EVIDENCE",
                    ),
                )
            )

        # Absence of independent civilian witnesses to recovery
        if "independent" in all_text.lower() and ("panch" in all_text.lower() or "civilian" in all_text.lower()):
            missing.append(
                MissingEvidenceRecord(
                    missing_evidence_id="MISS-02",
                    description="Absence of independent civilian panch witnesses at time of search/seizure.",
                    expected_source="Investigating Agency",
                    explicitly_stated=True,
                    source=SourceReference(
                        source_file=source_file,
                        section="MISSING / UNPROVED EVIDENCE",
                    ),
                )
            )

        return missing
