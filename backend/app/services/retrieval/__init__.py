"""Retrieval service package (Phase 3)."""

from backend.app.services.retrieval.faiss_index import (
    FAISSIndexManager,
    get_faiss_index_manager,
)
from backend.app.services.retrieval.tfidf_search import (
    TFIDFSearchService,
    get_tfidf_search_service,
)
from backend.app.services.retrieval.semantic_search import (
    SemanticSearchService,
    get_semantic_search_service,
)
from backend.app.services.retrieval.evidence_retriever import (
    EvidenceRetrieverService,
    get_evidence_retriever_service,
)

__all__ = [
    "FAISSIndexManager",
    "get_faiss_index_manager",
    "TFIDFSearchService",
    "get_tfidf_search_service",
    "SemanticSearchService",
    "get_semantic_search_service",
    "EvidenceRetrieverService",
    "get_evidence_retriever_service",
]
