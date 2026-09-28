"""Vector store interface and FAISS integration abstraction."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
from pydantic import BaseModel


class SearchResult(BaseModel):
    id: str
    score: float
    metadata: Dict[str, Any]
    text: Optional[str] = None


class BaseVectorStore(ABC):
    """Abstract interface for dense vector indices."""

    @abstractmethod
    def add_vectors(self, vectors: np.ndarray, metadata: List[Dict[str, Any]]) -> None:
        """Add dense vectors and corresponding metadata to the index."""
        pass

    @abstractmethod
    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[SearchResult]:
        """Query index for nearest neighbor vectors."""
        pass

    @abstractmethod
    def save(self, file_path: Path) -> None:
        """Persist index to disk."""
        pass

    @abstractmethod
    def load(self, file_path: Path) -> None:
        """Load index from disk."""
        pass


class FAISSVectorStore(BaseVectorStore):
    """FAISS-backed vector search store stub for Phase 1."""

    def __init__(self, dimension: int = 384, index_type: str = "FlatL2"):
        self.dimension = dimension
        self.index_type = index_type

    def add_vectors(self, vectors: np.ndarray, metadata: List[Dict[str, Any]]) -> None:
        raise NotImplementedError("FAISS vector ingestion will be implemented in Phase 1.")

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[SearchResult]:
        raise NotImplementedError("FAISS vector search will be implemented in Phase 1.")

    def save(self, file_path: Path) -> None:
        raise NotImplementedError("FAISS index saving will be implemented in Phase 1.")

    def load(self, file_path: Path) -> None:
        raise NotImplementedError("FAISS index loading will be implemented in Phase 1.")
