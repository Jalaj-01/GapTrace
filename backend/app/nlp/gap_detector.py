"""Scientific research gap, limitation, and contradiction detector interface."""

from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel


class DetectedGap(BaseModel):
    category: str  # limitation, contradiction, unaddressed_question, methodology_gap
    summary: str
    evidence_quote: str
    source_paper_title: str
    source_section: str
    confidence: Optional[float] = None


class BaseGapDetector(ABC):
    """Abstract interface for research gap detection across scientific papers."""

    @abstractmethod
    def extract_limitations_and_gaps(self, paper_text: str, sections: dict) -> List[DetectedGap]:
        """Identify explicit limitations and open questions stated in paper sections."""
        pass

    @abstractmethod
    def detect_cross_paper_contradictions(self, claim_pairs: List[tuple]) -> List[DetectedGap]:
        """Detect conflicting empirical findings or contradictory claims across papers."""
        pass


class GapDetector(BaseGapDetector):
    """Scientific research gap detector stub for Phase 1."""

    def extract_limitations_and_gaps(self, paper_text: str, sections: dict) -> List[DetectedGap]:
        raise NotImplementedError("Research gap detection will be implemented in Phase 1.")

    def detect_cross_paper_contradictions(self, claim_pairs: List[tuple]) -> List[DetectedGap]:
        raise NotImplementedError("Cross-paper contradiction detection will be implemented in Phase 1.")
