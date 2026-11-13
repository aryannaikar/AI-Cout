"""
Configurable Scoring Engine for Phase 5 — AI Court Judgment Comparison Engine.
Computes the fixed seven-dimensional core benchmark and derives
the weighted overall score. Strictly avoids verdict-only bias.
Supports dynamic exclusion of non-assessable / insufficient data categories.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from app.comparison.schemas import ComparisonScores

logger = logging.getLogger(__name__)


class ComparisonScoringConfig:
    """Fixed Phase 5 core benchmark weights; diagnostic scores are not weighted."""

    DEFAULT_WEIGHTS: Dict[str, float] = {
        "verdict_alignment": 0.20,
        "reasoning_alignment": 0.25,
        "factual_accuracy": 0.15,
        "issue_alignment": 0.10,
        "evidence_alignment": 0.15,
        "charge_alignment": 0.10,
        "final_order_alignment": 0.05,
    }

    @classmethod
    def get_weights(cls, custom_weights: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """Return the exact benchmark weights; caller overrides cannot change the rubric."""
        if custom_weights and custom_weights != cls.DEFAULT_WEIGHTS:
            logger.warning("Custom comparison weights are ignored; Phase 5 uses the fixed seven-dimension rubric.")
        return dict(cls.DEFAULT_WEIGHTS)


class ScoringEngine:
    """
    Calculates dimension scores and computes balanced, non-verdict-dominated overall score.
    Dynamically excludes unassessable / insufficient data categories from the denominator.
    """

    def __init__(self, custom_weights: Optional[Dict[str, float]] = None):
        self.weights = ComparisonScoringConfig.get_weights(custom_weights)

    def calculate_scores(
        self,
        verdict_alignment: float,
        issue_alignment: float,
        factual_accuracy: float,
        charge_alignment: float,
        witness_alignment: float,
        evidence_alignment: float,
        legal_alignment: float,
        reasoning_alignment: float,
        finding_alignment: float,
        final_order_alignment: float,
        assessability: Optional[Dict[str, bool]] = None,
    ) -> ComparisonScores:
        """
        Compute weighted overall score, separating pure verdict from substantive legal quality.
        When a category is unassessable (e.g. insufficient data in Ground Truth summary),
        it is excluded from the active weighted denominator and reported.
        """
        # Findings are merged into Charge Alignment by ComparisonService. Keep
        # the diagnostic fields available in the report, but exclude them from
        # the core benchmark to avoid counting the same finding twice.
        scores_map = {
            "verdict_alignment": float(verdict_alignment),
            "reasoning_alignment": float(reasoning_alignment),
            "factual_accuracy": float(factual_accuracy),
            "issue_alignment": float(issue_alignment),
            "evidence_alignment": float(evidence_alignment),
            "charge_alignment": float(charge_alignment),
            "final_order_alignment": float(final_order_alignment),
        }
        diagnostic_scores = {
            "finding_alignment": float(finding_alignment),
            "witness_alignment": float(witness_alignment),
            "legal_alignment": float(legal_alignment),
        }

        assess_map = assessability or {}
        active_weights: Dict[str, float] = {}
        excluded_categories: List[str] = []

        # Filter assessable dimensions
        active_raw_weight_sum = 0.0
        for dim in scores_map:
            is_assessable = assess_map.get(dim, True)
            if is_assessable:
                active_raw_weight_sum += self.weights.get(dim, 0.0)
            else:
                excluded_categories.append(dim)

        if active_raw_weight_sum > 0:
            for dim in scores_map:
                if dim not in excluded_categories:
                    active_weights[dim] = self.weights.get(dim, 0.0) / active_raw_weight_sum
        else:
            active_weights = {}

        # Weighted calculation across assessable categories
        overall = sum(scores_map[k] * active_weights.get(k, 0.0) for k in active_weights)
        overall = max(0.0, min(100.0, round(overall, 2)))

        # Substantive score: all assessable categories EXCLUDING verdict
        substantive_dims = [k for k in active_weights if k != "verdict_alignment"]
        substantive_weight_sum = sum(active_weights[k] for k in substantive_dims)
        if substantive_weight_sum > 0:
            substantive_score = sum(scores_map[k] * active_weights[k] for k in substantive_dims) / substantive_weight_sum
            substantive_score = max(0.0, min(100.0, round(substantive_score, 2)))
        else:
            substantive_score = None

        formula = (
            f"Overall Score = sum(assessable core score * fixed weight) / sum(assessable fixed weights). "
            f"Active weight denominator: {round(active_raw_weight_sum * 100, 1)}% of total. "
            f"Excluded non-assessable categories: {', '.join(excluded_categories) if excluded_categories else 'None'}."
        )

        return ComparisonScores(
            verdict_alignment=round(scores_map["verdict_alignment"], 2),
            issue_alignment=round(scores_map["issue_alignment"], 2),
            factual_accuracy=round(scores_map["factual_accuracy"], 2),
            charge_alignment=round(scores_map["charge_alignment"], 2),
            witness_alignment=round(diagnostic_scores["witness_alignment"], 2),
            evidence_alignment=round(scores_map["evidence_alignment"], 2),
            legal_alignment=round(diagnostic_scores["legal_alignment"], 2),
            reasoning_alignment=round(scores_map["reasoning_alignment"], 2),
            finding_alignment=round(diagnostic_scores["finding_alignment"], 2),
            final_order_alignment=round(scores_map["final_order_alignment"], 2),
            overall_score=overall,
            weights=self.weights,
            substantive_score=substantive_score,
            verdict_score=round(scores_map["verdict_alignment"], 2),
            active_weights=active_weights,
            active_weight_denominator=active_raw_weight_sum,
            excluded_categories=excluded_categories,
            scoring_formula=formula,
        )
