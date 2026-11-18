"""
Independent Devil's Advocate Scrutiny Agent for Phase 3 Judicial Reasoning.
Challenges a draft Judgment for accused-attribution gaps, unaddressed contradictions,
burden-of-proof reversals, uncorroborated co-accused/recovery inferences, and
merged connected proceedings without automatically reversing the verdict.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Optional

from app.models.case_models import StructuredCase
from app.models.conflict_models import ConflictReport
from app.models.evidence_models import EvidenceAnalysisReport
from app.models.judgment_models import (
    DevilsAdvocateReport,
    IngredientChecklist,
    Judgment,
    ScrutinyChallenge,
)
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class DevilsAdvocateScrutiny:
    """
    Independent judicial scrutiny reviewer.
    Configurable via ENABLE_DEVILS_ADVOCATE / enable_llm; never adds unbounded retry loops.
    """

    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        enable_llm: Optional[bool] = None,
    ):
        self.llm_service = llm_service
        if enable_llm is None:
            self.enable_llm = os.getenv("ENABLE_DEVILS_ADVOCATE_LLM", "false").lower() in {"1", "true", "yes"}
        else:
            self.enable_llm = enable_llm

    def review(
        self,
        draft: Judgment,
        case: StructuredCase,
        evidence_report: EvidenceAnalysisReport,
        conflict_report: ConflictReport,
        checklists: list[IngredientChecklist],
    ) -> DevilsAdvocateReport:
        """Review the draft judgment and return structured challenges."""
        challenges: list[ScrutinyChallenge] = []
        idx = 1

        # 1. Connected proceedings & multi-accused coverage check
        subjects = case.distinct_decision_subjects() if hasattr(case, "distinct_decision_subjects") else list(case.accused)
        if len(subjects) > 1 or len(getattr(case, "connected_proceedings", [])) > 1:
            covered = {af.accused_name.strip().casefold() for af in draft.accused_findings}
            missing_subjects = [s for s in subjects if s.strip().casefold() not in covered]
            if missing_subjects:
                challenges.append(
                    ScrutinyChallenge(
                        challenge_id=f"DA-{idx:02d}",
                        category="merged_or_missing_accused_findings",
                        severity="high",
                        description=(
                            f"Case involves {len(subjects)} distinct decision subjects, but accused_findings "
                            f"omits separate findings for: {', '.join(missing_subjects)}."
                        ),
                        affected_accused_or_charge=", ".join(missing_subjects),
                        recommendation="Render separate accused_findings for each distinct accused and connected proceeding.",
                    )
                )
                idx += 1

        # 2. Burden-of-proof reversal check
        full_text = f"{draft.evidence_assessment} {draft.reasons}".casefold()
        if re.search(r"\b(?:accused failed to prove (?:his |their )?innocence|burden lies on the accused to disprove)\b", full_text):
            challenges.append(
                ScrutinyChallenge(
                    challenge_id=f"DA-{idx:02d}",
                    category="burden_of_proof_reversal",
                    severity="high",
                    description="Draft contains language suggesting an improper shift of initial burden of proof onto the accused.",
                    recommendation="Verify that the prosecution discharged its initial burden beyond reasonable doubt.",
                )
            )
            idx += 1

        # 3. Recovery / co-accused statement treated as automatic guilt
        if draft.final_decision in {"CONVICTION", "PARTIAL CONVICTION"}:
            if re.search(r"\b(?:mere recovery|mere possession)\b", full_text) and "knowledge" not in full_text:
                challenges.append(
                    ScrutinyChallenge(
                        challenge_id=f"DA-{idx:02d}",
                        category="unsupported_recovery_inference",
                        severity="high",
                        description="Conviction relies on recovery/possession without explicitly establishing guilty knowledge or link to offence.",
                        recommendation="Analyze whether conscious possession and statutory mens rea are proved beyond reasonable doubt.",
                    )
                )
                idx += 1

        # 4. Unaddressed high/fatal conflicts
        if conflict_report.critical_conflicts_count > 0:
            addressed = any(
                w in full_text for w in ("contradict", "conflict", "discrepanc", "gap", "doubt", "inconsisten")
            )
            if not addressed:
                challenges.append(
                    ScrutinyChallenge(
                        challenge_id=f"DA-{idx:02d}",
                        category="unaddressed_material_contradictions",
                        severity="high",
                        description=(
                            f"ConflictReport flags {conflict_report.critical_conflicts_count} critical conflict(s) "
                            "that are not explicitly addressed in evidence_assessment or reasons."
                        ),
                        recommendation="Address each material contradiction and explain its impact on reasonable doubt.",
                    )
                )
                idx += 1

        # 5. Conviction despite Not established / Not assessable ingredients
        if draft.final_decision == "CONVICTION" and checklists:
            unproved = [
                f"{cl.charge_key} ({item.ingredient_id})"
                for cl in checklists
                for item in cl.ingredients
                if item.assessment_status in {"Not established", "Not assessable"}
            ]
            if unproved:
                challenges.append(
                    ScrutinyChallenge(
                        challenge_id=f"DA-{idx:02d}",
                        category="missing_statutory_ingredients",
                        severity="high",
                        description=f"Draft returns CONVICTION while statutory ingredients remain unproved/unassessable: {', '.join(unproved[:5])}.",
                        affected_accused_or_charge=unproved[0],
                        recommendation="Re-examine whether every statutory ingredient is established beyond reasonable doubt.",
                    )
                )
                idx += 1

        llm_used = False
        if self.enable_llm and self.llm_service is not None:
            try:
                llm_prompt = (
                    "Review this draft Indian criminal judgment as an independent Devil's Advocate. "
                    "Challenge any unsupported inference, burden reversal, merged accused, or unaddressed contradiction. "
                    "Do NOT reverse the verdict automatically; return a DevilsAdvocateReport JSON.\n"
                    + json.dumps({
                        "case_title": case.case_title,
                        "decision_subjects": subjects,
                        "draft_decision": draft.final_decision,
                        "draft_reasons": draft.reasons[:1500],
                        "critical_conflicts": conflict_report.critical_conflicts_count,
                    }, ensure_ascii=False)
                )
                llm_rep = self.llm_service.generate_structured(
                    prompt=llm_prompt,
                    response_schema=DevilsAdvocateReport,
                    system_prompt="You are an independent judicial scrutiny reviewer checking for legal and evidentiary rigor.",
                )
                llm_used = True
                for c in llm_rep.challenges:
                    challenges.append(c)
            except Exception as exc:
                logger.warning("Optional LLM Devil's Advocate scrutiny skipped: %s", exc)

        requires_revision = any(c.severity == "high" for c in challenges)
        summary = (
            f"Scrutiny raised {len(challenges)} challenge(s) (requires_revision={requires_revision})."
            if challenges
            else "Scrutiny found no structural or burden-of-proof defects in the draft judgment."
        )
        return DevilsAdvocateReport(
            reviewed=True,
            requires_revision=requires_revision,
            challenges=challenges,
            summary=summary,
            llm_used=llm_used,
        )
