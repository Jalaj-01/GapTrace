"""Semantic Search Engine backed by Sentence Transformers and FAISS (Phase 3).

Coordinates dense query embedding, vector similarity ranking via FAISS IndexFlatIP,
multi-criteria metadata filtering, and standardized scientific evidence presentation.
"""

from typing import Any, Dict, List, Optional
from backend.app.core.logging import get_logger
from backend.app.core.errors import ValidationError
from backend.app.services.embeddings.embedding_service import BaseEmbeddingService, get_embedding_service
from backend.app.services.retrieval.faiss_index import FAISSIndexManager, get_faiss_index_manager

logger = get_logger("app.retrieval.semantic")


class SemanticSearchService:
    """End-to-end dense semantic search over indexed scientific evidence."""

    def __init__(
        self,
        embedding_service: Optional[BaseEmbeddingService] = None,
        index_manager: Optional[FAISSIndexManager] = None,
    ):
        self._embedding_service = embedding_service
        self._index_manager = index_manager

    @property
    def embedding_service(self) -> BaseEmbeddingService:
        if self._embedding_service is None:
            self._embedding_service = get_embedding_service()
        return self._embedding_service

    @property
    def index_manager(self) -> FAISSIndexManager:
        if self._index_manager is None:
            self._index_manager = get_faiss_index_manager()
        return self._index_manager

    def search(
        self,
        query: str,
        top_k: int = 5,
        paper_id: Optional[int] = None,
        section: Optional[str] = None,
        extraction_type: Optional[str] = None,
        year: Optional[int] = None,
        min_year: Optional[int] = None,
        max_year: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Perform semantic search with multi-field filtering.

        Args:
            query: Free-text search query.
            top_k: Number of nearest neighbors.
            paper_id: Filter by paper ID.
            section: Filter by section substring.
            extraction_type: Filter by extraction type (PROBLEM, METHOD, LIMITATION, etc.).
            year: Filter by exact publication year.
            min_year: Filter by minimum publication year.
            max_year: Filter by maximum publication year.

        Returns:
            List of standardized evidence results with provenance and similarity scores.
        """
        if not query or not query.strip():
            raise ValidationError("Search query cannot be empty or whitespace only.")

        clean_query = query.strip()

        # Build filters dictionary
        filters: Dict[str, Any] = {}
        if paper_id is not None:
            filters["paper_id"] = paper_id
        if section is not None:
            filters["section"] = section
        if extraction_type is not None:
            filters["extraction_type"] = extraction_type
        if year is not None:
            filters["year"] = year
        if min_year is not None:
            filters["min_year"] = min_year
        if max_year is not None:
            filters["max_year"] = max_year

        # 1. Embed search query
        query_vec = self.embedding_service.embed_query(clean_query)

        # 2. Query FAISS index
        raw_results = self.index_manager.search(
            query_vector=query_vec,
            top_k=top_k,
            filters=filters,
        )

        # 3. Format into standardized scientific evidence presentation
        formatted: List[Dict[str, Any]] = []
        for item in raw_results:
            meta = item["metadata"]
            score = item["similarity_score"]

            prov = meta.get("provenance", {})
            p_id = meta.get("paper_id")
            s_id = meta.get("sentence_id")
            s_order = meta.get("sentence_order", prov.get("sentence_order"))

            formatted.append({
                "source_text": meta.get("source_text", ""),
                "similarity_score": score,
                "paper": {
                    "id": p_id,
                    "title": meta.get("paper_title", "Unknown"),
                    "year": meta.get("year"),
                },
                "section": meta.get("section", "Unknown"),
                "page": meta.get("page", 1),
                "sentence": {
                    "id": s_id,
                    "order": s_order,
                } if s_id is not None else None,
                "extraction_type": meta.get("extraction_type", "SENTENCE"),
                "provenance": {
                    "paper_id": p_id,
                    "section_name": meta.get("section", "Unknown"),
                    "page_number": meta.get("page", 1),
                    "paragraph_id": prov.get("paragraph_id", 0),
                    "sentence_id": s_id,
                    "sentence_order": s_order,
                    "extraction_id": meta.get("extraction_id"),
                },
                "embedding_id": meta.get("embedding_id"),
                "model_name": meta.get("model_name", self.embedding_service.model_name),
            })

        return formatted


# Singleton instance
_semantic_search_service: Optional[SemanticSearchService] = None


def get_semantic_search_service() -> SemanticSearchService:
    """Retrieve global SemanticSearchService singleton."""
    global _semantic_search_service
    if _semantic_search_service is None:
        _semantic_search_service = SemanticSearchService()
    return _semantic_search_service
