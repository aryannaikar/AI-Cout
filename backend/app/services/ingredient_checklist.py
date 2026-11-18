"""
Canonical Statutory Ingredient Checklist Builder for Phase 3 Judicial Reasoning.
Maps verified statutory text, accused-wise evidence, contradictions, and party rebuttals
to each statutory ingredient without fabricating legal text or evidence.
"""

from __future__ import annotations

from typing import Optional

from app.models.case_models import Charge, StructuredCase
from app.models.evidence_models import EvidenceAnalysisReport
from app.models.judgment_models import (
    DefenseCase,
    IngredientChecklist,
    IngredientItem,
    ProsecutionCase,
)
from app.models.legal_models import ApplicableProvision, LegalResearchResult


class IngredientChecklistBuilder:
    """Builds canonical IngredientChecklist objects for every current charge."""

    @staticmethod
    def build(
        case: StructuredCase,
        evidence_report: Optional[EvidenceAnalysisReport] = None,
        prosecution_legal_research: Optional[LegalResearchResult] = None,
        defense_legal_research: Optional[LegalResearchResult] = None,
        prosecution_case: Optional[ProsecutionCase] = None,
        defense_case: Optional[DefenseCase] = None,
    ) -> list[IngredientChecklist]:
        active_charges = (
            case.current_charges()
            if hasattr(case, "current_charges")
            else [c for c in case.charges if c.record_status == "current"]
        )
        if not active_charges:
            return []

        verified_provisions: list[ApplicableProvision] = []
        for res in (prosecution_legal_research, defense_legal_research):
            if res is not None and getattr(res, "status", "completed") == "completed":
                verified_provisions.extend(res.applicable_provisions)

        accused_map = {}
        if evidence_report and evidence_report.accused_mappings:
            accused_map = {m.accused_name.casefold(): m for m in evidence_report.accused_mappings}

        material_contradictions = []
        if evidence_report and evidence_report.contradiction_matrix:
            material_contradictions = [
                c.issue for c in evidence_report.contradiction_matrix.entries
                if c.materiality == "material_contradiction"
            ]

        checklists: list[IngredientChecklist] = []
        for idx, ch in enumerate(active_charges, start=1):
            matched_prov = IngredientChecklistBuilder._match_provision(ch, verified_provisions)
            mapping = accused_map.get(ch.accused_name.casefold())

            supporting: list[str] = []
            contradictory: list[str] = list(material_contradictions)
            rel_witnesses: list[str] = []
            rel_exhibits: list[str] = []
            if mapping:
                supporting.extend(mapping.allegations)
                supporting.extend(mapping.direct_evidence)
                supporting.extend(mapping.circumstantial_evidence)
                supporting.extend(mapping.recovery_evidence)
                contradictory.extend(mapping.exculpatory_or_defense_evidence)
                contradictory.extend(mapping.missing_evidence)
                rel_witnesses.extend(mapping.witness_testimony)
                rel_exhibits.extend(mapping.documentary_evidence + mapping.physical_exhibits + mapping.recovery_evidence)

            pros_arg = prosecution_case.prosecution_theory if prosecution_case else ""
            def_arg = defense_case.defense_theory if defense_case else ""

            items: list[IngredientItem] = []
            if matched_prov and matched_prov.legal_ingredients:
                for i_idx, ing_text in enumerate(matched_prov.legal_ingredients, start=1):
                    status = "Disputed" if contradictory else ("Supported" if supporting else "Not established")
                    items.append(
                        IngredientItem(
                            ingredient_id=f"ING-{idx}-{i_idx}",
                            legal_description=ing_text,
                            source_citation=matched_prov.citation,
                            supporting_evidence=supporting,
                            contradictory_evidence=contradictory,
                            related_witnesses=rel_witnesses,
                            related_exhibits=rel_exhibits,
                            prosecution_argument=pros_arg,
                            defense_argument=def_arg,
                            assessment_status=status,
                        )
                    )
            elif ch.elements_alleged:
                src_cit = matched_prov.citation if matched_prov else f"{ch.statute}, {ch.section} (record allegation; statutory text not in corpus)"
                for i_idx, elem in enumerate(ch.elements_alleged, start=1):
                    status = "Not assessable" if not matched_prov and not supporting else ("Disputed" if contradictory else "Supported")
                    items.append(
                        IngredientItem(
                            ingredient_id=f"ING-{idx}-{i_idx}",
                            legal_description=elem,
                            source_citation=src_cit,
                            supporting_evidence=supporting,
                            contradictory_evidence=contradictory,
                            related_witnesses=rel_witnesses,
                            related_exhibits=rel_exhibits,
                            prosecution_argument=pros_arg,
                            defense_argument=def_arg,
                            assessment_status=status,
                        )
                    )
            else:
                items.append(
                    IngredientItem(
                        ingredient_id=f"ING-{idx}-1",
                        legal_description=ch.description or f"Statutory ingredients of {ch.section} ({ch.statute})",
                        source_citation=matched_prov.citation if matched_prov else f"{ch.statute}, {ch.section} (statutory text unavailable)",
                        supporting_evidence=supporting,
                        contradictory_evidence=contradictory,
                        related_witnesses=rel_witnesses,
                        related_exhibits=rel_exhibits,
                        prosecution_argument=pros_arg,
                        defense_argument=def_arg,
                        assessment_status="Not assessable" if not matched_prov else ("Disputed" if contradictory else "Not established"),
                    )
                )

            checklists.append(
                IngredientChecklist(
                    charge_key=f"{ch.statute}, {ch.section}",
                    act_name=ch.statute,
                    section=ch.section,
                    accused_name=ch.accused_name,
                    ingredients=items,
                )
            )
        return checklists

    @staticmethod
    def _match_provision(
        charge: Charge,
        provisions: list[ApplicableProvision],
    ) -> Optional[ApplicableProvision]:
        sec_low = charge.section.lower().replace("section", "").strip()
        act_low = charge.statute.lower()
        for p in provisions:
            p_sec = p.section_or_article.lower().replace("section", "").strip()
            if sec_low and sec_low == p_sec and (p.short_name.lower() in act_low or p.act_name.lower() in act_low):
                return p
        return None
