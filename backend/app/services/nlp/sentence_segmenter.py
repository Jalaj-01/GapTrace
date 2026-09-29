"""Scientific Sentence Segmenter (Phase 2).

Segments scientific text into granular sentences while preserving complete provenance:
paper_id, section_name, page_number, paragraph_id, and sentence_order.

Carefully avoids false splits on scientific abbreviations, decimal numbers,
citations, and inline equations.
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from backend.app.core.logging import get_logger
from backend.app.services.nlp.scientific_preprocessor import scientific_preprocessor

logger = get_logger("app.nlp.segmenter")

# Sentinels used to protect non-terminating periods
SENTINEL_DOT = "\ue000"


@dataclass
class SegmentedSentence:
    """Dataclass holding a segmented sentence and its full provenance context."""

    paper_id: int
    paragraph_id: int
    sentence_order: int
    source_text: str
    section_name: str
    page_number: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "paper_id": self.paper_id,
            "paragraph_id": self.paragraph_id,
            "sentence_order": self.sentence_order,
            "source_text": self.source_text,
            "section_name": self.section_name,
            "page_number": self.page_number,
        }


class SentenceSegmenter:
    """Scientific sentence boundary detector with abbreviation & citation protection."""

    # Sentinels used to protect non-terminating periods
    SENTINEL_DOT = "\ue000"

    # Known scientific & academic abbreviations
    ABBREVIATIONS = [
        # Academic & Latin
        "e.g.",
        "i.e.",
        "et al.",
        "etc.",
        "cf.",
        "viz.",
        "vs.",
        "v.",
        "ca.",
        "ibid.",
        "op. cit.",
        # References, figures, equations
        "fig.",
        "figs.",
        "eq.",
        "eqs.",
        "eqn.",
        "eqns.",
        "ref.",
        "refs.",
        "sec.",
        "secs.",
        "tab.",
        "tabs.",
        "vol.",
        "vols.",
        "no.",
        "nos.",
        "pp.",
        "p.",
        "ch.",
        "app.",
        # Titles & institutions
        "dr.",
        "prof.",
        "mr.",
        "mrs.",
        "ms.",
        "univ.",
        "dept.",
        "assoc.",
        "proc.",
        "conf.",
        # Common acronyms with dots
        "u.s.",
        "u.k.",
        "ph.d.",
        "m.sc.",
        "b.sc.",
        "approx.",
        "min.",
        "sec.",
        "hr.",
    ]

    # Precompile regex for fast abbreviation protection
    _ABBR_REGEXES = [
        re.compile(r"\b" + re.escape(abbr) if abbr[0].isalnum() else re.escape(abbr), re.IGNORECASE)
        for abbr in ABBREVIATIONS
    ]

    # Pattern for single initial (e.g., "A. Vaswani", "J. L. Ba")
    _INITIAL_PATTERN = re.compile(r"\b([A-Z])\.\s+(?=[A-Z])")

    # Pattern for decimal numbers (e.g., 3.1415, 0.05, .25)
    _DECIMAL_PATTERN = re.compile(r"(\d+)\.(\d+)")

    # Pattern for scientific notation (e.g., 1.5e-4, 3.2 x 10^-3)
    _SCI_NOTATION_PATTERN = re.compile(r"(\d+)\.(\d+[eE][+-]?\d+)")

    # Pattern for citations in brackets containing periods/commas (e.g., [1.2], [1, 2. 3])
    _CITATION_DOT_PATTERN = re.compile(r"(\[\s*\d+)\.(\s*\d+\])")

    # Sentence boundary splitting regex
    # Matches standard termination: period, exclamation, question mark, or closing quote/bracket
    _SPLIT_PATTERN = re.compile(
        r"(?<=[.!?])"  # Lookbehind for terminal punctuation
        r'(?:[\'"”’\)\]]+)?'  # Optional closing quotes or brackets
        r"\s+"  # Whitespace after delimiter
        r'(?=[A-Z"“\'(\[\d•\-\*])'  # Lookahead for start of next sentence
    )

    # Bullet / list item boundary splitting
    _LIST_ITEM_SPLIT = re.compile(
        r"\n\s*(?:[-•*]|\(?\d+[\.\)]|\(?[a-zA-Z][\.\)])\s+"
    )

    def __init__(self) -> None:
        pass

    def protect_non_boundary_periods(self, text: str) -> str:
        """Protects periods in abbreviations, decimals, and citations with sentinels."""
        protected = text

        # 1. Protect scientific notation and decimal numbers
        protected = self._SCI_NOTATION_PATTERN.sub(
            f"\\1{SENTINEL_DOT}\\2", protected
        )
        protected = self._DECIMAL_PATTERN.sub(
            f"\\1{SENTINEL_DOT}\\2", protected
        )

        # 2. Protect author initials (e.g. "A. Vaswani" -> "A<sentinel> Vaswani")
        protected = self._INITIAL_PATTERN.sub(
            f"\\1{SENTINEL_DOT} ", protected
        )

        # 3. Protect specific scientific abbreviations preserving case
        for pattern in self._ABBR_REGEXES:
            protected = pattern.sub(
                lambda m: m.group(0).replace(".", SENTINEL_DOT), protected
            )

        # 4. Protect citations like [1.2]
        protected = self._CITATION_DOT_PATTERN.sub(
            f"\\1{self.SENTINEL_DOT}\\2", protected
        )

        return protected

    def restore_periods(self, text: str) -> str:
        """Restores protected sentinels back to regular periods."""
        return text.replace(self.SENTINEL_DOT, ".")

    def segment_text(self, text: str) -> List[str]:
        """Splits raw text into a list of cleaned, individual sentences."""
        if not text or not text.strip():
            return []

        # 1. Clean with preprocessor
        cleaned = scientific_preprocessor.clean_text(text)
        if not cleaned:
            return []

        # 2. Protect periods
        protected = self.protect_non_boundary_periods(cleaned)

        # 3. Handle paragraph/bullet splits
        paragraphs = re.split(r"\n{2,}", protected)
        raw_sentences: List[str] = []

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Check for bullet list items within paragraph
            if any(bullet in para for bullet in ["\n- ", "\n* ", "\n• "]) or re.search(r"\n\d+\.\s+", para):
                bullet_parts = self._LIST_ITEM_SPLIT.split(para)
                for part in bullet_parts:
                    part_cleaned = part.strip()
                    if part_cleaned:
                        # Further split each bullet part into sentences
                        sub_splits = self._SPLIT_PATTERN.split(part_cleaned)
                        raw_sentences.extend(sub_splits)
            else:
                # Standard paragraph split
                splits = self._SPLIT_PATTERN.split(para)
                raw_sentences.extend(splits)

        # 4. Restore sentinels and normalize each sentence
        results: List[str] = []
        for raw in raw_sentences:
            restored = self.restore_periods(raw)
            normalized = scientific_preprocessor.normalize_sentence(restored)
            # Filter out empty or trivial single-punctuation fragments
            if normalized and len(normalized) > 3 and any(c.isalnum() for c in normalized):
                results.append(normalized)

        return results

    def segment_section(
        self,
        paper_id: int,
        section_name: str,
        paragraphs: List[str],
        page_start: int = 1,
        page_end: int = 1,
        start_order: int = 1,
    ) -> List[SegmentedSentence]:
        """Segments all paragraphs in a section, assigning page numbers and order."""
        segmented_records: List[SegmentedSentence] = []
        current_order = start_order

        total_paragraphs = max(len(paragraphs), 1)

        for p_idx, paragraph_text in enumerate(paragraphs):
            # Estimate page number proportionally across the section's page range
            if page_end > page_start and total_paragraphs > 1:
                progress = p_idx / (total_paragraphs - 1)
                est_page = int(page_start + round(progress * (page_end - page_start)))
            else:
                est_page = page_start

            sentences = self.segment_text(paragraph_text)
            for sent_text in sentences:
                record = SegmentedSentence(
                    paper_id=paper_id,
                    paragraph_id=p_idx,
                    sentence_order=current_order,
                    source_text=sent_text,
                    section_name=section_name,
                    page_number=est_page,
                )
                segmented_records.append(record)
                current_order += 1

        return segmented_records

    # Alias for convenience
    segment = segment_text


# Singleton instance
sentence_segmenter = SentenceSegmenter()
