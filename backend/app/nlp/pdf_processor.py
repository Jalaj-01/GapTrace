"""Scientific PDF text extraction and structural section parser."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional
import fitz
from pydantic import BaseModel

from backend.app.services.paper_processor import PaperProcessor, ExtractedPaperData


class ParsedSection(BaseModel):
    title: str
    content: str
    page_start: int
    page_end: int
    paragraphs: List[str] = []


class ParsedPaper(BaseModel):
    title: str
    authors: List[str] = []
    year: Optional[int] = None
    abstract: Optional[str] = None
    sections: List[ParsedSection] = []
    metadata: Dict[str, str] = {}


class BasePDFProcessor(ABC):
    """Abstract interface for scientific PDF parsers."""

    @abstractmethod
    def extract_text(self, pdf_path: Path) -> str:
        """Extract raw text from PDF file."""
        pass

    @abstractmethod
    def parse_paper_structure(self, pdf_path: Path) -> ParsedPaper:
        """Parse structured sections such as Abstract, Introduction, Limitations, Conclusion."""
        pass


class PDFProcessor(BasePDFProcessor):
    """Scientific PDF parser implementation powered by PyMuPDF and PaperProcessor heuristics."""

    def __init__(self):
        self.service = PaperProcessor()

    def extract_text(self, pdf_path: Path) -> str:
        doc = fitz.open(pdf_path)
        try:
            return "".join(page.get_text() for page in doc)
        finally:
            doc.close()

    def parse_paper_structure(self, pdf_path: Path) -> ParsedPaper:
        extracted: ExtractedPaperData = self.service.process_pdf(pdf_path)
        sections = [
            ParsedSection(
                title=s.name,
                content=s.text,
                page_start=s.page_start,
                page_end=s.page_end,
                paragraphs=s.paragraphs,
            )
            for s in extracted.sections
        ]
        return ParsedPaper(
            title=extracted.title,
            authors=extracted.authors,
            year=extracted.year,
            abstract=extracted.abstract,
            sections=sections,
            metadata={"file_hash": extracted.file_hash, "page_count": str(extracted.page_count)},
        )
