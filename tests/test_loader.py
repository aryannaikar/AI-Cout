"""
Unit and integration tests for PDF loading and text extraction.
"""

from pathlib import Path
import pytest
from rag.loader import PDFLoader, extract_pdf_pages, extract_pdf_text
from rag.config import config


def test_load_existing_pdf():
    loader = PDFLoader()
    pdf_path = config.legal_corpus_dir / "it_act" / "information_technology_act_2000.pdf"
    assert pdf_path.exists(), f"IT Act PDF not found at {pdf_path}"

    pages = loader.load_pdf(pdf_path)
    assert len(pages) > 0
    assert pages[0].page_number == 1
    assert len(pages[0].text) > 0
    assert pages[0].source_file == pdf_path.name


def test_load_document_with_metadata():
    loader = PDFLoader()
    pdf_path = config.legal_corpus_dir / "bns" / "bharatiya_nyaya_sanhita_2023.pdf"
    assert pdf_path.exists(), f"BNS PDF not found at {pdf_path}"

    doc = loader.load_document(pdf_path)
    assert doc.act_name == "Bharatiya Nyaya Sanhita, 2023"
    assert doc.short_name == "BNS"
    assert doc.year == 2023
    assert doc.document_type == "act"
    assert doc.total_pages == 102
    assert len(doc.full_text) > 1000


def test_load_missing_pdf_raises_error():
    loader = PDFLoader()
    missing_path = Path("data/non_existent_file.pdf")
    with pytest.raises(FileNotFoundError):
        loader.load_pdf(missing_path)


def test_functional_helpers():
    pdf_path = config.legal_corpus_dir / "bsa" / "Bharatiya Sakshya Adhiniyam, 2023 (BSA).pdf"
    assert pdf_path.exists()

    pages = extract_pdf_pages(str(pdf_path))
    assert isinstance(pages, list)
    assert len(pages) == 47
    assert "page" in pages[0]
    assert "text" in pages[0]

    text = extract_pdf_text(str(pdf_path))
    assert isinstance(text, str)
    assert len(text) > 1000
