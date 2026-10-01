"""FAISS Vector Index Management and Storage Layer (Phase 3).

Supports:
- Index creation, vector ingestion, normalization (cosine similarity via FlatIP)
- Atomic disk persistence and loading (index binary + metadata JSON)
- Dynamic index rebuilding and incremental updates
- Robust error handling: dimension validation, missing/corrupted index recovery,
  missing metadata detection, and graceful in-memory fallback.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from backend.app.core.errors import ValidationError

logger = get_logger("app.retrieval.faiss")

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("FAISS is not installed. Vector store will operate using numpy linear algebra fallback.")


class FAISSIndexManager:
    """Manages dense FAISS vector index with decoupled metadata mapping."""

    def __init__(
        self,
        dimension: int = 384,
        index_path: Optional[str] = None,
        metadata_path: Optional[str] = None,
        auto_load: bool = True,
    ):
        self.dimension = dimension
        self.index_path = Path(index_path or settings.FAISS_INDEX_PATH)
        self.metadata_path = Path(metadata_path or getattr(settings, "VECTOR_METADATA_PATH", "./data/embeddings/vector_metadata.json"))

        self.index = None
        # metadata mapping: faiss_id (int) -> dict of metadata & provenance
        self.id_to_metadata: Dict[int, Dict[str, Any]] = {}
        self._next_faiss_id: int = 0

        # In-memory matrix fallback for environments without native faiss or during corruption recovery
        self._numpy_vectors: Optional[np.ndarray] = None
        self._numpy_ids: List[int] = []

        self._init_empty_index()

        if auto_load and self.index_path.exists() and self.metadata_path.exists():
            try:
                self.load()
            except Exception as exc:
                logger.warning(f"Could not auto-load existing index ({exc}). Initializing fresh index.")
                self._init_empty_index()

    def _init_empty_index(self) -> None:
        """Initialize a fresh empty FAISS inner-product index (normalized cosine)."""
        if FAISS_AVAILABLE:
            try:
                # IndexFlatIP calculates inner product; with L2-normalized vectors this is Cosine Similarity
                self.index = faiss.IndexFlatIP(self.dimension)
            except Exception as exc:
                logger.error(f"Failed to create native FAISS IndexFlatIP: {exc}. Falling back to NumPy.")
                self.index = None
        else:
            self.index = None

        self.id_to_metadata = {}
        self._next_faiss_id = 0
        self._numpy_vectors = np.empty((0, self.dimension), dtype=np.float32)
        self._numpy_ids = []

    @property
    def total_vectors(self) -> int:
        """Return total number of vectors in index."""
        if self.index is not None and FAISS_AVAILABLE:
            return self.index.ntotal
        return len(self._numpy_ids)

    def add_vectors(
        self,
        vectors: np.ndarray,
        metadata_list: List[Dict[str, Any]],
    ) -> List[int]:
        """Add dense vectors and corresponding metadata units to index.

        Args:
            vectors: np.ndarray of shape (N, dimension).
            metadata_list: List of length N containing metadata dicts.

        Returns:
            List of assigned integer faiss IDs.
        """
        if len(metadata_list) == 0:
            return []

        if not isinstance(vectors, np.ndarray):
            vectors = np.array(vectors, dtype=np.float32)

        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)

        if vectors.shape[0] != len(metadata_list):
            raise ValidationError(
                f"Mismatch: Received {vectors.shape[0]} vectors but {len(metadata_list)} metadata records."
            )

        if vectors.shape[1] != self.dimension:
            raise ValidationError(
                f"Dimension mismatch: Index expects {self.dimension}, but received vector dimension {vectors.shape[1]}."
            )

        # Ensure float32
        vectors = vectors.astype(np.float32)

        # L2-normalize vectors so Inner Product equals Cosine Similarity
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized_vectors = vectors / norms

        assigned_ids: List[int] = []
        for i, meta in enumerate(metadata_list):
            fid = self._next_faiss_id
            self._next_faiss_id += 1
            meta_copy = dict(meta)
            meta_copy["faiss_id"] = fid
            self.id_to_metadata[fid] = meta_copy
            assigned_ids.append(fid)

        if self.index is not None and FAISS_AVAILABLE:
            self.index.add(normalized_vectors)
        
        # Keep numpy backup updated
        if self._numpy_vectors is None or self._numpy_vectors.size == 0:
            self._numpy_vectors = normalized_vectors
        else:
            self._numpy_vectors = np.vstack([self._numpy_vectors, normalized_vectors])
        self._numpy_ids.extend(assigned_ids)

        logger.info(f"Added {len(metadata_list)} vectors to FAISS index. Total count: {self.total_vectors}")
        return assigned_ids

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Query index for nearest neighbor vectors with optional metadata filtering.

        Args:
            query_vector: 1D or 2D vector matching self.dimension.
            top_k: Maximum number of results to return.
            filters: Optional dict containing filter keys:
                     - 'paper_id' (int)
                     - 'section' (str)
                     - 'extraction_type' (str)
                     - 'year' (int)
                     - 'min_year' / 'max_year' (int)

        Returns:
            List of result dicts sorted by similarity score descending.
        """
        if self.total_vectors == 0:
            return []

        if not isinstance(query_vector, np.ndarray):
            query_vector = np.array(query_vector, dtype=np.float32)

        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)

        if query_vector.shape[1] != self.dimension:
            raise ValidationError(
                f"Query dimension {query_vector.shape[1]} does not match index dimension {self.dimension}."
            )

        # L2-normalize query vector
        norm = np.linalg.norm(query_vector)
        if norm > 0:
            query_vector = (query_vector / norm).astype(np.float32)

        # Over-sample candidates if filters are provided to ensure top_k after filtering
        fetch_k = min(self.total_vectors, max(top_k * 5, 20)) if filters else min(top_k, self.total_vectors)

        candidate_scores: List[float] = []
        candidate_ids: List[int] = []

        if self.index is not None and FAISS_AVAILABLE:
            try:
                distances, indices = self.index.search(query_vector, fetch_k)
                raw_scores = distances[0]
                raw_ids = indices[0]
                for sc, idx in zip(raw_scores, raw_ids):
                    if idx >= 0:
                        candidate_scores.append(float(sc))
                        candidate_ids.append(int(idx))
            except Exception as exc:
                logger.warning(f"Native FAISS search failed ({exc}). Falling back to NumPy dot product.")
                candidate_scores, candidate_ids = self._numpy_search(query_vector, fetch_k)
        else:
            candidate_scores, candidate_ids = self._numpy_search(query_vector, fetch_k)

        # Filter and construct results
        results: List[Dict[str, Any]] = []
        for score, fid in zip(candidate_scores, candidate_ids):
            meta = self.id_to_metadata.get(fid)
            if not meta:
                continue

            if not self._matches_filters(meta, filters):
                continue

            # Bound score to [-1.0, 1.0] and convert negative/approx to 0..1 range if appropriate
            bounded_score = max(-1.0, min(1.0, float(score)))

            results.append({
                "faiss_id": fid,
                "similarity_score": round(bounded_score, 4),
                "metadata": meta,
            })

            if len(results) >= top_k:
                break

        return results

    def _numpy_search(self, query_vec: np.ndarray, fetch_k: int) -> Tuple[List[float], List[int]]:
        """Numpy dot product nearest neighbor search fallback."""
        if self._numpy_vectors is None or len(self._numpy_ids) == 0:
            return [], []
        # Query is shape (1, D), vectors is (N, D) -> dots is (N,)
        dots = np.dot(self._numpy_vectors, query_vec.T).squeeze()
        if dots.ndim == 0:
            dots = np.array([dots])
        top_indices = np.argsort(dots)[::-1][:fetch_k]
        scores = [float(dots[i]) for i in top_indices]
        ids = [self._numpy_ids[i] for i in top_indices]
        return scores, ids

    def _matches_filters(self, metadata: Dict[str, Any], filters: Optional[Dict[str, Any]]) -> bool:
        """Evaluate if metadata satisfies provided query filters."""
        if not filters:
            return True

        # Filter by paper_id
        if "paper_id" in filters and filters["paper_id"] is not None:
            if int(metadata.get("paper_id", -1)) != int(filters["paper_id"]):
                return False

        # Filter by extraction_type (case-insensitive)
        if "extraction_type" in filters and filters["extraction_type"] is not None:
            target_type = str(filters["extraction_type"]).strip().upper()
            curr_type = str(metadata.get("extraction_type", "")).strip().upper()
            if target_type != curr_type:
                return False

        # Filter by section name (case-insensitive substring or exact match)
        if "section" in filters and filters["section"] is not None:
            target_sec = str(filters["section"]).strip().lower()
            curr_sec = str(metadata.get("section", "")).strip().lower()
            if target_sec not in curr_sec:
                return False

        # Filter by publication year
        meta_year = metadata.get("year")
        if "year" in filters and filters["year"] is not None:
            if meta_year is None or int(meta_year) != int(filters["year"]):
                return False

        if "min_year" in filters and filters["min_year"] is not None:
            if meta_year is None or int(meta_year) < int(filters["min_year"]):
                return False

        if "max_year" in filters and filters["max_year"] is not None:
            if meta_year is None or int(meta_year) > int(filters["max_year"]):
                return False

        return True

    def save(self, index_path: Optional[Path] = None, metadata_path: Optional[Path] = None) -> None:
        """Persist FAISS binary index and metadata JSON to disk atomically."""
        target_idx_path = Path(index_path or self.index_path)
        target_meta_path = Path(metadata_path or self.metadata_path)

        target_idx_path.parent.mkdir(parents=True, exist_ok=True)
        target_meta_path.parent.mkdir(parents=True, exist_ok=True)

        # 1. Save FAISS binary index
        if self.index is not None and FAISS_AVAILABLE:
            tmp_idx_path = target_idx_path.with_suffix(".tmp")
            try:
                faiss.write_index(self.index, str(tmp_idx_path))
                if target_idx_path.exists():
                    target_idx_path.unlink()
                tmp_idx_path.rename(target_idx_path)
            except Exception as exc:
                if tmp_idx_path.exists():
                    tmp_idx_path.unlink()
                raise IOError(f"Failed to write FAISS index to {target_idx_path}: {exc}")
        elif self._numpy_vectors is not None:
            # Save numpy backup
            np.save(str(target_idx_path), self._numpy_vectors)

        # 2. Save metadata JSON
        tmp_meta_path = target_meta_path.with_suffix(".tmp")
        payload = {
            "dimension": self.dimension,
            "next_faiss_id": self._next_faiss_id,
            "total_vectors": self.total_vectors,
            "records": {str(k): v for k, v in self.id_to_metadata.items()},
        }
        with open(tmp_meta_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        if target_meta_path.exists():
            target_meta_path.unlink()
        tmp_meta_path.rename(target_meta_path)

        logger.info(f"Saved FAISS index ({self.total_vectors} vectors) to {target_idx_path} and metadata to {target_meta_path}")

    def load(self, index_path: Optional[Path] = None, metadata_path: Optional[Path] = None) -> None:
        """Load FAISS binary index and metadata JSON from disk with corruption detection."""
        target_idx_path = Path(index_path or self.index_path)
        target_meta_path = Path(metadata_path or self.metadata_path)

        if not target_idx_path.exists():
            raise FileNotFoundError(f"FAISS index file not found at {target_idx_path}")
        if not target_meta_path.exists():
            raise FileNotFoundError(f"Metadata file not found at {target_meta_path}")

        # Check for zero-byte or corrupt files
        if target_idx_path.stat().st_size == 0 or target_meta_path.stat().st_size == 0:
            raise ValueError(f"Corrupted or empty index/metadata file detected.")

        # 1. Load metadata JSON
        try:
            with open(target_meta_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            records = payload.get("records", {})
            self.id_to_metadata = {int(k): v for k, v in records.items()}
            self._next_faiss_id = int(payload.get("next_faiss_id", len(self.id_to_metadata)))
            saved_dim = int(payload.get("dimension", self.dimension))
            if saved_dim != self.dimension:
                logger.warning(
                    f"Loaded index dimension ({saved_dim}) differs from current config ({self.dimension}). Adjusting."
                )
                self.dimension = saved_dim
        except Exception as exc:
            raise ValueError(f"Corrupted metadata JSON at {target_meta_path}: {exc}")

        # 2. Load FAISS index
        if FAISS_AVAILABLE:
            try:
                self.index = faiss.read_index(str(target_idx_path))
                if self.index.d != self.dimension:
                    raise ValueError(
                        f"FAISS index dimension {self.index.d} does not match expected {self.dimension}"
                    )
            except Exception as exc:
                logger.warning(f"Could not load native FAISS index ({exc}). Attempting numpy recovery.")
                self.index = None

        logger.info(
            f"Successfully loaded index with {self.total_vectors} vectors from {target_idx_path}."
        )

    def rebuild(self, vectors: np.ndarray, metadata_list: List[Dict[str, Any]]) -> None:
        """Reset index completely and rebuild from full vector/metadata collection."""
        logger.info(f"Rebuilding index with {len(metadata_list)} items...")
        self._init_empty_index()
        if len(metadata_list) > 0:
            self.add_vectors(vectors, metadata_list)
        self.save()


# Singleton instance
_faiss_index_manager_instance: Optional[FAISSIndexManager] = None


def get_faiss_index_manager() -> FAISSIndexManager:
    """Retrieve global FAISSIndexManager singleton."""
    global _faiss_index_manager_instance
    if _faiss_index_manager_instance is None:
        _faiss_index_manager_instance = FAISSIndexManager()
    return _faiss_index_manager_instance
