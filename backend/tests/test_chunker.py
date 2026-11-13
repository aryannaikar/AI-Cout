"""
Unit and integration tests for legal-aware chunking and metadata preservation.
"""

from rag.chunker import LegalAwareChunker, LegalChunk
from rag.loader import LegalDocument, PDFLoader, PDFPage
from rag.config import config


def test_chunk_empty_document():
    chunker = LegalAwareChunker()
    doc = LegalDocument(
        act_name="Empty Act",
        short_name="Empty",
        year=2023,
        document_type="act",
        source_file="empty.pdf",
        file_path=None,
        pages=[],
    )
    chunks = chunker.chunk_document(doc)
    assert chunks == []


def test_chunk_bns_extracts_murder_theft_and_stolen_property():
    loader = PDFLoader()
    chunker = LegalAwareChunker()
    doc = loader.load_document(config.legal_corpus_dir / "bns" / "bharatiya_nyaya_sanhita_2023.pdf")
    chunks = chunker.chunk_document(doc)

    assert len(chunks) > 100

    # Verify Section 103 (Murder)
    sec_103 = [c for c in chunks if c.section == "Section 103"]
    assert len(sec_103) > 0
    assert "murder" in sec_103[0].text.lower()
    assert sec_103[0].act_name == "Bharatiya Nyaya Sanhita, 2023"
    assert sec_103[0].chunk_type in ["section", "sub_section"]

    # Verify Section 317 (Stolen property)
    sec_317 = [c for c in chunks if c.section == "Section 317"]
    assert len(sec_317) > 0
    assert "stolen property" in sec_317[0].text.lower()
    assert sec_317[0].page == 85


def test_chunk_bsa_extracts_electronic_evidence_provisions():
    loader = PDFLoader()
    chunker = LegalAwareChunker()
    doc = loader.load_document(config.legal_corpus_dir / "bsa" / "Bharatiya Sakshya Adhiniyam, 2023 (BSA).pdf")
    chunks = chunker.chunk_document(doc)

    assert len(chunks) > 50

    # Verify Section 61 (Admissibility of electronic records)
    sec_61 = [c for c in chunks if c.section == "Section 61"]
    assert len(sec_61) > 0
    assert "electronic" in sec_61[0].text.lower()
    assert sec_61[0].page == 22

    # Verify Section 63 (Conditions for admissibility of electronic records)
    sec_63 = [c for c in chunks if c.section == "Section 63"]
    assert len(sec_63) > 0
    assert any("electronic" in c.text.lower() for c in sec_63)


def test_chunk_it_act_extracts_computer_offences():
    loader = PDFLoader()
    chunker = LegalAwareChunker()
    doc = loader.load_document(config.legal_corpus_dir / "it_act" / "information_technology_act_2000.pdf")
    chunks = chunker.chunk_document(doc)

    assert len(chunks) > 50

    # Verify Section 65 (Tampering with computer source documents)
    sec_65 = [c for c in chunks if c.section == "Section 65"]
    assert len(sec_65) > 0
    assert "computer source" in sec_65[0].text.lower()

    # Verify Section 66 (Computer related offences)
    sec_66 = [c for c in chunks if c.section and c.section.startswith("Section 66")]
    assert len(sec_66) > 0


def test_chunk_constitution_extracts_articles_and_preamble():
    loader = PDFLoader()
    chunker = LegalAwareChunker()
    doc = loader.load_document(config.legal_corpus_dir / "constitution" / "constitution_of_india.pdf")
    chunks = chunker.chunk_document(doc)

    assert len(chunks) > 200

    # Verify Preamble
    preamble = [c for c in chunks if c.chunk_type == "preamble"]
    assert len(preamble) == 1
    assert "WE, THE PEOPLE OF INDIA" in preamble[0].text

    # Verify Article 21 (Protection of life and personal liberty)
    art_21 = [c for c in chunks if c.article == "Article 21"]
    assert len(art_21) > 0
    assert "protection of life and personal liberty" in art_21[0].text.lower()
    assert art_21[0].page == 42


def test_metadata_preservation():
    loader = PDFLoader()
    chunker = LegalAwareChunker()
    doc = loader.load_document(config.legal_corpus_dir / "bns" / "bharatiya_nyaya_sanhita_2023.pdf")
    chunks = chunker.chunk_document(doc)

    c = chunks[0]
    meta = c.to_metadata()

    # Verify required keys
    assert "act_name" in meta
    assert "short_name" in meta
    assert "section" in meta
    assert "article" in meta
    assert "page" in meta
    assert "chunk_type" in meta
    assert "source_file" in meta
    assert "jurisdiction" in meta
    assert "year" in meta

    # Verify ChromaDB value types (must not contain None)
    for k, v in meta.items():
        assert isinstance(v, (str, int, float, bool)), f"Invalid type for {k}: {type(v)}"


def test_subchunking_context_injection():
    chunker = LegalAwareChunker(max_chunk_size=100)
    page = PDFPage(
        page_number=1,
        source_file="test.pdf",
        text="""
CHAPTER I - PRELIMINARY
10. Major Offence.
(1) First part of major offence with substantial details.
(2) Second part of major offence with penalties.
Provided that a fine may be levied.
Explanation.—This defines the offence.
"""
    )
    doc = LegalDocument(
        act_name="Test Act, 2024",
        short_name="TestAct",
        year=2024,
        document_type="act",
        source_file="test.pdf",
        file_path=None,
        pages=[page],
    )
    chunks = chunker.chunk_document(doc)
    assert len(chunks) >= 2

    # Verify parent context is prepended to sub-chunks
    for chunk in chunks:
        assert "[Test Act, 2024 | Section 10" in chunk.text
