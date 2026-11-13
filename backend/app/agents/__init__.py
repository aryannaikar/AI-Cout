"""
Courtroom Agents package for AI Court of India.
Provides all 10 adversarial and judicial roles for Phase 2.
"""

from app.agents.case_agent import CaseUnderstandingAgent
from app.agents.conflict_agent import ConflictDetectionAgent
from app.agents.defense_agent import DefenseAgent
from app.agents.evidence_agent import EvidenceAnalysisAgent
from app.agents.judge_agent import JudgeAgent
from app.agents.legal_research_agent import LegalResearchAgent
from app.agents.prosecutor_agent import ProsecutorAgent
from app.agents.web_research_agent import WebResearchAgent

__all__ = [
    "CaseUnderstandingAgent",
    "EvidenceAnalysisAgent",
    "LegalResearchAgent",
    "WebResearchAgent",
    "ProsecutorAgent",
    "DefenseAgent",
    "ConflictDetectionAgent",
    "JudgeAgent",
]
