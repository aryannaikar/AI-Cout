"""
Query processing for Legal RAG to extract semantic concepts and suggest acts.
"""
from dataclasses import dataclass
from typing import Optional
import re

@dataclass
class ProcessedQuery:
    original_query: str
    suggested_act: Optional[str]
    keywords: list[str]
    historical_statute_requested: Optional[str] = None

class QueryProcessor:
    """Heuristic query processor to suggest act filters based on query content."""

    def __init__(self):
        # Map of concepts to Act short_names
        self.act_keywords = {
            "BSA": ["evidence", "admissibility", "relevancy", "sakshya", "electronic record", "witness", "confession", "admissible"],
            "BNS": ["punishment", "offence", "nyaya", "murder", "theft", "stolen property", "fabricating", "cheating"],
            "IT_Act": ["computer", "cyber", "electronic signature", "tampering", "source code", "hacking"],
            "Constitution": ["constitution", "fundamental right", "liberty", "article", "directive principle", "writ"]
        }

    def process(self, query: str) -> ProcessedQuery:
        query_lower = query.lower()
        
        # Explicit act mentions - Modern
        if re.search(r'\b(bsa|bharatiya sakshya adhiniyam)\b', query_lower):
            return ProcessedQuery(query, "BSA", [], historical_statute_requested=None)
        if re.search(r'\b(bns|bharatiya nyaya sanhita)\b', query_lower):
            return ProcessedQuery(query, "BNS", [], historical_statute_requested=None)
        if re.search(r'\b(it act|information technology act)\b', query_lower):
            return ProcessedQuery(query, "IT_Act", [], historical_statute_requested=None)
        if re.search(r'\b(constitution)\b', query_lower):
            return ProcessedQuery(query, "Constitution", [], historical_statute_requested=None)

        # Historical statutes must remain source-faithful. Returning a BSA/BNS
        # chunk and relabelling it IEA/IPC creates an unsupported citation.
        if re.search(r'\b(indian evidence act|evidence act,? 1872|iea)\b', query_lower):
            return ProcessedQuery(query, "IEA", [], historical_statute_requested="Indian Evidence Act, 1872")
        if re.search(r'\b(indian penal code|ipc)\b', query_lower):
            return ProcessedQuery(query, "IPC", [], historical_statute_requested="Indian Penal Code, 1860")
        if re.search(r'\b(crpc|code of criminal procedure)\b', query_lower):
            return ProcessedQuery(query, "CrPC", [], historical_statute_requested="Code of Criminal Procedure, 1973")
        if re.search(r'(railway property|r\.?p\.?\(?u\.?p\.?\)?\s*act)', query_lower):
            return ProcessedQuery(query, "RPUP_Act", [], historical_statute_requested="Railway Property (Unlawful Possession) Act, 1966")
        if re.search(r'\barms act\b', query_lower):
            return ProcessedQuery(query, "Arms_Act", [], historical_statute_requested="Arms Act, 1959")

        # Implicit concept scoring
        act_scores = {act: 0 for act in self.act_keywords}
        for act, keywords in self.act_keywords.items():
            for kw in keywords:
                if re.search(rf'\b{kw}\b', query_lower):
                    act_scores[act] += 1

        # Pick the act with the highest score if > 0
        best_act = None
        max_score = 0
        for act, score in act_scores.items():
            if score > max_score:
                max_score = score
                best_act = act

        return ProcessedQuery(
            original_query=query,
            suggested_act=best_act,
            keywords=[]
        )
