"""
Pydantic data models for execution reporting and trial audit in AI Court of India.
Provides structured summary of the courtroom run and links to generated judgment artifacts.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Literal, Optional

# Ensure backend directory is in sys.path
_backend_dir = str(Path(__file__).resolve().parents[2])
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.graph.state import CourtError, ExecutionLogEntry
from app.graph.validation import validate_no_forbidden_keys
from app.models.judgment_models import Judgment


class ExecutionReport(BaseModel):
    """
    Exhaustive execution summary of the AI Courtroom trial.
    Contains timing, node statuses, error tracking, and links to persisted judgment files.
    Strictly forbids ground truth evaluation data.
    """

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(description="Case identifier.")
    status: Literal["completed", "failed", "partial"] = Field(
        default="completed", description="Overall execution status."
    )
    ai_judgment: Optional[Judgment] = Field(
        default=None, description="Generated 12-section AI judgment."
    )
    execution_log: list[ExecutionLogEntry] = Field(
        default_factory=list, description="Audit log of all node executions."
    )
    agent_statuses: dict[str, str] = Field(
        default_factory=dict, description="Status breakdown per agent role."
    )
    errors: list[CourtError] = Field(
        default_factory=list, description="Explicit record of any errors encountered."
    )
    execution_time_seconds: float = Field(
        default=0.0, description="Total execution time in seconds."
    )
    output_dir: Optional[str] = Field(
        default=None, description="Directory where judgment artifacts are saved."
    )
    json_path: Optional[str] = Field(
        default=None, description="Path to ai_judgment.json."
    )
    text_path: Optional[str] = Field(
        default=None, description="Path to ai_judgment.txt."
    )
    pdf_path: Optional[str] = Field(
        default=None, description="Path to ai_judgment.pdf."
    )

    @model_validator(mode="before")
    @classmethod
    def validate_security(cls, data: Any) -> Any:
        if isinstance(data, dict):
            validate_no_forbidden_keys(data)
        return data
