"""
Evidence Intelligence Builder for Phase 3.
Builds canonical witnesses, canonical exhibits, EvidenceTimeline, AccusedEvidenceMapping,
ContradictionMatrix, RecoveryChainAnalysis, and gated MedicalForensicComparison
without inventing metadata or merging distinct persons.
"""

from __future__ import annotations

import re
from typing import Optional

from app.models.case_models import StructuredCase
from app.models.evidence_models import (
    AccusedEvidenceMapping,
    CanonicalExhibitRecord,
    CanonicalWitnessRecord,
    ContradictionEntry,
    ContradictionMatrix,
    EvidenceTimeline,
    MedicalForensicComparison,
    RecoveryChainAnalysis,
    TimelineEvent,
)
from app.models.evidence_package_models import EvidencePackage


_DATE_RE = re.compile(
    r"\b(?:\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}"
    r"|\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{4}[/\-]\d{1,2}[/\-]\d{1,2})\b",
    re.IGNORECASE,
)


def _norm_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip()).casefold()


def _text_mentions_person(text: str, person: str, all_persons: list[str]) -> bool:
    """
    Check if text attributes an item to `person` without confusing similarly-named individuals
    (e.g., 'Md. Israful Ansari' vs 'Israfil Ansari').
    """
    p_norm = _norm_name(person)
    if not p_norm:
        return False
    t_norm = _norm_name(text)
    if re.search(rf"(?<![a-z0-9]){re.escape(p_norm)}(?![a-z0-9])", t_norm):
        return True
    return False


class EvidenceIntelligenceBuilder:
    """Canonical deterministic builder for Phase 3 Evidence Intelligence."""

    @classmethod
    def build(
        cls,
        case: Optional[StructuredCase] = None,
        package: Optional[EvidencePackage] = None,
    ) -> dict:
        witnesses = cls._build_canonical_witnesses(case, package)
        exhibits = cls._build_canonical_exhibits(case, package)
        timeline = cls._build_timeline(case, package)
        accused_mappings = cls._build_accused_mappings(case, package, witnesses, exhibits)
        contradiction_matrix = cls._build_contradiction_matrix(case, package)
        recovery_analyses = cls._build_recovery_analyses(case, package, exhibits, witnesses)
        medical_forensic = cls._build_medical_forensic(case, package, witnesses)

        return {
            "canonical_witnesses": witnesses,
            "canonical_exhibits": exhibits,
            "timeline": timeline,
            "accused_mappings": accused_mappings,
            "contradiction_matrix": contradiction_matrix,
            "recovery_analyses": recovery_analyses,
            "medical_forensic_comparison": medical_forensic,
        }

    @classmethod
    def _build_canonical_witnesses(
        cls,
        case: Optional[StructuredCase],
        package: Optional[EvidencePackage],
    ) -> list[CanonicalWitnessRecord]:
        by_key: dict[tuple[str, str], CanonicalWitnessRecord] = {}
        if case and case.witnesses:
            for w in case.witnesses:
                wid = w.witness_id.strip().upper()
                wname = w.witness_name.strip()
                key = (wid, _norm_name(wname))
                side = "defense" if wid.startswith("DW") or w.witness_type == "defense_witness" else (
                    "prosecution" if wid.startswith("PW") else "unknown"
                )
                if key not in by_key:
                    by_key[key] = CanonicalWitnessRecord(
                        witness_id=wid,
                        witness_name=wname,
                        side=side,
                        role=w.witness_type,
                        statement_references=[f"{wid} deposition"],
                        material_assertions=list(w.key_assertions),
                        source_references=[f"{wid}: {wname}"],
                    )
        if package:
            pkg_witnesses = [
                *(getattr(package, "prosecution_witnesses", []) or []),
                *(getattr(package, "defence_witnesses", []) or []),
            ]
            for w in pkg_witnesses:
                wid = (getattr(w, "witness_code", None) or getattr(w, "witness_id", None) or getattr(w, "witness_number", "") or "").strip().upper()
                wname = (w.name or "").strip()
                key = (wid, _norm_name(wname))
                raw_side = (getattr(w, "side", None) or "").strip().lower()
                if raw_side in ("prosecution", "defense", "court", "unknown"):
                    side = raw_side
                elif raw_side == "defence":
                    side = "defense"
                else:
                    side = "defense" if wid.startswith("DW") else ("prosecution" if wid.startswith("PW") else "unknown")
                if key not in by_key:
                    linked_ex = getattr(w, "linked_exhibits", None) or getattr(w, "evidence_referred_to", None) or []
                    assertions = getattr(w, "key_assertions", None) or getattr(w, "facts_testified", None) or ([w.testimony_summary] if getattr(w, "testimony_summary", None) else [])
                    by_key[key] = CanonicalWitnessRecord(
                        witness_id=wid,
                        witness_name=wname,
                        side=side,
                        role=w.role,
                        statement_references=[f"{wid} (Page {w.source_page or 'record'})"],
                        related_exhibits=list(linked_ex),
                        material_assertions=list(assertions),
                        source_references=[f"Page {w.source_page}" if w.source_page else wid],
                    )
        return list(by_key.values())

    @classmethod
    def _build_canonical_exhibits(
        cls,
        case: Optional[StructuredCase],
        package: Optional[EvidencePackage],
    ) -> list[CanonicalExhibitRecord]:
        by_id: dict[str, CanonicalExhibitRecord] = {}
        if case and case.exhibits:
            for ex in case.exhibits:
                key = ex.exhibit_id.strip().upper()
                is_marked = bool(re.search(r"\b(?:ex(?:t|hibit)?\.?|mo|material)\b", ex.exhibit_id, re.IGNORECASE))
                if key not in by_id:
                    by_id[key] = CanonicalExhibitRecord(
                        exhibit_id=ex.exhibit_id.strip(),
                        exhibit_marking=ex.exhibit_id.strip(),
                        is_formally_marked=is_marked,
                        description=ex.description,
                        document_type=ex.exhibit_type,
                        introducing_witness=ex.marked_by or None,
                        source_reference=f"{ex.exhibit_id} ({ex.title})",
                        chain_of_custody_notes=[ex.admissibility_notes] if ex.admissibility_notes else [],
                        verification_status="formally_marked" if is_marked else "narrative_mention_only",
                    )
        if package and package.exhibits:
            for ex in package.exhibits:
                key = ex.exhibit_number.strip().upper()
                if key not in by_id:
                    by_id[key] = CanonicalExhibitRecord(
                        exhibit_id=ex.evidence_id,
                        exhibit_marking=ex.exhibit_number,
                        is_formally_marked=True,
                        description=ex.description,
                        document_type=ex.evidence_type,
                        introducing_witness=ex.introduced_through_witness,
                        source_reference=f"{ex.exhibit_number} (Page {ex.source_page or 'record'})",
                        verification_status="formally_marked",
                    )
        return list(by_id.values())

    @classmethod
    def _build_timeline(
        cls,
        case: Optional[StructuredCase],
        package: Optional[EvidencePackage],
    ) -> EvidenceTimeline:
        events: list[TimelineEvent] = []
        date_conflicts: list[str] = []
        idx = 1

        if case:
            for fact in case.prosecution_facts:
                dates = _DATE_RE.findall(fact)
                stage = "incident"
                fl = fact.lower()
                if any(k in fl for k in ("recover", "seiz", "panchnama")):
                    stage = "recovery_seizure"
                elif any(k in fl for k in ("arrest", "apprehend")):
                    stage = "arrest"
                elif any(k in fl for k in ("fir", "investigat", "enquir", "charge")):
                    stage = "investigation"
                elif any(k in fl for k in ("medical", "post-mortem", "forensic", "expert")):
                    stage = "medical_forensic"

                has_conflict = len(set(d.lower() for d in dates)) > 1 and "conflict" in fl
                if has_conflict:
                    date_conflicts.append(f"Conflicting dates noted in event: {dates}")
                events.append(
                    TimelineEvent(
                        event_id=f"EVT-{idx:02d}",
                        stage=stage,
                        date_text=dates[0] if dates else None,
                        description=fact,
                        source_reference="Prosecution facts",
                        has_date_conflict=has_conflict,
                        conflicting_dates=dates if has_conflict else [],
                    )
                )
                idx += 1

            if case.procedural_history:
                dates = _DATE_RE.findall(case.procedural_history)
                events.append(
                    TimelineEvent(
                        event_id=f"EVT-{idx:02d}",
                        stage="trial_procedural",
                        date_text=dates[0] if dates else None,
                        description=case.procedural_history,
                        source_reference="Procedural history",
                    )
                )
        elif package:
            for ev in getattr(package, "timeline_of_events", []) or []:
                events.append(
                    TimelineEvent(
                        event_id=f"EVT-{idx:02d}",
                        stage="incident",
                        date_text=getattr(ev, "date", None),
                        time_text=getattr(ev, "time", None),
                        location=getattr(ev, "location", None),
                        description=getattr(ev, "event_description", ""),
                        source_reference=f"Page {ev.source_page}" if getattr(ev, "source_page", None) else "EvidencePackage",
                    )
                )
                idx += 1
            for proc in getattr(package, "procedural_records", []) or []:
                events.append(
                    TimelineEvent(
                        event_id=f"EVT-{idx:02d}",
                        stage="investigation",
                        date_text=getattr(proc, "date", None),
                        time_text=None,
                        location=None,
                        description=f"{getattr(proc, 'procedure_type', 'Procedure')}: {getattr(proc, 'description', '') or getattr(proc, 'related_document', '')}".strip(": "),
                        source_reference=f"Page {proc.source_page}" if getattr(proc, "source_page", None) else "EvidencePackage",
                    )
                )
                idx += 1
            for rec in getattr(package, "recoveries", []) or []:
                events.append(
                    TimelineEvent(
                        event_id=f"EVT-{idx:02d}",
                        stage="recovery_seizure",
                        date_text=getattr(rec, "date", None),
                        time_text=None,
                        location=getattr(rec, "location", None),
                        description=f"Recovery of {getattr(rec, 'recovered_item', 'item')}",
                        source_reference=f"Page {rec.source_page}" if getattr(rec, "source_page", None) else "EvidencePackage",
                    )
                )
                idx += 1

        return EvidenceTimeline(events=events, date_conflicts_detected=date_conflicts)

    @classmethod
    def _build_accused_mappings(
        cls,
        case: Optional[StructuredCase],
        package: Optional[EvidencePackage],
        witnesses: list[CanonicalWitnessRecord],
        exhibits: list[CanonicalExhibitRecord],
    ) -> list[AccusedEvidenceMapping]:
        if not case:
            return []

        subjects = case.distinct_decision_subjects() if hasattr(case, "distinct_decision_subjects") else list(case.accused)
        if not subjects:
            return []

        proc_by_accused: dict[str, str] = {}
        for proc in getattr(case, "connected_proceedings", []):
            for person in proc.accused_or_petitioners:
                proc_by_accused[_norm_name(person)] = proc.proceeding_id

        mappings: list[AccusedEvidenceMapping] = []
        for person in subjects:
            p_norm = _norm_name(person)
            allegations = [f for f in case.prosecution_facts if _text_mentions_person(f, person, subjects)]
            exculpatory = [f for f in case.defense_facts if _text_mentions_person(f, person, subjects)]
            w_refs: list[str] = []
            for w in witnesses:
                joined = " ".join([w.role, *w.material_assertions])
                if _text_mentions_person(joined, person, subjects):
                    w_refs.append(f"{w.witness_id} ({w.witness_name})")

            doc_ex: list[str] = []
            phys_ex: list[str] = []
            rec_ex: list[str] = []
            exp_ex: list[str] = []
            for ex in exhibits:
                if _text_mentions_person(f"{ex.description} {ex.source_reference}", person, subjects):
                    label = f"{ex.exhibit_marking}: {ex.description}"
                    if any(k in ex.document_type.lower() or k in ex.description.lower() for k in ("recover", "seiz", "memo")):
                        rec_ex.append(label)
                    elif any(k in ex.document_type.lower() for k in ("medical", "forensic", "expert")):
                        exp_ex.append(label)
                    elif "physical" in ex.document_type.lower():
                        phys_ex.append(label)
                    else:
                        doc_ex.append(label)

            charges = [
                f"{c.statute}, {c.section}"
                for c in case.charges
                if c.record_status == "current" and (
                    _norm_name(c.accused_name) == p_norm
                    or _norm_name(c.accused_name) in {"accused", "all accused", "petitioners"}
                )
            ]

            mappings.append(
                AccusedEvidenceMapping(
                    accused_name=person,
                    proceeding_id=proc_by_accused.get(p_norm),
                    allegations=allegations,
                    witness_testimony=w_refs,
                    documentary_evidence=doc_ex,
                    physical_exhibits=phys_ex,
                    recovery_evidence=rec_ex,
                    expert_evidence=exp_ex,
                    exculpatory_or_defense_evidence=exculpatory,
                    missing_evidence=list(case.missing_or_uncertain_info),
                    related_charges=charges,
                )
            )
        return mappings

    @classmethod
    def _build_contradiction_matrix(
        cls,
        case: Optional[StructuredCase],
        package: Optional[EvidencePackage],
    ) -> ContradictionMatrix:
        entries: list[ContradictionEntry] = []
        idx = 1

        if case:
            for disp in case.disputed_facts:
                dl = disp.lower()
                materiality = "minor_inconsistency" if "minor" in dl or "trivial" in dl else "material_contradiction"
                entries.append(
                    ContradictionEntry(
                        contradiction_id=f"CM-{idx:02d}",
                        issue=disp,
                        source_a="Prosecution record",
                        source_b="Defence contention",
                        conflicting_content=disp,
                        materiality=materiality,
                        resolution_status="unresolved",
                    )
                )
                idx += 1
            for gap in case.missing_or_uncertain_info:
                entries.append(
                    ContradictionEntry(
                        contradiction_id=f"CM-{idx:02d}",
                        issue=gap,
                        source_a="Evidentiary record",
                        source_b="Statutory proof requirement",
                        conflicting_content=gap,
                        materiality="missing_information",
                        resolution_status="unresolved",
                    )
                )
                idx += 1

        if package:
            for c in package.contradictions:
                entries.append(
                    ContradictionEntry(
                        contradiction_id=f"CM-{idx:02d}",
                        issue=c.description,
                        source_a=c.source_a or "Source A",
                        source_b=c.source_b or "Source B",
                        conflicting_content=c.description,
                        materiality="material_contradiction",
                        resolution_status="unresolved",
                    )
                )
                idx += 1

        return ContradictionMatrix(
            entries=entries,
            material_count=sum(1 for e in entries if e.materiality == "material_contradiction"),
            minor_count=sum(1 for e in entries if e.materiality == "minor_inconsistency"),
        )

    @classmethod
    def _build_recovery_analyses(
        cls,
        case: Optional[StructuredCase],
        package: Optional[EvidencePackage],
        exhibits: list[CanonicalExhibitRecord],
        witnesses: list[CanonicalWitnessRecord],
    ) -> list[RecoveryChainAnalysis]:
        analyses: list[RecoveryChainAnalysis] = []
        idx = 1
        panch_witnesses = [f"{w.witness_id} ({w.witness_name})" for w in witnesses if "panch" in w.role.lower()]

        for ex in exhibits:
            desc_l = f"{ex.document_type} {ex.description}".lower()
            if any(k in desc_l for k in ("recover", "seiz", "panchnama", "material_object", "physical")):
                missing_links = list(ex.chain_of_custody_notes)
                if not panch_witnesses:
                    missing_links.append("Independent public/panch witness attestation not established on record.")
                if not ex.introducing_witness:
                    missing_links.append("Recovering/introducing officer not explicitly identified.")
                analyses.append(
                    RecoveryChainAnalysis(
                        recovery_id=f"REC-{idx:02d}",
                        item_description=ex.description,
                        recovered_by=ex.introducing_witness,
                        seizure_documentation=ex.exhibit_marking if ex.is_formally_marked else None,
                        witnesses_present=panch_witnesses,
                        exhibit_marking=ex.exhibit_marking,
                        missing_links=missing_links,
                    )
                )
                idx += 1
        return analyses

    @classmethod
    def _build_medical_forensic(
        cls,
        case: Optional[StructuredCase],
        package: Optional[EvidencePackage],
        witnesses: list[CanonicalWitnessRecord],
    ) -> MedicalForensicComparison:
        records: list[str] = []
        if case:
            for ex in case.exhibits:
                if any(k in ex.exhibit_type.lower() or k in ex.title.lower() for k in ("medical", "post_mortem", "post-mortem", "forensic", "expert")):
                    records.append(f"{ex.exhibit_id}: {ex.title}")
            for w in case.witnesses:
                if w.witness_type in {"medical_officer", "expert_witness"}:
                    records.append(f"{w.witness_id}: {w.witness_name} ({w.witness_type})")
        if package:
            for ex in package.exhibits:
                if any(k in ex.evidence_type.lower() or k in ex.description.lower() for k in ("medical", "post-mortem", "forensic", "lab")):
                    records.append(f"{ex.exhibit_number}: {ex.description}")

        if not records:
            return MedicalForensicComparison(
                status="not_available",
                source_records=[],
                comparisons=[],
                discrepancies=[],
                notes="not_available: No medical, post-mortem, forensic, or expert report exists in the supplied case record.",
            )

        return MedicalForensicComparison(
            status="available",
            source_records=records,
            comparisons=[f"Expert/medical source present on record: {r}" for r in records],
            discrepancies=[],
            notes="Medical/forensic source records identified and available for judicial comparison against ocular claims.",
        )
