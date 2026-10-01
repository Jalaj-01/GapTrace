"""Measurable Scientific Signals for Research Gap Detection (Phase 6).

Implements the 7 core empirical signals:
1. UNDEREXPLORATION: Detects low research coverage / sparse graph connectivity
2. REPEATED_LIMITATIONS: Detects recurrent bottlenecks across multiple independent papers
3. METHODOLOGICAL_CONCENTRATION: Detects algorithmic monopoly / high HHI
4. DATASET_CONCENTRATION: Detects over-reliance on limited empirical benchmarks
5. TEMPORAL_OPPORTUNITY: Detects limitations that persist unaddressed across multiple years
6. CROSS_DOMAIN_OPPORTUNITY: Detects methods/topics lacking cross-domain evaluation
7. CONFLICTING_EVIDENCE: Detects disputed claims or contradictory findings
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np

from backend.app.core.logging import get_logger

logger = get_logger("app.gaps.signals")


class SignalType(str, Enum):
    UNDEREXPLORATION = "underexploration"
    REPEATED_LIMITATIONS = "repeated_limitations"
    METHODOLOGICAL_CONCENTRATION = "methodological_concentration"
    DATASET_CONCENTRATION = "dataset_concentration"
    TEMPORAL_OPPORTUNITY = "temporal_opportunity"
    CROSS_DOMAIN_OPPORTUNITY = "cross_domain_opportunity"
    CONFLICTING_EVIDENCE = "conflicting_evidence"


@dataclass
class SignalResult:
    """Result of an individual signal evaluation."""
    signal_type: SignalType
    raw_value: float  # Normalized to [0.0, 1.0]
    is_active: bool
    explanation: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class GapSignalDetectors:
    """Collection of mathematical and rule-based detectors for the 7 research gap signals."""

    @staticmethod
    def detect_underexploration(
        topic_paper_count: int,
        mean_topic_papers: float = 4.0,
        subgraph_density: float = 0.05,
    ) -> SignalResult:
        """1. Detects areas where important relationships or topics have low research coverage."""
        if mean_topic_papers <= 0:
            mean_topic_papers = 1.0

        ratio = topic_paper_count / mean_topic_papers
        # Underexplored if paper volume is noticeably lower than corpus average
        if ratio < 0.75:
            score = max(0.0, min(1.0, 1.0 - (ratio / 0.75) * 0.7))
            active = True
            exp = (
                f"Topic is underexplored with only {topic_paper_count} papers "
                f"(corpus average is {mean_topic_papers:.1f} papers/topic)."
            )
        else:
            score = 0.0
            active = False
            exp = f"Topic has adequate coverage ({topic_paper_count} papers vs avg {mean_topic_papers:.1f})."

        return SignalResult(
            signal_type=SignalType.UNDEREXPLORATION,
            raw_value=round(score, 4),
            is_active=active,
            explanation=exp,
            metadata={"topic_paper_count": topic_paper_count, "mean_topic_papers": mean_topic_papers},
        )

    @staticmethod
    def detect_repeated_limitations(
        distinct_paper_ids: Set[int],
        limitation_count: int,
    ) -> SignalResult:
        """2. Detects limitations appearing across multiple independent papers."""
        k = len(distinct_paper_ids)
        if k >= 2:
            # Activates at 2 papers; scales upwards with paper breadth
            score = min(1.0, 0.60 + 0.15 * (k - 2) + min(0.10, limitation_count * 0.02))
            active = True
            exp = f"Limitation appears independently across {k} distinct publications ({limitation_count} total citations/occurrences)."
        else:
            score = 0.0
            active = False
            exp = "Limitation is isolated to a single paper or author cohort."

        return SignalResult(
            signal_type=SignalType.REPEATED_LIMITATIONS,
            raw_value=round(score, 4),
            is_active=active,
            explanation=exp,
            metadata={"distinct_papers": k, "total_limitations": limitation_count},
        )

    @staticmethod
    def detect_methodological_concentration(
        method_counts: Dict[str, int],
    ) -> SignalResult:
        """3. Detects areas dominated by a small number of methods using Herfindahl-Hirschman Index (HHI)."""
        total = sum(method_counts.values())
        if total <= 1:
            return SignalResult(
                signal_type=SignalType.METHODOLOGICAL_CONCENTRATION,
                raw_value=0.0,
                is_active=False,
                explanation="Insufficient method count to evaluate concentration.",
            )

        # Calculate HHI = sum(p_i^2)
        shares = [cnt / total for cnt in method_counts.values()]
        hhi = sum(p**2 for p in shares)

        # High concentration if HHI >= 0.50 (monopolized or duopolized)
        if hhi >= 0.50:
            top_method, top_cnt = max(method_counts.items(), key=lambda x: x[1])
            score = min(1.0, (hhi - 0.40) / 0.60)
            active = True
            exp = (
                f"High methodological concentration (HHI: {hhi:.2f}). Dominant method '{top_method}' "
                f"accounts for {top_cnt}/{total} ({top_cnt/total*100:.0f}%) of usage."
            )
        else:
            score = 0.0
            active = False
            exp = f"Methodological diversity is healthy (HHI: {hhi:.2f})."

        return SignalResult(
            signal_type=SignalType.METHODOLOGICAL_CONCENTRATION,
            raw_value=round(score, 4),
            is_active=active,
            explanation=exp,
            metadata={"hhi": round(hhi, 3), "top_methods": sorted(method_counts.items(), key=lambda x: -x[1])[:3]},
        )

    @staticmethod
    def detect_dataset_concentration(
        dataset_counts: Dict[str, int],
    ) -> SignalResult:
        """4. Detects research heavily dependent on a small number of datasets."""
        total = sum(dataset_counts.values())
        if total <= 1:
            return SignalResult(
                signal_type=SignalType.DATASET_CONCENTRATION,
                raw_value=0.0,
                is_active=False,
                explanation="Insufficient dataset evaluation instances.",
            )

        shares = [cnt / total for cnt in dataset_counts.values()]
        hhi = sum(p**2 for p in shares)

        if hhi >= 0.50:
            top_dataset, top_cnt = max(dataset_counts.items(), key=lambda x: x[1])
            score = min(1.0, (hhi - 0.40) / 0.60)
            active = True
            exp = (
                f"Severe dataset concentration (HHI: {hhi:.2f}). Benchmark '{top_dataset}' "
                f"represents {top_cnt}/{total} ({top_cnt/total*100:.0f}%) of all evaluations."
            )
        else:
            score = 0.0
            active = False
            exp = f"Dataset evaluation is reasonably diverse (HHI: {hhi:.2f})."

        return SignalResult(
            signal_type=SignalType.DATASET_CONCENTRATION,
            raw_value=round(score, 4),
            is_active=active,
            explanation=exp,
            metadata={"hhi": round(hhi, 3), "dataset_counts": dataset_counts},
        )

    @staticmethod
    def detect_temporal_opportunity(
        earliest_year: Optional[int],
        latest_year: Optional[int],
        is_addressed: bool = False,
    ) -> SignalResult:
        """5. Detects limitations that persist over time without being addressed."""
        if not earliest_year or not latest_year or is_addressed:
            return SignalResult(
                signal_type=SignalType.TEMPORAL_OPPORTUNITY,
                raw_value=0.0,
                is_active=False,
                explanation="Limitation is either addressed or lacks longitudinal span.",
            )

        span = latest_year - earliest_year
        if span >= 1:
            # Active if unaddressed for at least 1-2 years
            score = min(1.0, 0.50 + 0.15 * span)
            active = True
            exp = f"Limitation has persisted unaddressed for {span} years ({earliest_year} to {latest_year})."
        else:
            score = 0.0
            active = False
            exp = f"Limitation is recent ({latest_year}) without multi-year persistence."

        return SignalResult(
            signal_type=SignalType.TEMPORAL_OPPORTUNITY,
            raw_value=round(score, 4),
            is_active=active,
            explanation=exp,
            metadata={"span_years": span, "earliest_year": earliest_year, "latest_year": latest_year},
        )

    @staticmethod
    def detect_cross_domain_opportunity(
        domain_counts: Dict[str, int],
        is_high_performing: bool = True,
    ) -> SignalResult:
        """6. Detects methods or techniques that have limited cross-domain evaluation."""
        total_domains = len([d for d, c in domain_counts.items() if c > 0])
        if total_domains <= 1 and is_high_performing:
            score = 0.85
            active = True
            exp = (
                f"Method is proven in domain '{list(domain_counts.keys())[0] if domain_counts else 'General'}' "
                "but has virtually zero cross-domain evaluation in other scientific fields."
            )
        else:
            score = 0.0
            active = False
            exp = f"Method is already evaluated across {total_domains} distinct domains."

        return SignalResult(
            signal_type=SignalType.CROSS_DOMAIN_OPPORTUNITY,
            raw_value=round(score, 4),
            is_active=active,
            explanation=exp,
            metadata={"domain_count": total_domains, "domains": list(domain_counts.keys())},
        )

    @staticmethod
    def detect_conflicting_evidence(
        conflict_count: int,
        conflicting_paper_ids: Set[int],
    ) -> SignalResult:
        """7. Detects contradictory findings or disputing empirical claims."""
        if conflict_count >= 1 and len(conflicting_paper_ids) >= 2:
            score = min(1.0, 0.75 + 0.10 * (conflict_count - 1))
            active = True
            exp = (
                f"Empirical contradiction detected: {conflict_count} conflicting claims found across "
                f"{len(conflicting_paper_ids)} papers."
            )
        else:
            score = 0.0
            active = False
            exp = "No contradictory evidence detected in current literature subset."

        return SignalResult(
            signal_type=SignalType.CONFLICTING_EVIDENCE,
            raw_value=round(score, 4),
            is_active=active,
            explanation=exp,
            metadata={"conflict_count": conflict_count, "papers": list(conflicting_paper_ids)},
        )
