"""Scientific Result & Finding Detector (Phase 2).

Extracts empirical findings, performance gains, comparative baselines,
statistical significance, and state-of-the-art breakthroughs.
"""

import re
from typing import Any, Dict, List, Optional

from backend.app.core.logging import get_logger

logger = get_logger("app.nlp.result_detector")


class ResultDetector:
    """Detects empirical findings and performance comparisons."""

    # Patterns for finding quantitative improvements
    NUMERICAL_GAIN_PATTERN = re.compile(
        r"(?:improves?|gains?|boosts?|outperforms?|by)\s+(?:an\s+average\s+of\s+)?(\+?\d+(?:\.\d+)?%?)\s*(?:points?|%|BLEU|ROUGE|accuracy)?",
        re.I,
    )

    # Patterns for statistical significance
    P_VALUE_PATTERN = re.compile(r"\(?\s*p\s*(?:<|<=|=)\s*0?\.\d+\s*\)?", re.I)

    RESULT_PATTERNS = [
        (re.compile(r"\boutperforms?\b", re.I), 3.5),
        (re.compile(r"\bachieves?\s+(?:a\s+)?(?:new\s+)?(?:state-of-the-art|SOTA|superior|competitive|higher)\b", re.I), 3.5),
        (re.compile(r"\bimproves?\s+(?:performance|results|accuracy|BLEU|efficiency)\s+(?:by|over)\b", re.I), 3.2),
        (re.compile(r"\bwe\s+observe\s+(?:a\s+)?(?:statistically\s+significant|consistent|substantial)\s+(?:gain|improvement|advantage)\b", re.I), 3.2),
        (re.compile(r"\bresults?\s+(?:demonstrate|show|indicate|reveal|confirm)\s+that\b", re.I), 2.8),
        (re.compile(r"\byields?\s+(?:higher|superior|better|competitive)\b", re.I), 2.6),
        (re.compile(r"\bconsistently\s+beats?\b", re.I), 3.0),
        (re.compile(r"\bestablishes?\s+(?:a\s+)?new\s+benchmark\b", re.I), 3.0),
    ]

    def __init__(self) -> None:
        pass

    def detect(self, sentence: str, section_name: str = "") -> Optional[Dict[str, Any]]:
        """Detects whether a sentence expresses an empirical result or scientific finding.

        Returns:
            Dictionary with {result_text, confidence, numerical_gain, has_p_value} or None.
        """
        if not sentence or len(sentence.strip()) < 10:
            return None

        clean_sent = sentence.strip()
        sec_lower = section_name.strip().lower()

        in_results_section = any(
            kw in sec_lower for kw in ["result", "results", "evaluation", "experiments", "findings", "discussion"]
        )

        matched_weight = 0.0
        for pat, weight in self.RESULT_PATTERNS:
            if pat.search(clean_sent):
                if weight > matched_weight:
                    matched_weight = weight

        # Check for numerical gains and p-values
        num_gain_match = self.NUMERICAL_GAIN_PATTERN.search(clean_sent)
        numerical_gain = num_gain_match.group(0) if num_gain_match else None

        p_val_match = self.P_VALUE_PATTERN.search(clean_sent)
        has_p_value = bool(p_val_match)

        if numerical_gain or has_p_value:
            matched_weight = max(matched_weight, 2.8)

        if in_results_section and matched_weight == 0.0:
            if re.search(r"\b(?:table|figure)\s+\d+\s+(?:shows|illustrates|summarizes)\b", clean_sent, re.I):
                matched_weight = 2.2

        if matched_weight == 0.0:
            return None

        base_conf = 0.70
        if matched_weight >= 3.0:
            base_conf += 0.16
        if in_results_section:
            base_conf += 0.08

        confidence = round(min(base_conf, 0.98), 2)

        return {
            "result_text": clean_sent,
            "confidence": confidence,
            "numerical_gain": numerical_gain,
            "has_p_value": has_p_value,
            "in_results_section": in_results_section,
        }


# Singleton instance
result_detector = ResultDetector()
