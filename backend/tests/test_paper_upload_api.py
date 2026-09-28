"""Integration tests for Paper upload, validation, extraction, and database persistence."""

from pathlib import Path
from sqlalchemy.orm import Session

from backend.app.models.paper import Paper, PaperReference, PaperSection

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_PDF = FIXTURES_DIR / "sample_paper.pdf"
SHORT_PDF = FIXTURES_DIR / "sample_paper_short.pdf"
CORRUPT_PDF = FIXTURES_DIR / "corrupted_paper.pdf"
TXT_FILE = FIXTURES_DIR / "invalid_file.txt"


def test_upload_valid_pdf_success(client, db_session: Session):
    """Test full upload pipeline: validation -> parsing -> database persistence -> response."""
    with open(SAMPLE_PDF, "rb") as f:
        response = client.post(
            "/api/v1/papers/upload",
            files={"file": ("sample_paper.pdf", f, "application/pdf")},
        )

    assert response.status_code == 201
    payload = response.json()

    # 1. Verify JSON structure
    assert "paper_id" in payload
    assert payload["paper_id"] > 0
    assert "Attention Is All You Need" in payload["title"]
    assert len(payload["authors"]) >= 1
    assert payload["page_count"] == 2
    assert "file_hash" in payload
    assert len(payload["sections"]) >= 3
    assert len(payload["references"]) >= 2

    # Check section representation
    first_section = payload["sections"][0]
    assert "name" in first_section
    assert "page_start" in first_section
    assert "page_end" in first_section
    assert "text" in first_section

    paper_id = payload["paper_id"]

    # 2. Verify Database Persistence directly in DB
    db_paper = db_session.query(Paper).filter(Paper.id == paper_id).first()
    assert db_paper is not None
    assert db_paper.file_hash == payload["file_hash"]

    # Check sections in DB
    db_sections = db_session.query(PaperSection).filter(PaperSection.paper_id == paper_id).all()
    assert len(db_sections) == len(payload["sections"])
    assert any(s.section_name.lower() == "introduction" for s in db_sections)
    assert any(s.section_name.lower() == "limitations" for s in db_sections)

    # Check references in DB
    db_refs = db_session.query(PaperReference).filter(PaperReference.paper_id == paper_id).all()
    assert len(db_refs) == len(payload["references"])
    assert any("Bahdanau" in r.raw_text or "Hochreiter" in r.raw_text for r in db_refs)


def test_upload_duplicate_pdf_conflict(client):
    """Test uploading an identical paper twice triggers 409 Conflict with details."""
    with open(SHORT_PDF, "rb") as f:
        res1 = client.post(
            "/api/v1/papers/upload",
            files={"file": ("short_paper.pdf", f, "application/pdf")},
        )
    assert res1.status_code == 201
    initial_id = res1.json()["paper_id"]

    # Attempt second upload of identical content
    with open(SHORT_PDF, "rb") as f:
        res2 = client.post(
            "/api/v1/papers/upload",
            files={"file": ("short_paper_renamed.pdf", f, "application/pdf")},
        )

    assert res2.status_code == 409
    err = res2.json()
    assert err["success"] is False
    assert err["error"]["code"] == "DUPLICATE_PAPER"
    assert err["error"]["details"]["existing_paper_id"] == initial_id


def test_upload_invalid_extension(client):
    """Test uploading a non-pdf file triggers 400 Bad Request."""
    with open(TXT_FILE, "rb") as f:
        response = client.post(
            "/api/v1/papers/upload",
            files={"file": ("invalid_file.txt", f, "text/plain")},
        )

    assert response.status_code == 400
    err = response.json()
    assert err["success"] is False
    assert err["error"]["code"] == "INVALID_FILE_TYPE"


def test_upload_corrupted_pdf(client):
    """Test uploading damaged/corrupted PDF triggers 422 Unprocessable Content."""
    with open(CORRUPT_PDF, "rb") as f:
        response = client.post(
            "/api/v1/papers/upload",
            files={"file": ("corrupted.pdf", f, "application/pdf")},
        )

    assert response.status_code == 422
    err = response.json()
    assert err["success"] is False
    assert err["error"]["code"] == "CORRUPTED_PDF"


def test_get_structured_paper_endpoint(client):
    """Test retrieving structured paper representation by ID."""
    with open(SAMPLE_PDF, "rb") as f:
        upload_res = client.post(
            "/api/v1/papers/upload",
            files={"file": ("sample_paper.pdf", f, "application/pdf")},
        )
    paper_id = upload_res.json()["paper_id"]

    get_res = client.get(f"/api/v1/papers/{paper_id}")
    assert get_res.status_code == 200
    data = get_res.json()

    assert data["paper_id"] == paper_id
    assert "Attention Is All You Need" in data["title"]
    assert len(data["sections"]) > 0
    assert len(data["references"]) > 0


def test_get_paper_subsections_and_references(client):
    """Test sub-resource routes: /sections and /references."""
    with open(SHORT_PDF, "rb") as f:
        upload_res = client.post(
            "/api/v1/papers/upload",
            files={"file": ("short_paper.pdf", f, "application/pdf")},
        )
    paper_id = upload_res.json()["paper_id"]

    # 1. Sections endpoint
    sec_res = client.get(f"/api/v1/papers/{paper_id}/sections")
    assert sec_res.status_code == 200
    sections = sec_res.json()
    assert isinstance(sections, list)
    assert len(sections) >= 2
    assert "page_start" in sections[0]
    assert "text" in sections[0]

    # 2. References endpoint
    ref_res = client.get(f"/api/v1/papers/{paper_id}/references")
    assert ref_res.status_code == 200
    refs = ref_res.json()
    assert isinstance(refs, list)
    assert len(refs) >= 1
    assert "raw_text" in refs[0]
    assert "ref_index" in refs[0]


def test_get_nonexistent_paper_404(client):
    """Test querying nonexistent paper returns 404 with standard envelope."""
    response = client.get("/api/v1/papers/888888")
    assert response.status_code == 404
    err = response.json()
    assert err["success"] is False
    assert err["error"]["code"] == "NOT_FOUND"
