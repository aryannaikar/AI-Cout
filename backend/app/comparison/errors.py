"""
Error definitions for Phase 5 — AI Court Judgment Comparison Engine.
"""

from __future__ import annotations


class ComparisonError(Exception):
    """Base exception for all comparison engine errors."""
    pass


class AIJudgmentNotFoundError(ComparisonError):
    """Raised when an AI Judgment file or object is missing for a case."""
    pass


class RealJudgmentNotFoundError(ComparisonError):
    """Raised when an authoritative Real Court Judgment is missing."""
    pass


class InvalidJudgmentFormatError(ComparisonError):
    """Raised when an uploaded document cannot be parsed into a judgment representation."""
    pass


class GroundTruthSecurityViolation(ComparisonError, PermissionError):
    """Raised when Ground Truth / Real Court Judgment is illegally injected into the courtroom graph."""
    pass
