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
    """FAISS-backed vector search store implementation (Phase 3)."""

    def __init__(self, dimension: int = 384, index_type: str = "FlatIP", index_path: Optional[str] = None):
        self.dimension = dimension
        self.index_type = index_type
        from backend.app.services.retrieval.faiss_index import FAISSIndexManager
        self._manager = FAISSIndexManager(dimension=dimension, index_path=index_path, auto_load=False)

    def add_vectors(self, vectors: np.ndarray, metadata: List[Dict[str, Any]]) -> None:
        self._manager.add_vectors(vectors, metadata)

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[SearchResult]:
        raw_results = self._manager.search(query_vector=query_vector, top_k=top_k)
        results = []
        for item in raw_results:
            meta = item["metadata"]
            results.append(
                SearchResult(
                    id=str(item["faiss_id"]),
                    score=item["similarity_score"],
                    metadata=meta,
                    text=meta.get("source_text"),
                )
            )
        return results

    def save(self, file_path: Path) -> None:
        self._manager.save(index_path=file_path)

    def load(self, file_path: Path) -> None:
        self._manager.load(index_path=file_path)
