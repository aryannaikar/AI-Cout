"""
LangGraph Courtroom Orchestration Package for AI Court of India.
Provides state definition, nodes, parallel workflow topology, and run_court entry point.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure backend directory is in sys.path
_backend_dir = str(Path(__file__).resolve().parents[2])
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app.graph.state import (
    CourtError,
    CourtState,
    ExecutionLogEntry,
    JudgeInput,
)
from app.graph.validation import BlindEvaluationViolation
from app.graph.workflow import CourtWorkflow, create_court_graph, run_court
from app.models.execution_models import ExecutionReport
from app.services.judgment_writer import JudgmentWriter

__all__ = [
    "CourtState",
    "JudgeInput",
    "CourtError",
    "ExecutionLogEntry",
    "BlindEvaluationViolation",
    "create_court_graph",
    "CourtWorkflow",
    "run_court",
    "ExecutionReport",
    "JudgmentWriter",
]
