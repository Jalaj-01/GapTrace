"""Scientific embedding generator interface."""

from abc import ABC, abstractmethod
from typing import List
import numpy as np


class BaseEmbeddingService(ABC):
    """Abstract interface for text embeddings (Sentence Transformers / SPECTER)."""

    @abstractmethod
    def embed_query(self, text: str) -> np.ndarray:
        """Embed a single query string into a dense vector."""
        pass

    @abstractmethod
    def embed_documents(self, documents: List[str]) -> np.ndarray:
        """Embed a batch of document texts into a 2D numpy matrix."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding vector dimension."""
        pass


class EmbeddingService(BaseEmbeddingService):
    """Sentence Transformers embedding service implementation (Phase 3)."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        from backend.app.services.embeddings.embedding_service import SentenceTransformerEmbeddingService
        self._service = SentenceTransformerEmbeddingService(model_name=model_name)

    def embed_query(self, text: str) -> np.ndarray:
        return self._service.embed_query(text)

    def embed_documents(self, documents: List[str]) -> np.ndarray:
        return self._service.embed_documents(documents)

    @property
    def dimension(self) -> int:
        return self._service.dimension
