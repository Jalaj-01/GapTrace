"""Papers API endpoints: upload, ingestion, section extraction, and retrieval."""

from pathlib import Path
import re
from typing import List, Optional
from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from backend.app.core.config import settings
from backend.app.core.errors import (
    CorruptedPDFError,
    DuplicatePaperError,
    FileTooLargeError,
    InvalidFileTypeError,
    NotFoundError,
)
from backend.app.core.logging import get_logger
from backend.app.db.session import get_db
from backend.app.models.paper import (
    Paper,
    PaperCreate,
    PaperRead,
    PaperReference,
    PaperSection,
    ReferenceJSON,
    SectionJSON,
    StructuredPaperResponse,
)
from backend.app.services.paper_processor import ExtractedPaperData, PaperProcessor

logger = get_logger("app.api.papers")
router = APIRouter()
paper_processor = PaperProcessor()


def sanitize_filename(filename: str) -> str:
    """Removes unsafe characters and path traversal sequences from filenames."""
    basename = Path(filename).name
    # Keep only alphanumerics, underscores, dashes, dots
    cleaned = re.sub(r"[^\w\.\-]", "_", basename)
    return cleaned or "document.pdf"


@router.post(
    "/upload",
    response_model=StructuredPaperResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload & Ingest Scientific PDF",
    description="Validates, securely stores, parses layout/sections/references, and persists paper metadata.",
)
async def upload_paper(
    file: UploadFile = File(..., description="Scientific research paper in PDF format"),
    db: Session = Depends(get_db),
) -> StructuredPaperResponse:
    # 1. Validate file extension
    original_name = file.filename or "paper.pdf"
    if not original_name.lower().endswith(".pdf"):
        raise InvalidFileTypeError(
            f"Invalid file extension for '{original_name}'. Only .pdf files are supported.",
            details={"filename": original_name, "allowed": settings.ALLOWED_EXTENSIONS},
        )

    # 2. Validate MIME content-type
    content_type = (file.content_type or "").lower()
    if content_type and content_type not in settings.ALLOWED_MIME_TYPES:
        raise InvalidFileTypeError(
            f"Invalid MIME type '{content_type}'. Must be 'application/pdf'.",
            details={"content_type": content_type, "allowed": settings.ALLOWED_MIME_TYPES},
        )

    # 3. Read content and validate maximum size
    try:
        content = await file.read()
    except Exception as exc:
        raise CorruptedPDFError(f"Failed to read uploaded stream: {exc}")

    if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise FileTooLargeError(
            f"File size ({len(content)} bytes) exceeds limit of {settings.MAX_UPLOAD_SIZE_BYTES} bytes.",
            details={"size_bytes": len(content), "max_bytes": settings.MAX_UPLOAD_SIZE_BYTES},
        )

    # 4. Validate PDF structure, header magic bytes, and uncorrupted stream
    paper_processor.validate_pdf_bytes(content, settings.MAX_UPLOAD_SIZE_BYTES)

    # 5. Compute SHA-256 hash and check duplicate uploads
    file_hash = paper_processor.compute_sha256(content)
    existing = db.query(Paper).filter(Paper.file_hash == file_hash).first()
    if existing:
        raise DuplicatePaperError(
            f"Paper with identical content already exists (ID: {existing.id}, Title: '{existing.title}').",
            details={"existing_paper_id": existing.id, "title": existing.title, "file_hash": file_hash},
        )

    # 6. Store file safely on disk
    raw_dir = Path(settings.RAW_UPLOAD_DIR)
    raw_dir.mkdir(parents=True, exist_ok=True)
    safe_name = sanitize_filename(original_name)
    target_filename = f"{file_hash[:12]}_{safe_name}"
    target_path = raw_dir / target_filename

    # Ensure path stays within raw_dir (prevent path traversal)
    if not target_path.resolve().is_relative_to(raw_dir.resolve()):
        raise InvalidFileTypeError("Insecure filename causes illegal path traversal.")

    target_path.write_bytes(content)
    logger.info(f"Saved uploaded PDF to: {target_path}")

    # 7. Extract structural sections, authors, year, and references
    extracted: ExtractedPaperData = paper_processor.process_pdf(target_path)

    # 8. Persist to Database within a transaction
    try:
        paper = Paper(
            title=extracted.title,
            doi=extracted.doi,
            abstract=extracted.abstract,
            authors=extracted.authors,
            publication_year=extracted.year,
            venue=extracted.venue,
            file_path=str(target_path),
            file_hash=file_hash,
            file_size=len(content),
            page_count=extracted.page_count,
        )
        db.add(paper)
        db.flush()  # Flush to generate paper.id

        # Insert sections
        for idx, sec in enumerate(extracted.sections):
            paper_section = PaperSection(
                paper_id=paper.id,
                section_name=sec.name,
                section_order=idx,
                page_start=sec.page_start,
                page_end=sec.page_end,
                content=sec.text,
                paragraphs=sec.paragraphs,
            )
            db.add(paper_section)

        # Insert references
        for ref in extracted.references:
            paper_reference = PaperReference(
                paper_id=paper.id,
                ref_index=ref.ref_index,
                raw_text=ref.raw_text,
                title=ref.title,
                authors=ref.authors,
                year=ref.year,
                venue=ref.venue,
            )
            db.add(paper_reference)

        db.commit()
        db.refresh(paper)
        logger.info(f"Successfully ingested Paper ID {paper.id}: '{paper.title}' with {len(extracted.sections)} sections")
    except Exception as exc:
        db.rollback()
        # Clean up saved file on database failure
        if target_path.exists():
            target_path.unlink()
        logger.error(f"Database error during paper ingestion: {exc}")
        raise

    # 9. Format response matching structured JSON specification
    return _build_structured_response(paper)


@router.get(
    "",
    response_model=List[PaperRead],
    status_code=status.HTTP_200_OK,
    summary="List Ingested Papers",
)
def list_papers(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)) -> List[Paper]:
    papers = db.query(Paper).offset(skip).limit(limit).all()
    return papers


@router.post(
    "",
    response_model=PaperRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register New Paper (Metadata)",
)
def create_paper(payload: PaperCreate, db: Session = Depends(get_db)) -> Paper:
    import hashlib
    file_hash = payload.file_hash or hashlib.sha256(f"{payload.title}_{payload.doi}_{payload.publication_year}".encode()).hexdigest()
    paper = Paper(
        title=payload.title,
        doi=payload.doi,
        abstract=payload.abstract,
        authors=payload.authors,
        publication_year=payload.publication_year,
        venue=payload.venue,
        file_path=payload.file_path,
        file_hash=file_hash,
        file_size=payload.file_size,
        page_count=payload.page_count,
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)
    return paper


@router.get(
    "/{paper_id}",
    response_model=StructuredPaperResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Structured Paper Details",
)
def get_paper(paper_id: int, db: Session = Depends(get_db)) -> StructuredPaperResponse:
    paper = (
        db.query(Paper)
        .options(
            joinedload(Paper.sections),
            joinedload(Paper.references),
        )
        .filter(Paper.id == paper_id)
        .first()
    )
    if not paper:
        raise NotFoundError(message=f"Paper with ID {paper_id} not found")

    return _build_structured_response(paper)


@router.get(
    "/{paper_id}/sections",
    response_model=List[SectionJSON],
    status_code=status.HTTP_200_OK,
    summary="Get Paper Structural Sections",
)
def get_paper_sections(paper_id: int, db: Session = Depends(get_db)) -> List[SectionJSON]:
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise NotFoundError(message=f"Paper with ID {paper_id} not found")

    sections = (
        db.query(PaperSection)
        .filter(PaperSection.paper_id == paper_id)
        .order_by(PaperSection.section_order)
        .all()
    )
    return [
        SectionJSON(
            name=s.section_name,
            page_start=s.page_start,
            page_end=s.page_end,
            text=s.content,
            paragraphs=s.paragraphs or [],
        )
        for s in sections
    ]


@router.get(
    "/{paper_id}/references",
    response_model=List[ReferenceJSON],
    status_code=status.HTTP_200_OK,
    summary="Get Paper References",
)
def get_paper_references(paper_id: int, db: Session = Depends(get_db)) -> List[ReferenceJSON]:
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise NotFoundError(message=f"Paper with ID {paper_id} not found")

    refs = (
        db.query(PaperReference)
        .filter(PaperReference.paper_id == paper_id)
        .order_by(PaperReference.ref_index)
        .all()
    )
    return [
        ReferenceJSON(
            ref_index=r.ref_index,
            raw_text=r.raw_text,
            title=r.title,
            authors=r.authors or [],
            year=r.year,
            venue=r.venue,
        )
        for r in refs
    ]


def _build_structured_response(paper: Paper) -> StructuredPaperResponse:
    """Builds clean structured JSON matching the project specification."""
    sections_json = [
        SectionJSON(
            name=sec.section_name,
            page_start=sec.page_start,
            page_end=sec.page_end,
            text=sec.content,
            paragraphs=sec.paragraphs or [],
        )
        for sec in sorted(paper.sections, key=lambda s: s.section_order)
    ]

    references_json = [
        ReferenceJSON(
            ref_index=ref.ref_index,
            raw_text=ref.raw_text,
            title=ref.title,
            authors=ref.authors or [],
            year=ref.year,
            venue=ref.venue,
        )
        for ref in sorted(paper.references, key=lambda r: r.ref_index)
    ]

    return StructuredPaperResponse(
        paper_id=paper.id,
        id=paper.id,
        title=paper.title,
        authors=paper.authors or [],
        year=paper.publication_year,
        doi=paper.doi,
        abstract=paper.abstract,
        venue=paper.venue,
        page_count=paper.page_count,
        file_path=paper.file_path,
        file_hash=paper.file_hash,
        sections=sections_json,
        references=references_json,
    )
