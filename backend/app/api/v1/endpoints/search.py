"""Semantic Search API Endpoints (Phase 3).

Exposes:
- GET /api/v1/search/semantic?q=...
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.core.errors import ValidationError
from backend.app.db.session import get_db
from backend.app.models.paper import EvidenceSearchResponse, EvidenceSearchResult
from backend.app.services.retrieval.evidence_retriever import get_evidence_retriever_service

router = APIRouter()


@router.get(
    "/semantic",
    response_model=EvidenceSearchResponse,
    summary="Semantic Search across Scientific Evidence",
    description="Vector similarity search using Sentence Transformers and FAISS with provenance tracking.",
)
def semantic_search_endpoint(
    q: str = Query(..., min_length=1, description="Natural language search query"),
    top_k: int = Query(5, ge=1, le=100, description="Maximum number of nearest matches to return"),
    paper_id: Optional[int] = Query(None, description="Filter by specific paper ID"),
    section: Optional[str] = Query(None, description="Filter by section title substring"),
    extraction_type: Optional[str] = Query(None, description="Filter by extraction type (PROBLEM, METHOD, LIMITATION, etc.)"),
    year: Optional[int] = Query(None, description="Filter by exact publication year"),
    min_year: Optional[int] = Query(None, description="Filter by minimum publication year"),
    max_year: Optional[int] = Query(None, description="Filter by maximum publication year"),
    db: Session = Depends(get_db),
) -> EvidenceSearchResponse:
    """Execute dense semantic search using FAISS vector store with full scientific provenance."""
    if not q or not q.strip():
        raise ValidationError("Query parameter 'q' cannot be empty or whitespace.")

    retriever = get_evidence_retriever_service()
    res = retriever.search_evidence(
        query=q.strip(),
        method="semantic",
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
