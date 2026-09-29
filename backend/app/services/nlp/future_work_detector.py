"""Scientific Future Work Detector (Phase 2).

Identifies forward-looking statements, proposed extensions, open questions,
and recommended experimental directions across scientific literature.
"""

import re
from typing import Any, Dict, Optional

from backend.app.core.logging import get_logger

logger = get_logger("app.nlp.future_work_detector")


class FutureWorkDetector:
    """Contextual detector for future work statements and research trajectories."""

    FUTURE_WORK_PATTERNS = [
        # Explicit author commitments
        (re.compile(r"\b(?:leave|leaves)\s+(?:this|these|it|all\s+this|further\s+analysis)\s+(?:for|to)\s+(?:future|subsequent)\s+work\b", re.I), 3.5),
        (re.compile(r"\bin\s+(?:the\s+)?future\s*,\s*(?:we|one)\s+(?:plan|plans|aim|aims|intend|hope)\b", re.I), 3.2),
        (re.compile(r"\bwe\s+(?:plan|intend|hope|aim)\s+to\s+(?:extend|explore|investigate|generalize|apply|evaluate|incorporate)\b", re.I), 3.0),
        # Open research questions & opportunities
        (re.compile(r"\bremains?\s+an\s+open\s+(?:question|problem|challenge|avenue)\s+(?:for|in)\b", re.I), 3.0),
        (re.compile(r"\ban\s+(?:interesting|promising|exciting|natural)\s+(?:direction|avenue|extension)\s+(?:for|of)\s+future\b", re.I), 3.2),
        (re.compile(r"\bfuture\s+(?:work|research|investigations?|studies)\s+(?:will|should|could|might)\s+(?:focus|explore|address|examine)\b", re.I), 3.0),
        (re.compile(r"\bfurther\s+(?:research|investigation|exploration|study|work)\s+is\s+(?:needed|warranted|required|encouraged)\b", re.I), 2.8),
        # Conditional extensions
        (re.compile(r"\bcould\s+be\s+(?:fruitfully\s+)?(?:extended|applied|adapted|generalized|scaled)\s+to\b", re.I), 2.6),
        (re.compile(r"\bit\s+would\s+be\s+(?:valuable|interesting|worthwhile)\s+to\s+(?:explore|investigate|test)\b", re.I), 2.8),
        (re.compile(r"\ba\s+promising\s+direction\s+is\s+to\b", re.I), 2.8),
    ]

    def __init__(self) -> None:
        pass

    def detect(self, sentence: str, section_name: str = "") -> Optional[Dict[str, Any]]:
        """Detects whether a sentence specifies a future work direction.

        Returns:
            Dictionary with {future_work_text, confidence, in_future_work_section} or None.
        """
        if not sentence or len(sentence.strip()) < 10:
            return None

        clean_sent = sentence.strip()
        sec_lower = section_name.strip().lower()

        in_conclusion_or_future = any(
            kw in sec_lower for kw in ["future work", "conclusion", "conclusions and future work", "discussion"]
        )

        matched_weight = 0.0
        for pat, weight in self.FUTURE_WORK_PATTERNS:
            if pat.search(clean_sent):
                if weight > matched_weight:
                    matched_weight = weight

        # Section heuristic boost
        if "future work" in sec_lower and matched_weight == 0.0:
            # Inside a dedicated 'Future Work' section, check if it contains forward verbs
            if re.search(r"\b(?:will|should|could|plan|aim|explore|investigate|study|hope|next)\b", clean_sent, re.I):
                matched_weight = 2.2

        if matched_weight == 0.0:
            return None

        base_conf = 0.72
        if matched_weight >= 3.0:
            base_conf += 0.16
        if in_conclusion_or_future:
            base_conf += 0.08

        confidence = round(min(base_conf, 0.98), 2)

        return {
            "future_work_text": clean_sent,
            "confidence": confidence,
            "in_future_work_section": in_conclusion_or_future,
        }


# Singleton instance
future_work_detector = FutureWorkDetector()
