"""Scientific Limitation Detector (Phase 2).

Specialized detector identifying scientific weaknesses, constraints, bottlenecks,
lack of generalization, and failure modes across scientific text.
Crucial foundation for research gap discovery.
"""

import re
from typing import Any, Dict, Optional, Tuple

from backend.app.core.logging import get_logger

logger = get_logger("app.nlp.limitation_detector")


class LimitationDetector:
    """Contextual scientific limitation detector with subtype categorization."""

    SUBTYPES = ["computational", "data_scarcity", "generalization", "methodological", "generic"]

    # Subtype-specific linguistic markers
    SUBTYPE_PATTERNS = {
        "computational": [
            re.compile(r"\b(?:quadratic|exponential|polynomial)\s+(?:time|complexity|memory|cost|scaling)\b", re.I),
            re.compile(r"\bO\([nN]\^[2-9]\)|\bO\([nN]\s*log\s*[nN]\)", re.I),
            re.compile(r"\b(?:computationally|prohibitively|excessively)\s+(?:expensive|costly|demanding|slow|heavy)\b", re.I),
            re.compile(r"\b(?:gpu|memory|vram|hardware|inference)\s+(?:overhead|bottleneck|constraint|footprint|latency)\b", re.I),
            re.compile(r"\b(?:cannot|unable\s+to)\s+scale\s+to\b", re.I),
            re.compile(r"\blong\s+(?:context|sequences?|documents?)\s+remains?\s+(?:prohibitive|challenging)\b", re.I),
        ],
        "data_scarcity": [
            re.compile(r"\b(?:lack|scarcity|shortage|sparsity|absence)\s+of\s+(?:annotated|labeled|training|paired)?\s*data\b", re.I),
            re.compile(r"\b(?:expensive|costly|difficult|labor-intensive)\s+to\s+(?:annotate|label|collect|acquire)\b", re.I),
            re.compile(r"\bsmall\s+(?:sample\s+size|dataset|corpus|benchmark)\b", re.I),
            re.compile(r"\brequires?\s+(?:large|vast|huge|massive)\s+(?:amounts|volumes)\s+of\s+(?:labeled|training)\b", re.I),
            re.compile(r"\blimited\s+(?:labeled|training|annotated)\s+(?:examples|data|supervision)\b", re.I),
        ],
        "generalization": [
            re.compile(r"\b(?:fails?|struggles?|degrades?)\s+(?:to\s+generalize|on\s+out-of-distribution|across\s+domains?)\b", re.I),
            re.compile(r"\b(?:out-of-domain|out-of-distribution|cross-domain)\s+(?:performance|generalization|transfer)\b", re.I),
            re.compile(r"\b(?:domain|distributional)\s+shift\b", re.I),
            re.compile(r"\bsusceptible\s+to\s+(?:hallucination|overfitting|shortcuts|spurious)\b", re.I),
            re.compile(r"\brestricted\s+to\s+(?:the\s+)?(?:synthetic|narrow|specific)\s+(?:setting|domain|benchmark)\b", re.I),
            re.compile(r"\bdoes\s+not\s+(?:readily\s+)?transfer\s+to\b", re.I),
        ],
        "methodological": [
            re.compile(r"\bsensitive\s+to\s+(?:hyperparameters?|initialization|prompting|choice\s+of)\b", re.I),
            re.compile(r"\brelies\s+on\s+the\s+(?:strong|unrealistic|simplifying)\s+assumption\b", re.I),
            re.compile(r"\b(?:approximation|accumulated|cascading)\s+errors?\b", re.I),
            re.compile(r"\btrade-?offs?\s+between\s+(?:speed|accuracy|precision|recall|memory)\b", re.I),
            re.compile(r"\black\s+of\s+(?:interpretability|explainability|theoretical\s+guarantees)\b", re.I),
            re.compile(r"\bcannot\s+(?:guarantee|prove|ensure)\b", re.I),
        ],
        "generic": [
            re.compile(r"\b(?:a|the|major|key|primary|notable|inherent)\s+limitations?\b", re.I),
            re.compile(r"\b(?:suffer|suffers|suffering)\s+from\b", re.I),
            re.compile(r"\b(?:drawback|weakness|shortcoming|vulnerability|flaw)s?\b", re.I),
            re.compile(r"\bremains?\s+(?:a\s+)?(?:major\s+)?(?:challenge|bottleneck|open\s+issue|unsolved)\b", re.I),
            re.compile(r"\b(?:despite|notwithstanding)\s+(?:these|the)\s+(?:advances|gains|improvements)\b", re.I),
            re.compile(r"\bfails?\s+to\s+(?:capture|account\s+for|address|handle)\b", re.I),
            re.compile(r"\bunderperforms?\b", re.I),
            re.compile(r"\bnot\s+suitable\s+for\b", re.I),
        ],
    }

    def __init__(self) -> None:
        pass

    def detect(self, sentence: str, section_name: str = "") -> Optional[Dict[str, Any]]:
        """Detects whether a sentence expresses a scientific limitation.

        Returns:
            Dictionary with {limitation_text, subtype, confidence} or None if not a limitation.
        """
        if not sentence or len(sentence.strip()) < 10:
            return None

        clean_sent = sentence.strip()
        sec_lower = section_name.strip().lower()

        # Section heuristic boost
        in_limitation_section = any(
            kw in sec_lower for kw in ["limitation", "threats to validity", "weakness", "drawback"]
        )

        matched_subtype = None
        highest_weight = 0.0

        for subtype, patterns in self.SUBTYPE_PATTERNS.items():
            for pat in patterns:
                if pat.search(clean_sent):
                    weight = 2.5 if subtype != "generic" else 1.8
                    if weight > highest_weight:
                        highest_weight = weight
                        matched_subtype = subtype

        # If in a dedicated limitation section, default to generic limitation even if subtle
        if in_limitation_section and not matched_subtype:
            # Check if negative/constraint discourse marker exists
            if re.search(r"\b(?:however|although|yet|while|though|cannot|limited|constrained|assumes?)\b", clean_sent, re.I):
                matched_subtype = "generic"
                highest_weight = 1.6

        if not matched_subtype:
            return None

        # Calculate calibrated confidence
        base_conf = 0.70
        if highest_weight >= 2.5:
            base_conf += 0.18
        if in_limitation_section:
            base_conf += 0.10

        confidence = round(min(base_conf, 0.98), 2)

        return {
            "limitation_text": clean_sent,
            "subtype": matched_subtype,
            "confidence": confidence,
            "in_limitation_section": in_limitation_section,
        }


# Singleton instance
limitation_detector = LimitationDetector()
