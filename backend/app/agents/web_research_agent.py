"""
Web Research Agent for AI Court of India.
Reusable across Prosecution and Defense perspectives.
Performs external legal and statutory research with strict blind-evaluation query guardrails.
"""

from __future__ import annotations

import logging
from typing import Literal, Optional
from uuid import uuid4

from app.models.legal_models import WebResearchItem, WebResearchResult
from app.services.web_search_service import WebSearchService

logger = logging.getLogger(__name__)


class WebResearchAgent:
    """
    Conducts external legal research on judicial precedents, recent amendments,
    and statutory commentaries without compromising the blind evaluation architecture.
    """

    def __init__(
        self,
        side: Literal["prosecution", "defense", "judicial"] = "prosecution",
        search_service: Optional[WebSearchService] = None,
    ):
        self.side = side
        self.search_service = search_service or WebSearchService()
        logger.info("Initialized WebResearchAgent for side: '%s'", self.side)

    def validate_query(self, query: str) -> None:
        """Validate that a web query complies with blind evaluation rules."""
        self.search_service.validate_query_blindness(query)

    def research(
        self,
        question: str,
        max_sources: int = 3,
        force_search: bool = False,
    ) -> WebResearchResult:
        """
        Research external legal authorities relevant to the case.

        Args:
            question: Legal question (e.g. 'Supreme court precedent on Section 63 BSA electronic evidence certificate').
            max_sources: Number of external sources.
            force_search: Force external search even if local RAG might suffice.

        Returns:
            WebResearchResult containing external legal sources, citations, and summaries.
        """
        logger.info("[%s Web Research] Question: '%s'", self.side.upper(), question)

        # Enforce blind evaluation query validation
        self.search_service.validate_query_blindness(question)

        sources = self.search_service.search_legal(
            query=question,
            max_results=max_sources,
            side=self.side,
        )

        if sources:
            primary_src = sources[0]
            finding = (
                f"According to established legal precedent in '{primary_src.title}', "
                f"{primary_src.passage_summary}"
            )
            why_it_matters = primary_src.why_source_matters
        else:
            finding = f"No external authorities found for query: '{question}'."
            why_it_matters = "Local statutory provisions remain the primary governing law."

        return WebResearchResult(
            research_id=f"RES-WEB-{uuid4().hex[:8].upper()}",
            side=self.side,
            research_question=question,
            finding=finding,
            sources=sources,
            why_it_matters=why_it_matters,
        )
