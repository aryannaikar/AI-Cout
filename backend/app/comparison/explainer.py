"""
"Understand the Difference" Ã¢â‚¬â€ plain-language explanation of why the AI Court judgment
differs from the real court judgment.

Strictly explanatory and read-only:
  * never modifies, regenerates or re-scores either judgment;
  * grounds every statement in the already-computed ComparisonReport, the two normalised
    judgments and (optionally) the case packet;
  * labels each point as coming from the judgments, from AI analysis, or as unavailable;
  * uses the existing LLM provider/failover stack and falls back to a deterministic,
    data-derived explanation when no real LLM is reachable.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from app.comparison.schemas import ComparisonReport, NormalizedJudgment

logger = logging.getLogger(__name__)

Basis = Literal["from_judgments", "ai_analysis", "information_unavailable"]
Category = Literal["evidence", "witnesses", "legal_rules", "investigation", "missing_information", "reasoning"]

CATEGORY_TITLES: Dict[str, str] = {
    "evidence": "How the evidence was weighed",
    "witnesses": "How witness statements were understood",
    "legal_rules": "Which legal rules were applied",
    "investigation": "Investigation problems",
    "missing_information": "Information the AI did not have",
    "reasoning": "Main reasoning difference",
}

UNAVAILABLE = "This information is not available in the documents provided."


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------

class KeyDifference(BaseModel):
    category: Category = "reasoning"
    title: str = ""
    ai_view: str = Field(default="", description="What the AI Court thought")
    real_court_view: str = Field(default="", description="What the real court decided")
    why_different: str = Field(default="", description="Why they differ, in simple language")
    basis: Basis = "ai_analysis"


class LegalTermExplained(BaseModel):
    term: str
    meaning: str


class DifferenceExplanation(BaseModel):
    simple_summary: str = Field(default="", description="2-3 very short sentences for a non-lawyer")
    main_reasons: List[str] = Field(default_factory=list, description="At most 3 one-sentence reasons")
    analogy: str = Field(default="", description="One-sentence software analogy, clearly an analogy")
    verdicts_differ: Optional[bool] = None
    ai_verdict: str = ""
    real_verdict: str = ""
    why_judgments_differ: str = ""
    ai_court_concluded: str = ""
    real_court_concluded: str = ""
    key_differences: List[KeyDifference] = Field(default_factory=list)
    how_it_led_to_different_verdicts: str = ""
    what_we_can_learn: str = ""
    legal_terms: List[LegalTermExplained] = Field(default_factory=list)
    unavailable_information: List[str] = Field(default_factory=list)


class DifferenceExplanationResponse(DifferenceExplanation):
    case_id: Optional[str] = None
    case_title: str = ""
    generated_by: Literal["llm", "deterministic_fallback"] = "deterministic_fallback"
    model_note: str = ""
    disclaimer: str = (
        "This is an explanation, not a new judgment. Neither the AI Court nor the real court is "
        "assumed to be correct. Items marked 'AI analysis' are machine-generated interpretations."
    )


# ---------------------------------------------------------------------------
# Plain-language glossary (generic definitions only; no case facts)
# ---------------------------------------------------------------------------

_GLOSSARY: Dict[str, str] = {
    "reasonable doubt": "if a sensible person still has real doubts about guilt after looking at all the evidence, the accused must be freed",
    "corroboration": "support from another independent source that confirms a statement",
    "admissibility": "whether the court is legally allowed to use a piece of evidence at all",
    "admissible": "something the court is legally allowed to use as evidence",
    "sanction": "official written permission needed before certain public servants can be prosecuted",
    "burden of proof": "the duty of the prosecution to prove guilt; the accused does not have to prove innocence",
    "recovery": "police finding or taking back an object, usually after the accused tells them where it is",
    "panch witness": "an independent local person who watches a police search or seizure so it can be trusted",
    "chain of custody": "the written trail showing who held an item from the moment it was found until court",
    "hostile witness": "a witness who goes against the side that called them",
    "precedent": "an earlier Supreme Court or High Court decision that later courts follow",
    "acquittal": "the court declares the accused not guilty",
    "conviction": "the court declares the accused guilty",
    "fir": "First Information Report, the first written police record of an alleged crime",
    "extra-judicial confession": "an admission of guilt made outside court, such as to a friend or villager",
    "ratio decidendi": "the main legal reason behind a court's decision",
    "forensic": "scientific testing of physical material, like fingerprints, blood or documents",
}


def _glossary_for(text: str) -> List[LegalTermExplained]:
    found: List[LegalTermExplained] = []
    for term, meaning in _GLOSSARY.items():
        if term == "fir":
            hit = re.search(r"\bFIR\b", text)
        else:
            hit = re.search(re.escape(term), text, re.IGNORECASE)
        if hit:
            found.append(LegalTermExplained(term="FIR" if term == "fir" else term, meaning=meaning))
    return found[:10]


# ---------------------------------------------------------------------------
# Grounding bundle
# ---------------------------------------------------------------------------

_INVESTIGATION_PATTERN = re.compile(
    r"(delay|panch|independent witness|seizure|recovery|recovered|memo|sanction|fsl|forensic|"
    r"chain of custody|identification parade|\bTIP\b|hostile|confession|FIR|investigat|"
    r"not proved|not produced|failed to|absence of|no evidence)",
    re.IGNORECASE,
)


def _clip(value: Any, limit: int = 420) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "Ã¢â‚¬Â¦"


def _investigation_sentences(judgment: Optional[NormalizedJudgment], max_items: int = 8) -> List[str]:
    """Sentences from the (real) judgment that describe investigation/procedure problems."""
    if judgment is None:
        return []
    pool: List[str] = []
    if judgment.raw_text:
        pool.extend(re.split(r"(?<=[.!?])\s+", judgment.raw_text))
    pool.extend(judgment.reasoning.key_chains or [])
    pool.extend(i.judicial_assessment or "" for i in judgment.evidence_items)
    pool.extend(w.credibility_finding or "" for w in judgment.prosecution_witnesses)
    seen: set[str] = set()
    hits: List[str] = []
    for sentence in pool:
        clean = _clip(sentence, 320)
        if len(clean) < 30 or clean in seen:
            continue
        if _INVESTIGATION_PATTERN.search(clean):
            seen.add(clean)
            hits.append(clean)
        if len(hits) >= max_items:
            break
    return hits


def _judgment_digest(judgment: Optional[NormalizedJudgment]) -> Dict[str, Any]:
    if judgment is None:
        return {}
    return {
        "verdict": judgment.verdict.value,
        "verdict_text": _clip(judgment.verdict_raw, 300),
        "final_order": _clip(judgment.final_order, 400),
        "ratio_decidendi": _clip(judgment.reasoning.ratio_decidendi, 900),
        "reasoning_chain": [_clip(c, 300) for c in judgment.reasoning.key_chains[:8]],
        "legal_issues": [
            {"issue": _clip(i.statement, 240), "finding": i.finding, "reason": _clip(i.reasoning_summary, 300)}
            for i in judgment.legal_issues[:6]
        ],
        "witnesses": [
            {"id": w.witness_id, "role": w.designation, "testimony": _clip(w.testimony_summary, 240),
             "credibility": _clip(w.credibility_finding, 240) or None}
            for w in (judgment.prosecution_witnesses + judgment.defence_witnesses)[:10]
        ],
        "evidence": [
            {"id": e.exhibit_id, "type": e.evidence_type, "what": _clip(e.description, 200),
             "court_assessment": _clip(e.judicial_assessment, 240) or None}
            for e in judgment.evidence_items[:12]
        ],
        "charges": [f"{c.statute}: {_clip(c.finding, 160)}" if c.finding else c.statute for c in judgment.charges[:8]],
        "legal_provisions": judgment.legal_provisions[:12],
        "extraction_warnings": judgment.extraction_warnings[:4],
    }


def build_grounding_bundle(
    report: ComparisonReport,
    ai_judgment: Optional[NormalizedJudgment],
    real_judgment: Optional[NormalizedJudgment],
    packet_text: Optional[str],
) -> Dict[str, Any]:
    r = report
    return {
        "case_title": r.case_title,
        "verdicts": {
            "ai_verdict": r.verdict_comparison.ai_verdict,
            "real_verdict": r.verdict_comparison.real_verdict,
            "alignment": r.verdict_comparison.alignment,
            "note": _clip(r.verdict_comparison.explanation, 400),
        },
        "real_court_judgment": _judgment_digest(real_judgment),
        "ai_court_judgment": _judgment_digest(ai_judgment),
        "investigation_sentences_from_real_judgment": _investigation_sentences(real_judgment),
        "comparison_findings": {
            "evidence": {
                "summary": _clip(r.evidence_comparison.explanation),
                "ignored_by_ai": r.evidence_comparison.ignored_evidence[:6],
                "misinterpreted_by_ai": r.evidence_comparison.misinterpreted_evidence[:6],
                "improperly_proved": r.evidence_comparison.improperly_proved_evidence[:6],
                "invented_by_ai": r.evidence_comparison.invented_evidence[:6],
            },
            "witnesses": {
                "summary": _clip(r.witness_comparison.explanation),
                "omitted_key_witnesses": r.witness_comparison.omitted_key_witnesses[:6],
                "misattributed_testimony": r.witness_comparison.misattributed_testimony[:6],
            },
            "legal_provisions": {
                "summary": _clip(r.legal_provision_comparison.explanation),
                "missing_in_ai": r.legal_provision_comparison.missing_provisions[:8],
                "incorrect_in_ai": r.legal_provision_comparison.incorrectly_cited_provisions[:8],
                "historically_inapplicable": r.legal_provision_comparison.historically_inapplicable_provisions[:6],
            },
            "reasoning": {
                "summary": _clip(r.reasoning_comparison.explanation),
                "themes": [
                    {"theme": t.theme_name, "real": _clip(t.real_court_position, 260),
                     "ai": _clip(t.ai_position, 260), "match": t.match_status}
                    for t in r.reasoning_comparison.theme_evaluations[:8]
                ],
            },
            "issues": {
                "missed_by_ai": r.issue_comparison.ai_missed_issues[:6],
                "unrelated_in_ai": r.issue_comparison.ai_unrelated_issues[:6],
            },
            "facts": {
                "incorrect": r.factual_comparison.incorrect_facts[:5],
                "invented": r.factual_comparison.invented_facts[:5],
                "omitted": r.factual_comparison.omitted_material_facts[:6],
            },
            "major_errors": [
                {"type": e.type, "ai": _clip(e.ai_claim, 220), "real": _clip(e.real_court_position, 220),
                 "why": _clip(e.explanation, 260)}
                for e in r.major_errors[:6]
            ],
            "missing_important_points": r.missing_important_points[:8],
        },
        "case_packet_excerpt": _clip(packet_text, 1800) if packet_text else None,
        "case_packet_provided": bool(packet_text),
    }


# ---------------------------------------------------------------------------
# LLM generation
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are a patient teacher explaining Indian court decisions to an ordinary person with no legal training.
Task: explain WHY the AI Court judgment differs from the real court judgment, using ONLY the supplied GROUNDING DATA.

Strict rules:
1. Simple, conversational English. Short sentences. Use legal terms rarely; when you use one (e.g. reasonable doubt, corroboration, admissibility, sanction, burden of proof), explain it right there in brackets and also list it in legal_terms.
2. NEVER invent evidence, witnesses, sections, case names, citations or judicial reasoning. If something is not in the data, say it is not available and add it to unavailable_information.
3. Do not assume either court is right. Describe, do not judge. Do not change or restate the verdicts as new decisions.
4. For each key difference set `basis`: "from_judgments" when it comes directly from the two judgments, "ai_analysis" when it is the comparison engine's interpretation, "information_unavailable" when the data does not say.
5. Cover these categories when the data allows (skip with an 'unavailable' item if not): evidence, witnesses, legal_rules, investigation, missing_information, reasoning.
6. If the verdicts are actually the same, say so and explain where the reasoning still differs.
7. Keep each field under about 50 words. The reader is a computer-science professor with no law background: be brief and concrete.
9. STYLE FOR simple_summary / main_reasons / analogy: write like you are explaining to a smart friend over chai. Each main reason is ONE sentence of at most 20 words. Do NOT use section numbers, act names, or words like presumption, burden, circumstantial, foundational, corroboration, evidentiary, adjudicate. Say what happened in everyday words (e.g. "Nobody proved the cash was actually stolen, so the court could not blame the accused for having it.").
8. simple_summary: at most 3 short sentences. main_reasons: at most 3 items, one plain sentence each, most important first. analogy: one sentence comparing the situation to software (e.g. test cases, input validation) and it must be clearly an analogy, not a legal fact.
Return the JSON object only."""


def _is_usable(result: Optional[DifferenceExplanation]) -> bool:
    return bool(result and result.key_differences and result.why_judgments_differ.strip())


def _llm_explanation(bundle: Dict[str, Any], fallback: DifferenceExplanation) -> Optional[DifferenceExplanation]:
    from app.core.llm_provider import LLMConfig
    from app.services.llm_service import LLMService

    if LLMConfig.provider() == "mock":
        return None
    try:
        import json

        service = LLMService(agent_name="comparison_explainer")
        prompt = (
            "GROUNDING DATA (JSON). Everything you write must be traceable to this data:\n"
            + json.dumps(bundle, ensure_ascii=False, default=str)
            + "\n\nWrite the explanation now."
        )
        result = service.generate_structured(
            prompt=prompt,
            response_schema=DifferenceExplanation,
            system_prompt=_SYSTEM_PROMPT,
        )
        return result if _is_usable(result) else None
    except Exception as exc:  # noqa: BLE001 - fall back on any provider failure
        logger.warning("Difference explainer LLM unavailable, using deterministic fallback: %s", exc)
        return None



_JARGON = re.compile(
    r"(section\s+\d+|\b\d+\s*(?:ipc|crpc|bns|bnss)\b|evidence act|presumption|burden|circumstantial|foundational|"
    r"corroborat|evidentiary|adjudicat|admissib|ratio|statutory|precedent|prima facie|beyond reasonable)",
    re.IGNORECASE,
)


class _SimpleText(BaseModel):
    simple_summary: str = ""
    main_reasons: List[str] = Field(default_factory=list)


def _too_complex(text: str) -> bool:
    return len(text.split()) > 28 or bool(_JARGON.search(text))


def _simplify_with_llm(summary: str, reasons: List[str]) -> Optional[_SimpleText]:
    """Second pass: rewrite already-grounded sentences in everyday words WITHOUT adding facts."""
    from app.core.llm_provider import LLMConfig
    from app.services.llm_service import LLMService

    if LLMConfig.provider() == "mock":
        return None
    try:
        import json

        prompt = (
            "Rewrite the text below for a computer-science professor who knows nothing about law.\n"
            "Rules: keep the SAME meaning and facts; add NOTHING new; no section numbers, no act names; "
            "avoid words like presumption, burden, circumstantial, foundational, corroboration; "
            "each reason is ONE sentence of at most 20 words in everyday language; "
            "simple_summary is at most 2 short sentences.\n\n"
            + json.dumps({"simple_summary": summary, "main_reasons": reasons}, ensure_ascii=False)
        )
        out = LLMService(agent_name="comparison_explainer_simplifier").generate_structured(
            prompt=prompt,
            response_schema=_SimpleText,
            system_prompt="You turn legal explanations into plain, short, friendly English. Output JSON only.",
        )
        reasons_ok = [r.strip() for r in out.main_reasons if r.strip()]
        return out if (reasons_ok or out.simple_summary.strip()) else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Simplification pass unavailable: %s", exc)
        return None

# ---------------------------------------------------------------------------
# Deterministic fallback (derived entirely from the computed report)
# ---------------------------------------------------------------------------

def _join(items: List[str], limit: int = 3) -> str:
    return "; ".join(_clip(i, 200) for i in items[:limit])


_ENGINE_JARGON = re.compile(
    r"(formula|f1|alignment|assessable|score|precision|recall|proposition|extract|denominator|"
    r"semantically|inventory|diagnostic|weighted)",
    re.IGNORECASE,
)
_CONCLUSION = re.compile(
    r"(held|hold|accordingly|in view|benefit of doubt|acquit|convict|not proved|proved|guilty|"
    r"find that|finds that|cannot be sustained|sustained)",
    re.IGNORECASE,
)
_HEADING = re.compile(r"(COURT OF INDIA|HIGH COURT|APPEAL NO|PETITION NO|^JUDGMENT$|^[A-Z0-9 .,/()-]{12,}$)")


def _looks_like_raw_data(text: str) -> bool:
    """True for JSON/dict fragments leaked from a file loader (never show these to readers)."""
    flat = text.strip()
    return flat.startswith(("{", "[")) or '":' in flat or '\\"' in flat or flat.endswith("}")


def _plain(text: Any, default: str = "", limit: int = 450) -> str:
    """Drop report-engine jargon (scores, formulas) so only reader-friendly sentences remain."""
    flat = re.sub(r"\s+", " ", str(text or "")).strip()
    if _looks_like_raw_data(flat):
        return default
    sentences = re.split(r"(?<=[.!?])\s+", flat)
    kept = [s for s in sentences if s and not _ENGINE_JARGON.search(s)]
    return _clip(" ".join(kept), limit) if kept else default


def _clean_point(text: str) -> str:
    cleaned = re.sub(r"^(Issue omitted by AI:|Omitted by AI:)\s*", "", text.strip(), flags=re.IGNORECASE)
    return re.sub(r"^\d+\.\s*", "", cleaned)


def _real_points(items: List[str]) -> List[str]:
    return [p for p in (_clean_point(i) for i in items) if p and not _HEADING.search(p) and not _looks_like_raw_data(p)]


def _concise_reasoning(judgment: Optional[NormalizedJudgment]) -> str:
    """Conclusion-bearing sentences from a judgment's own reasoning (never raw headers or JSON)."""
    if judgment is None:
        return ""
    pool = re.split(r"(?<=[.!?])\s+", judgment.reasoning.ratio_decidendi or "") + list(judgment.reasoning.key_chains)
    picks: List[str] = []
    for s in pool:
        s = _clean_point(_clip(s, 260))
        if _looks_like_raw_data(s) or _HEADING.search(s) or len(s) < 25:
            continue
        if _CONCLUSION.search(s) and s not in picks:
            picks.append(s)
        if len(picks) >= 3:
            break
    return " ".join(picks)


def _plain_verdict(value: str) -> str:
    mapping = {
        "ACQUITTAL": "not guilty (acquittal)",
        "CONVICTION": "guilty (conviction)",
        "APPEAL_ALLOWED": "appeal allowed",
        "APPEAL_DISMISSED": "appeal dismissed",
        "PARTIAL_CONVICTION": "guilty on some charges only",
        "DISCHARGE": "discharged before trial",
        "REMAND": "sent back to the lower court",
        "UNKNOWN": "not clearly stated",
        "EXTRACTION_ERROR": "could not be read from the document",
    }
    return mapping.get((value or "").upper(), value or "not clearly stated")


def _deterministic_explanation(
    report: ComparisonReport,
    ai_j: Optional[NormalizedJudgment],
    real_j: Optional[NormalizedJudgment],
    packet_text: Optional[str],
) -> DifferenceExplanation:
    vc = report.verdict_comparison
    ai_v, real_v = vc.ai_verdict, vc.real_verdict
    unknown = {"UNKNOWN", "EXTRACTION_ERROR", ""}
    verdicts_known = ai_v.upper() not in unknown and real_v.upper() not in unknown
    differ: Optional[bool] = (vc.alignment != "aligned") if verdicts_known else None
    unavailable: List[str] = []
    diffs: List[KeyDifference] = []

    # 1. Evidence
    ev = report.evidence_comparison
    if ev.is_assessable and (ev.ignored_evidence or ev.misinterpreted_evidence or ev.improperly_proved_evidence
                             or ev.invented_evidence):
        diffs.append(KeyDifference(
            category="evidence", title=CATEGORY_TITLES["evidence"],
            ai_view=(f"The AI Court read or described some evidence differently: {_join(ev.misinterpreted_evidence + ev.invented_evidence)}"
                     if (ev.misinterpreted_evidence or ev.invented_evidence)
                     else "The AI Court's judgment does not clearly show how it weighed the exhibits."),
            real_court_view=(f"The real court gave weight to or discussed: {_join(ev.ignored_evidence + ev.improperly_proved_evidence)}"
                             if (ev.ignored_evidence or ev.improperly_proved_evidence) else UNAVAILABLE),
            why_different=_plain(ev.explanation, "The two courts did not give the same importance to the same pieces of evidence."),
            basis="ai_analysis",
        ))
    else:
        diffs.append(KeyDifference(
            category="evidence", title=CATEGORY_TITLES["evidence"],
            ai_view=UNAVAILABLE, real_court_view=UNAVAILABLE,
            why_different="The documents did not list the exhibits clearly enough to compare how each court weighed them.",
            basis="information_unavailable",
        ))
        unavailable.append("A detailed exhibit-by-exhibit comparison was not possible from the documents provided.")

    # 2. Witnesses
    wc = report.witness_comparison
    if wc.is_assessable and (wc.omitted_key_witnesses or wc.misattributed_testimony):
        diffs.append(KeyDifference(
            category="witnesses", title=CATEGORY_TITLES["witnesses"],
            ai_view=(f"The AI Court's account of testimony differed on: {_join(wc.misattributed_testimony)}"
                     if wc.misattributed_testimony else "The AI Court did not discuss some witnesses that the real court discussed."),
            real_court_view=(f"Witnesses the real court discussed that the AI left out: {_join(wc.omitted_key_witnesses)}"
                             if wc.omitted_key_witnesses else UNAVAILABLE),
            why_different=_plain(wc.explanation, "The courts did not rely on the same witnesses or read their statements the same way."),
            basis="ai_analysis",
        ))
    else:
        diffs.append(KeyDifference(
            category="witnesses", title=CATEGORY_TITLES["witnesses"],
            ai_view=UNAVAILABLE, real_court_view=UNAVAILABLE,
            why_different="Witness statements could not be compared in detail from the documents provided.",
            basis="information_unavailable",
        ))
        unavailable.append("Witness testimony could not be compared in detail from the documents provided.")

    # 3. Legal rules
    lp = report.legal_provision_comparison
    ai_bits = lp.incorrectly_cited_provisions + lp.historically_inapplicable_provisions
    if lp.missing_provisions or ai_bits:
        diffs.append(KeyDifference(
            category="legal_rules", title=CATEGORY_TITLES["legal_rules"],
            ai_view=(f"The AI Court relied on or cited: {_join(ai_bits)}" if ai_bits
                     else "The AI Court's cited laws mostly overlap with the real court's."),
            real_court_view=(f"The real court also relied on: {_join(lp.missing_provisions)}" if lp.missing_provisions
                             else UNAVAILABLE),
            why_different=_plain(lp.explanation, "The courts did not rely on exactly the same set of laws."),
            basis="ai_analysis",
        ))
    elif lp.is_assessable and (lp.correct_provisions or lp.matched_count):
        diffs.append(KeyDifference(
            category="legal_rules", title=CATEGORY_TITLES["legal_rules"],
            ai_view=f"The AI Court cited: {_join(lp.correct_provisions)}",
            real_court_view=f"The real court cited the same main law(s): {_join(lp.correct_provisions)}",
            why_different="Both applied the same main law, so the different outcome did not come from choosing a different law, "
                          "but from how each court decided the law was proved on the facts.",
            basis="ai_analysis",
        ))
    else:
        unavailable.append("The legal provisions cited by the two courts could not be compared from the documents provided.")

    # 4. Investigation problems (only from sentences actually found in the real judgment)
    sentences = list(dict.fromkeys(_clean_point(s) for s in _investigation_sentences(real_j, max_items=6)))[:3]
    if sentences:
        diffs.append(KeyDifference(
            category="investigation", title=CATEGORY_TITLES["investigation"],
            ai_view="The AI Court's judgment does not give these investigation points the same weight."
                    if ai_j is not None else UNAVAILABLE,
            real_court_view="From the real judgment: " + " | ".join(sentences),
            why_different="These are points the real judgment itself raises about how the case was investigated or proved. "
                          "Where the AI judgment did not stress them, it may have trusted the prosecution story more.",
            basis="from_judgments",
        ))
    else:
        diffs.append(KeyDifference(
            category="investigation", title=CATEGORY_TITLES["investigation"],
            ai_view=UNAVAILABLE, real_court_view=UNAVAILABLE,
            why_different="No investigation problems (delayed FIR, recovery issues, missing papers) could be identified in the documents provided.",
            basis="information_unavailable",
        ))
        unavailable.append("Investigation details (FIR timing, recovery, seizure papers) were not clearly stated in the documents provided.")

    # 5. Missing information
    missing = _real_points(report.missing_important_points)[:4]
    diffs.append(KeyDifference(
        category="missing_information", title=CATEGORY_TITLES["missing_information"],
        ai_view="The AI Court worked only from the case materials it was given.",
        real_court_view=(f"Points the real judgment covers that the AI judgment lacks: {_join(missing, 4)}"
                         if missing else UNAVAILABLE),
        why_different=("A real court hears witnesses in person and sees every document; the AI only sees the papers uploaded to it. "
                       + ("The original case packet was not provided here, so we cannot say exactly what the AI could not see."
                          if not packet_text else "")).strip(),
        basis="ai_analysis" if missing else "information_unavailable",
    ))
    if not packet_text:
        unavailable.append("The original case packet was not supplied, so the exact material available to the AI is unknown.")

    # 6. Reasoning
    rc = report.reasoning_comparison
    real_ratio = _concise_reasoning(real_j)
    ai_ratio = _concise_reasoning(ai_j)
    mism = [t for t in rc.theme_evaluations if t.match_status.upper() != "MATCH" and not _HEADING.search(t.real_court_position or "")]
    if mism:
        t = mism[0]
        diffs.append(KeyDifference(
            category="reasoning", title=CATEGORY_TITLES["reasoning"],
            ai_view=_plain(t.ai_position, "The AI Court did not address this point.", 400),
            real_court_view=_plain(t.real_court_position, UNAVAILABLE, 400),
            why_different="The two judgments took different positions on this point, which pushed them toward different conclusions.",
            basis="from_judgments",
        ))
    elif real_ratio or ai_ratio:
        diffs.append(KeyDifference(
            category="reasoning", title=CATEGORY_TITLES["reasoning"],
            ai_view=ai_ratio or UNAVAILABLE, real_court_view=real_ratio or UNAVAILABLE,
            why_different="These are the main reasons each judgment gave for its decision.",
            basis="from_judgments",
        ))
    else:
        diffs.append(KeyDifference(
            category="reasoning", title=CATEGORY_TITLES["reasoning"],
            ai_view=UNAVAILABLE, real_court_view=UNAVAILABLE,
            why_different="The main reasoning of one or both judgments could not be extracted clearly.",
            basis="information_unavailable",
        ))
    if not real_ratio:
        unavailable.append("The real court's main reasoning could not be clearly extracted from the document.")
    if not ai_ratio:
        unavailable.append("The AI Court's main reasoning could not be clearly extracted from its judgment.")

    if differ is True:
        headline = (f"The AI Court decided the accused should be {_plain_verdict(ai_v)}, while the real court decided "
                    f"{_plain_verdict(real_v)}. The difference mainly comes from how each weighed the evidence and legal rules, listed below.")
        impact = (f"Because the two judgments weighed the evidence and legal rules differently, they ended at different outcomes "
                  f"({_plain_verdict(ai_v)} vs {_plain_verdict(real_v)}).")
    elif differ is False:
        headline = (f"Both courts reached the same outcome ({_plain_verdict(real_v)}), but their reasoning differs in the places listed below.")
        impact = "The final decisions match, so the differences affect how the result is justified rather than the result itself."
    else:
        headline = "The final decisions could not both be read clearly, so we can only compare how each judgment reasoned."
        impact = UNAVAILABLE
        unavailable.append("The outcome of one or both judgments could not be determined from the documents.")

    # Short reader-first view: top 3 concrete reasons, most informative first.
    order = ["investigation", "evidence", "witnesses", "legal_rules", "reasoning", "missing_information"]
    concrete = sorted((d for d in diffs if d.basis != "information_unavailable"), key=lambda d: order.index(d.category))
    reasons: List[str] = []
    for d in concrete[:3]:
        if d.category == "investigation":
            gist = _clip(d.real_court_view.replace("From the real judgment: ", "").split(" | ")[0], 170)
            reasons.append(f"The real judgment points out: {gist}")
        else:
            reasons.append(_clip(d.why_different, 170))
    if differ is True:
        summary = headline.split(". The difference")[0] + "."
        analogy = ("Think of it like two test runs on the same input that return different results: "
                   "the real court only accepts evidence it can verify, while the AI may accept inputs the court rejects.")
    else:
        summary, analogy = headline, ""

    combined_text = " ".join([headline, impact] + [f"{d.ai_view} {d.real_court_view} {d.why_different}" for d in diffs])
    return DifferenceExplanation(
        simple_summary=summary, main_reasons=reasons, analogy=analogy,
        verdicts_differ=differ,
        ai_verdict=_plain_verdict(ai_v), real_verdict=_plain_verdict(real_v),
        why_judgments_differ=headline,
        ai_court_concluded=(f"Verdict: {_plain_verdict(ai_v)}. " + ai_ratio).strip() if verdicts_known else (ai_ratio or UNAVAILABLE),
        real_court_concluded=(f"Verdict: {_plain_verdict(real_v)}. " + real_ratio).strip() if verdicts_known else (real_ratio or UNAVAILABLE),
        key_differences=diffs,
        how_it_led_to_different_verdicts=impact,
        what_we_can_learn=("Courts decide on proof, not suspicion: even a believable story can fail if independent witnesses, "
                           "proper seizure papers or clear identification of the stolen item are missing. "
                           "An AI reading only the papers can miss the weight a judge gives to such gaps."),
        legal_terms=_glossary_for(combined_text),
        unavailable_information=list(dict.fromkeys(unavailable)),
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def explain_differences(
    report: ComparisonReport,
    ai_judgment: Optional[NormalizedJudgment] = None,
    real_judgment: Optional[NormalizedJudgment] = None,
    packet_text: Optional[str] = None,
) -> DifferenceExplanationResponse:
    """Produce the plain-language explanation. Read-only: never mutates the report or judgments."""
    fallback = _deterministic_explanation(report, ai_judgment, real_judgment, packet_text)
    bundle = build_grounding_bundle(report, ai_judgment, real_judgment, packet_text)
    llm_result = _llm_explanation(bundle, fallback)

    if llm_result is not None:
        data = llm_result.model_copy(deep=True)
        # Keep factual anchors deterministic so the LLM cannot misstate either verdict.
        data.ai_verdict = data.ai_verdict or fallback.ai_verdict
        data.real_verdict = data.real_verdict or fallback.real_verdict
        data.verdicts_differ = fallback.verdicts_differ if fallback.verdicts_differ is not None else data.verdicts_differ
        data.simple_summary = data.simple_summary.strip() or fallback.simple_summary
        data.main_reasons = [r for r in data.main_reasons if r.strip()][:3] or fallback.main_reasons
        data.analogy = data.analogy.strip() or fallback.analogy
        if _too_complex(data.simple_summary) or any(_too_complex(r) for r in data.main_reasons):
            simpler = _simplify_with_llm(data.simple_summary, data.main_reasons)
            if simpler is not None:
                new_reasons = [r.strip() for r in simpler.main_reasons if r.strip()][:3]
                if new_reasons and not any(_too_complex(r) for r in new_reasons):
                    data.main_reasons = new_reasons
                if simpler.simple_summary.strip() and not _too_complex(simpler.simple_summary):
                    data.simple_summary = simpler.simple_summary.strip()
            # Still jargon-heavy or too long -> use the plain deterministic wording instead.
            if any(_too_complex(r) for r in data.main_reasons):
                data.main_reasons = fallback.main_reasons
            if _too_complex(data.simple_summary):
                data.simple_summary = fallback.simple_summary
        for field in ("ai_court_concluded", "real_court_concluded", "how_it_led_to_different_verdicts", "what_we_can_learn"):
            if not getattr(data, field).strip():
                setattr(data, field, getattr(fallback, field))
        if not data.legal_terms:
            data.legal_terms = _glossary_for(data.model_dump_json())
        generated_by: Literal["llm", "deterministic_fallback"] = "llm"
        note = "Written by the configured AI model from the two judgments and the comparison findings."
    else:
        data = fallback
        generated_by = "deterministic_fallback"
        note = "The AI writing service was unavailable, so this explanation was assembled directly from the comparison findings."

    return DifferenceExplanationResponse(
        **data.model_dump(),
        case_id=report.case_id,
        case_title=report.case_title,
        generated_by=generated_by,
        model_note=note,
    )



