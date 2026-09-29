"""Scientific Text Preprocessor (Phase 2).

Normalizes scientific PDF extraction text without aggressively destroying
citations, acronyms, mathematical symbols, or sentence boundary cues.
"""

import re
import unicodedata
from typing import Optional

from backend.app.core.logging import get_logger

logger = get_logger("app.nlp.preprocessor")


class ScientificPreprocessor:
    """Robust, non-destructive text preprocessor for scientific literature."""

    # Unicode ligatures mapping to ASCII equivalents
    LIGATURE_MAP = {
        "\ufb00": "ff",
        "\ufb01": "fi",
        "\ufb02": "fl",
        "\ufb03": "ffi",
        "\ufb04": "ffl",
        "\ufb05": "ft",
        "\ufb06": "st",
        "\u0152": "OE",
        "\u0153": "oe",
        "\u00c6": "AE",
        "\u00e6": "ae",
    }

    # Zero-width, non-printing, and soft-hyphen characters
    ZERO_WIDTH_CHARS_REGEX = re.compile(
        r"[\u200B\u200C\u200D\u200E\u200F\uFEFF\u00AD\u202A-\u202E]"
    )

    # Line-break hyphenation repair: "atten-\ntion" -> "attention"
    # Matches a lowercase letter followed by hyphen, newline, and lowercase letter
    HYPHENATION_REGEX = re.compile(r"([a-z]{2,})-\s*\n\s*([a-z]{2,})")

    # Broken footnote/page-number fragments at ends of lines like "[1]\n" or "12\n"
    STANDALONE_LINE_NUMBER = re.compile(r"\n\s*\d+\s*\n")

    def __init__(self) -> None:
        pass

    def clean_text(self, text: Optional[str]) -> str:
        """Cleans and normalizes scientific text while preserving critical tokens."""
        if not text:
            return ""

        # 1. Normalize Unicode (NFC form standardizes accented glyphs)
        cleaned = unicodedata.normalize("NFC", text)

        # 2. Replace Unicode ligatures
        for lig, repl in self.LIGATURE_MAP.items():
            if lig in cleaned:
                cleaned = cleaned.replace(lig, repl)

        # 3. Strip zero-width & directional markers
        cleaned = self.ZERO_WIDTH_CHARS_REGEX.sub("", cleaned)

        # 4. Repair line-break hyphenations (e.g., "repre-\nsentation" -> "representation")
        cleaned = self.HYPHENATION_REGEX.sub(r"\1\2", cleaned)

        # 5. Remove isolated line numbers that frequently appear in PDF margins
        cleaned = self.STANDALONE_LINE_NUMBER.sub("\n", cleaned)

        # 6. Normalize non-standard whitespace while respecting paragraphs
        # Replace carriage returns and vertical tabs
        cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")

        # Collapse excessive inline spaces and tabs (2+ horizontal spaces -> 1)
        cleaned = re.sub(r"[ \t]+", " ", cleaned)

        # Collapse 3+ newlines to 2 (preserving paragraph breaks)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

        # 7. Strip leading and trailing whitespace
        return cleaned.strip()

    def normalize_sentence(self, sentence: str) -> str:
        """Normalizes a single segmented sentence.
        
        Collapses any internal line breaks into a single space and trims whitespace.
        """
        if not sentence:
            return ""
        # Remove internal linebreaks inside a single sentence
        s = re.sub(r"\s*\n\s*", " ", sentence)
        # Collapse multiple spaces
        s = re.sub(r"\s{2,}", " ", s)
        return s.strip()

    # Alias for API uniformity
    preprocess = clean_text


# Singleton instance
scientific_preprocessor = ScientificPreprocessor()
