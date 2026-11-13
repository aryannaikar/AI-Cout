"""
Standardized Evidence Representation and Schema Models for AI Court of India.

Defines strongly-typed Pydantic models for structured evidentiary packets:
- Case Identification
- Charges / Allegations
- Prosecution & Defence Witnesses
- Documentary Evidence & Exhibits
- Physical / Material Evidence
- Recovery Evidence
- Identification Evidence
- Witness Testimony (Atomic factual claims)
- Statements & Disclosures
- Procedural & Investigation Records
- Evidence Linkages
- Contradictions & Inconsistencies
- Missing / Unproved Evidence
- Source & Page Provenance

Strictly distinguishes between facts, claims, and inferences.
Never decides guilt or innocence.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ClaimType(str, Enum):
    """Allowed categorical types for atomic testimony claims."""

    FACT = "FACT"
    OBSERVATION = "OBSERVATION"
    IDENTIFICATION = "IDENTIFICATION"
    RECOVERY = "RECOVERY"
    PROCEDURAL = "PROCEDURAL"
    DOCUMENT_REFERENCE = "DOCUMENT_REFERENCE"
    HEARSAY_IF_EXPLICITLY_STATED = "HEARSAY_IF_EXPLICITLY_STATED"
    ADMISSION = "ADMISSION"
    DENIAL = "DENIAL"
    OTHER = "OTHER"


class SourceReference(BaseModel):
    """Provenance tracking an evidentiary item back to its origin in the Evidence PDF."""

    model_config = ConfigDict(extra="ignore")

    source_file: str = Field(default="Evidence_Packet.pdf", description="Filename or URI of source document.")
    page: Optional[int] = Field(default=None, description="1-indexed page number in the source PDF.")
    section: Optional[str] = Field(default=None, description="Section heading or conceptual section.")
    exhibit_number: Optional[str] = Field(default=None, description="Exhibit identifier where applicable.")
    witness_number: Optional[str] = Field(default=None, description="Witness identifier where applicable.")


class CaseIdentification(BaseModel):
    """Case identification data. Missing fields are represented as None/empty, never invented."""

    model_config = ConfigDict(extra="ignore")

    case_id: Optional[str] = Field(default=None, description="Case identifier if stated.")
    case_title: Optional[str] = Field(default=None, description="Case title or cause title.")
    court: Optional[str] = Field(default=None, description="Court or forum.")
    police_station: Optional[str] = Field(default=None, description="Police station having jurisdiction.")
    FIR_number: Optional[str] = Field(default=None, description="FIR or Crime number.")
    FIR_date: Optional[str] = Field(default=None, description="Date of FIR registration.")
    relevant_dates: list[str] = Field(default_factory=list, description="Material incident, arrest, or charge-sheet dates.")
    parties: list[str] = Field(default_factory=list, description="Parties to the proceeding.")
    applicable_charges: list[str] = Field(default_factory=list, description="Penal provisions framed or alleged.")
    source: Optional[SourceReference] = Field(default=None, description="Source provenance.")


class ChargeAllegation(BaseModel):
    """Statutory charge or allegation. Does NOT determine whether charge is proved."""

    model_config = ConfigDict(extra="ignore")

    charge_id: str = Field(description="Unique identifier for the charge (e.g. 'CH-01').")
    legal_provision: str = Field(description="Statutory section (e.g. 'Section 317 BNS', 'Section 25 Arms Act').")
    allegation_description: str = Field(description="Substantive factual allegation.")
    accused: str = Field(description="Accused person against whom allegation is directed.")
    related_evidence_ids: list[str] = Field(
        default_factory=list,
        description="Evidence item IDs cited by prosecution in support of this allegation.",
    )
    source: Optional[SourceReference] = Field(default=None, description="Source provenance.")


class Witness(BaseModel):
    """Witness examined in the proceedings. Preserves exact name, role, side, and testimony facts."""

    model_config = ConfigDict(extra="ignore")

    witness_id: str = Field(description="Identifier (e.g. 'PW-1', 'PW-6', 'DW-1').")
    witness_number: Optional[str] = Field(default=None, description="Numerical designation or exact string.")
    name: str = Field(description="Full name or official title of witness.")
    role: Optional[str] = Field(default=None, description="Role in case (e.g. 'alleged victim/vehicle owner', 'IO').")
    side: str = Field(default="Prosecution", description="'Prosecution' or 'Defense'.")
    testimony_summary: Optional[str] = Field(default=None, description="Objective summary of deposition.")
    facts_testified: list[str] = Field(default_factory=list, description="Specific factual assertions testified to.")
    identification_information: Optional[str] = Field(default=None, description="Identifications made by witness.")
    evidence_referred_to: list[str] = Field(default_factory=list, description="Exhibits or documents proved/referred to.")
    source_page: Optional[int] = Field(default=None, description="Page number of deposition in Evidence PDF.")
    source: Optional[SourceReference] = Field(default=None, description="Detailed source provenance.")


class EvidenceItem(BaseModel):
    """Documentary or material exhibit marked in evidence. Preserves exhibit number exactly."""

    model_config = ConfigDict(extra="ignore")

    evidence_id: str = Field(description="Unique internal ID (e.g. 'EX_P1', 'EX_PA').")
    exhibit_number: str = Field(description="Exact marked exhibit string (e.g. 'Ex.P1', 'Ex.PA', 'Ex.PB/1').")
    evidence_type: str = Field(description="Type: documentary, material, electronic, memo, affidavit, etc.")
    description: str = Field(description="Description of the exhibit or document.")
    introduced_by: Optional[str] = Field(default=None, description="Party introducing (Prosecution/Defense).")
    introduced_through_witness: Optional[str] = Field(default=None, description="Witness who proved the exhibit.")
    contents_summary: Optional[str] = Field(default=None, description="Summary of exhibit contents.")
    relevance_claimed: Optional[str] = Field(default=None, description="Relevance claimed by the introducing party.")
    linked_witnesses: list[str] = Field(default_factory=list, description="Witnesses who identified or proved this.")
    linked_charges: list[str] = Field(default_factory=list, description="Charges connected to this exhibit.")
    source_page: Optional[int] = Field(default=None, description="Source page number in Evidence PDF.")
    original_or_copy: Optional[str] = Field(default=None, description="'original', 'photocopy', 'attested copy', etc.")
    authenticity_status_if_stated: Optional[str] = Field(default=None, description="If disputed or admitted on record.")
    source: Optional[SourceReference] = Field(default=None, description="Detailed source provenance.")


class PhysicalEvidenceItem(BaseModel):
    """Physical or material object seized, recovered, or produced in trial."""

    model_config = ConfigDict(extra="ignore")

    evidence_id: str = Field(description="Unique identifier (e.g. 'PE-01', 'MO-01').")
    item_description: str = Field(description="Description of physical object (e.g. 'Pistol', 'Number plate', 'Car').")
    recovered_from: Optional[str] = Field(default=None, description="Person or premises from where recovered.")
    recovered_by: Optional[str] = Field(default=None, description="Officer effecting recovery.")
    recovery_date: Optional[str] = Field(default=None, description="Date of seizure/recovery.")
    recovery_location: Optional[str] = Field(default=None, description="Exact location of recovery.")
    seizure_document: Optional[str] = Field(default=None, description="Seizure memo or panchnama exhibit number.")
    physical_description: Optional[str] = Field(default=None, description="Physical state, calibre, markings.")
    linked_exhibits: list[str] = Field(default_factory=list, description="Associated exhibit IDs (e.g. 'Ex.P3', 'Ex.PB').")
    source_page: Optional[int] = Field(default=None, description="Source page number.")
    source: Optional[SourceReference] = Field(default=None, description="Source provenance.")


class RecoveryRecord(BaseModel):
    """Alleged recovery under investigation. Keeps prosecution claim separate from established fact."""

    model_config = ConfigDict(extra="ignore")

    recovery_id: str = Field(description="Unique recovery identifier (e.g. 'REC-01').")
    recovered_item: str = Field(description="Item allegedly recovered.")
    person: Optional[str] = Field(default=None, description="Accused or person from whom recovered.")
    location: Optional[str] = Field(default=None, description="Place of recovery.")
    date: Optional[str] = Field(default=None, description="Date of alleged recovery.")
    recovering_officer: Optional[str] = Field(default=None, description="Officer who conducted recovery.")
    witnesses_present: list[str] = Field(default_factory=list, description="Independent or police attesting witnesses.")
    seizure_memo: Optional[str] = Field(default=None, description="Exhibit number of seizure memo.")
    related_exhibit: Optional[str] = Field(default=None, description="Exhibit marked for the recovered article.")
    prosecution_claim: Optional[str] = Field(
        default=None,
        description="Factual claim asserted by the prosecution regarding the recovery.",
    )
    source_page: Optional[int] = Field(default=None, description="Source page number.")
    source: Optional[SourceReference] = Field(default=None, description="Source provenance.")


class IdentificationRecord(BaseModel):
    """Identification proceedings (TIP, in-court, vehicle, or document). Does NOT decide reliability."""

    model_config = ConfigDict(extra="ignore")

    identification_id: str = Field(description="Unique ID (e.g. 'ID-01').")
    identification_type: str = Field(
        description="Type: 'Test Identification Parade', 'in-court identification', 'vehicle identification', 'document identification', 'photograph identification'."
    )
    person_identifying: Optional[str] = Field(default=None, description="Witness performing identification.")
    person_or_object_identified: Optional[str] = Field(default=None, description="Person or property identified.")
    identification_method: Optional[str] = Field(default=None, description="Procedure or method utilized.")
    date: Optional[str] = Field(default=None, description="Date identification took place.")
    location: Optional[str] = Field(default=None, description="Location where identification took place.")
    identification_memo: Optional[str] = Field(default=None, description="Memo or record exhibit number.")
    witness: Optional[str] = Field(default=None, description="Witness designation (e.g. 'PW-6').")
    source_page: Optional[int] = Field(default=None, description="Source page number.")
    source: Optional[SourceReference] = Field(default=None, description="Source provenance.")


class TestimonyClaim(BaseModel):
    """Atomic factual claim made in witness testimony. Strictly separates claims from facts."""

    model_config = ConfigDict(extra="ignore")

    claim_id: str = Field(description="Unique claim ID (e.g. 'CLM-01').")
    witness_id: str = Field(description="Witness asserting the claim (e.g. 'PW-1').")
    statement: str = Field(description="The precise statement or assertion made.")
    claim_type: ClaimType = Field(default=ClaimType.OBSERVATION, description="Categorical claim type.")
    related_evidence: list[str] = Field(default_factory=list, description="Exhibits referred to in this claim.")
    related_charge: Optional[str] = Field(default=None, description="Charge provision relevant to this claim.")
    source_page: Optional[int] = Field(default=None, description="Page number of deposition.")
    source: Optional[SourceReference] = Field(default=None, description="Source provenance.")


class StatementRecord(BaseModel):
    """Recorded statement or disclosure under investigation or inquiry."""

    model_config = ConfigDict(extra="ignore")

    statement_id: str = Field(description="Unique statement ID (e.g. 'STM-01').")
    person: str = Field(description="Person making the statement.")
    statement_type: str = Field(
        description="Type: 'disclosure statement', 'statement under investigation', 'recorded statement', 'admission', 'denial'."
    )
    statement_summary: str = Field(description="Objective summary of what was stated.")
    disclosed_fact: Optional[str] = Field(default=None, description="Specific material fact allegedly disclosed.")
    related_evidence: list[str] = Field(default_factory=list, description="Evidence discovered or produced pursuant to statement.")
    source_page: Optional[int] = Field(default=None, description="Source page number.")
    source: Optional[SourceReference] = Field(default=None, description="Source provenance.")


class ProceduralRecord(BaseModel):
    """Investigative or procedural action. Does NOT decide legal validity."""

    model_config = ConfigDict(extra="ignore")

    procedure_id: str = Field(description="Unique procedure ID (e.g. 'PROC-01').")
    procedure_type: str = Field(
        description="Step: 'FIR registration', 'site inspection', 'seizure', 'search', 'arrest', 'memo preparation', 'rough sketch', 'final report', 'examination of witnesses'."
    )
    date: Optional[str] = Field(default=None, description="Date action was taken.")
    officer: Optional[str] = Field(default=None, description="Police officer or magistrate who executed step.")
    description: str = Field(description="Factual description of procedural step.")
    related_document: Optional[str] = Field(default=None, description="Document generated (e.g. FIR copy, rough site plan).")
    related_evidence: list[str] = Field(default_factory=list, description="Exhibits linked to this procedural step.")
    source_page: Optional[int] = Field(default=None, description="Source page number.")
    source: Optional[SourceReference] = Field(default=None, description="Source provenance.")


class EvidenceLink(BaseModel):
    """Explicit relational link connecting different evidentiary nodes by their IDs."""

    model_config = ConfigDict(extra="ignore")

    link_id: Optional[str] = Field(default=None, description="Optional unique link ID.")
    source_id: str = Field(description="Source identifier (e.g. 'PW-6', 'EX_P3', 'REC-01').")
    relation_type: str = Field(
        description="Relationship type: 'testified_about', 'supports_claim', 'related_to', 'identified', 'produced', 'referenced_by'."
    )
    target_id: str = Field(description="Target identifier (e.g. 'EX_PG', 'CH-01', 'Jai Bhagwan').")
    description: Optional[str] = Field(default=None, description="Brief explanation of link.")


class ContradictionRecord(BaseModel):
    """Objectively detectable contradiction between two sources on record. Does NOT decide truth."""

    model_config = ConfigDict(extra="ignore")

    contradiction_id: str = Field(description="Unique ID (e.g. 'CONTR-01').")
    subject: str = Field(description="Topic or fact in dispute (e.g. 'vehicle registration number').")
    statement_a: str = Field(description="First statement or record entry.")
    source_a: str = Field(description="Source of first statement (e.g. 'PW-6 deposition', 'Ex.PC').")
    statement_b: str = Field(description="Second contradictory statement or entry.")
    source_b: str = Field(description="Source of second statement (e.g. 'PW-7 testimony', 'Ex.PB').")
    contradiction_type: str = Field(description="Type: 'factual', 'temporal', 'documentary', 'identification'.")
    description: str = Field(description="Analytical summary of the divergence.")


class MissingEvidenceRecord(BaseModel):
    """Evidence explicitly noted on record as missing, unproduced, unproved, or unavailable."""

    model_config = ConfigDict(extra="ignore")

    missing_evidence_id: str = Field(description="Unique ID (e.g. 'MISS-01').")
    description: str = Field(description="Description of missing or unproved evidence.")
    expected_source: Optional[str] = Field(default=None, description="Source from which it was expected (e.g. 'Independent panchas', 'FSL report').")
    related_charge: Optional[str] = Field(default=None, description="Charge provision impacted by absence.")
    source_page: Optional[int] = Field(default=None, description="Page where omission is explicitly stated.")
    explicitly_stated: bool = Field(default=True, description="True if explicitly noted in record; never invented.")
    source: Optional[SourceReference] = Field(default=None, description="Source provenance.")


class EvidencePackage(BaseModel):
    """
    Complete Standardized Evidence Representation Package for AI-Court-of-India.
    Provides structured, non-judgmental ingestion of case evidence without Ground Truth leakage.
    """

    model_config = ConfigDict(extra="ignore")

    case_identification: CaseIdentification = Field(
        default_factory=CaseIdentification,
        description="Case metadata, parties, FIR, and court details.",
    )
    charges: list[ChargeAllegation] = Field(
        default_factory=list,
        description="Charges and allegations framed against the accused.",
    )
    prosecution_witnesses: list[Witness] = Field(
        default_factory=list,
        description="All witnesses examined by the prosecution.",
    )
    defence_witnesses: list[Witness] = Field(
        default_factory=list,
        description="Witnesses examined by the defense (empty list if none).",
    )
    exhibits: list[EvidenceItem] = Field(
        default_factory=list,
        description="All marked documentary and material exhibits.",
    )
    physical_evidence: list[PhysicalEvidenceItem] = Field(
        default_factory=list,
        description="Physical articles, weapons, vehicles, or seized objects.",
    )
    recoveries: list[RecoveryRecord] = Field(
        default_factory=list,
        description="Documented recoveries and seizure operations.",
    )
    identifications: list[IdentificationRecord] = Field(
        default_factory=list,
        description="Identification records (TIP, in-court, vehicle, etc.).",
    )
    testimony_claims: list[TestimonyClaim] = Field(
        default_factory=list,
        description="Atomic factual claims asserted during depositions.",
    )
    statements: list[StatementRecord] = Field(
        default_factory=list,
        description="Investigation disclosures, admissions, or statements.",
    )
    procedural_records: list[ProceduralRecord] = Field(
        default_factory=list,
        description="Chronological investigative procedures and steps taken.",
    )
    evidence_links: list[EvidenceLink] = Field(
        default_factory=list,
        description="Explicit relational linkages between evidentiary entities.",
    )
    contradictions: list[ContradictionRecord] = Field(
        default_factory=list,
        description="Contradictions and inconsistencies identified on record.",
    )
    missing_evidence: list[MissingEvidenceRecord] = Field(
        default_factory=list,
        description="Explicitly stated gaps, unproved documents, or missing items.",
    )
    raw_metadata: dict = Field(
        default_factory=dict,
        description="Additional ingestion metadata such as page count and source file name.",
    )
