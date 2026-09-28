"""Scientific Paper Ingestion & PDF Processing Service."""

import hashlib
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import fitz  # PyMuPDF
from pydantic import BaseModel, Field

from backend.app.core.errors import CorruptedPDFError, FileTooLargeError, InvalidFileTypeError
from backend.app.core.logging import get_logger

logger = get_logger("app.paper_processor")


class ExtractedSection(BaseModel):
    name: str
    page_start: int
    page_end: int
    text: str
    paragraphs: List[str] = Field(default_factory=list)


class ExtractedReference(BaseModel):
    ref_index: int
    raw_text: str
    title: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = None
    venue: Optional[str] = None


class ExtractedPaperData(BaseModel):
    title: str
    authors: List[str] = Field(default_factory=list)
    abstract: Optional[str] = None
    year: Optional[int] = None
    doi: Optional[str] = None
    venue: Optional[str] = None
    page_count: int
    file_hash: str
    file_size: int
    sections: List[ExtractedSection] = Field(default_factory=list)
    references: List[ExtractedReference] = Field(default_factory=list)


class PaperProcessor:
    """Robust scientific PDF extractor and structure parser."""

    # Standard scientific section name detection patterns
    KNOWN_SECTIONS = [
        "abstract",
        "introduction",
        "related work",
        "background",
        "literature review",
        "methodology",
        "method",
        "methods",
        "approach",
        "system architecture",
        "proposed method",
        "materials and methods",
        "experiments",
        "experimental setup",
        "evaluation",
        "results",
        "results and discussion",
        "discussion",
        "limitations",
        "threats to validity",
        "future work",
        "conclusion",
        "conclusions",
        "conclusions and future work",
        "acknowledgments",
        "acknowledgements",
        "references",
        "bibliography",
        "appendix",
    ]

    SECTION_HEADER_REGEX = re.compile(
        r"^(?:(?:\d+(?:\.\d+)*|[I|V|X]+(?:\.[A-Z])?)\.?\s+)?("
        + "|".join(re.escape(s) for s in KNOWN_SECTIONS)
        + r")(?:[:\.\s].*)?$",
        re.IGNORECASE,
    )

    YEAR_REGEX = re.compile(r"\b(19\d{2}|20[0-2]\d)\b")
    DOI_REGEX = re.compile(r"\b(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)\b")

    @classmethod
    def compute_sha256(cls, file_bytes: bytes) -> str:
        """Computes SHA-256 hex digest for document deduplication."""
        return hashlib.sha256(file_bytes).hexdigest()

    @classmethod
    def validate_pdf_bytes(cls, content: bytes, max_size_bytes: int = 25 * 1024 * 1024) -> None:
        """Validates PDF file size, header magic bytes, and readable structure."""
        if len(content) > max_size_bytes:
            raise FileTooLargeError(
                f"File size ({len(content)} bytes) exceeds maximum limit of {max_size_bytes} bytes."
            )

        if not content.startswith(b"%PDF-"):
            raise InvalidFileTypeError("File header does not contain valid PDF magic bytes (%PDF-).")

        try:
            doc = fitz.open(stream=content, filetype="pdf")
            if doc.is_encrypted:
                raise CorruptedPDFError("Encrypted or password-protected PDFs are not supported.")
            if len(doc) == 0:
                raise CorruptedPDFError("PDF document contains 0 pages.")
            # Probe first page to confirm readable stream
            _ = doc[0].get_text()
            doc.close()
        except Exception as exc:
            if isinstance(exc, (CorruptedPDFError, InvalidFileTypeError, FileTooLargeError)):
                raise
            raise CorruptedPDFError(f"PDF integrity validation failed: {str(exc)}")

    def process_pdf(self, file_path: Path | str) -> ExtractedPaperData:
        """Parses a scientific PDF file into a clean structured representation."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found at: {file_path}")

        file_bytes = file_path.read_bytes()
        file_hash = self.compute_sha256(file_bytes)
        file_size = len(file_bytes)

        try:
            doc = fitz.open(file_path)
        except Exception as exc:
            raise CorruptedPDFError(f"Failed to open PDF document: {exc}")

        try:
            page_count = len(doc)
            logger.info(f"Processing PDF '{file_path.name}' ({page_count} pages, {file_size} bytes)")

            # 1. Extract per-page text blocks and spans
            pages_data = self._extract_pages_content(doc)

            # 2. Detect Paper Title
            title = self._detect_title(pages_data, doc.metadata)

            # 3. Detect Abstract
            abstract = self._detect_abstract(pages_data)

            # 4. Detect Authors
            authors = self._detect_authors(pages_data, title, abstract, doc.metadata)

            # 5. Detect Publication Year & DOI
            year = self._detect_publication_year(pages_data, doc.metadata)
            doi = self._detect_doi(pages_data, doc.metadata)

            # 6. Detect Structural Sections & Paragraphs
            sections, references = self._detect_sections_and_references(pages_data, abstract)

            return ExtractedPaperData(
                title=title,
                authors=authors,
                abstract=abstract,
                year=year,
                doi=doi,
                venue=None,
                page_count=page_count,
                file_hash=file_hash,
                file_size=file_size,
                sections=sections,
                references=references,
            )
        finally:
            doc.close()

    def _extract_pages_content(self, doc: fitz.Document) -> List[Dict[str, Any]]:
        """Extracts structured text blocks and layout metadata with font sizes for each page."""
        pages = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_dict = page.get_text("dict")
            text_blocks = []

            for b in page_dict.get("blocks", []):
                # type 0 is text block
                if b.get("type") == 0:
                    block_lines = []
                    max_size = 0.0
                    for line in b.get("lines", []):
                        line_text = "".join(span.get("text", "") for span in line.get("spans", []))
                        for span in line.get("spans", []):
                            sz = span.get("size", 0.0)
                            if sz > max_size:
                                max_size = sz
                        if line_text.strip():
                            block_lines.append(line_text.strip())

                    block_text = "\n".join(block_lines).strip()
                    if block_text:
                        text_blocks.append({
                            "bbox": b.get("bbox", (0, 0, 0, 0)),
                            "text": block_text,
                            "max_font_size": max_size,
                            "block_no": b.get("number", 0),
                        })

            rect = page.rect
            width, height = rect.width, rect.height
            sorted_blocks = self._sort_reading_order(text_blocks, width)

            pages.append({
                "page_num": page_num + 1,
                "width": width,
                "height": height,
                "blocks": sorted_blocks,
                "raw_text": page.get_text("text"),
            })

        return pages

    def _sort_reading_order(self, blocks: List[Dict[str, Any]], page_width: float) -> List[Dict[str, Any]]:
        """Sorts blocks in reading order, handling single or two-column scientific papers."""
        if not blocks:
            return []

        mid = page_width / 2.0
        left_col = []
        right_col = []
        full_width = []

        for b in blocks:
            x0, y0, x1, y1 = b["bbox"]
            if x0 < mid * 0.7 and x1 > mid * 1.3:
                full_width.append(b)
            elif x1 <= mid + 20:
                left_col.append(b)
            elif x0 >= mid - 20:
                right_col.append(b)
            else:
                full_width.append(b)

        if len(left_col) >= 2 and len(right_col) >= 2:
            full_width.sort(key=lambda b: b["bbox"][1])
            left_col.sort(key=lambda b: b["bbox"][1])
            right_col.sort(key=lambda b: b["bbox"][1])
            return full_width + left_col + right_col

        return sorted(blocks, key=lambda b: (round(b["bbox"][1] / 10) * 10, b["bbox"][0]))

    def _detect_title(self, pages_data: List[Dict[str, Any]], metadata: Dict[str, Any]) -> str:
        """Identifies paper title using font size prominence and header filtering."""
        if not pages_data:
            return metadata.get("title") or "Untitled Paper"

        page1_blocks = pages_data[0]["blocks"]
        page_height = pages_data[0]["height"]

        # Filter candidate title blocks in upper 45% of page 1
        candidates = []
        for b in page1_blocks:
            y0 = b["bbox"][1]
            text = b["text"].strip()
            # Ignore blocks below upper 45% of page 1
            if y0 > page_height * 0.45:
                continue
            # Stop if we hit Abstract
            if re.search(r"^\s*abstract\b", text, re.IGNORECASE):
                break
            # Skip common running headers (Proceedings, arXiv, DOI, Journal, Volume)
            if re.search(r"^(proceedings|doi:|arxiv:|issn|isbn|vol\.|volume|journal|ieee|acm)", text, re.IGNORECASE):
                continue
            if len(text) < 4:
                continue

            candidates.append(b)

        if candidates:
            # Pick the candidate block with the largest font size
            best_block = max(candidates, key=lambda b: b.get("max_font_size", 0.0))
            title = best_block["text"].replace("\n", " ").strip()
            title = re.sub(r"\s+", " ", title).strip()
            if len(title) >= 5:
                return title

        meta_title = (metadata.get("title") or "").strip()
        if meta_title and len(meta_title) > 3 and not meta_title.endswith(".pdf"):
            return meta_title

        return "Untitled Paper"

    def _detect_abstract(self, pages_data: List[Dict[str, Any]]) -> Optional[str]:
        """Extracts the abstract section text."""
        abstract_lines = []
        capturing = False

        for page in pages_data[:2]:  # Abstracts are on page 1 or 2
            for block in page["blocks"]:
                text = block["text"]
                lines = text.split("\n")

                for line in lines:
                    trimmed = line.strip()
                    # Check for abstract start
                    match = re.match(r"^\s*abstract[\s\:\.\—\-]*(.*)$", trimmed, re.IGNORECASE)
                    if match:
                        capturing = True
                        rest = match.group(1).strip()
                        if rest:
                            abstract_lines.append(rest)
                        continue

                    if capturing:
                        # Check for end of abstract: keywords or introduction
                        if re.match(r"^(?:(?:1\.|I\.)\s+)?(?:introduction|keywords|index terms)\b", trimmed, re.IGNORECASE):
                            capturing = False
                            break
                        abstract_lines.append(trimmed)

                if capturing and abstract_lines and len(" ".join(abstract_lines)) > 200:
                    # Check if next block is a clear section
                    pass

            if abstract_lines and not capturing:
                break

        if abstract_lines:
            abstract_text = " ".join(abstract_lines)
            return re.sub(r"\s+", " ", abstract_text).strip()

        return None

    def _detect_authors(
        self,
        pages_data: List[Dict[str, Any]],
        title: str,
        abstract: Optional[str],
        metadata: Dict[str, Any],
    ) -> List[str]:
        """Detects author list between title and abstract."""
        authors = []
        if pages_data:
            page1_blocks = pages_data[0]["blocks"]
            found_title = False
            for b in page1_blocks:
                b_text = b["text"].strip()
                if not found_title:
                    if title in b_text or b_text in title:
                        found_title = True
                    continue

                # Stop if we hit abstract or introduction
                if re.search(r"^\s*(abstract|introduction)\b", b_text, re.IGNORECASE):
                    break

                # Exclude obvious affiliation markers (department, university, email, @)
                lines = [l.strip() for l in b_text.split("\n") if l.strip()]
                for line in lines:
                    if "@" in line or re.search(r"\b(university|institute|department|college|lab|email)\b", line, re.IGNORECASE):
                        continue
                    # Clean author names separated by commas or 'and'
                    candidates = re.split(r",|\band\b|;", line)
                    for c in candidates:
                        cleaned = re.sub(r"[\d\*\†\‡\§]", "", c).strip()
                        if cleaned and len(cleaned.split()) in [2, 3, 4] and not re.search(r"abstract", cleaned, re.IGNORECASE):
                            if cleaned not in authors:
                                authors.append(cleaned)

        if not authors and metadata.get("author"):
            meta_authors = metadata["author"]
            for a in re.split(r",|;|\band\b", meta_authors):
                a_clean = a.strip()
                if a_clean and a_clean not in authors:
                    authors.append(a_clean)

        return authors

    def _detect_publication_year(
        self,
        pages_data: List[Dict[str, Any]],
        metadata: Dict[str, Any],
    ) -> Optional[int]:
        """Detects publication year from text patterns or document metadata."""
        # 1. Search text on page 1
        if pages_data:
            page1_text = pages_data[0]["raw_text"]
            # Look for copyright or header date
            match = re.search(r"(?:©|copyright|published|proceedings|arxiv:[\d\.]+|vol\.)[^\n\r]*\b(19\d{2}|20[0-2]\d)\b", page1_text, re.IGNORECASE)
            if match:
                return int(match.group(1))

        # 2. Check metadata creationDate (e.g. D:20240412...)
        creation_date = metadata.get("creationDate") or metadata.get("modDate") or ""
        year_match = self.YEAR_REGEX.search(creation_date)
        if year_match:
            return int(year_match.group(1))

        # 3. Fallback: scan page 1 for any valid 4-digit scientific year
        if pages_data:
            years = [int(y) for y in self.YEAR_REGEX.findall(pages_data[0]["raw_text"])]
            # Filter reasonable publication years
            valid_years = [y for y in years if 1950 <= y <= 2027]
            if valid_years:
                return valid_years[0]

        return None

    def _detect_doi(self, pages_data: List[Dict[str, Any]], metadata: Dict[str, Any]) -> Optional[str]:
        """Extracts Digital Object Identifier (DOI) if present."""
        if pages_data:
            match = self.DOI_REGEX.search(pages_data[0]["raw_text"])
            if match:
                return match.group(1)

        for val in metadata.values():
            if isinstance(val, str):
                match = self.DOI_REGEX.search(val)
                if match:
                    return match.group(1)

        return None

    def _detect_sections_and_references(
        self,
        pages_data: List[Dict[str, Any]],
        abstract_text: Optional[str],
    ) -> Tuple[List[ExtractedSection], List[ExtractedReference]]:
        """Parses document into distinct named sections with page ranges and paragraphs."""
        sections: List[ExtractedSection] = []
        references: List[ExtractedReference] = []

        # If abstract exists, register it as the first section
        if abstract_text:
            sections.append(ExtractedSection(
                name="Abstract",
                page_start=1,
                page_end=1,
                text=abstract_text,
                paragraphs=[abstract_text],
            ))

        current_section_name: Optional[str] = None
        current_page_start: int = 1
        current_paragraphs: List[str] = []
        is_in_references = False
        reference_raw_lines: List[str] = []

        for page in pages_data:
            page_num = page["page_num"]
            for block in page["blocks"]:
                block_text = block["text"].strip()
                lines = [l.strip() for l in block_text.split("\n") if l.strip()]
                if not lines:
                    continue

                # Check if the first line of the block is a section header
                first_line = lines[0]
                header_match = self._match_section_header(first_line)

                if header_match:
                    # If this is Abstract and we already recorded an Abstract section, skip re-adding it
                    if header_match.lower() == "abstract" and any(s.name.lower() == "abstract" for s in sections):
                        continue

                    # Save accumulated previous section
                    if current_section_name and current_paragraphs:
                        section_text = "\n\n".join(current_paragraphs)
                        sections.append(ExtractedSection(
                            name=current_section_name,
                            page_start=current_page_start,
                            page_end=page_num,
                            text=section_text,
                            paragraphs=list(current_paragraphs),
                        ))
                        current_paragraphs.clear()

                    current_section_name = header_match
                    current_page_start = page_num

                    if "reference" in current_section_name.lower() or "bibliography" in current_section_name.lower():
                        is_in_references = True
                    else:
                        is_in_references = False

                    # Remaining lines in this block belong to the new section
                    remaining_content = "\n".join(lines[1:]).strip()
                    if remaining_content:
                        if is_in_references:
                            reference_raw_lines.append(remaining_content)
                        else:
                            current_paragraphs.append(self._clean_paragraph_text(remaining_content))
                    continue

                # Regular content block
                cleaned_block = self._clean_paragraph_text(block_text)
                if is_in_references:
                    reference_raw_lines.append(cleaned_block)
                elif current_section_name:
                    current_paragraphs.append(cleaned_block)
                else:
                    # Before first explicit section header (e.g. Introduction)
                    # If it's on page 1 after title/authors and not abstract, treat as Intro/Body
                    if not sections:
                        current_section_name = "Introduction"
                        current_page_start = page_num
                        current_paragraphs.append(cleaned_block)

        # Flush final open section
        if current_section_name and current_paragraphs:
            section_text = "\n\n".join(current_paragraphs)
            sections.append(ExtractedSection(
                name=current_section_name,
                page_start=current_page_start,
                page_end=pages_data[-1]["page_num"] if pages_data else 1,
                text=section_text,
                paragraphs=list(current_paragraphs),
            ))

        # Parse references
        if reference_raw_lines:
            references = self._parse_reference_items(reference_raw_lines)

        return sections, references

    def _match_section_header(self, line: str) -> Optional[str]:
        """Tests if a single line represents a recognized scientific section header."""
        trimmed = line.strip()
        if len(trimmed) > 75:  # Section headers are concise
            return None

        # Check regex pattern
        match = self.SECTION_HEADER_REGEX.match(trimmed)
        if match:
            # Normalize title (e.g., '1. Introduction' -> 'Introduction')
            matched_name = match.group(1).title()
            return matched_name

        # Exact case-insensitive match for common keywords
        lower = trimmed.lower()
        for s in self.KNOWN_SECTIONS:
            if lower == s or lower.startswith(s + ":") or lower.startswith(s + " -"):
                return s.title()

        return None

    def _clean_paragraph_text(self, text: str) -> str:
        """Removes hyphenation artifacts and normalizes whitespace."""
        # Fix line-broken hyphens: e.g. "connec-\ntion" -> "connection"
        cleaned = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)
        cleaned = re.sub(r"\n+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()

    def _parse_reference_items(self, lines: List[str]) -> List[ExtractedReference]:
        """Splits and structures bibliography lines into individual reference records."""
        full_ref_text = "\n".join(lines)
        # Split on bibliography indicators like [1], [2], or (1), (2), or numbered lines
        entries = re.split(r"(?:^|\n)\s*(?:\[(\d+)\]|(\d+)\.)\s*", full_ref_text)
        references: List[ExtractedReference] = []

        if len(entries) > 1:
            idx = 1
            i = 1
            while i < len(entries):
                matched_idx = entries[i] or entries[i+1] if i + 1 < len(entries) else None
                ref_num = int(matched_idx) if matched_idx and matched_idx.isdigit() else idx
                i += 2
                if i < len(entries):
                    item_text = entries[i].strip()
                    if item_text:
                        references.append(self._create_reference_item(ref_num, item_text))
                        idx += 1
                i += 1
        else:
            # Fallback: split by lines
            for idx, item in enumerate(full_ref_text.split("\n"), start=1):
                clean_item = item.strip()
                if len(clean_item) > 15:
                    references.append(self._create_reference_item(idx, clean_item))

        return references

    def _create_reference_item(self, index: int, raw_text: str) -> ExtractedReference:
        """Extracts candidate year and authors from raw reference string."""
        normalized = re.sub(r"\s+", " ", raw_text).strip()
        year_match = self.YEAR_REGEX.search(normalized)
        year = int(year_match.group(1)) if year_match else None

        # Candidate title: text inside quotes if present
        title_match = re.search(r'["“]([^"”]+)["”]', normalized)
        title = title_match.group(1).strip() if title_match else None

        return ExtractedReference(
            ref_index=index,
            raw_text=normalized,
            title=title,
            year=year,
        )
