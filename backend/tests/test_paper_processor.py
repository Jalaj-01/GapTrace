"""Unit tests for PaperProcessor extraction and validation logic."""

from pathlib import Path
import pytest

from backend.app.core.errors import CorruptedPDFError, FileTooLargeError, InvalidFileTypeError
from backend.app.services.paper_processor import ExtractedPaperData, PaperProcessor

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_PDF = FIXTURES_DIR / "sample_paper.pdf"
SHORT_PDF = FIXTURES_DIR / "sample_paper_short.pdf"
CORRUPT_PDF = FIXTURES_DIR / "corrupted_paper.pdf"
TXT_FILE = FIXTURES_DIR / "invalid_file.txt"


@pytest.fixture
def processor():
    return PaperProcessor()


def test_validate_pdf_bytes_success(processor):
    """Verify validation passes for genuine PDF bytes."""
    valid_bytes = SAMPLE_PDF.read_bytes()
    processor.validate_pdf_bytes(valid_bytes)


def test_validate_pdf_bytes_magic_error(processor):
    """Verify non-PDF bytes raise InvalidFileTypeError."""
    invalid_bytes = TXT_FILE.read_bytes()
    with pytest.raises(InvalidFileTypeError):
        processor.validate_pdf_bytes(invalid_bytes)


def test_validate_pdf_bytes_corrupted(processor):
    """Verify corrupted PDF bytes raise CorruptedPDFError."""
    corrupted_bytes = CORRUPT_PDF.read_bytes()
    with pytest.raises(CorruptedPDFError):
        processor.validate_pdf_bytes(corrupted_bytes)


def test_validate_pdf_bytes_too_large(processor):
    """Verify file exceeding max limit raises FileTooLargeError."""
    valid_bytes = SAMPLE_PDF.read_bytes()
    with pytest.raises(FileTooLargeError):
        processor.validate_pdf_bytes(valid_bytes, max_size_bytes=100)


def test_process_sample_pdf_metadata(processor):
    """Verify metadata extraction: title, authors, abstract, year, DOI."""
    data: ExtractedPaperData = processor.process_pdf(SAMPLE_PDF)

    assert "Attention Is All You Need" in data.title
    assert data.page_count == 2
    assert data.year == 2024 or data.year == 2017
    assert data.doi is not None
    assert "10.48550" in data.doi
    assert data.abstract is not None
    assert "Transformer" in data.abstract
    assert len(data.authors) >= 1
    assert any("Vaswani" in a for a in data.authors)


def test_process_sample_pdf_sections(processor):
    """Verify section extraction preserves names, page numbers, and paragraphs."""
    data: ExtractedPaperData = processor.process_pdf(SAMPLE_PDF)
    section_names = [s.name.lower() for s in data.sections]

    assert any("abstract" in name for name in section_names)
    assert any("introduction" in name for name in section_names)
    assert any("methodology" in name for name in section_names)
    assert any("limitations" in name for name in section_names)
    assert any("conclusion" in name for name in section_names)

    # Check page numbers
    for section in data.sections:
        assert section.page_start >= 1
        assert section.page_end >= section.page_start
        assert section.page_end <= data.page_count
        assert len(section.text) > 0
        assert len(section.paragraphs) > 0

    # Specifically check Limitations section
    limitations = next(s for s in data.sections if "limitations" in s.name.lower())
    assert limitations.page_start == 2
    assert "quadratic" in limitations.text.lower()


def test_process_sample_pdf_references(processor):
    """Verify references are parsed into structured items."""
    data: ExtractedPaperData = processor.process_pdf(SAMPLE_PDF)

    assert len(data.references) >= 2
    first_ref = data.references[0]
    assert first_ref.ref_index >= 1
    assert "Bahdanau" in first_ref.raw_text or "Hochreiter" in first_ref.raw_text
    assert first_ref.year in [1997, 2015, 2017]


def test_process_short_pdf(processor):
    """Verify processing single-page paper."""
    data: ExtractedPaperData = processor.process_pdf(SHORT_PDF)

    assert "Graph Neural Networks" in data.title
    assert data.page_count == 1
    assert len(data.sections) >= 2
    assert any("limitations" in s.name.lower() for s in data.sections)
    assert len(data.references) >= 1


def test_compute_sha256_stability(processor):
    """Verify SHA-256 computation produces consistent 64-char hex string."""
    b1 = b"%PDF-1.4 sample content"
    hash1 = processor.compute_sha256(b1)
    hash2 = processor.compute_sha256(b1)
    assert hash1 == hash2
    assert len(hash1) == 64
