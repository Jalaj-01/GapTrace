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
        # Explicit author commitments & forward indicators
        (re.compile(r"\b(?:in\s+future\s+work|for\s+future\s+(?:work|research|inquiry|study|iterations)|future\s+(?:research|investigations?|studies|work)\s+(?:will|should|could|might|focus))\b", re.I), 3.6),
        (re.compile(r"\bwe\s+(?:plan|intend|hope|aim)\s+to\s+(?:extend|explore|investigate|generalize|apply|evaluate|incorporate|validate|release)\b", re.I), 3.4),
        (re.compile(r"\b(?:leave|leaves)\b.*?\b(?:for|to|as\s+an\s+avenue\s+for)\s+(?:future|subsequent)\s+(?:work|research|inquiry|iterations|studies)\b", re.I), 3.6),
        (re.compile(r"\b(?:promising|natural|interesting|exciting)\s+(?:direction|avenue|next\s+step)\s+(?:for\s+future|to)\b", re.I), 3.2),
        (re.compile(r"\bfurther\s+(?:research|investigation|exploration|study|work)\s+is\s+(?:needed|warranted|required|encouraged)\b", re.I), 3.0),
        (re.compile(r"\brepresents\s+a\s+natural\s+next\s+step\b", re.I), 3.2),
        (re.compile(r"\bremains\s+(?:an?\s+)?(?:open|promising)\s+(?:question|direction|problem|avenue)\s+for\s+future\b", re.I), 3.2),
        (re.compile(r"\bcould\s+be\s+(?:extended|applied|adapted|generalized)\s+to\b", re.I), 2.4),
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
            if re.search(r"\b(?:will|should|could|plan|aim|explore|investigate|study|hope|next|release)\b", clean_sent, re.I):
                matched_weight = 2.5

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
