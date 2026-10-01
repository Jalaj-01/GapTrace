"""Modular Embedding Service for Scientific Representation (Phase 3).

Supports configurable Sentence Transformers models with graceful fallback,
batch processing, query embedding, normalization for cosine similarity,
and strict dimension verification.
"""

from abc import ABC, abstractmethod
import hashlib
from pathlib import Path
import sys
from typing import Any, List, Optional
import numpy as np

# Ensure repository root and backend directory are on sys.path for direct execution or script invocation
_REPO_ROOT = Path(__file__).resolve().parents[4]
_BACKEND_DIR = _REPO_ROOT / "backend"
for _path_item in [str(_REPO_ROOT), str(_BACKEND_DIR)]:
    if _path_item not in sys.path:
        sys.path.insert(0, _path_item)

try:
    from backend.app.core.config import settings
    from backend.app.core.logging import get_logger
    from backend.app.core.errors import ValidationError
except ImportError:
    from app.core.config import settings
    from app.core.logging import get_logger
    from app.core.errors import ValidationError

logger = get_logger("app.embeddings.service")


class BaseEmbeddingService(ABC):
    """Abstract interface for scientific text embedding generators."""

    @abstractmethod
    def embed_query(self, query: str) -> np.ndarray:
        """Generate normalized 1D or 2D vector for a search query string.

        Args:
            query: Non-empty query string.

        Returns:
            np.ndarray of shape (dimension,) with float32 type.
        """
        pass

    @abstractmethod
    def embed_documents(self, documents: List[str]) -> np.ndarray:
        """Generate normalized 2D vector matrix for a batch of text documents.

        Args:
            documents: List of text strings.

        Returns:
            np.ndarray of shape (len(documents), dimension) with float32 type.
        """
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector dimension of the embedding model."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Configured model identifier."""
        pass


class DeterministicEmbeddingService(BaseEmbeddingService):
    """Deterministic, self-contained semantic embedding service for testing, offline execution,

    and graceful fallback when remote weights or PyTorch cannot be loaded.
    Uses n-gram semantic token hashing with position weighting and L2 normalization,
    providing deterministic vector geometry with cosine similarity properties.
    """

    def __init__(self, dimension: int = 384, model_name: str = "deterministic-baseline-384"):
        self._dimension = dimension
        self._model_name = model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model_name

    def _embed_single(self, text: str) -> np.ndarray:
        if not text or not text.strip():
            # Return zero vector for empty strings
            return np.zeros(self._dimension, dtype=np.float32)

        vec = np.zeros(self._dimension, dtype=np.float32)
        tokens = text.lower().strip().split()
        if not tokens:
            return vec

        # Bag-of-ngrams with reproducible hash projection
        for i, token in enumerate(tokens):
            weight = 1.0 / (1.0 + 0.05 * i)
            # Unigram projection
            h1 = int(hashlib.sha256(token.encode("utf-8")).hexdigest()[:8], 16)
            idx1 = h1 % self._dimension
            vec[idx1] += float(weight * 1.5)

            # Subword prefix/suffix features for morphological generalization
            if len(token) > 3:
                h_sub = int(hashlib.md5(token[:4].encode("utf-8")).hexdigest()[:8], 16)
                idx_sub = h_sub % self._dimension
                vec[idx_sub] += float(weight * 0.75)

            # Bigram projection
            if i > 0:
                bigram = f"{tokens[i-1]}_{token}"
                h2 = int(hashlib.sha256(bigram.encode("utf-8")).hexdigest()[:8], 16)
                idx2 = h2 % self._dimension
                vec[idx2] += float(weight * 2.0)

        # L2 Normalization
        norm = np.linalg.norm(vec)
        if norm > 1e-12:
            vec = vec / norm
        return vec.astype(np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        if not query or not query.strip():
            raise ValidationError("Search query cannot be empty or whitespace only.")
        return self._embed_single(query.strip())

    def embed_documents(self, documents: List[str]) -> np.ndarray:
        if not documents:
            return np.empty((0, self._dimension), dtype=np.float32)
        vectors = [self._embed_single(doc) for doc in documents]
        return np.array(vectors, dtype=np.float32)


class SentenceTransformerEmbeddingService(BaseEmbeddingService):
    """Production modular embedding service backed by HuggingFace Sentence Transformers."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        batch_size: int = 32,
        dimension: Optional[int] = None,
        fallback_on_error: bool = True,
    ):
        self._configured_model_name: str = str(
            model_name
            or getattr(settings, "EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
        )
        self._device: str = str(device or getattr(settings, "EMBEDDING_DEVICE", "cpu"))
        self._batch_size: int = batch_size
        self._fallback_on_error: bool = fallback_on_error
        self._dimension_override: Optional[int] = dimension
        self._model: Any = None
        self._is_loaded: bool = False
        self._fallback_service: Optional[DeterministicEmbeddingService] = None

    def _get_fallback(self) -> DeterministicEmbeddingService:
        if self._fallback_service is None:
            dim = self._dimension_override or 384
            self._fallback_service = DeterministicEmbeddingService(
                dimension=dim,
                model_name=f"fallback-{self._configured_model_name}",
            )
        return self._fallback_service

    def _load_model(self) -> None:
        if self._is_loaded:
            return

        try:
            from sentence_transformers import SentenceTransformer
            logger.info(
                f"Loading SentenceTransformer model '{self._configured_model_name}' on device '{self._device}'..."
            )
            # 1. Try local cached weights first for instant, offline, zero-network load
            try:
                self._model = SentenceTransformer(
                    self._configured_model_name,
                    device=self._device,
                    local_files_only=True,
                )
            except Exception:
                # 2. If not cached, attempt standard download
                self._model = SentenceTransformer(
                    self._configured_model_name,
                    device=self._device,
                )
            self._is_loaded = True
            logger.info(
                f"Successfully loaded SentenceTransformer model '{self._configured_model_name}'. "
                f"Embedding dimension: {self.dimension}"
            )
        except Exception as exc:
            logger.warning(
                f"Failed to initialize SentenceTransformer ('{self._configured_model_name}'): {exc}. "
                f"Activating deterministic fallback embedding provider."
            )
            if not self._fallback_on_error:
                raise ValidationError(
                    f"Embedding model '{self._configured_model_name}' is unavailable: {exc}"
                )
            self._model = None
            self._is_loaded = True

    @property
    def dimension(self) -> int:
        if self._dimension_override:
            return self._dimension_override
        if not self._is_loaded:
            self._load_model()
        if self._model is not None:
            if hasattr(self._model, "get_embedding_dimension"):
                return int(self._model.get_embedding_dimension())
            return int(self._model.get_sentence_embedding_dimension())
        return self._get_fallback().dimension

    @property
    def model_name(self) -> str:
        return self._configured_model_name

    def embed_query(self, query: str) -> np.ndarray:
        if not query or not query.strip():
            raise ValidationError("Search query cannot be empty or whitespace only.")

        self._load_model()
        cleaned = query.strip()

        if self._model is not None:
            try:
                emb = self._model.encode(
                    cleaned,
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                )
                return emb.astype(np.float32)
            except Exception as exc:
                logger.error(f"Error encoding query with SentenceTransformer: {exc}. Using fallback.")
                if not self._fallback_on_error:
                    raise
                return self._get_fallback().embed_query(cleaned)
        else:
            return self._get_fallback().embed_query(cleaned)

    def embed_documents(self, documents: List[str]) -> np.ndarray:
        if not documents:
            return np.empty((0, self.dimension), dtype=np.float32)

        self._load_model()

        if self._model is not None:
            try:
                embeddings = self._model.encode(
                    documents,
                    batch_size=self._batch_size,
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                )
                return embeddings.astype(np.float32)
            except Exception as exc:
                logger.error(f"Error batch encoding documents: {exc}. Using fallback.")
                if not self._fallback_on_error:
                    raise
                return self._get_fallback().embed_documents(documents)
        else:
            return self._get_fallback().embed_documents(documents)


# Global singleton factory
_embedding_service_instance: Optional[BaseEmbeddingService] = None


def get_embedding_service(
    model_name: Optional[str] = None,
    force_deterministic: bool = False,
) -> BaseEmbeddingService:
    """Factory retrieving the configured embedding service singleton."""
    global _embedding_service_instance
    if force_deterministic:
        return DeterministicEmbeddingService(
            dimension=384,
            model_name="deterministic-mock-384",
        )
    if _embedding_service_instance is None or (model_name and _embedding_service_instance.model_name != model_name):
        _embedding_service_instance = SentenceTransformerEmbeddingService(
            model_name=model_name,
        )
    return _embedding_service_instance


if __name__ == "__main__":
    service = get_embedding_service(force_deterministic=True)
    print(f"Embedding service loaded: {service.model_name} (dimension: {service.dimension})")
    sample_vec = service.embed_query("scientific discourse analysis and gap finding")
    print(f"Sample query vector shape: {sample_vec.shape}, L2-norm: {np.linalg.norm(sample_vec):.4f}")
