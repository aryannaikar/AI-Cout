"""
Security and data separation tests.
Verifies strict isolation between Case Packet, Ground Truth Verdict, and Legal Corpus.
"""

from pathlib import Path
import pytest
from rag.loader import PDFLoader
from rag.config import config


def test_verdict_file_blocked_from_loader(tmp_path: Path):
    loader = PDFLoader()
    verdict_fake = tmp_path / "Ground_Truth_Verdict.pdf"
    verdict_fake.write_bytes(b"%PDF-1.4 dummy verdict content")

    # Attempting to load a verdict file MUST raise PermissionError
    with pytest.raises(PermissionError, match="SECURITY VIOLATION"):
        loader.load_pdf(verdict_fake)


def test_judgment_file_blocked_from_loader(tmp_path: Path):
    loader = PDFLoader()
    judgment_fake = tmp_path / "court_judgment.pdf"
    judgment_fake.write_bytes(b"%PDF-1.4 dummy judgment content")

    # Attempting to load any judgment file MUST raise PermissionError
    with pytest.raises(PermissionError, match="SECURITY VIOLATION"):
        loader.load_pdf(judgment_fake)


def test_case_packet_not_in_legal_corpus():
    """Ensure the legal corpus directory does NOT contain any case files or verdict files."""
    legal_files = list(config.legal_corpus_dir.glob("**/*"))
    for f in legal_files:
        name_lower = f.name.lower()
        assert "verdict" not in name_lower, f"Prohibited verdict file found in corpus: {f}"
        assert "judgment" not in name_lower, f"Prohibited judgment file found in corpus: {f}"
        assert "case_packet" not in name_lower, f"Case packet must not be in legal corpus: {f}"
