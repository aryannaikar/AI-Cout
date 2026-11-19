"""
Pydantic data models for Prosecution Arguments, Defense Arguments, and the 12-section Judicial Verdict.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class StatementType(str, Enum):
    """Rigorous epistemic classification required of all courtroom arguments."""

    FACT = "FACT"
    EVIDENCE = "EVIDENCE"
    LEGAL_RULE = "LEGAL_RULE"
    INFERENCE = "INFERENCE"
    ARGUMENT = "ARGUMENT"


class ArgumentComponent(BaseModel):
    """An individual constituent proposition of a legal submission."""

    statement_type: StatementType = Field(
        description="Epistemic nature: FACT, EVIDENCE, LEGAL_RULE, INFERENCE, or ARGUMENT."
    )
    content: str = Field(description="The proposition or assertion.")
    source_reference: Optional[str] = Field(
        default=None,
        description="Grounded citation or evidentiary source (e.g. 'PW-1 at Page 12', 'BNS Section 317(2)', 'Ex. P-4').",
    )


class ProsecutionCase(BaseModel):
    """Complete adversarial case submitted by the Prosecutor Agent."""

    case_id: str = Field(description="Case identifier.")
    prosecution_theory: str = Field(description="Central narrative and theory of guilt.")
    statutory_elements: list[str] = Field(
        default_factory=list,
        description="Elements of offences that must be established beyond reasonable doubt.",
    )
    argument_components: list[ArgumentComponent] = Field(
        default_factory=list,
        description="Structured arguments explicitly categorized by statement type.",
    )
    supporting_witnesses: list[str] = Field(
        default_factory=list,
        description="Witnesses establishing the chain of events.",
    )
    supporting_exhibits: list[str] = Field(
        default_factory=list,
        description="Physical and digital exhibits corroborating charges.",
    )
    addressed_weaknesses: list[str] = Field(
        default_factory=list,
        description="Proactive explanation or mitigation of evidentiary infirmities in the case packet.",
    )
    legal_citations: list[str] = Field(
        default_factory=list,
        description="Statutory citations retrieved via Phase 1 Legal RAG.",
    )
    final_prayer: str = Field(description="Formal request for conviction and statutory sentencing.")


class DefenseCase(BaseModel):
    """Complete adversarial defense submitted by the Defense Agent."""

    case_id: str = Field(description="Case identifier.")
    defense_theory: str = Field(description="Central theory of defense (e.g. false implication, alibi, lack of mens rea).")
    argument_components: list[ArgumentComponent] = Field(
        default_factory=list,
        description="Structured arguments explicitly categorized by statement type.",
    )
    reasonable_doubt_grounds: list[str] = Field(
        default_factory=list,
        description="Specific material doubts raised by the record (e.g. contradiction between medical and ocular testimony).",
    )
    witness_inconsistencies_highlighted: list[str] = Field(
        default_factory=list,
        description="Witness contradictions undermining prosecution credibility.",
    )
    missing_evidence_highlighted: list[str] = Field(
        default_factory=list,
        description="Investigative omissions creating reasonable doubt.",
    )
    alternative_interpretation: str = Field(
        description="Plausible exculpatory interpretation of the facts supported by the evidence.",
    )
    legal_citations: list[str] = Field(
        default_factory=list,
        description="Statutory citations retrieved via Phase 1 Legal RAG supporting the defense.",
    )
    final_prayer: str = Field(description="Formal request for complete acquittal and discharge.")


class JudicialIssueAnalysis(BaseModel):
    """Independent analysis by the Judge of a specific issue in controversy."""

    issue_number: int = Field(description="Issue number (e.g. 1, 2, 3).")
    issue_statement: str = Field(description="Formal question of law or fact framed for decision.")
    applicable_law: str = Field(description="Statutory section and standard of proof governing this issue.")
    prosecution_submission_summary: str = Field(description="Summary of prosecution's argument on this issue.")
    defense_submission_summary: str = Field(description="Summary of defense's argument on this issue.")
    evidentiary_evaluation: str = Field(description="Independent judicial appreciation of oral and documentary evidence.")
    judicial_finding: str = Field(description="Finding: 'PROVED', 'NOT PROVED', or 'DISPROVED'.")


class IngredientItem(BaseModel):
    """Single statutory ingredient evaluated against evidence and rebuttals."""

    ingredient_id: str = ""
    legal_description: str = ""
    source_citation: str = ""
    supporting_evidence: list[str] = Field(default_factory=list)
    contradictory_evidence: list[str] = Field(default_factory=list)
    related_witnesses: list[str] = Field(default_factory=list)
    related_exhibits: list[str] = Field(default_factory=list)
    prosecution_argument: str = ""
    defense_argument: str = ""
    assessment_status: Literal["Supported", "Disputed", "Not established", "Not assessable"] = "Not assessable"
    judge_reasoning: str = ""

    @model_validator(mode="before")
    @classmethod
    def _coerce_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        out = dict(data)
        for k in ("ingredient_id", "legal_description", "source_citation", "prosecution_argument", "defense_argument", "judge_reasoning"):
            if out.get(k) is None:
                out[k] = ""
        for k in ("supporting_evidence", "contradictory_evidence", "related_witnesses", "related_exhibits"):
            if out.get(k) is None:
                out[k] = []
        valid_status = {"Supported", "Disputed", "Not established", "Not assessable"}
        if out.get("assessment_status") not in valid_status:
            out["assessment_status"] = "Not assessable"
        return out


class IngredientChecklist(BaseModel):
    """Structured statutory ingredient checklist for a single current charge & accused."""

    charge_key: str
    act_name: str
    section: str
    accused_name: str
    burden_of_proof: str = "Prosecution must prove every statutory ingredient beyond reasonable doubt."
    ingredients: list[IngredientItem] = Field(default_factory=list)


class ScrutinyChallenge(BaseModel):
    """Challenge raised by the independent Devil's Advocate scrutiny stage."""

    challenge_id: str = ""
    category: str = ""
    severity: Literal["low", "medium", "high"] = "medium"
    description: str = ""
    affected_accused_or_charge: Optional[str] = None
    recommendation: str = ""

    @model_validator(mode="before")
    @classmethod
    def _coerce_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        out = dict(data)
        for k in ("challenge_id", "category", "description", "recommendation"):
            if out.get(k) is None:
                out[k] = ""
        sev = str(out.get("severity") or "").strip().lower()
        if any(tok in sev for tok in ("high", "critical", "serious")):
            out["severity"] = "high"
        elif any(tok in sev for tok in ("low", "minor")):
            out["severity"] = "low"
        else:
            out["severity"] = "medium"
        return out


class DevilsAdvocateReport(BaseModel):
    """Output of the independent Devil's Advocate scrutiny review."""

    reviewed: bool = True
    requires_revision: bool = False
    challenges: list[ScrutinyChallenge] = Field(default_factory=list)
    summary: str = ""
    llm_used: bool = False


class AccusedFinding(BaseModel):
    """Per-accused / per-proceeding finding when multiple accused or connected proceedings exist."""

    accused_name: str = Field(description="Name of the specific accused or petitioner.")
    proceeding_id: Optional[str] = Field(default=None, description="Connected proceeding identifier if applicable.")
    charges_decided: list[str] = Field(default_factory=list, description="Charges decided for this specific person.")
    finding: str = Field(description="Outcome for this accused: 'CONVICTION', 'ACQUITTAL', or 'PARTIAL CONVICTION'.")
    reasoning_summary: str = Field(description="Brief individualized reasoning distinguishing this accused's role and evidence.")


class Judgment(BaseModel):
    """
    Formal, exhaustive judicial verdict rendered by the Judge Agent.
    Strictly follows the 12-section judicial reasoning framework.
    """

    judgment_id: str = Field(default="JUDG-001", description="Judgment identifier.")
    case_title: str = Field(description="Formal case title.")
    presiding_court: str = Field(default="Court of Sessions / AI Court of India", description="Court name.")
    date_of_decision: str = Field(description="Date of verdict.")

    # 1. Case background
    case_background: str = Field(description="Section 1: Factual background, FIR narrative, and prosecution origin.")

    # 2. Issues for determination
    issues_for_determination: list[str] = Field(
        description="Section 2: Points for determination formulated by the court."
    )

    # 3. Applicable law
    applicable_law: list[str] = Field(
        description="Section 3: Governing provisions of BNS, BSA, IT Act, and the Constitution."
    )

    # 4. Evidence assessment
    evidence_assessment: str = Field(
        description="Section 4: Judicial assessment of exhibits, electronic records, and chain of custody."
    )

    # 5. Witness assessment
    witness_assessment: str = Field(
        description="Section 5: Credibility analysis of prosecution and defense witnesses."
    )

    # 6. Prosecution submissions
    prosecution_submissions: str = Field(
        description="Section 6: Summary of submissions made on behalf of the State."
    )

    # 7. Defense submissions
    defense_submissions: str = Field(
        description="Section 7: Summary of submissions made on behalf of the accused."
    )

    # 8. Analysis of each issue
    issue_analyses: list[JudicialIssueAnalysis] = Field(
        description="Section 8: Systematic analysis and determination of each issue framed."
    )

    # 9. Findings
    findings_per_charge: dict[str, str] = Field(
        description="Section 9: Specific finding per charge (e.g. {'Section 303 BNS': 'Guilty', 'Section 66 IT Act': 'Acquitted'})."
    )

    @field_validator("findings_per_charge", mode="before")
    @classmethod
    def _coerce_findings_dict_values(cls, v):
        if not isinstance(v, dict):
            return {}
        out = {}
        for k, val in v.items():
            if isinstance(val, dict):
                out[str(k)] = "; ".join(f"{sub_k}: {sub_v}" for sub_k, sub_v in val.items())
            elif isinstance(val, list):
                out[str(k)] = "; ".join(str(x) for x in val)
            else:
                out[str(k)] = str(val)
        return out
    accused_findings: list[AccusedFinding] = Field(
        default_factory=list,
        description="Individualized findings per accused/petitioner across connected proceedings or multi-accused trials.",
    )

    # 10. Final decision
    final_decision: str = Field(
        description="Section 10: Formal operative verdict ('CONVICTION', 'ACQUITTAL', or 'PARTIAL CONVICTION')."
    )

    # 11. Reasons
    reasons: str = Field(
        description="Section 11: Ratio decidendi and detailed reasoning justifying the decision."
    )

    # 12. Legal citations
    legal_citations: list[str] = Field(
        description="Section 12: Grounded statutory citations supporting the judgment."
    )
    ingredient_checklists: list[IngredientChecklist] = Field(
        default_factory=list,
        description="Structured statutory ingredient checklists evaluated per charge and accused.",
    )
    scrutiny_report: Optional[DevilsAdvocateReport] = Field(
        default=None,
        description="Independent Devil's Advocate scrutiny findings considered before final judgment.",
    )
