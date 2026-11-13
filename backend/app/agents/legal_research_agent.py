"""
Legal Research Agent for AI Court of India.
Reusable across Prosecution and Defense perspectives.
Integrates directly with the stable Phase-1 LegalRetriever and persistent ChromaDB.
"""

from __future__ import annotations

import logging
import re
from typing import Literal, Optional
from uuid import uuid4

from app.models.legal_models import ApplicableProvision, LegalResearchResult
from app.services.legal_transition import map_provision_to_historical
from rag.retriever import LegalRetriever, RetrievalResult

logger = logging.getLogger(__name__)


class LegalResearchAgent:
    """
    Researches statutory law using the local Phase-1 LegalRetriever.
    Reusable for both prosecution and defense viewpoints.
    """

    def __init__(
        self,
        side: Literal["prosecution", "defense", "judicial"] = "prosecution",
        retriever: Optional[LegalRetriever] = None,
    ):
        self.side = side
        self.retriever = retriever or LegalRetriever(top_k=5)
        logger.info("Initialized LegalResearchAgent for side: '%s'", self.side)

    def research(
        self,
        question: str,
        top_k: Optional[int] = None,
        act_filter: Optional[str] = None,
        is_historical: bool = False,
    ) -> LegalResearchResult:
        """
        Execute legal research against the local legal corpus.

        Args:
            question: Legal question (e.g. 'What constitutes receiving stolen property under BNS?').
            top_k: Number of statutory chunks to retrieve.
            act_filter: Optional statute filter ('BNS', 'BSA', 'IT_Act', 'Constitution').
            is_historical: If True, grounds findings and citations in historical statutes (IEA/IPC).

        Returns:
            LegalResearchResult with grounded provisions, page citations, and relevance analysis.
        """
        logger.info("[%s Legal Research] Query: '%s' (is_historical=%s)", self.side.upper(), question, is_historical)

        # Detect historical intent from query terms if not explicitly set
        q_lower = question.lower()
        if not is_historical and any(term in q_lower for term in ["indian evidence act", "evidence act 1872", "iea", "indian penal code", "ipc"]):
            is_historical = True

        retrieval_results = self.retriever.retrieve(
            query=question,
            top_k=top_k or 5,
            act_filter=act_filter,
        )

        applicable_provisions: list[ApplicableProvision] = []
        citations: list[str] = []
        source_pages: list[int] = []

        for r in retrieval_results:
            prov_name = r.section or r.article or "General Provision"
            act_name = r.act_name
            short_name = r.short_name

            if is_historical:
                mapped_act, mapped_prov = map_provision_to_historical(act_name, prov_name)
                cit = f"{mapped_act}, {mapped_prov} [Source: {r.source_file}, Page {r.page}]"
                act_name = mapped_act
                prov_name = mapped_prov
            else:
                cit = r.citation()

            citations.append(cit)
            source_pages.append(r.page)

            # Contextual reasoning tailored by side
            relevance = self._derive_relevance_mapped(act_name, prov_name, question)

            applicable_provisions.append(
                ApplicableProvision(
                    act_name=act_name,
                    short_name=short_name,
                    section_or_article=prov_name,
                    title=r.title,
                    page=r.page,
                    source_file=r.source_file,
                    chunk_id=r.chunk_id,
                    citation=cit,
                    text=r.text,
                    relevance_reasoning=relevance,
                )
            )

        # Synthesize overall finding
        findings = self._synthesize_findings(question, applicable_provisions)
        reasoning = (
            f"From the {self.side} perspective, the governing legal framework rests upon "
            + (", ".join(citations[:3]) if citations else "the applicable statutory rules")
            + ". These provisions dictate the legal standard and evidentiary thresholds required."
        )

        return LegalResearchResult(
            research_id=f"RES-LEG-{uuid4().hex[:8].upper()}",
            side=self.side,
            question=question,
            findings=findings,
            applicable_provisions=applicable_provisions,
            citations=list(dict.fromkeys(citations)),  # deduplicate preserving order
            source_pages=sorted(list(set(source_pages))),
            reasoning_relevance=reasoning,
        )

    def _derive_relevance_mapped(self, act_name: str, prov: str, question: str) -> str:
        """Derive substantive relevance based on courtroom side and applicable statute."""
        if self.side == "prosecution":
            return (
                f"From the prosecution perspective, {act_name}, {prov} establishes the essential statutory ingredients "
                f"that the State must substantiate to prove culpability beyond reasonable doubt."
            )
        elif self.side == "defense":
            return (
                f"From the defense perspective, {act_name}, {prov} sets the statutory limits, exceptions, and mandatory "
                f"procedural safeguards which the prosecution has failed to strictly comply with, creating reasonable doubt."
            )
        return f"{act_name}, {prov} governs the legal question: '{question}'."

    def _derive_relevance(self, r: RetrievalResult, question: str) -> str:
        """Derive substantive relevance based on courtroom side."""
        prov = r.section or r.article or "the provision"
        return self._derive_relevance_mapped(r.act_name, prov, question)

    def _synthesize_findings(self, question: str, provisions: list[ApplicableProvision]) -> str:
        """Synthesize overall finding from retrieved statutory text."""
        if not provisions:
            return f"No statutory provisions directly matched the query '{question}' in the local corpus."

        top_p = provisions[0]
        return (
            f"Under {top_p.act_name}, {top_p.section_or_article}, the governing legal principle is: "
            f"{top_p.text[:200]}... This directly resolves the query regarding '{question}'."
        )
