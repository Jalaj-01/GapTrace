"""Transparent & Explainable Prioritization Scoring Engine (Phase 6).

Implements the documented prioritization ranking formula:
S_priority = sum(w_k * s_k)

IMPORTANT SYSTEM GUARANTEE:
- gap_priority_score is strictly an empirical PRIORITIZATION score.
- It must NEVER be presented as the 'probability that the research gap is true'.
- Every score is accompanied by an itemized contribution breakdown.
"""

from typing import Any, Dict, List, Tuple
from backend.app.models.paper import GapSignalContribution
from backend.app.services.gaps.signals import SignalResult, SignalType


# Canonical, mathematically documented signal weights (Sum = 1.00)
SIGNAL_WEIGHTS: Dict[SignalType, float] = {
    SignalType.REPEATED_LIMITATIONS: 0.25,        # Recurrent bottlenecks have highest urgency
    SignalType.UNDEREXPLORATION: 0.20,            # Unexplored territories represent prime white-space
    SignalType.TEMPORAL_OPPORTUNITY: 0.15,        # Multi-year stagnation signals unaddressed challenges
    SignalType.CROSS_DOMAIN_OPPORTUNITY: 0.15,    # Generalization failure outside primary silo
    SignalType.CONFLICTING_EVIDENCE: 0.10,        # Scientific disputes demanding arbitration
    SignalType.METHODOLOGICAL_CONCENTRATION: 0.08,# Monoculture vulnerability
    SignalType.DATASET_CONCENTRATION: 0.07,       # Benchmark overfitting vulnerability
}

SCORING_FORMULA_DOCUMENTATION = (
    "S_priority = 0.25 * RepeatedLimitations + 0.20 * Underexploration + "
    "0.15 * TemporalOpportunity + 0.15 * CrossDomainOpportunity + "
    "0.10 * ConflictingEvidence + 0.08 * MethodConcentration + "
    "0.07 * DatasetConcentration. "
    "Scale: [0.0, 1.0]. Represents empirical prioritization urgency, NOT probability of truth."
)


class GapPriorityScorer:
    """Computes transparent, component-wise prioritization scores for candidate research gaps."""

    @classmethod
    def calculate_priority(
        cls,
        signals: Dict[SignalType, SignalResult],
        confidence_multiplier: float = 1.0,
    ) -> Tuple[float, List[GapSignalContribution], str]:
        """Compute the weighted priority score and generate explainable contributions.

        Returns:
            Tuple of (priority_score, breakdown_list, narrative_explanation)
        """
        total_score = 0.0
        contributions: List[GapSignalContribution] = []
        explanation_lines = []

        for sig_type, weight in SIGNAL_WEIGHTS.items():
            res = signals.get(sig_type)
            val = res.raw_value if res else 0.0
            contrib = round(weight * val, 4)
            total_score += contrib

            exp = res.explanation if res else f"Signal {sig_type.value} was inactive."
            contributions.append(GapSignalContribution(
                signal_name=sig_type.value,
                signal_value=round(val, 4),
                weight=weight,
                contribution=contrib,
                explanation=exp,
            ))

            if res and res.is_active:
                explanation_lines.append(f"+{contrib:.3f} ({sig_type.value}): {exp}")

        # Clamp priority score to [0.0, 1.0]
        final_priority = round(max(0.0, min(1.0, total_score)), 4)

        if explanation_lines:
            narrative = (
                f"Candidate priority score is {final_priority:.2f} based on {len(explanation_lines)} active signals: "
                + " | ".join(explanation_lines)
            )
        else:
            narrative = "No empirical signals were strongly active for this candidate."

        return final_priority, contributions, narrative
