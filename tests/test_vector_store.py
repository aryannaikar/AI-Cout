"""
Unit and integration tests for ChromaDB vector store and duplicate prevention.
"""

from pathlib import Path
from rag.chunker import LegalChunk
from rag.vector_store import LegalVectorStore


def test_vector_store_idempotency_and_duplicate_prevention(tmp_path: Path):
    store = LegalVectorStore(
        persist_directory=tmp_path / "test_chroma",
        collection_name="test_legal_collection",
    )

    assert store.count() == 0

    # Create 3 sample chunks
    chunks = [
        LegalChunk(
            chunk_id=f"test_sec_{i}",
            text=f"Section {i} text describing legal provision {i}.",
            act_name="Test Act, 2024",
            short_name="TestAct",
            section=f"Section {i}",
            article=None,
            title=f"Provision {i}",
            chapter="Chapter I",
            part=None,
            page=i,
            page_end=i,
            chunk_type="section",
            parent_chunk_id=None,
            source_file="test.pdf",
            year=2024,
        )
        for i in range(1, 4)
    ]
    # Simple dummy 4-dimensional embeddings for fast testing
    dummy_embeddings = [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
    ]

    # First insertion
    upserted_1 = store.add_chunks(chunks, dummy_embeddings)
    assert upserted_1 == 3
    assert store.count() == 3

    # Second insertion (IDEMPOTENCY / DUPLICATE PREVENTION TEST)
    # Re-inserting the exact same chunks must NOT increase count
    upserted_2 = store.add_chunks(chunks, dummy_embeddings)
    assert upserted_2 == 3
    assert store.count() == 3, "Count increased after re-indexing! Duplicate prevention failed."

    # Test get_by_id
    res = store.get_by_id("test_sec_2")
    assert res is not None
    assert res["id"] == "test_sec_2"
    assert "Section 2" in res["document"]
    assert res["metadata"]["section"] == "Section 2"

    # Test search
    search_res = store.search(query_embedding=[0.0, 1.0, 0.0, 0.0], n_results=1)
    assert len(search_res["ids"][0]) == 1
    assert search_res["ids"][0][0] == "test_sec_2"

    # Test clear
    store.clear()
    assert store.count() == 0
