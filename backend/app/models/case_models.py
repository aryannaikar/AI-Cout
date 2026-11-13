"""
Pydantic data models for structured case representation extracted from Case_Packet.pdf.
"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


class Party(BaseModel):
    """Represents a party in the legal proceeding."""

    name: str = Field(description="Name of the person, organisation, or State entity.")
    role: str = Field(
        description="Role in proceedings: 'prosecution', 'accused', 'victim', 'complainant', 'appellant', 'respondent'."
    )
    details: Optional[str] = Field(default=None, description="Demographic or contextual details if provided.")


class Charge(BaseModel):
    """Represents a statutory charge or allegation framed against an accused."""

    section: str = Field(description="Statutory section or provision (e.g. 'Section 303 BNS', 'Section 66 IT Act').")
    statute: str = Field(description="Act name (e.g. 'Bharatiya Nyaya Sanhita, 2023', 'Information Technology Act, 2000').")
    description: str = Field(description="Description of the alleged offence.")
    accused_name: str = Field(description="Name of the accused against whom the charge is framed.")
    elements_alleged: list[str] = Field(
        default_factory=list,
        description="Specific statutory elements alleged by the prosecution to have occurred.",
    )
    record_status: Literal["current", "procedural_history", "other_accused", "uncertain"] = Field(
        default="current",
        description="Whether charge is currently before the court for accused_name or appears only in history/against another accused.",
    )


class WitnessStatement(BaseModel):
    """Represents testimony provided by a witness during investigation or trial."""

    witness_id: str = Field(description="Unique witness identifier (e.g. 'PW-1', 'DW-1').")
    witness_name: str = Field(description="Full name of witness.")
    witness_type: str = Field(
        description="Type: 'eye_witness', 'police_officer', 'investigating_officer', 'expert_witness', 'medical_officer', 'pancha_witness', 'defense_witness'."
    )
    testimony_summary: str = Field(description="Summary of facts and observations stated by the witness.")
    key_assertions: list[str] = Field(default_factory=list, description="Direct factual assertions made in testimony.")
    reliability_indicators: list[str] = Field(
        default_factory=list,
        description="Noted factors affecting credibility (e.g. hostility, interested witness, prompt statement).",
    )


class Exhibit(BaseModel):
    """Represents an evidentiary item or document marked as an exhibit in the case packet."""

    exhibit_id: str = Field(description="Identifier (e.g. 'Ex. P-1', 'Ex. D-1', 'MO-1').")
    title: str = Field(description="Title or label of the exhibit.")
    exhibit_type: str = Field(
        description="Type: 'documentary', 'electronic_record', 'physical_object', 'forensic_report', 'medical_report', 'recovery_memo'."
    )
    description: str = Field(description="Description of the physical or digital evidence.")
    marked_by: str = Field(description="Party or witness who produced or proved the exhibit.")
    admissibility_notes: Optional[str] = Field(default=None, description="Notes on compliance with statutory admissibility rules.")


class StructuredCase(BaseModel):
    """Complete, structured representation of a case extracted strictly from Case_Packet.pdf."""

    case_id: str = Field(default="CASE-001", description="Unique case identifier.")
    case_title: str = Field(description="Formal title of the case (e.g. 'State v. Rahul Sharma').")
    court_identifier: Optional[str] = Field(
        default=None,
        description="Court name, jurisdiction, or FIR / Sessions Case Number if available.",
    )
    jurisdiction: str = Field(default="India", description="Legal jurisdiction.")
    parties: list[Party] = Field(default_factory=list, description="All parties participating in the proceeding.")
    accused: list[str] = Field(default_factory=list, description="Names of all accused persons.")
    allegations_summary: str = Field(description="Core prosecution allegations against the accused.")
    charges: list[Charge] = Field(default_factory=list, description="Specific statutory charges framed.")
    prosecution_facts: list[str] = Field(
        default_factory=list,
        description="Chronological factual assertions put forward by the prosecution.",
    )
    defense_facts: list[str] = Field(
        default_factory=list,
        description="Factual assertions, alibis, or defenses raised by the accused.",
    )
    witnesses: list[WitnessStatement] = Field(
        default_factory=list,
        description="Witnesses and statements included in the case packet.",
    )
    exhibits: list[Exhibit] = Field(
        default_factory=list,
        description="Exhibits and evidentiary materials marked in the case packet.",
    )
    procedural_history: Optional[str] = Field(
        default=None,
        description="Summary of FIR registration, charge-sheet, committal, or prior orders.",
    )
    proceeding_type: Optional[str] = Field(
        default=None,
        description="Current proceeding, if stated: trial, appeal, revision, bail, or other. Never infer from a cited prior order alone.",
    )
    decision_subject: Optional[str] = Field(
        default=None,
        description="Accused/appellant whose liability is currently for decision, if explicitly identifiable. None means charge scope is unresolved.",
    )
    legal_issues: list[str] = Field(
        default_factory=list,
        description="Key legal and factual questions requiring determination.",
    )
    disputed_facts: list[str] = Field(
        default_factory=list,
        description="Facts contested between prosecution and defense.",
    )
    undisputed_facts: list[str] = Field(
        default_factory=list,
        description="Facts conceded or agreed upon by both sides.",
    )
    missing_or_uncertain_info: list[str] = Field(
        default_factory=list,
        description="Evidentiary gaps, uncalled witnesses, or missing documents noted in the packet.",
    )
