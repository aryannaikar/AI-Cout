"""
CourtState definition and schemas for AI Court of India LangGraph Orchestration.
Defines strongly-typed state with defensive validation against Ground Truth leakage.
"""

from __future__ import annotations

import operator
import sys
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Literal, Optional

# Ensure backend directory is in sys.path when executed from workspace root
_backend_dir = str(Path(__file__).resolve().parents[2])
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.graph.validation import (
    BlindEvaluationViolation,
    validate_case_packet_path,
    validate_no_forbidden_keys,
    validate_no_ground_truth_text,
)
from app.models.case_models import StructuredCase
from app.models.conflict_models import ConflictReport
from app.models.evidence_models import EvidenceAnalysisReport
from app.models.evidence_package_models import EvidencePackage
from app.models.judgment_models import DefenseCase, Judgment, ProsecutionCase
from app.models.legal_models import LegalResearchResult, WebResearchResult


class CourtError(BaseModel):
    """Represents an explicit error that occurred in a workflow node."""

    agent: str = Field(description="Name of the node or agent that encountered the failure")
    error: str = Field(description="Error message or exception details")
    recoverable: bool = Field(default=True, description="Whether the workflow can proceed despite this error")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ExecutionLogEntry(BaseModel):
    """Audit log item tracking the execution of each node in the courtroom graph."""

    node: str = Field(description="Name of the executed node")
    status: Literal["completed", "failed", "skipped"] = Field(description="Status of execution")
    start_time: Optional[str] = Field(default=None, description="ISO timestamp when node started")
    end_time: Optional[str] = Field(default=None, description="ISO timestamp when node ended")
    error: Optional[str] = Field(default=None, description="Error message if node failed")


from app.models.execution_models import ExecutionReport


class JudgeInput(BaseModel):
    """
    Sanitized, structured dossier provided to the Judge Agent.
    Strictly excludes Ground Truth Verdict, real court findings, and hidden labels.
    """

    model_config = ConfigDict(extra="forbid")

    case_analysis: StructuredCase
    prosecution: ProsecutionCase
    defense: DefenseCase
    evidence_analysis: EvidenceAnalysisReport
    conflicts: ConflictReport
    evidence_package: Optional[EvidencePackage] = None
    prosecution_legal_research: Optional[LegalResearchResult] = None
    defense_legal_research: Optional[LegalResearchResult] = None
    prosecution_web_research: Optional[WebResearchResult] = None
    defense_web_research: Optional[WebResearchResult] = None

    @model_validator(mode="before")
    @classmethod
    def validate_security(cls, data: Any) -> Any:
        if isinstance(data, dict):
            validate_no_forbidden_keys(data)
        return data


class CourtState(BaseModel):
    """
    Strongly typed courtroom state for LangGraph orchestration.
    Maintains complete trial record across all 10 adversarial and judicial roles.
    Strictly forbids ground-truth evaluation files or attributes.
    """

    model_config = ConfigDict(extra="forbid")

    # 1. Case Ingestion & Analysis
    case_packet: str = Field(description="File path or raw text of Case_Packet.pdf")
    case_analysis: Optional[StructuredCase] = Field(default=None, description="Structured factual and charge breakdown")
    evidence_package: Optional[EvidencePackage] = Field(
        default=None, description="Standardized evidentiary package ingested from Evidence PDF"
    )


    # 2. Prosecution Track
    prosecution: Optional[ProsecutionCase] = Field(default=None, description="Prosecution theory and arguments")
    prosecution_legal_research: Optional[LegalResearchResult] = Field(
        default=None, description="Grounded statutory research from Phase-1 LegalRetriever"
    )
    prosecution_web_research: Optional[WebResearchResult] = Field(
        default=None, description="External precedent research from WebResearchAgent"
    )

    # 3. Defense Track
    defense: Optional[DefenseCase] = Field(default=None, description="Defense theory, doubts, and arguments")
    defense_legal_research: Optional[LegalResearchResult] = Field(
        default=None, description="Grounded statutory research for defense"
    )
    defense_web_research: Optional[WebResearchResult] = Field(
        default=None, description="External precedent research for defense"
    )

    # 4. Evidentiary & Conflict Analysis
    evidence_analysis: Optional[EvidenceAnalysisReport] = Field(
        default=None, description="Objective analysis of exhibits and witness testimonies"
    )
    conflicts: Optional[ConflictReport] = Field(
        default=None, description="Contradictions flagged for judicial resolution"
    )

    # 5. Judicial Adjudication
    judge_input: Optional[JudgeInput] = Field(
        default=None, description="Sanitized dossier compiled for the Judge Agent"
    )
    judgment: Optional[Judgment] = Field(
        default=None, description="Final 12-section AI courtroom judgment"
    )

    # 6. Live Hearing Conversation
    active_issue: Optional[str] = Field(
        default=None, description="The current issue being debated in the live hearing"
    )
    current_issue: Optional[str] = Field(
        default=None, description="The specific factual/legal issue currently under debate"
    )
    previous_speaker: Optional[str] = Field(
        default=None, description="Role of the previous speaker (judge, prosecutor, defense, evidence, conflict)"
    )
    previous_message: Optional[str] = Field(
        default=None, description="Exact statement made by the previous speaker"
    )
    unresolved_argument: Optional[str] = Field(
        default=None, description="The active point of contention awaiting reply"
    )
    relevant_evidence: Optional[list[str]] = Field(
        default_factory=list, description="Specific evidence items relevant to current issue"
    )
    relevant_witnesses: Optional[list[str]] = Field(
        default_factory=list, description="Specific witnesses relevant to current issue"
    )
    relevant_exhibits: Optional[list[str]] = Field(
        default_factory=list, description="Specific exhibits relevant to current issue"
    )
    applicable_law: Optional[list[str]] = Field(
        default_factory=list, description="Applicable statutory provisions for current issue"
    )
    turn_in_issue: int = Field(
        default=0, description="Debate turn within the current issue: 0=Judge intro, 1=Pros arg, 2=Def challenge, 3=Pros reply, 4=Def reply, 5=Judge close/next"
    )
    issue_index: int = Field(
        default=0, description="Index of the current issue being addressed"
    )
    concluded_issues: list[str] = Field(
        default_factory=list, description="List of issues already closed by the Judge"
    )
    next_speaker: Optional[str] = Field(
        default=None, description="Routing flag for the live hearing loop"
    )
    transcript: Annotated[list[dict[str, Any]], operator.add] = Field(
        default_factory=list, description="List of dicts representing the turn-by-turn courtroom conversation"
    )

    # 7. Audit & Resilience
    errors: Annotated[list[CourtError], operator.add] = Field(
        default_factory=list, description="Explicit record of node failures"
    )
    execution_log: Annotated[list[ExecutionLogEntry], operator.add] = Field(
        default_factory=list, description="Ordered audit log of graph execution"
    )
    execution_report: Optional[ExecutionReport] = Field(
        default=None, description="Execution report containing trial audit and output file paths"
    )

    @model_validator(mode="before")
    @classmethod
    def enforce_blind_evaluation(cls, data: Any) -> Any:
        if isinstance(data, dict):
            validate_no_forbidden_keys(data)
            if "case_packet" in data and isinstance(data["case_packet"], (str, Path)):
                validate_case_packet_path(data["case_packet"])
                validate_no_ground_truth_text(str(data["case_packet"]))
        return data

    @property
    def case_id(self) -> Optional[str]:
        if self.execution_report:
            return self.execution_report.case_id
        if self.case_analysis:
            return self.case_analysis.case_id
        return None

    @property
    def status(self) -> str:
        if self.execution_report:
            return self.execution_report.status
        return "completed" if self.judgment else "pending"

    @property
    def ai_judgment(self) -> Optional[Judgment]:
        return self.judgment

    @property
    def agent_statuses(self) -> dict[str, str]:
        if self.execution_report:
            return self.execution_report.agent_statuses
        return {}

    @property
    def output_dir(self) -> Optional[str]:
        if self.execution_report:
            return self.execution_report.output_dir
        return None

    @property
    def execution_time_seconds(self) -> float:
        if self.execution_report:
            return self.execution_report.execution_time_seconds
        return 0.0
