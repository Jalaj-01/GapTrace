"""Evidence Retrieval & Representation API Endpoints (Phase 3).

Exposes:
- GET /api/v1/evidence/search
- POST /api/v1/evidence/embed/{paper_id}
- POST /api/v1/evidence/batch-embed
- GET /api/v1/evidence/stats
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.core.errors import ValidationError
from backend.app.db.session import get_db
from backend.app.models.paper import (
    EvidenceBatchEmbedResponse,
    EvidenceSearchResponse,
    EvidenceSearchResult,
)
from backend.app.services.retrieval.evidence_retriever import get_evidence_retriever_service

router = APIRouter()


@router.get(
    "/search",
    response_model=EvidenceSearchResponse,
    summary="Search Scientific Evidence with Provenance",
    description="Retrieve evidence snippets using dense semantic search or TF-IDF baseline with multi-field filtering.",
)
def search_evidence_endpoint(
    q: str = Query(..., min_length=1, description="Search query string"),
    method: str = Query("semantic", description="Retrieval method: 'semantic' (FAISS) or 'tfidf' (Baseline)"),
    top_k: int = Query(5, ge=1, le=100, description="Number of results to retrieve"),
    paper_id: Optional[int] = Query(None, description="Filter by paper ID"),
    section: Optional[str] = Query(None, description="Filter by section name"),
    extraction_type: Optional[str] = Query(None, description="Filter by extraction type (PROBLEM, METHOD, LIMITATION, etc.)"),
    year: Optional[int] = Query(None, description="Filter by publication year"),
    min_year: Optional[int] = Query(None, description="Filter by min year"),
    max_year: Optional[int] = Query(None, description="Filter by max year"),
    db: Session = Depends(get_db),
) -> EvidenceSearchResponse:
    """Execute evidence search with full scientific provenance."""
    if not q or not q.strip():
        raise ValidationError("Query parameter 'q' cannot be empty or whitespace.")

    retriever = get_evidence_retriever_service()
    res = retriever.search_evidence(
        query=q.strip(),
        method=method,
        top_k=top_k,
        paper_id=paper_id,
        section=section,
        extraction_type=extraction_type,
        year=year,
        min_year=min_year,
        max_year=max_year,
    )

    return EvidenceSearchResponse(
        query=res["query"],
        total_results=res["total_results"],
        retrieval_method=res["retrieval_method"],
        model_name=res.get("model_name"),
        results=[EvidenceSearchResult(**item) for item in res["results"]],
    )


@router.post(
    "/embed/{paper_id}",
    status_code=status.HTTP_200_OK,
    summary="Generate Semantic Embeddings for a Paper",
    description="Incrementally generate dense embeddings for sentences and extractions of an ingested paper.",
)
def embed_paper_endpoint(
    paper_id: int,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Incrementally embed all evidence units for a single paper."""
    retriever = get_evidence_retriever_service()
    result = retriever.embed_paper_evidence(paper_id=paper_id, db=db, save_index=True)
    return result


@router.post(
    "/batch-embed",
    response_model=EvidenceBatchEmbedResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch Embed Entire Paper Collection",
    description="Batch process and index all papers in the collection without requiring manual one-by-one execution.",
)
def batch_embed_endpoint(
    db: Session = Depends(get_db),
) -> EvidenceBatchEmbedResponse:
    """Embed and index all papers currently stored in the database."""
    retriever = get_evidence_retriever_service()
    return retriever.batch_embed_collection(db=db)


@router.get(
    "/stats",
    summary="Vector Index & Retrieval Diagnostics",
    description="Retrieve live diagnostics on FAISS vector count, embedding dimension, and configured model.",
)
def get_retrieval_stats() -> Dict[str, Any]:
    """Return status and diagnostics for vector index and retrieval engines."""
    retriever = get_evidence_retriever_service()
    return {
        "model_name": retriever.embedding_service.model_name,
        "embedding_dimension": retriever.embedding_service.dimension,
        "total_faiss_vectors": retriever.faiss_manager.total_vectors,
        "total_tfidf_documents": retriever.tfidf_service.total_documents,
        "index_path": str(retriever.faiss_manager.index_path),
        "status": "operational",
    }
