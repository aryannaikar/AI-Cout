"""
Phase 5 Tests: Document Loaders and Judicial Normalization.
Verifies loading across PDF, TXT, and JSON formats and normalization into
the canonical NormalizedJudgment intermediate representation.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
import pymupdf

from app.comparison.errors import InvalidJudgmentFormatError, RealJudgmentNotFoundError
from app.comparison.extractor import JudgmentNormalizer
from app.comparison.loaders import ComparisonDocumentLoader
from app.comparison.schemas import NormalizedJudgment, OperativeVerdict, StatuteEra
from app.models.judgment_models import Judgment


def test_load_ai_judgment_from_pydantic_model(synthetic_ai_judgment: Judgment):
    """Verify loading AI Judgment directly from Judgment Pydantic model."""
    loaded = ComparisonDocumentLoader.load_ai_judgment(synthetic_ai_judgment)
    assert isinstance(loaded, Judgment)
    assert loaded.case_title == "State v. Jai Bhagwan"


def test_load_ai_judgment_from_json_string(synthetic_ai_judgment_json: str):
    """Verify loading AI Judgment from JSON string."""
    loaded = ComparisonDocumentLoader.load_ai_judgment(synthetic_ai_judgment_json)
    assert isinstance(loaded, Judgment)
    assert loaded.final_decision == "ACQUITTAL"


def test_load_ai_judgment_from_json_file(tmp_path: Path, synthetic_ai_judgment_json: str):
    """Verify loading AI Judgment from .json file path on disk."""
    json_path = tmp_path / "ai_judgment.json"
    json_path.write_text(synthetic_ai_judgment_json, encoding="utf-8")

    loaded = ComparisonDocumentLoader.load_ai_judgment(json_path)
    assert isinstance(loaded, Judgment)
    assert loaded.judgment_id == "JUDG-SYNTH-001"


def test_load_ai_judgment_from_pdf_file(tmp_path: Path, synthetic_ai_judgment_json: str):
    """Verify loading AI Judgment from .pdf file."""
    pdf_path = tmp_path / "ai_judgment.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text(pymupdf.Point(50, 50), "SECTION 10: OPERATIVE ORDER\nVERDICT: ACQUITTAL\nSECTION 11: REASONS\nBenefit of doubt granted.")
    doc.save(str(pdf_path))
    doc.close()

    loaded = ComparisonDocumentLoader.load_ai_judgment(pdf_path)
    assert isinstance(loaded, str)
    assert "ACQUITTAL" in loaded


def test_load_real_judgment_from_text(real_court_judgment_text: str):
    """Verify loading Real Court Judgment from string."""
    loaded = ComparisonDocumentLoader.load_real_judgment(real_court_judgment_text)
    assert isinstance(loaded, str)
    assert "Jai Bhagwan" in loaded


def test_load_real_judgment_from_pdf(real_court_judgment_pdf: Path):
    """Verify loading Real Court Judgment from PDF file."""
    loaded = ComparisonDocumentLoader.load_real_judgment(real_court_judgment_pdf)
    assert isinstance(loaded, str)
    assert "Jai Bhagwan" in loaded
    assert "Section 411" in loaded


def test_load_real_judgment_none_raises_error():
    """Verify loading None for Real Judgment raises RealJudgmentNotFoundError."""
    with pytest.raises(RealJudgmentNotFoundError):
        ComparisonDocumentLoader.load_real_judgment(None)


def test_load_optional_case_packet(tmp_path: Path, sample_case_packet_txt: str):
    """Verify loading optional Case Packet."""
    # None returns None
    assert ComparisonDocumentLoader.load_case_packet(None) is None

    # String returns string
    assert "Kashmere Gate" in ComparisonDocumentLoader.load_case_packet(sample_case_packet_txt)

    # PDF returns extracted text
    packet_pdf = tmp_path / "Case_Packet.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text(pymupdf.Point(50, 50), sample_case_packet_txt)
    doc.save(str(packet_pdf))
    doc.close()

    res = ComparisonDocumentLoader.load_case_packet(packet_pdf)
    assert res is not None
    assert "Kashmere Gate" in res


def test_normalization_ai_judgment(synthetic_ai_judgment: Judgment):
    """Verify normalizing AI Judgment model captures all required facets."""
    norm = JudgmentNormalizer.normalize_ai_judgment(synthetic_ai_judgment)
    assert isinstance(norm, NormalizedJudgment)
    assert norm.case_title == "State v. Jai Bhagwan"
    assert norm.verdict == OperativeVerdict.ACQUITTAL
    assert len(norm.charges) >= 1
    assert norm.charges[0].era == StatuteEra.MODERN_BNS_BNSS_BSA
    assert len(norm.legal_issues) == 2
    assert norm.reasoning.ratio_decidendi != ""


def test_normalization_real_court_judgment(real_court_judgment_text: str):
    """Verify normalizing Real Court Judgment text captures operative facts, charges, and verdict."""
    norm = JudgmentNormalizer.normalize_real_judgment(real_court_judgment_text)
    assert isinstance(norm, NormalizedJudgment)
    assert norm.case_title == "State v. Jai Bhagwan"
    assert norm.verdict in (OperativeVerdict.ACQUITTAL, OperativeVerdict.APPEAL_ALLOWED)
    assert any("411" in c.statute for c in norm.charges)
    assert any(c.era == StatuteEra.HISTORICAL_IPC_CRPC for c in norm.charges)
    assert len(norm.legal_issues) >= 1
    assert len(norm.prosecution_witnesses) >= 1
    assert any(w.witness_id == "PW-1" for w in norm.prosecution_witnesses)
    assert any(w.witness_id == "PW-6" for w in norm.prosecution_witnesses)
    assert len(norm.evidence_items) >= 1
    assert any("P-1" in e.exhibit_id for e in norm.evidence_items)
