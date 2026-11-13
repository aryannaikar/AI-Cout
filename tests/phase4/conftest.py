"""
Pytest configuration and fixtures for Phase 4 tests.
Generates synthetic legal Case_Packet.pdf files using PyMuPDF for realistic file-based testing.
"""

from pathlib import Path
import pytest
import pymupdf

from tests.phase2.test_case_agent import SAMPLE_CASE_PACKET_TEXT


@pytest.fixture(scope="session")
def sample_case_packet_pdf(tmp_path_factory) -> Path:
    """Generate a realistic synthetic Case_Packet.pdf file fixture."""
    temp_dir = tmp_path_factory.mktemp("case_packet_fixture")
    pdf_path = temp_dir / "Case_Packet.pdf"

    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)

    y = 60
    for line in SAMPLE_CASE_PACKET_TEXT.strip().split("\n"):
        page.insert_text(pymupdf.Point(50, y), line, fontsize=10, fontname="helv")
        y += 15

    doc.save(pdf_path)
    doc.close()
    return pdf_path
