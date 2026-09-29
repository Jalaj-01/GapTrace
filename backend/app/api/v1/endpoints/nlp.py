"""Scientific NLP API Endpoints (Phase 2).

Provides REST APIs for:
- POST /api/v1/nlp/process/{paper_id}
- GET /api/v1/nlp/papers/{paper_id}/sentences
- GET /api/v1/nlp/papers/{paper_id}/extractions
- GET /api/v1/nlp/papers/{paper_id}/limitations
- GET /api/v1/nlp/papers/{paper_id}/future-work
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.errors import NotFoundError
from backend.app.db.session import get_db
from backend.app.models.paper import (
    FutureWorkExtractionResponse,
    LimitationExtractionResponse,
    Paper,
    PaperNLPProcessResponse,
    ScientificExtraction,
    ScientificExtractionResponse,
    ScientificSentence,
    ScientificSentenceResponse,
)
from backend.app.services.nlp.nlp_service import scientific_nlp_service

router = APIRouter(prefix="/nlp", tags=["Scientific NLP (Phase 2)"])


@router.post(
    "/process/{paper_id}",
    response_model=PaperNLPProcessResponse,
    status_code=status.HTTP_200_OK,
    summary="Process scientific paper with Phase 2 NLP pipeline",
)
def process_paper_nlp(
    paper_id: int,
    db: Session = Depends(get_db),
) -> PaperNLPProcessResponse:
    """Segments paper text into granular scientific sentences, executes discourse

    classification, detects limitations and future work, and extracts domain entities
    with full provenance.
    """
    return scientific_nlp_service.process_paper(paper_id=paper_id, db=db)


@router.get(
    "/papers/{paper_id}/sentences",
    response_model=List[ScientificSentenceResponse],
    summary="Retrieve segmented sentences for a paper with provenance",
)
def get_paper_sentences(
    paper_id: int,
    db: Session = Depends(get_db),
) -> List[ScientificSentenceResponse]:
    """Retrieves all segmented sentences with preserved section and page numbers."""
    paper = db.scalar(select(Paper).where(Paper.id == paper_id))
    if not paper:
        raise NotFoundError(f"Paper with ID {paper_id} not found.")

    sentences = db.scalars(
        select(ScientificSentence)
        .where(ScientificSentence.paper_id == paper_id)
        .order_by(ScientificSentence.sentence_order)
    ).all()

    return [
        ScientificSentenceResponse(
            id=s.id,
            paper_id=s.paper_id,
            paragraph_id=s.paragraph_id,
            sentence_order=s.sentence_order,
            source_text=s.source_text,
            section_name=s.section_name,
            page_number=s.page_number,
        )
        for s in sentences
    ]


@router.get(
    "/papers/{paper_id}/extractions",
    response_model=List[ScientificExtractionResponse],
    summary="Retrieve classified scientific extractions for a paper",
)
def get_paper_extractions(
    paper_id: int,
    extraction_type: Optional[str] = Query(
        None,
        description="Filter by type: PROBLEM, OBJECTIVE, METHOD, DATASET, METRIC, RESULT, LIMITATION, FUTURE_WORK",
    ),
    db: Session = Depends(get_db),
) -> List[ScientificExtractionResponse]:
    """Retrieves classified scientific claims and entities with traceable provenance."""
    paper = db.scalar(select(Paper).where(Paper.id == paper_id))
    if not paper:
        raise NotFoundError(f"Paper with ID {paper_id} not found.")

    stmt = select(ScientificExtraction).where(ScientificExtraction.paper_id == paper_id)
    if extraction_type:
        stmt = stmt.where(ScientificExtraction.extraction_type == extraction_type.upper().strip())

    extractions = db.scalars(stmt.order_by(ScientificExtraction.id)).all()

    return [
        ScientificExtractionResponse(
            id=e.id,
            paper_id=e.paper_id,
            sentence_id=e.sentence_id,
            extraction_type=e.extraction_type,
            extracted_text=e.extracted_text,
            confidence=e.confidence,
            extraction_method=e.extraction_method,
            provenance=e.provenance or {},
            created_at=e.created_at,
        )
        for e in extractions
    ]


@router.get(
    "/papers/{paper_id}/limitations",
    response_model=List[LimitationExtractionResponse],
    summary="Retrieve detected research limitations and bottlenecks",
)
def get_paper_limitations(
    paper_id: int,
    db: Session = Depends(get_db),
) -> List[LimitationExtractionResponse]:
    """Retrieves all detected limitations, categorized by subtype (computational,

    data scarcity, generalization, methodological, etc.).
    """
    paper = db.scalar(select(Paper).where(Paper.id == paper_id))
    if not paper:
        raise NotFoundError(f"Paper with ID {paper_id} not found.")

    extractions = db.scalars(
        select(ScientificExtraction)
        .where(
            ScientificExtraction.paper_id == paper_id,
            ScientificExtraction.extraction_type == "LIMITATION",
        )
        .order_by(ScientificExtraction.id)
    ).all()

    results: List[LimitationExtractionResponse] = []
    for e in extractions:
        prov = e.provenance or {}
        results.append(
            LimitationExtractionResponse(
                id=e.id,
                paper_id=e.paper_id,
                sentence_id=e.sentence_id,
                limitation_text=e.extracted_text,
                limitation_type=prov.get("limitation_subtype", "generic"),
                confidence=e.confidence,
                provenance=prov,
                section_name=prov.get("section_name", "Unknown"),
                page_number=prov.get("page_number", 1),
            )
        )

    return results


@router.get(
    "/papers/{paper_id}/future-work",
    response_model=List[FutureWorkExtractionResponse],
    summary="Retrieve detected future research directions and proposed extensions",
)
def get_paper_future_work(
    paper_id: int,
    db: Session = Depends(get_db),
) -> List[FutureWorkExtractionResponse]:
    """Retrieves candidate future directions and proposed extensions."""
    paper = db.scalar(select(Paper).where(Paper.id == paper_id))
    if not paper:
        raise NotFoundError(f"Paper with ID {paper_id} not found.")

    extractions = db.scalars(
        select(ScientificExtraction)
        .where(
            ScientificExtraction.paper_id == paper_id,
            ScientificExtraction.extraction_type == "FUTURE_WORK",
        )
        .order_by(ScientificExtraction.id)
    ).all()

    results: List[FutureWorkExtractionResponse] = []
    for e in extractions:
        prov = e.provenance or {}
        results.append(
            FutureWorkExtractionResponse(
                id=e.id,
                paper_id=e.paper_id,
                sentence_id=e.sentence_id,
                future_work_text=e.extracted_text,
                confidence=e.confidence,
                provenance=prov,
                section_name=prov.get("section_name", "Unknown"),
                page_number=prov.get("page_number", 1),
            )
        )

    return results
