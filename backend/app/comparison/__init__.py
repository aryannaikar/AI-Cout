"""
AI Court of India — Phase 5 Judgment Comparison Engine.
Provides substantive legal content, ratio decidendi, and epistemic error comparison
between AI Court judgments and authoritative Real Court judgments.
"""

from app.comparison.comparator import JudgmentComparator
from app.comparison.errors import (
    AIJudgmentNotFoundError,
    CaseIdentityMismatchError,
    ComparisonError,
    GroundTruthSecurityViolation,
    InvalidJudgmentFormatError,
    RealJudgmentNotFoundError,
)
from app.comparison.extractor import JudgmentNormalizer
from app.comparison.loaders import ComparisonDocumentLoader
from app.comparison.report_generator import ComparisonReportGenerator
from app.comparison.schemas import (
    ComparisonErrorDetail,
    ComparisonReport,
    ComparisonScores,
    NormalizedJudgment,
    OperativeVerdict,
)
from app.comparison.scoring import ComparisonScoringConfig, ScoringEngine
from app.comparison.service import ComparisonService

__all__ = [
    "ComparisonService",
    "JudgmentComparator",
    "JudgmentNormalizer",
    "ComparisonDocumentLoader",
    "ComparisonReportGenerator",
    "ScoringEngine",
    "ComparisonScoringConfig",
    "ComparisonReport",
    "ComparisonScores",
    "ComparisonErrorDetail",
    "NormalizedJudgment",
    "OperativeVerdict",
    "ComparisonError",
    "AIJudgmentNotFoundError",
    "CaseIdentityMismatchError",
    "RealJudgmentNotFoundError",
    "InvalidJudgmentFormatError",
    "GroundTruthSecurityViolation",
]
