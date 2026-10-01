"""Embeddings service package (Phase 3)."""

from backend.app.services.embeddings.embedding_service import (
    BaseEmbeddingService,
    SentenceTransformerEmbeddingService,
    DeterministicEmbeddingService,
    get_embedding_service,
)

__all__ = [
    "BaseEmbeddingService",
    "SentenceTransformerEmbeddingService",
    "DeterministicEmbeddingService",
    "get_embedding_service",
]
