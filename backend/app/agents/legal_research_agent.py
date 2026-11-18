"""Source-faithful, date-aware legal research over the persistent legal corpus."""

from __future__ import annotations

import logging
import re
from typing import Any, Literal, Optional
from uuid import uuid4

from app.models.legal_models import ApplicableProvision, LegalResearchResult
from app.services.legal_transition import (
    HISTORICAL_ACT_FILTERS,
    MODERN_ACT_FILTERS,
    detect_case_legal_regime,
)
from rag.retriever import LegalRetriever, RetrievalResult

logger = logging.getLogger(__name__)


class LegalResearchAgent:
    """Retrieve only legal sources compatible with the case's applicable regime."""

    def __init__(self, side: Literal["prosecution", "defense", "judicial"] = "prosecution", retriever: Optional[LegalRetriever] = None):
        self.side = side
        self.retriever = retriever or LegalRetriever(top_k=5)

    def research(
        self,
        question: str,
        top_k: Optional[int] = None,
        act_filter: Optional[str] = None,
        is_historical: bool = False,
        case: Any = None,
        regime: Optional[dict[str, Any]] = None,
    ) -> LegalResearchResult:
        """Return traceable provisions without relabelling one statute as another."""
        resolved_regime = regime or (detect_case_legal_regime(case) if case is not None else None)
        if resolved_regime is None:
            resolved_regime = {
                "is_historical": is_historical,
                "regime": "historical" if is_historical else "modern",
                "allowed_act_filters": HISTORICAL_ACT_FILTERS if is_historical else MODERN_ACT_FILTERS,
                "applicability_confidence": "high",
                "reasoning": "Regime supplied by the calling workflow.",
            }

        allowed_acts = tuple(resolved_regime["allowed_act_filters"])
        # An explicit requested statute must be compatible with the selected law.
        if act_filter and act_filter not in allowed_acts:
            return self._empty_result(
                question,
                resolved_regime,
                f"Requested act '{act_filter}' is incompatible with the selected legal regime.",
                status="unavailable",
            )

        results = self.retriever.retrieve(
            query=question,
            top_k=top_k or 5,
            act_filter=act_filter,
            act_filters=None if act_filter else allowed_acts,
        )
        # Defense against custom/legacy retrievers that ignore metadata filters.
        results = [result for result in results if result.short_name in allowed_acts]
        if not results:
            return self._empty_result(
                question,
                resolved_regime,
                f"No source-faithful {resolved_regime['regime']} statutory material was found in the legal corpus. "
                "No modern provision was substituted or relabelled.",
                status="empty",
            )

        provisions = [self._to_provision(result, question, resolved_regime) for result in results]
        citations = list(dict.fromkeys(p.citation for p in provisions))
        retrieval_method = getattr(
            self.retriever,
            "last_retrieval_method",
            results[0].metadata.get("retrieval_method", "hybrid_rrf") if results else "not_run",
        )
        reranker_status = getattr(
            self.retriever,
            "last_reranker_status",
            results[0].metadata.get("reranker_status", "not_run") if results else "not_run",
        )
        return LegalResearchResult(
            research_id=f"RES-LEG-{uuid4().hex[:8].upper()}",
            side=self.side,
            status="completed",
            question=question,
            findings=self._synthesize_findings(question, provisions),
            applicable_provisions=provisions,
            citations=citations,
            source_pages=sorted(set(p.page for p in provisions)),
            reasoning_relevance=(
                f"{resolved_regime['reasoning']} Retrieved only: {', '.join(sorted(set(p.short_name for p in provisions)))}."
            ),
            retrieval_method=retrieval_method,
            reranker_status=reranker_status,
        )

    def _to_provision(self, result: RetrievalResult, question: str, regime: dict[str, Any]) -> ApplicableProvision:
        provision = result.section or result.article or "General Provision"
        return ApplicableProvision(
            act_name=result.act_name,
            short_name=result.short_name,
            section_or_article=provision,
            title=result.title,
            page=result.page,
            source_file=result.source_file,
            chunk_id=result.chunk_id,
            citation=result.citation(),
            text=result.text,
            relevance_reasoning=self._derive_relevance(result.act_name, provision, question),
            applicable_version=regime["regime"],
            legal_ingredients=self._extract_legal_ingredients(result.text),
            applicability_confidence=regime.get("applicability_confidence", "high"),
            applicability_uncertainty=(
                regime["reasoning"] if regime.get("applicability_confidence") == "uncertain" else None
            ),
        )

    def _empty_result(
        self,
        question: str,
        regime: dict[str, Any],
        limitation: str,
        status: Literal["empty", "unavailable", "failed"] = "empty",
    ) -> LegalResearchResult:
        return LegalResearchResult(
            research_id=f"RES-LEG-{uuid4().hex[:8].upper()}",
            side=self.side,
            status=status,
            error_message=limitation,
            question=question,
            findings=limitation,
            applicable_provisions=[],
            citations=[],
            source_pages=[],
            reasoning_relevance=f"{regime['reasoning']} {limitation}",
        )

    def _derive_relevance(self, act_name: str, provision: str, question: str) -> str:
        focus = "the State's burden to prove every ingredient" if self.side == "prosecution" else (
            "whether proof, admissibility, and safeguards create reasonable doubt" if self.side == "defense" else "the judicial issue presented"
        )
        return f"{act_name}, {provision} is retrieved for {focus}: {question}"

    @staticmethod
    def _extract_legal_ingredients(text: str) -> list[str]:
        sentences = re.split(r"(?<=[.;])\s+", text)
        selected = [sentence.strip() for sentence in sentences if re.search(
            r"\b(shall|must|whoever|where|unless|provided|presum|proof|burden|admissib)\b", sentence, re.I
        )]
        return selected[:4]

    @staticmethod
    def _synthesize_findings(question: str, provisions: list[ApplicableProvision]) -> str:
        lead = provisions[0]
        return (
            f"The research found {len(provisions)} source-traceable provision(s) for '{question}'. "
            f"The highest-ranked source is {lead.citation}."
        )
