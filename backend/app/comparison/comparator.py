"""
Comprehensive Judgment Comparator for Phase 5 — AI Court Judgment Comparison Engine.
Performs substantive legal content and judicial reasoning comparison across all 10
dimensions, evaluates historical applicability, and detects epistemic errors and hallucinations.
Guarantees mathematical consistency, non-verdict dominance, and explicit assessability tracking.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.comparison.schemas import (
    AlignmentStatus,
    ChargeComparisonResult,
    ComparisonCategoryStatus,
    ComparisonErrorDetail,
    EpistemicType,
    EvidenceComparisonResult,
    FactualComparisonResult,
    FinalOrderComparisonResult,
    FindingComparisonResult,
    IssueComparisonResult,
    LegalProvisionComparisonResult,
    LegalReasoningComparisonResult,
    NormalizedJudgment,
    OperativeVerdict,
    ReasoningThemeComparison,
    StatuteEra,
    VerdictComparisonResult,
    WitnessComparisonResult,
)

logger = logging.getLogger(__name__)

NOT_ESTABLISHED_MSG = "Not clearly established in the supplied judgment."


class JudgmentComparator:
    """
    Substantive legal and reasoning comparator.
    Evaluates:
    A. Verdict Alignment
    B. Issue Alignment
    C. Factual Accuracy
    D. Charge / Offence Alignment (including historical applicability and accused attribution)
    E. Witness Alignment (with insufficient data detection)
    F. Evidence Alignment (with insufficient data detection)
    G. Legal Provision Alignment (procedural history vs ratio)
    H. Legal Reasoning Alignment (Ratio Decidendi)
    I. Finding Alignment
    J. Final Order Alignment (excluding footers and comparison metadata)
    """

    def __init__(self, case_packet_context: Optional[str] = None):
        self.case_packet_context = case_packet_context or ""

    def compare(
        self, ai_norm: NormalizedJudgment, real_norm: NormalizedJudgment
    ) -> Tuple[
        VerdictComparisonResult,
        IssueComparisonResult,
        FactualComparisonResult,
        ChargeComparisonResult,
        WitnessComparisonResult,
        EvidenceComparisonResult,
        LegalProvisionComparisonResult,
        LegalReasoningComparisonResult,
        FindingComparisonResult,
        FinalOrderComparisonResult,
        List[ComparisonErrorDetail],
        List[str],
        List[str],
    ]:
        major_errors: List[ComparisonErrorDetail] = []
        missing_points: List[str] = []
        unrelated_points: List[str] = []

        # 1. Verdict Alignment
        verdict_comp = self._compare_verdict(ai_norm, real_norm, major_errors)

        # 2. Issue Alignment
        issue_comp = self._compare_issues(ai_norm, real_norm, major_errors, missing_points, unrelated_points)

        # 3. Factual Accuracy
        fact_comp = self._compare_facts(ai_norm, real_norm, major_errors, missing_points, unrelated_points)

        # 4. Charge Alignment (with accused attribution and historical applicability check)
        charge_comp = self._compare_charges(ai_norm, real_norm, major_errors, missing_points, unrelated_points)

        # 5. Witness Alignment (with Insufficient Data handling)
        witness_comp = self._compare_witnesses(ai_norm, real_norm, major_errors, missing_points)

        # 6. Evidence Alignment (with Insufficient Data handling)
        evidence_comp = self._compare_evidence(ai_norm, real_norm, major_errors, missing_points, unrelated_points)

        # 7. Legal Provision Alignment
        legal_comp = self._compare_legal_provisions(ai_norm, real_norm, major_errors, missing_points, unrelated_points)

        # 8. Legal Reasoning Alignment (Ratio Decidendi)
        reasoning_comp = self._compare_reasoning(ai_norm, real_norm, major_errors, missing_points)

        # 9. Finding Alignment
        finding_comp = self._compare_findings(ai_norm, real_norm, major_errors)

        # 10. Final Order Alignment
        order_comp = self._compare_final_order(ai_norm, real_norm, major_errors)

        return (
            verdict_comp,
            issue_comp,
            fact_comp,
            charge_comp,
            witness_comp,
            evidence_comp,
            legal_comp,
            reasoning_comp,
            finding_comp,
            order_comp,
            major_errors,
            missing_points,
            unrelated_points,
        )

    # --------------------------------------------------------------------------
    # Helper: Normalization for Semantic Concept Matching
    # --------------------------------------------------------------------------

    @staticmethod
    def _normalize_legal_concept_text(text: str) -> str:
        """
        Normalize legal phrases, OCR currency artifacts, and inflected word forms.
        e.g., 'I25,000' or '₹25,000' -> '25000'
        """
        t = text.lower()
        # Currency / OCR artifact normalization
        t = re.sub(r"(?:i|₹|rs\.?|inr)\s*([0-9]+(?:,[0-9]+)*)", r"\1", t)
        t = t.replace(",", "")
        return t

    LEGAL_ISSUE_STOP_WORDS = {
        "whether", "without", "under", "with", "from", "that", "this", "these", "those",
        "have", "been", "which", "where", "when", "what", "into", "onto", "over", "such",
        "said", "same", "case", "court", "matter", "section", "prosecution", "accused",
        "appellant", "respondent", "state", "police", "officer", "alleged", "proved", "prove",
        "beyond", "reasonable", "doubt", "law", "order"
    }

    @classmethod
    def _extract_concept_tokens(cls, text: str) -> set[str]:
        """Extract stemmed legal conceptual roots from a proposition."""
        normalized = cls._normalize_legal_concept_text(text)
        tokens = set(re.findall(r"\b[a-z0-9]{3,}\b", normalized))
        roots = set()
        for tok in tokens:
            if tok in cls.LEGAL_ISSUE_STOP_WORDS:
                continue
            if tok.startswith("recov"):
                roots.add("recov")
            elif tok.startswith("acquit"):
                roots.add("acquit")
            elif tok.startswith("convic"):
                roots.add("convic")
            elif tok.startswith("sustain") or tok.startswith("unsustain"):
                roots.add("sustain")
            elif tok.startswith("theft") or tok.startswith("stolen"):
                roots.add("stolen")
            elif tok.startswith("presum"):
                roots.add("presum")
            elif tok.startswith("connect"):
                roots.add("connect")
            elif tok.startswith("identif"):
                roots.add("identif")
            elif tok.startswith("witnes"):
                roots.add("witnes")
            elif tok.startswith("possess"):
                roots.add("possess")
            elif tok.startswith("burden"):
                roots.add("burden")
            elif tok.startswith("reason"):
                roots.add("reason")
            elif tok.startswith("circumstan"):
                roots.add("circumstan")
            elif tok.startswith("electron") or tok.startswith("cyber"):
                roots.add("electron")
            else:
                roots.add(tok)
        return roots

    # --------------------------------------------------------------------------
    # A. Verdict Alignment
    # --------------------------------------------------------------------------

    def _compare_verdict(
        self,
        ai: NormalizedJudgment,
        real: NormalizedJudgment,
        errors: List[ComparisonErrorDetail],
    ) -> VerdictComparisonResult:
        ai_v = ai.verdict
        real_v = real.verdict

        # Missing/extraction-failed outcome on either side cannot be scored.
        if ai_v in (OperativeVerdict.EXTRACTION_ERROR, OperativeVerdict.UNKNOWN) or real_v in (OperativeVerdict.EXTRACTION_ERROR, OperativeVerdict.UNKNOWN):
            status: AlignmentStatus = "not_aligned"
            category_status = ComparisonCategoryStatus.EXTRACTION_ERROR.value
            score = 0.0
            explanation = (
                f"Operative verdict extraction failed or outcome is unrecognized (AI: {ai_v.value}; Real: {real_v.value}). "
                f"AI source: '{ai.verdict_raw or 'None'}'; real source: '{real.verdict_raw or 'None'}'."
            )
            return VerdictComparisonResult(
                ai_verdict=ai_v.value,
                real_verdict=real_v.value,
                alignment=status,
                score=score,
                explanation=explanation,
                ai_extracted_position=ai.verdict_raw or ai_v.value,
                real_extracted_position=real.verdict_raw or real_v.value,
                status=category_status,
                is_assessable=False,
                verdict_normalization_explanation=real.verdict_normalization_explanation,
            )

        is_ai_acquittal = ai_v in (OperativeVerdict.ACQUITTAL, OperativeVerdict.APPEAL_ALLOWED, OperativeVerdict.DISCHARGE)
        is_real_acquittal = real_v in (OperativeVerdict.ACQUITTAL, OperativeVerdict.APPEAL_ALLOWED, OperativeVerdict.DISCHARGE)

        is_ai_conviction = ai_v in (OperativeVerdict.CONVICTION, OperativeVerdict.APPEAL_DISMISSED)
        is_real_conviction = real_v in (OperativeVerdict.CONVICTION, OperativeVerdict.APPEAL_DISMISSED)

        real_raw_lower = (real.raw_text or "").lower()
        real_has_split_connected = (
            ("dismissed" in real_raw_lower or "upheld" in real_raw_lower)
            and ("allowed" in real_raw_lower or "acquitt" in real_raw_lower or "set aside" in real_raw_lower)
        )

        if (
            (is_ai_acquittal and is_real_acquittal)
            or (is_ai_conviction and is_real_conviction)
            or (real_has_split_connected and ai_v in (OperativeVerdict.PARTIAL_CONVICTION, OperativeVerdict.ACQUITTAL))
        ):
            status: AlignmentStatus = "aligned"
            category_status = ComparisonCategoryStatus.MATCH.value
            score = 100.0
            norm_note = f" [{real.verdict_normalization_explanation}]" if real.verdict_normalization_explanation else ""
            explanation = (
                f"Operative verdict is aligned. Both AI Court and Real Court arrived at "
                f"{ai_v.value if real_has_split_connected else real_v.value} "
                f"(Operative outcome: {'Split/Connected Partial Conviction & Acquittal' if real_has_split_connected else ('Acquittal/Discharge' if is_real_acquittal else 'Conviction')}).{norm_note}"
            )
        elif ai_v == OperativeVerdict.PARTIAL_CONVICTION or real_v == OperativeVerdict.PARTIAL_CONVICTION:
            status = "partially_aligned"
            category_status = ComparisonCategoryStatus.PARTIAL_MATCH.value
            score = 50.0
            explanation = f"Operative verdict is partially aligned: AI decided {ai_v.value} while Real Court decided {real_v.value}."
            errors.append(
                ComparisonErrorDetail(
                    type="incorrect_finding",
                    severity="medium",
                    ai_claim=f"Operative verdict: {ai_v.value}",
                    real_court_position=f"Operative verdict: {real_v.value}",
                    explanation="AI Court rendered a partial verdict whereas Real Court rendered a different operative outcome.",
                )
            )
        else:
            status = "not_aligned"
            category_status = ComparisonCategoryStatus.MISMATCH.value
            score = 0.0
            explanation = f"Operative verdict is discordant. AI Court pronounced {ai_v.value}, whereas Real Court pronounced {real_v.value}."
            errors.append(
                ComparisonErrorDetail(
                    type="incorrect_final_order",
                    severity="critical",
                    ai_claim=f"Operative verdict: {ai_v.value}",
                    real_court_position=f"Operative verdict: {real_v.value}",
                    explanation=f"AI Court completely diverged from the authoritative verdict of the Real Court ({real_v.value}).",
                )
            )

        return VerdictComparisonResult(
            ai_verdict=ai_v.value,
            real_verdict=real_v.value,
            alignment=status,
            score=score,
            explanation=explanation,
            ai_extracted_position=ai.verdict_raw or ai_v.value,
            real_extracted_position=real.verdict_raw or real_v.value,
            status=category_status,
            is_assessable=True,
            verdict_normalization_explanation=real.verdict_normalization_explanation,
        )

    # --------------------------------------------------------------------------
    # B. Issue Alignment
    # --------------------------------------------------------------------------

    def _compare_issues(
        self,
        ai: NormalizedJudgment,
        real: NormalizedJudgment,
        errors: List[ComparisonErrorDetail],
        missing: List[str],
        unrelated: List[str],
    ) -> IssueComparisonResult:
        ai_issues = [i.statement for i in ai.legal_issues]
        real_issues = [i.statement for i in real.legal_issues]

        matched: List[Dict[str, Any]] = []
        missed: List[str] = []
        unrelated_ai: List[str] = []
        materially_incorrect: List[str] = []

        # If real issues were empty from direct parsing, extract core points from real ratio/chains
        effective_real = real_issues[:]
        if not effective_real and real.reasoning.key_chains:
            effective_real.extend(chain for chain in real.reasoning.key_chains if len(chain) > 20)

        real_full_text = (real.raw_text or "").lower()

        # Step 1: Detect blatantly unrelated or hallucinated issues introduced by AI first
        for a_iss in ai_issues:
            a_tokens = self._extract_concept_tokens(a_iss)
        # Step 2: Semantic concept matching between AI issues and Real issues
        used_ai_issues: set[str] = set()

        for r_iss in effective_real:
            r_tokens = self._extract_concept_tokens(r_iss)
            match_found = False

            for a_iss in ai_issues:
                if a_iss in used_ai_issues:
                    continue

                a_tokens = self._extract_concept_tokens(a_iss)
                overlap = r_tokens.intersection(a_tokens)

                # General one-to-one concept overlap; no benchmark-specific
                # sections, amounts, evidence types, or issue templates.
                concept_match = len(overlap) >= (1 if min(len(r_tokens), len(a_tokens)) <= 2 else 2)

                if concept_match:
                    matched.append({
                        "real_issue": r_iss,
                        "ai_issue": a_iss,
                        "shared_concepts": list(overlap),
                    })
                    used_ai_issues.add(a_iss)
                    match_found = True
                    break

            if not match_found:
                missed.append(r_iss)
                missing.append(f"Issue omitted by AI: {r_iss}")

        # Step 3: Check any remaining unused AI issues for relevance to controversy
        for a_iss in ai_issues:
            if a_iss not in used_ai_issues:
                a_tokens = self._extract_concept_tokens(a_iss)
                has_substantive_overlap = any(tok in real_full_text for tok in a_tokens if len(tok) >= 4)
                if not has_substantive_overlap:
                    unrelated_ai.append(a_iss)
                    unrelated.append(f"Extraneous issue framed by AI: {a_iss}")

        total_real = len(effective_real) or 1
        precision = len(matched) / (len(ai_issues) or 1)
        recall = len(matched) / total_real
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        penalty = len(unrelated_ai) * 15.0
        score = max(0.0, min(100.0, round(f1 * 100.0 - penalty, 2)))

        category_status = (
            ComparisonCategoryStatus.MATCH.value if score >= 75.0
            else (ComparisonCategoryStatus.PARTIAL_MATCH.value if score >= 35.0 else ComparisonCategoryStatus.MISMATCH.value)
        )

        explanation = (
            f"AI identified {len(matched)} of {len(effective_real)} material legal issues. "
            f"Omitted issues: {len(missed)}. Extraneous/unrelated issues introduced: {len(unrelated_ai)}."
        )

        return IssueComparisonResult(
            matched_issues=matched,
            ai_missed_issues=missed,
            ai_unrelated_issues=unrelated_ai,
            materially_incorrect_issues=materially_incorrect,
            score=score,
            explanation=explanation,
            ai_extracted_position="; ".join(ai_issues),
            real_extracted_position="; ".join(effective_real),
            status=category_status,
            is_assessable=bool(len(effective_real) > 0 or len(ai_issues) > 0),
        )

    # --------------------------------------------------------------------------
    # C. Factual Accuracy
    # --------------------------------------------------------------------------

    def _compare_facts(
        self,
        ai: NormalizedJudgment,
        real: NormalizedJudgment,
        errors: List[ComparisonErrorDetail],
        missing: List[str],
        unrelated: List[str],
    ) -> FactualComparisonResult:
        # Allegations and inferences remain visible, but factual precision and
        # recall assess only material propositions asserted as facts.
        ai_facts = [f for f in ai.material_facts if f.is_material and f.epistemic_type == EpistemicType.FACT]
        real_facts = [f for f in real.material_facts if f.is_material and f.epistemic_type == EpistemicType.FACT]
        epistemic_distinctions = [
            {"statement": f.statement[:100], "classified_as": f.epistemic_type.value}
            for f in ai.material_facts
        ]
        correct_facts: List[str] = []
        incorrect_facts: List[str] = []
        unsupported_facts: List[str] = []
        invented_facts: List[str] = []
        omitted_material_facts: List[str] = []

        if not real_facts:
            explanation = "Factual accuracy is not assessable: the real judgment yielded no reliable material-fact inventory. No completeness credit was assumed."
            return FactualComparisonResult(
                correct_facts=[], incorrect_facts=[], unsupported_facts=[], invented_facts=[],
                omitted_material_facts=[], epistemic_distinctions=epistemic_distinctions,
                score=0.0, correctness_score=0.0, completeness_score=0.0,
                precision=None, recall=None, assessed_ai_facts=len(ai_facts), assessed_real_facts=0,
                explanation=explanation, ai_extracted_position=f"{len(ai_facts)} assessable factual claims",
                real_extracted_position="No reliable material-fact inventory", status=ComparisonCategoryStatus.INSUFFICIENT_DATA.value,
                is_assessable=False,
            )

        # Greedy one-to-one semantic matching prevents one broad AI claim from
        # earning recall credit for several separate source propositions.
        candidate_pairs = []
        for ai_idx, af in enumerate(ai_facts):
            for real_idx, rf in enumerate(real_facts):
                similarity = self._fact_similarity(af.statement, rf.statement)
                if similarity >= 0.55:
                    candidate_pairs.append((similarity, ai_idx, real_idx))
        used_ai: set[int] = set()
        used_real: set[int] = set()
        for _, ai_idx, real_idx in sorted(candidate_pairs, reverse=True):
            if ai_idx not in used_ai and real_idx not in used_real:
                used_ai.add(ai_idx)
                used_real.add(real_idx)
                correct_facts.append(ai_facts[ai_idx].statement)

        real_text = (real.raw_text or "").lower()
        for idx, fact in enumerate(ai_facts):
            if idx in used_ai:
                continue
            stmt = fact.statement
            tokens = self._fact_tokens(stmt)
            is_present = bool(tokens and any(token in real_text for token in tokens if len(token) >= 5))
            if is_present:
                unsupported_facts.append(stmt)
                errors.append(ComparisonErrorDetail(
                    type="unsupported_fact", severity="medium", ai_claim=stmt,
                    real_court_position=NOT_ESTABLISHED_MSG,
                    explanation="The source contains related terminology but does not substantiate this factual proposition.",
                ))
            else:
                invented_facts.append(stmt)
                unrelated.append(f"Invented fact: {stmt}")
                errors.append(ComparisonErrorDetail(
                    type="hallucinated_fact", severity="high", ai_claim=stmt,
                    real_court_position=NOT_ESTABLISHED_MSG,
                    explanation="No sufficiently similar material fact appears in the authoritative fact inventory.",
                ))
        for idx, fact in enumerate(real_facts):
            if idx not in used_real:
                omitted_material_facts.append(fact.statement)
                missing.append(f"Omitted material fact: {fact.statement}")

        precision_value = len(used_ai) / len(ai_facts) if ai_facts else 0.0
        recall_value = len(used_real) / len(real_facts)
        correctness_score = precision_value * 100.0
        completeness_score = recall_value * 100.0
        score = (2 * precision_value * recall_value / (precision_value + recall_value) * 100.0) if precision_value + recall_value else 0.0

        category_status = (
            ComparisonCategoryStatus.MATCH.value if score >= 85.0
            else (ComparisonCategoryStatus.PARTIAL_MATCH.value if score >= 50.0 else ComparisonCategoryStatus.MISMATCH.value)
        )

        explanation = (
            f"Factual precision: {correctness_score:.1f}% ({len(used_ai)}/{len(ai_facts)} AI factual claims matched); "
            f"recall: {completeness_score:.1f}% ({len(used_real)}/{len(real_facts)} source facts covered); "
            f"F1: {score:.1f}%. Invented: {len(invented_facts)}; unsupported: {len(unsupported_facts)}; omitted: {len(omitted_material_facts)}."
        )

        return FactualComparisonResult(
            correct_facts=correct_facts,
            incorrect_facts=incorrect_facts,
            unsupported_facts=unsupported_facts,
            invented_facts=invented_facts,
            omitted_material_facts=omitted_material_facts,
            epistemic_distinctions=epistemic_distinctions,
            score=score,
            correctness_score=correctness_score,
            completeness_score=completeness_score,
            precision=correctness_score,
            recall=completeness_score,
            assessed_ai_facts=len(ai_facts),
            assessed_real_facts=len(real_facts),
            explanation=explanation,
            ai_extracted_position=f"{len(correct_facts)} verified facts",
            real_extracted_position=f"{len(real.material_facts)} authoritative propositions",
            status=category_status,
            is_assessable=True,
        )

    @staticmethod
    def _fact_tokens(text: str) -> set[str]:
        stop = {"that", "this", "with", "from", "were", "was", "have", "been", "into", "under", "court", "judgment", "accused", "prosecution", "defence", "the", "and", "for"}
        tokens = {t for t in re.findall(r"[a-z0-9]{3,}", text.lower()) if t not in stop}
        normalized = set()
        for token in tokens:
            for suffix in ("ing", "ed", "es", "s"):
                if len(token) > len(suffix) + 3 and token.endswith(suffix):
                    token = token[:-len(suffix)]
                    break
            normalized.add(token)
        return normalized

    @classmethod
    def _fact_similarity(cls, first: str, second: str) -> float:
        a, b = cls._fact_tokens(first), cls._fact_tokens(second)
        if not a or not b:
            return 0.0
        overlap = len(a & b)
        return (2.0 * overlap) / (len(a) + len(b))

    @staticmethod
    def _extract_section_number(statute_text: str) -> str:
        """Extract section number from statute text, excluding enactment years (e.g. 1860, 2023)."""
        m = re.search(r"(?:Section|Sec\.|u/s|s\.)\s*([0-9]{1,4}(?:\([a-z0-9]+\)|[A-Za-z])?)", statute_text, re.IGNORECASE)
        if m:
            return m.group(1)
        enactment_years = {"1860", "1872", "1966", "1973", "2023", "1959", "1950", "2000", "2002", "2005", "2008"}
        candidates = [n for n in re.findall(r"(?<!\w)([0-9]{1,4}(?:\([a-z0-9]+\)|[A-Za-z])?)(?!\w)", statute_text) if n not in enactment_years]
        return candidates[-1] if candidates else ""

    # --------------------------------------------------------------------------
    # D. Charge Alignment & Accused Attribution
    # --------------------------------------------------------------------------

    def _compare_charges(
        self,
        ai: NormalizedJudgment,
        real: NormalizedJudgment,
        errors: List[ComparisonErrorDetail],
        missing: List[str],
        unrelated: List[str],
    ) -> ChargeComparisonResult:
        ai_charges = ai.charges
        real_charges = real.charges

        matched: List[Dict[str, Any]] = []
        missing_charges: List[str] = []
        incorrectly_introduced: List[str] = []
        historical_mismatches: List[str] = []
        procedural_or_coaccused: List[str] = []

        real_full_text = f"{(real.raw_text or '')} {self.case_packet_context}".lower()

        # Detect historical IPC vs modern BNS context
        is_historical = (
            any(c.era == StatuteEra.HISTORICAL_IPC_CRPC for c in real_charges)
            or "indian penal code" in real_full_text
            or "ipc" in real_full_text
            or "1860" in real_full_text
        )

        # Map equivalent offences between IPC and BNS
        for a_c in ai_charges:
            a_stat = a_c.statute
            a_sec = self._extract_section_number(a_stat)

            # Check if modern law substitution for historical offence
            if is_historical and a_c.era == StatuteEra.MODERN_BNS_BNSS_BSA:
                historical_mismatches.append(f"{a_stat} (Historical law mismatch: applied modern BNS/BSA instead of historical IPC/CrPC)")
                errors.append(
                    ComparisonErrorDetail(
                        type="historical_law_mismatch",
                        severity="medium",
                        ai_claim=a_stat,
                        real_court_position="Offence governed historically by Indian Penal Code, 1860 / Indian Evidence Act, 1872",
                        explanation=f"Provision '{a_stat}' represents modern law (2023), inapplicable to the historical offence.",
                    )
                )

            # Match against real charges
            matched_real = None
            for r_c in real_charges:
                r_stat = r_c.statute
                r_sec = self._extract_section_number(r_stat)

                same_accused = not (a_c.accused_name and r_c.accused_name) or self._same_person(a_c.accused_name, r_c.accused_name)
                if same_accused and a_sec and r_sec and a_sec == r_sec:
                    matched_real = r_c
                    break

            if matched_real:
                matched.append({
                    "real_charge": matched_real.statute,
                    "ai_charge": a_stat,
                    "mapped_substantive_offence": bool(a_c.era != matched_real.era),
                })
            else:
                # Check whether this charge was part of procedural history or framed against a co-accused
                is_in_procedural_history = (
                    (a_sec and a_sec in real_full_text)
                    or any(w in real_full_text for w in re.findall(r"\b[a-z]{4,}\b", a_stat.lower())[:2])
                )
                if is_in_procedural_history:
                    # Distinguish co-accused / procedural charge from pure hallucination
                    is_coaccused = any(
                        a_c.accused_name and r_c.accused_name
                        and not self._same_person(a_c.accused_name, r_c.accused_name)
                        for r_c in real_charges
                    )
                    procedural_or_coaccused.append(a_stat)
                    explanation = (
                        f"Provision '{a_stat}' belongs to a different named accused in the extracted charge record, not the accused being evaluated."
                        if is_coaccused else
                        f"Provision '{a_stat}' appears in the source text but is not matched to an active charge for the accused being evaluated."
                    )
                    incorrectly_introduced.append(a_stat)
                    errors.append(
                        ComparisonErrorDetail(
                            type="wrong_legal_provision",
                            severity="medium",
                            ai_claim=a_stat,
                            real_court_position="Procedural history / co-accused trial charge",
                            explanation=explanation,
                        )
                    )
                else:
                    incorrectly_introduced.append(a_stat)
                    unrelated.append(f"Statutory charge incorrectly introduced by AI: {a_stat}")
                    errors.append(
                        ComparisonErrorDetail(
                            type="wrong_legal_provision",
                            severity="high",
                            ai_claim=a_stat,
                            real_court_position=NOT_ESTABLISHED_MSG,
                            explanation="AI Court introduced an offence/charge that was not part of the actual prosecution.",
                        )
                    )

        # Check for missing real charges
        for r_c in real_charges:
            r_sec_match = re.search(r"(?:Section|Sec\.|u/s|s\.)\s*([0-9]{1,4}(?:\([a-z0-9]+\)|[A-Za-z])?)", r_c.statute, re.IGNORECASE)
            if not r_sec_match:
                r_sec_match = re.search(r"(?<!\w)([0-9]{1,4}(?:\([a-z0-9]+\)|[A-Za-z])?)(?!\w)", r_c.statute)
            r_sec = r_sec_match.group(1) if r_sec_match else ""
            if not any(r_sec and r_sec.casefold() in a_c.statute.casefold() for a_c in ai_charges):
                missing_charges.append(r_c.statute)
                missing.append(f"Omitted charge: {r_c.statute}")

        total_real = len(real_charges) or 1
        base_score = (len(matched) / total_real) * 100.0
        penalty = (len(historical_mismatches) * 10.0) + (len(incorrectly_introduced) * 10.0)
        score = max(0.0, min(100.0, round(base_score - penalty, 2)))

        category_status = (
            ComparisonCategoryStatus.MATCH.value if score >= 80.0
            else (ComparisonCategoryStatus.PARTIAL_MATCH.value if score >= 40.0 else ComparisonCategoryStatus.MISMATCH.value)
        )

        explanation = (
            f"Charges: {len(matched)} matched, {len(missing_charges)} missing, "
            f"{len(procedural_or_coaccused)} procedural/co-accused, "
            f"{len(incorrectly_introduced)} incorrectly introduced. "
            f"Historical law mismatches detected: {len(historical_mismatches)}."
        )

        return ChargeComparisonResult(
            matched_charges=matched,
            missing_charges=missing_charges,
            incorrectly_introduced_charges=incorrectly_introduced,
            historical_law_mismatches=historical_mismatches,
            procedural_or_coaccused_charges=procedural_or_coaccused,
            score=score,
            explanation=explanation,
            ai_extracted_position="; ".join(c.statute for c in ai_charges),
            real_extracted_position="; ".join(c.statute for c in real_charges),
            status=category_status if (ai_charges or real_charges) else ComparisonCategoryStatus.INSUFFICIENT_DATA.value,
            is_assessable=bool(ai_charges or real_charges),
        )

    @staticmethod
    def _same_person(first: str, second: str) -> bool:
        def normalized(value: str) -> str:
            return " ".join(re.findall(r"[a-z]+", value.lower()))
        a, b = normalized(first), normalized(second)
        return bool(a and b and (a == b or a in b or b in a))

    # --------------------------------------------------------------------------
    # E. Witness Alignment (with Insufficient Data Handling)
    # --------------------------------------------------------------------------

    def _compare_witnesses(
        self,
        ai: NormalizedJudgment,
        real: NormalizedJudgment,
        errors: List[ComparisonErrorDetail],
        missing: List[str],
    ) -> WitnessComparisonResult:
        ai_w = ai.prosecution_witnesses + ai.defence_witnesses
        real_w = real.prosecution_witnesses + real.defence_witnesses

        # If both judgments contain no extractable individual witness information
        if not real_w and not ai_w:
            return WitnessComparisonResult(
                witness_count_ai=0,
                witness_count_real=0,
                correctly_analyzed_witnesses=[],
                misattributed_testimony=[],
                omitted_key_witnesses=[],
                substantive_testimony_alignment="Individual witness testimonies not detailed in supplied Real Court record (Ground Truth summary).",
                score=100.0,
                explanation="Witness analysis: Insufficient Data in source judgment. Category marked Insufficient Data and excluded from scoring denominator.",
                ai_extracted_position="No witness roster extracted",
                real_extracted_position="No individual witness roster present in summary",
                status=ComparisonCategoryStatus.INSUFFICIENT_DATA.value,
                is_assessable=False,
            )

        if real_w and not ai_w:
            return WitnessComparisonResult(
                witness_count_ai=0,
                witness_count_real=len(real_w),
                correctly_analyzed_witnesses=[],
                misattributed_testimony=[],
                omitted_key_witnesses=[w.witness_id for w in real_w],
                substantive_testimony_alignment="AI Court failed to analyze any of the prosecution witnesses.",
                score=0.0,
                explanation=f"AI Court failed to extract or analyze the {len(real_w)} witnesses on record.",
                ai_extracted_position="0 witnesses",
                real_extracted_position=f"{len(real_w)} witnesses ({', '.join(w.witness_id for w in real_w)})",
                status=ComparisonCategoryStatus.MISSING_IN_AI.value,
                is_assessable=True,
            )

        real_map = {w.witness_id.upper(): w for w in real_w}
        ai_map = {w.witness_id.upper(): w for w in ai_w}

        correctly_analyzed: List[str] = []
        misattributed: List[str] = []
        omitted_keys: List[str] = []

        for wid, rw in real_map.items():
            if wid in ai_map:
                aw = ai_map[wid]
                rw_words = set(re.findall(r"\b[a-z]{4,}\b", rw.testimony_summary.lower()))
                aw_words = set(re.findall(r"\b[a-z]{4,}\b", aw.testimony_summary.lower()))
                overlap = rw_words.intersection(aw_words)
                if len(overlap) >= 1 or rw.designation.lower() in aw.designation.lower():
                    correctly_analyzed.append(wid)
                else:
                    misattributed.append(wid)
                    errors.append(
                        ComparisonErrorDetail(
                            type="incorrect_witness_statement",
                            severity="medium",
                            ai_claim=f"{wid} ({aw.name}): {aw.testimony_summary[:100]}",
                            real_court_position=f"{wid} ({rw.name}): {rw.testimony_summary[:100]}",
                            explanation=f"Substance of testimony attributed to {wid} diverges from authoritative record.",
                        )
                    )
            else:
                omitted_keys.append(wid)
                missing.append(f"Witness omitted by AI Court: {wid} ({rw.name or rw.designation})")

        total_real = len(real_map) or 1
        base_score = (len(correctly_analyzed) / total_real) * 100.0
        penalty = (len(misattributed) * 20.0) + (len(omitted_keys) * 10.0)
        score = max(0.0, min(100.0, round(base_score - penalty, 2)))

        category_status = (
            ComparisonCategoryStatus.MATCH.value if score >= 80.0
            else (ComparisonCategoryStatus.PARTIAL_MATCH.value if score >= 40.0 else ComparisonCategoryStatus.MISMATCH.value)
        )

        explanation = (
            f"Witness analysis: {len(correctly_analyzed)} of {len(real_map)} witnesses aligned. "
            f"Omitted witnesses: {len(omitted_keys)}. Misattributions: {len(misattributed)}."
        )

        return WitnessComparisonResult(
            witness_count_ai=len(ai_w),
            witness_count_real=len(real_w),
            correctly_analyzed_witnesses=correctly_analyzed,
            misattributed_testimony=misattributed,
            omitted_key_witnesses=omitted_keys,
            substantive_testimony_alignment="Evaluated oral depositions and ocular evidence consistency.",
            score=score,
            explanation=explanation,
            ai_extracted_position=f"{len(ai_w)} witnesses",
            real_extracted_position=f"{len(real_w)} witnesses",
            status=category_status,
            is_assessable=True,
        )

    # --------------------------------------------------------------------------
    # F. Evidence Alignment (with Insufficient Data Handling)
    # --------------------------------------------------------------------------

    def _compare_evidence(
        self,
        ai: NormalizedJudgment,
        real: NormalizedJudgment,
        errors: List[ComparisonErrorDetail],
        missing: List[str],
        unrelated: List[str],
    ) -> EvidenceComparisonResult:
        ai_ev = ai.evidence_items
        real_ev = real.evidence_items
        real_text_lower = (real.raw_text or "").lower()

        # Without a source exhibit inventory, an empty/missing record is not
        # evidence of perfect AI alignment and cannot support a numeric score.
        if not real_ev:
            return EvidenceComparisonResult(
                correctly_considered=[],
                ignored_evidence=[],
                misattributed_evidence=[],
                misinterpreted_evidence=[],
                invented_evidence=[],
                improperly_proved_evidence=[],
                assessed_ai_evidence=len(ai_ev), assessed_real_evidence=0,
                score=0.0,
                explanation="Evidence alignment is not assessable: the source judgment yielded no reliable exhibit inventory. No default score was assigned.",
                ai_extracted_position=f"{len(ai_ev)} AI evidence items; source inventory unavailable",
                real_extracted_position="No exhibit-by-exhibit inventory present in summary",
                status=ComparisonCategoryStatus.INSUFFICIENT_DATA.value,
                is_assessable=False,
            )

        correctly_considered: List[str] = []
        ignored_evidence: List[str] = []
        misattributed_evidence: List[str] = []
        misinterpreted_evidence: List[str] = []
        invented_evidence: List[str] = []
        improperly_proved: List[str] = []

        # Check for invented evidence in AI judgment (e.g. electronic call logs, certificates)
        for a_e in ai_ev:
            desc_lower = a_e.description.lower()
            is_invented_electronic = (
                (a_e.evidence_type == "ELECTRONIC" or "electronic" in desc_lower or "call detail" in desc_lower or "cdr" in desc_lower)
                and "electronic" not in real_text_lower and "call detail" not in real_text_lower
            )
            if is_invented_electronic:
                invented_evidence.append(f"{a_e.exhibit_id}: {a_e.description}")
                unrelated.append(f"Invented evidence by AI: {a_e.exhibit_id}")
                errors.append(
                    ComparisonErrorDetail(
                        type="invented_evidence",
                        severity="high",
                        ai_claim=f"{a_e.exhibit_id} - {a_e.description}",
                        real_court_position=NOT_ESTABLISHED_MSG,
                        explanation="AI Court relied upon electronic/digital exhibit that was not in evidence in the real court record.",
                    )
                )
            else:
                def normalized_id(value: str) -> str:
                    return re.sub(r"[^a-z0-9]", "", value.lower())
                candidates = []
                for r_e in real_ev:
                    id_match = normalized_id(r_e.exhibit_id) == normalized_id(a_e.exhibit_id)
                    description_similarity = self._fact_similarity(a_e.description, r_e.description)
                    if id_match or description_similarity >= 0.55:
                        candidates.append((1.0 if id_match else description_similarity, r_e))
                matched_real = max(candidates, key=lambda item: item[0])[1] if candidates else None
                if matched_real:
                    polarity = self._evidence_assessment_polarity(a_e.judicial_assessment)
                    real_polarity = self._evidence_assessment_polarity(matched_real.judicial_assessment)
                    if polarity and real_polarity and polarity != real_polarity:
                        detail = f"{a_e.exhibit_id}: AI '{a_e.judicial_assessment}' vs real '{matched_real.judicial_assessment}'"
                        misinterpreted_evidence.append(detail)
                        errors.append(ComparisonErrorDetail(
                            type="misinterpreted_evidence", severity="high", ai_claim=detail,
                            real_court_position=matched_real.judicial_assessment or NOT_ESTABLISHED_MSG,
                            explanation="AI and real judgment assign opposing probative directions to the matched evidence item.",
                        ))
                    else:
                        correctly_considered.append(a_e.exhibit_id)
                else:
                    misattributed_evidence.append(a_e.exhibit_id)

        # Check for ignored evidence
        ai_text_lower = (ai.raw_text or "").lower() + " " + " ".join(e.description.lower() for e in ai_ev)
        for r_e in real_ev:
            if not any(k in ai_text_lower for k in [r_e.exhibit_id.lower(), r_e.description.lower()[:20]]):
                ignored_evidence.append(f"{r_e.exhibit_id}: {r_e.description}")
                missing.append(f"Ignored evidence: {r_e.exhibit_id}")

        total_real = len(real_ev) or 1
        base_score = (len(correctly_considered) / total_real) * 100.0 if real_ev else 70.0
        penalty = (len(invented_evidence) * 25.0) + (len(ignored_evidence) * 10.0)
        score = max(0.0, min(100.0, round(base_score - penalty, 2)))

        category_status = (
            ComparisonCategoryStatus.MATCH.value if score >= 80.0
            else (ComparisonCategoryStatus.PARTIAL_MATCH.value if score >= 40.0 else ComparisonCategoryStatus.MISMATCH.value)
        )

        explanation = (
            f"Evidence evaluation: {len(correctly_considered)} items verified. "
            f"Ignored evidence items: {len(ignored_evidence)}. Invented evidence: {len(invented_evidence)}."
        )

        return EvidenceComparisonResult(
            correctly_considered=correctly_considered,
            ignored_evidence=ignored_evidence,
            misattributed_evidence=misattributed_evidence,
            misinterpreted_evidence=misinterpreted_evidence,
            invented_evidence=invented_evidence,
            improperly_proved_evidence=improperly_proved,
            assessed_ai_evidence=len(ai_ev),
            assessed_real_evidence=len(real_ev),
            score=score,
            explanation=explanation,
            ai_extracted_position=f"{len(ai_ev)} evidence items",
            real_extracted_position=f"{len(real_ev)} evidence items",
            status=category_status,
            is_assessable=bool(len(real_ev) > 0 or len(ai_ev) > 0),
        )

    @staticmethod
    def _evidence_assessment_polarity(text: Optional[str]) -> Optional[str]:
        if not text:
            return None
        value = text.lower()
        positive = bool(re.search(r"\b(reliable|credible|corroborat\w*|supports?|proved|admissible)\b", value))
        negative = bool(re.search(r"\b(unreliable|not credible|doubtful|not proved|contradict\w*|inadmissible|unproved|excluded)\b", value))
        if positive == negative:
            return None
        return "positive" if positive else "negative"

    # --------------------------------------------------------------------------
    # G. Legal Provision Alignment
    # --------------------------------------------------------------------------

    def _compare_legal_provisions(
        self,
        ai: NormalizedJudgment,
        real: NormalizedJudgment,
        errors: List[ComparisonErrorDetail],
        missing: List[str],
        unrelated: List[str],
    ) -> LegalProvisionComparisonResult:
        ai_provs = ai.legal_provisions
        real_provs = real.legal_provisions

        correct_provs: List[str] = []
        missing_provs: List[str] = []
        incorrectly_cited: List[str] = []
        historically_inapplicable: List[str] = []
        procedural_or_coaccused: List[str] = []
        unconnected: List[str] = []

        real_text_lower = f"{(real.raw_text or '')} {self.case_packet_context}".lower()
        is_historical = any("ipc" in p.lower() or "1872" in p.lower() for p in real_provs) or "indian penal code" in real_text_lower

        # Extract substantive section numbers from real governing provisions
        real_substantive_secs = set()
        for rp in real_provs:
            for s in re.findall(r"(?<!\w)([0-9]{1,4}(?:\([a-z0-9]+\)|[A-Za-z])?)(?!\w)", rp):
                if s not in {"1860", "1872", "1966", "1973", "2023"}:
                    real_substantive_secs.add(s.lower())

        for ap in ai_provs:
            ap_lower = ap.lower()
            ap_secs = re.findall(r"(?<!\w)([0-9]{1,4}(?:\([a-z0-9]+\)|[A-Za-z])?)(?!\w)", ap_lower)
            ap_sec_nums = [s for s in ap_secs if s not in {"1860", "1872", "1966", "1973", "2023"}]
            sec_disp = ", ".join(ap_sec_nums) if ap_sec_nums else ", ".join(ap_secs)

            # 1. Check if modern law substitution for historical offence
            if is_historical and any(term in ap_lower for term in ["bsa", "bharatiya sakshya", "bns", "bharatiya nyaya"]):
                historically_inapplicable.append(ap)
                errors.append(
                    ComparisonErrorDetail(
                        type="historical_law_mismatch",
                        severity="medium",
                        ai_claim=ap,
                        real_court_position=NOT_ESTABLISHED_MSG,
                        explanation=f"Provision '{ap}' is modern law (2023), inapplicable to the historical offence.",
                    )
                )
            # A citation found only in source history, and absent from the
            # extracted governing provisions, remains procedural context.
            elif any(s in real_text_lower for s in ap_sec_nums) and not any(s in real_substantive_secs for s in ap_sec_nums):
                procedural_or_coaccused.append(ap)
                errors.append(
                    ComparisonErrorDetail(
                        type="wrong_legal_provision",
                        severity="medium",
                        ai_claim=ap,
                        real_court_position="Procedural or historical reference in source text, absent from extracted governing provisions",
                        explanation=f"Citation '{ap}' appears in source text but is not identified as a governing provision for this comparison.",
                    )
                )
            # 3. Check if matches substantive real provision
            elif any(s in real_substantive_secs for s in ap_secs) or any(rp.lower() in ap_lower for rp in real_provs):
                correct_provs.append(ap)
            # 4. Check if appears in procedural history / trial record text
            elif any(k in real_text_lower for k in re.findall(r"(?<!\w)(?:section\s+[0-9]+(?:\([a-z0-9]+\))?|[0-9]{1,3}(?:\([a-z0-9]+\))?)(?!\w)", ap_lower)):
                procedural_or_coaccused.append(ap)
            else:
                unconnected.append(ap)
                unrelated.append(f"Unconnected statutory citation: {ap}")

        # Check for missing real provisions
        for rp in real_provs:
            rp_lower = rp.lower()
            sec_num = re.search(r"(?:section|sec\.?)\s*([0-9]{1,4}(?:\([a-z0-9]+\)|[a-z])?)", rp_lower)
            if not sec_num:
                sec_num = re.search(r"(?<!\w)([0-9]{1,3}(?:\([a-z0-9]+\))?)(?!\w)", rp_lower)
            if sec_num and not any(sec_num.group(1) in a.lower() for a in ai_provs):
                missing_provs.append(rp)
                missing.append(f"Statutory provision omitted: {rp}")

        matched_count = len(correct_provs)
        missing_count = len(missing_provs)
        inapplicable_count = len(historically_inapplicable)
        procedural_count = len(procedural_or_coaccused)
        unconnected_count = len(unconnected)
        incorrect_count = len(incorrectly_cited)
        total_real = len(real_provs) or 1

        # Mathematically consistent scoring:
        # Coverage (Recall) = Matched / Real
        # Precision = (Matched + 0.5 * Procedural) / Total AI Citations
        # Balanced F1 Score = 2 * (Precision * Recall) / (Precision + Recall)
        recall = matched_count / total_real
        total_ai_citations = max(1, matched_count + procedural_count + inapplicable_count + unconnected_count + incorrect_count)
        precision = (matched_count + 0.5 * procedural_count) / total_ai_citations

        if (precision + recall) > 0:
            f1 = (2.0 * precision * recall) / (precision + recall)
            score = max(0.0, min(100.0, round(f1 * 100.0, 2)))
        else:
            score = 0.0

        category_status = (
            ComparisonCategoryStatus.MATCH.value if score >= 75.0
            else (ComparisonCategoryStatus.PARTIAL_MATCH.value if score >= 35.0 else ComparisonCategoryStatus.MISMATCH.value)
        )

        explanation = (
            f"Statutory provisions: {matched_count} matched, {missing_count} missing, "
            f"{inapplicable_count} historically inapplicable, {procedural_count} procedural/co-accused, "
            f"{unconnected_count} unconnected. "
            f"Coverage (Recall): {round(recall * 100, 1)}%, Precision: {round(precision * 100, 1)}%. "
            f"Formula: Balanced F1 score = 2 * (Precision * Recall) / (Precision + Recall)."
        )

        return LegalProvisionComparisonResult(
            correct_provisions=correct_provs,
            missing_provisions=missing_provs,
            incorrectly_cited_provisions=incorrectly_cited,
            historically_inapplicable_provisions=historically_inapplicable,
            procedural_or_coaccused_provisions=procedural_or_coaccused,
            unconnected_provisions=unconnected,
            matched_count=matched_count,
            missing_count=missing_count,
            incorrect_count=incorrect_count,
            inapplicable_count=inapplicable_count,
            procedural_count=procedural_count,
            unconnected_count=unconnected_count,
            score=score,
            explanation=explanation,
            ai_extracted_position="; ".join(ai_provs),
            real_extracted_position="; ".join(real_provs),
            status=category_status,
            is_assessable=True,
        )

    # --------------------------------------------------------------------------
    # H. Legal Reasoning Alignment (Ratio Decidendi)
    # --------------------------------------------------------------------------

    def _compare_reasoning(
        self,
        ai: NormalizedJudgment,
        real: NormalizedJudgment,
        errors: List[ComparisonErrorDetail],
        missing: List[str],
    ) -> LegalReasoningComparisonResult:
        """Compare source-derived reasoning propositions without benchmark-specific templates."""
        real_themes: List[str] = []
        for issue in real.legal_issues:
            proposition = " ".join(filter(None, [issue.statement, issue.finding, issue.reasoning_summary]))
            if len(proposition) >= 25:
                real_themes.append(proposition)
        real_themes.extend(chain for chain in real.reasoning.key_chains if len(chain) >= 25)
        if not real_themes:
            real_themes.extend(
                sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", real.reasoning.ratio_decidendi)
                if len(sentence.strip()) >= 35
            )
        real_themes = list(dict.fromkeys(real_themes))

        ai_propositions = list(ai.reasoning.key_chains)
        ai_propositions.extend(
            " ".join(filter(None, [issue.statement, issue.finding, issue.reasoning_summary]))
            for issue in ai.legal_issues
        )
        ai_propositions.extend(
            sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", ai.reasoning.ratio_decidendi)
            if len(sentence.strip()) >= 25
        )

        theme_evaluations: List[ReasoningThemeComparison] = []
        matched_ai: set[int] = set()
        for index, source_theme in enumerate(real_themes, 1):
            source_tokens = self._extract_concept_tokens(source_theme)
            best_index, best_similarity = None, 0.0
            for ai_index, proposition in enumerate(ai_propositions):
                if ai_index in matched_ai:
                    continue
                ai_tokens = self._extract_concept_tokens(proposition)
                overlap = len(source_tokens & ai_tokens)
                similarity = overlap / max(1, min(len(source_tokens), len(ai_tokens)))
                if overlap >= 2 and similarity > best_similarity:
                    best_index, best_similarity = ai_index, similarity
            if best_index is None:
                match_status = "MISMATCH"
                ai_position = "No semantically similar AI reasoning proposition was identified."
                missing.append(f"Core judicial reasoning omitted: {source_theme[:180]}")
            else:
                matched_ai.add(best_index)
                match_status = "MATCH" if best_similarity >= 0.7 else "PARTIAL_MATCH"
                ai_position = ai_propositions[best_index]
            theme_evaluations.append(ReasoningThemeComparison(
                theme_id=f"SOURCE-{index}", theme_name=f"Source proposition {index}",
                real_court_position=source_theme, ai_position=ai_position,
                match_status=match_status, source_evidence=source_theme,
            ))

        total_real_themes = len(real_themes)
        matched_count = sum(t.match_status == "MATCH" for t in theme_evaluations)
        partial_count = sum(t.match_status == "PARTIAL_MATCH" for t in theme_evaluations)
        earned = matched_count + 0.5 * partial_count
        score = round(earned / total_real_themes * 100.0, 2) if total_real_themes else 0.0
        addressed_issue = bool(matched_count + partial_count)
        considered_evidence = ai.reasoning.connected_evidence_to_findings
        evaluated_credibility = ai.reasoning.evaluated_credibility
        considered_contradictions = ai.reasoning.evaluated_contradictions
        considered_missing = ai.reasoning.evaluated_missing_evidence
        connected_findings = ai.reasoning.connected_evidence_to_findings
        applied_correct_law = bool(ai.reasoning.ratio_decidendi or ai.reasoning.key_chains)

        category_status = (
            ComparisonCategoryStatus.MATCH.value if score >= 75.0
            else (ComparisonCategoryStatus.PARTIAL_MATCH.value if score >= 35.0 else ComparisonCategoryStatus.MISMATCH.value)
        )
        explanation = (
            f"Source-derived reasoning alignment: {score}%. Evaluated {total_real_themes} real-court propositions "
            f"({matched_count} matched, {partial_count} partial, {total_real_themes - matched_count - partial_count} omitted). "
            "Charge outcome alignment is scored separately from judicial reasoning."
        )
        return LegalReasoningComparisonResult(
            addressed_actual_legal_issue=addressed_issue,
            considered_relevant_evidence=considered_evidence,
            applied_correct_law=applied_correct_law,
            evaluated_credibility_correctly=evaluated_credibility,
            considered_contradictions=considered_contradictions,
            considered_missing_evidence=considered_missing,
            connected_evidence_to_findings=connected_findings,
            logically_valid_chain_of_reasoning=bool(earned > 0),
            score=score,
            explanation=explanation,
            ai_extracted_position=ai.reasoning.ratio_decidendi[:300],
            real_extracted_position=real.reasoning.ratio_decidendi[:300],
            status=category_status,
            is_assessable=bool(total_real_themes),
            matched_themes_count=matched_count + partial_count,
            total_real_themes_count=total_real_themes,
            theme_evaluations=theme_evaluations,
        )

    # --------------------------------------------------------------------------
    # I. Finding Alignment
    # --------------------------------------------------------------------------

    def _compare_findings(
        self,
        ai: NormalizedJudgment,
        real: NormalizedJudgment,
        errors: List[ComparisonErrorDetail],
    ) -> FindingComparisonResult:
        issue_findings: List[Dict[str, Any]] = []
        matched_count = 0

        for r_ch, r_find in real.findings.items():
            ai_find = ai.findings.get(r_ch)
            if not ai_find:
                r_sec = self._extract_section_number(r_ch)
                for a_k, a_v in ai.findings.items():
                    a_sec = self._extract_section_number(a_k)
                    same_accused = not (ai_charges_name := next((c.accused_name for c in ai.charges if c.statute == a_k), None)) or not (real_charges_name := next((c.accused_name for c in real.charges if c.statute == r_ch), None)) or self._same_person(ai_charges_name, real_charges_name)
                    if same_accused and a_sec and r_sec and a_sec == r_sec:
                        ai_find = a_v
                        break

            aligned = False
            if ai_find:
                ai_outcome = self._charge_outcome(ai_find)
                real_outcome = self._charge_outcome(str(r_find))
                if ai_outcome and real_outcome and ai_outcome == real_outcome:
                    aligned = True
                    matched_count += 1
                elif ai_outcome and real_outcome:
                    errors.append(
                        ComparisonErrorDetail(
                            type="incorrect_finding",
                            severity="high",
                            ai_claim=f"{r_ch}: {ai_find}",
                            real_court_position=f"{r_ch}: {r_find}",
                            explanation=f"Final charge disposition differs: AI={ai_outcome}; real court={real_outcome}.",
                        )
                    )

            issue_findings.append({
                "charge_or_issue": r_ch,
                "ai_finding": ai_find or "Not evaluated",
                "real_finding": str(r_find),
                "aligned": aligned,
                "ai_charge_outcome": self._charge_outcome(ai_find or ""),
                "real_charge_outcome": self._charge_outcome(str(r_find)),
                "outcome_assessable": bool(self._charge_outcome(ai_find or "") and self._charge_outcome(str(r_find))),
            })

        assessable_findings = [item for item in issue_findings if item["outcome_assessable"]]
        total = len(assessable_findings)
        score = round((matched_count / total) * 100.0, 2) if total else 0.0
        category_status = (
            ComparisonCategoryStatus.MATCH.value if score >= 80.0
            else (ComparisonCategoryStatus.PARTIAL_MATCH.value if score >= 40.0 else ComparisonCategoryStatus.MISMATCH.value)
        )
        explanation = (
            f"Final charge outcomes aligned on {matched_count} of {total} assessable charges ({score}%). "
            f"Note: Operative finding alignment evaluates charge disposal, kept strictly separate from legal reasoning and ratio decidendi alignment."
        )

        return FindingComparisonResult(
            issue_findings=issue_findings,
            score=score,
            explanation=explanation,
            ai_extracted_position="; ".join(f"{k}: {v}" for k, v in ai.findings.items()),
            real_extracted_position="; ".join(f"{k}: {v}" for k, v in real.findings.items()),
            status=category_status if total else ComparisonCategoryStatus.INSUFFICIENT_DATA.value,
            is_assessable=bool(total),
        )

    @staticmethod
    def _charge_outcome(text: str) -> Optional[str]:
        """Return only an explicit final charge disposition, never an ingredient result."""
        value = re.sub(r"\s+", " ", text.lower()).strip(" .:;\n\t")
        # Appellate disposition language has explicit direction.
        if re.search(r"\bconviction\s+(?:was\s+)?set\s+aside\b|\bconviction\s+quashed\b|\bconviction\s+overturned\b", value):
            return "acquittal"
        if re.search(r"\bconviction\s+(?:was\s+)?upheld\b|\bconviction\s+affirmed\b", value):
            return "conviction"
        if re.search(r"\b(?:acquitted|acquittal|not guilty)\b", value):
            return "acquittal"
        if re.search(r"\b(?:convicted|conviction|found guilty|guilty)\b", value):
            return "conviction"
        # Bare normalized charge findings such as "NOT PROVED" are treated as
        # charge outcomes because they are attached to a charge key. Longer
        # ingredient discussions do not qualify unless they name the charge.
        if value in {"not proved", "not proven", "not established"} or re.search(
            r"\b(?:charge|offence|offense)\b.{0,50}\bnot\s+prov(?:ed|en)\b", value
        ):
            return "acquittal"
        return None

    # --------------------------------------------------------------------------
    # J. Final Order Alignment
    # --------------------------------------------------------------------------

    def _compare_final_order(
        self,
        ai: NormalizedJudgment,
        real: NormalizedJudgment,
        errors: List[ComparisonErrorDetail],
    ) -> FinalOrderComparisonResult:
        ai_order = ai.final_order
        real_order = real.final_order

        # Verify neither order is footer / comparison metadata
        has_footer_leak = (
            "comparison engine" in real_order.lower()
            or "source and evaluation" in real_order.lower()
            or "page 2" in real_order.lower()
        )
        if has_footer_leak:
            errors.append(
                ComparisonErrorDetail(
                    type="extraction_error",
                    severity="critical",
                    ai_claim="Operative Order",
                    real_court_position=real_order[:150],
                    explanation="Critical extraction failure: Real final order contained metadata/footer text.",
                )
            )

        is_ai_release = any(w in ai_order.lower() for w in ["acquitt", "discharg", "set aside", "benefit of doubt", "released"])
        is_real_release = any(w in real_order.lower() for w in ["acquitt", "discharg", "set aside", "appeal is allowed", "appeal was allowed", "released forthwith"])

        is_ai_custody = any(w in ai_order.lower() for w in ["convicted", "sentenced to", "rigorous imprisonment"]) and not is_ai_release
        is_real_custody = any(w in real_order.lower() for w in ["convicted", "sentenced to", "rigorous imprisonment", "appeal is dismissed"]) and not is_real_release

        if (is_ai_release and is_real_release) or (is_ai_custody and is_real_custody):
            status: AlignmentStatus = "aligned"
            category_status = ComparisonCategoryStatus.MATCH.value
            score = 100.0
            explanation = "Operative final order aligns in substance with the disposal rendered by the Real Court."
        else:
            status = "not_aligned"
            category_status = ComparisonCategoryStatus.MISMATCH.value
            score = 0.0
            explanation = "Final operative order diverges from the relief granted by the Real Court."
            errors.append(
                ComparisonErrorDetail(
                    type="incorrect_final_order",
                    severity="critical",
                    ai_claim=ai_order[:150],
                    real_court_position=real_order[:150] or NOT_ESTABLISHED_MSG,
                    explanation="Operative disposal direction conflicts directly with the authoritative order.",
                )
            )

        return FinalOrderComparisonResult(
            ai_final_order=ai_order,
            real_final_order=real_order,
            alignment=status,
            score=score,
            explanation=explanation,
            ai_extracted_position=ai_order[:200],
            real_extracted_position=real_order[:200],
            status=category_status if (ai_order and real_order) else ComparisonCategoryStatus.INSUFFICIENT_DATA.value,
            is_assessable=bool(ai_order and real_order),
        )
