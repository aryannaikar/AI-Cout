"""
Unit tests for the SentenceTransformer embedding model wrapper.
"""

import math
from rag.embeddings import EmbeddingModel


def test_embedding_model_initialization():
    model = EmbeddingModel()
    assert model.model_name == "sentence-transformers/all-MiniLM-L6-v2"


def test_embedding_encode_and_dimension():
    model = EmbeddingModel()
    texts = ["Indian Penal Code replacement", "Bharatiya Nyaya Sanhita"]
    vectors = model.encode(texts)

    assert len(vectors) == 2
    assert len(vectors[0]) == 384
    assert len(vectors[1]) == 384
    assert model.dimension == 384


def test_embedding_normalization():
    model = EmbeddingModel()
    vectors = model.encode(["Section 302 IPC Section 103 BNS"], normalize_embeddings=True)
    vec = vectors[0]

    # Calculate L2 norm: sqrt(sum(x^2))
    l2_norm = math.sqrt(sum(x * x for x in vec))
    assert abs(l2_norm - 1.0) < 1e-4


def test_embedding_empty_input():
    model = EmbeddingModel()
    assert model.encode([]) == []
