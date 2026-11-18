"""
Pydantic data models for structured case representation extracted from Case_Packet.pdf.
"""

from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, model_validator


def _coerce_none_fields(
    data: Any,
    str_fields: tuple[str, ...],
    list_fields: tuple[str, ...] = (),
) -> Any:
    """Coerce null LLM values on non-optional string/list fields to safe empty defaults."""
    if not isinstance(data, dict):
        return data
    updated = dict(data)
    for k in str_fields:
        if k in updated and updated[k] is None:
            updated[k] = ""
    for k in list_fields:
        if k in updated and updated[k] is None:
            updated[k] = []
    return updated


class Party(BaseModel):
    """Represents a party in the legal proceeding."""

    name: str = Field(default="", description="Name of the person, organisation, or State entity.")
    role: str = Field(
        default="",
        description="Role in proceedings: 'prosecution', 'accused', 'victim', 'complainant', 'appellant', 'respondent'.",
    )
    details: Optional[str] = Field(default=None, description="Demographic or contextual details if provided.")

    @model_validator(mode="before")
    @classmethod
    def _coerce_nulls(cls, data: Any) -> Any:
        return _coerce_none_fields(data, ("name", "role"))


class ProceedingScope(BaseModel):
    """Represents an individual or connected proceeding and its distinct decision subjects."""

    proceeding_id: str = Field(default="", description="Proceeding number or identifier (e.g. 'Cr. Revision No. 1247/2017').")
    proceeding_type: Optional[str] = Field(default=None, description="Type: 'trial', 'appeal', 'revision', 'bail', 'other'.")
    accused_or_petitioners: list[str] = Field(
        default_factory=list,
        description="Distinct accused, appellants, or petitioners belonging to this proceeding.",
    )
    role_summary: Optional[str] = Field(default=None, description="Procedural posture or alleged role in this proceeding.")

    @model_validator(mode="before")
    @classmethod
    def _coerce_nulls(cls, data: Any) -> Any:
        return _coerce_none_fields(data, ("proceeding_id",), ("accused_or_petitioners",))


class Charge(BaseModel):
    """Represents a statutory charge or allegation framed against an accused."""

    section: str = Field(default="", description="Statutory section or provision (e.g. 'Section 303 BNS', 'Section 66 IT Act').")
    statute: str = Field(default="", description="Act name (e.g. 'Bharatiya Nyaya Sanhita, 2023', 'Information Technology Act, 2000').")
    description: str = Field(default="", description="Description of the alleged offence.")
    accused_name: str = Field(default="", description="Name of the accused against whom the charge is framed.")
    elements_alleged: list[str] = Field(
        default_factory=list,
        description="Specific statutory elements alleged by the prosecution to have occurred.",
    )
    record_status: Literal["current", "procedural_history", "other_accused", "uncertain"] = Field(
        default="current",
        description="Whether charge is currently before the court for accused_name or appears only in history/against another accused.",
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_nulls(cls, data: Any) -> Any:
        updated = _coerce_none_fields(
            data,
            ("section", "statute", "description", "accused_name"),
            ("elements_alleged",),
        )
        if isinstance(updated, dict):
            rs = updated.get("record_status")
            if rs not in {"current", "procedural_history", "other_accused", "uncertain"}:
                updated["record_status"] = "current"
        return updated


class WitnessStatement(BaseModel):
    """Represents testimony provided by a witness during investigation or trial."""

    witness_id: str = Field(default="", description="Unique witness identifier (e.g. 'PW-1', 'DW-1').")
    witness_name: str = Field(default="", description="Full name of witness.")
    witness_type: str = Field(
        default="",
        description="Type: 'eye_witness', 'police_officer', 'investigating_officer', 'expert_witness', 'medical_officer', 'pancha_witness', 'defense_witness'.",
    )
    testimony_summary: str = Field(default="", description="Summary of facts and observations stated by the witness.")
    key_assertions: list[str] = Field(default_factory=list, description="Direct factual assertions made in testimony.")
    reliability_indicators: list[str] = Field(
        default_factory=list,
        description="Noted factors affecting credibility (e.g. hostility, interested witness, prompt statement).",
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_nulls(cls, data: Any) -> Any:
        return _coerce_none_fields(
            data,
            ("witness_id", "witness_name", "witness_type", "testimony_summary"),
            ("key_assertions", "reliability_indicators"),
        )


class Exhibit(BaseModel):
    """Represents an evidentiary item or document marked as an exhibit in the case packet."""

    exhibit_id: str = Field(default="", description="Identifier (e.g. 'Ex. P-1', 'Ex. D-1', 'MO-1').")
    title: str = Field(default="", description="Title or label of the exhibit.")
    exhibit_type: str = Field(
        default="",
        description="Type: 'documentary', 'electronic_record', 'physical_object', 'forensic_report', 'medical_report', 'recovery_memo'.",
    )
    description: str = Field(default="", description="Description of the physical or digital evidence.")
    marked_by: str = Field(default="", description="Party or witness who produced or proved the exhibit.")
    admissibility_notes: Optional[str] = Field(default=None, description="Notes on compliance with statutory admissibility rules.")

    @model_validator(mode="before")
    @classmethod
    def _coerce_nulls(cls, data: Any) -> Any:
        return _coerce_none_fields(
            data,
            ("exhibit_id", "title", "exhibit_type", "description", "marked_by"),
        )


class StructuredCase(BaseModel):
    """Complete, structured representation of a case extracted strictly from Case_Packet.pdf."""

    case_id: str = Field(default="CASE-001", description="Unique case identifier.")
    case_title: str = Field(default="", description="Formal title of the case (e.g. 'State v. Rahul Sharma').")
    court_identifier: Optional[str] = Field(
        default=None,
        description="Court name, jurisdiction, or FIR / Sessions Case Number if available.",
    )
    jurisdiction: str = Field(default="India", description="Legal jurisdiction.")
    parties: list[Party] = Field(default_factory=list, description="All parties participating in the proceeding.")
    accused: list[str] = Field(default_factory=list, description="Names of all accused persons.")
    allegations_summary: str = Field(default="", description="Core prosecution allegations against the accused.")
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
    connected_proceedings: list[ProceedingScope] = Field(
        default_factory=list,
        description="Connected trials, appeals, or revisions heard together with their distinct petitioners/accused.",
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
    ml_case_type: Optional[str] = Field(
        default=None,
        description="Stage-0 ML intake classifier prediction (e.g. 'CRL', 'CRA', 'BA', 'REV').",
    )
    ml_top_predictions: list[str] = Field(
        default_factory=list,
        description="Top Stage-0 ML classifier predictions with decision scores.",
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_nulls(cls, data: Any) -> Any:
        return _coerce_none_fields(
            data,
            ("case_id", "case_title", "jurisdiction", "allegations_summary"),
            (
                "parties",
                "accused",
                "charges",
                "prosecution_facts",
                "defense_facts",
                "witnesses",
                "exhibits",
                "connected_proceedings",
                "legal_issues",
                "disputed_facts",
                "undisputed_facts",
                "missing_or_uncertain_info",
                "ml_top_predictions",
            ),
        )

    def current_charges(self) -> list[Charge]:
        """Return only charges whose liability is presently before the court for decision."""
        if len(self.connected_proceedings) > 1 or not self.decision_subject:
            return [c for c in self.charges if c.record_status == "current"]
        subj = self.decision_subject.strip().casefold()
        active = [
            c for c in self.charges
            if c.record_status == "current"
            and (
                not c.accused_name.strip()
                or subj in c.accused_name.casefold()
                or c.accused_name.casefold() in subj
                or c.accused_name.strip().casefold() in {"accused", "all accused", "petitioners", "appellant", "appellants"}
            )
        ]
        return active

    def distinct_decision_subjects(self) -> list[str]:
        """Return distinct accused/petitioners across connected proceedings or current charges."""
        seen: dict[str, str] = {}
        for proc in self.connected_proceedings:
            for person in proc.accused_or_petitioners:
                key = person.strip().casefold()
                if key and key not in seen:
                    seen[key] = person.strip()
        if not seen:
            for c in self.current_charges():
                key = c.accused_name.strip().casefold()
                if key and key not in seen and key not in {"accused", "all accused", "petitioners"}:
                    seen[key] = c.accused_name.strip()
        if not seen and self.decision_subject:
            seen[self.decision_subject.strip().casefold()] = self.decision_subject.strip()
        if not seen:
            for person in self.accused:
                key = person.strip().casefold()
                if key and key not in seen:
                    seen[key] = person.strip()
        return list(seen.values())
