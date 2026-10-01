"""Research Gap Candidate Engine Services Package (Phase 6).

Implements:
- 7 measurable signals: Underexploration, Repeated Limitations, Method Concentration,
  Dataset Concentration, Temporal Opportunity, Cross-Domain Opportunity, Conflicting Evidence
- Evidence-backed Gap Candidate Generator with strict evidence thresholds
- Transparent, explainable Prioritization Scoring Engine (S_priority)
- Expert-labeled benchmark evaluator (Precision@5, Recall@10)
"""

from backend.app.services.gaps.signals import (
    GapSignalDetectors,
    SignalType,
    SignalResult,
)
from backend.app.services.gaps.priority_scorer import (
    GapPriorityScorer,
    SIGNAL_WEIGHTS,
)
from backend.app.services.gaps.candidate_generator import (
    ResearchGapCandidateGenerator,
    get_gap_candidate_generator,
)
from backend.app.services.gaps.benchmark_evaluator import (
    GapBenchmarkEvaluator,
)
from backend.app.services.gaps.lifecycle_service import (
    GapLifecycleTracker,
    get_gap_lifecycle_tracker,
)
from backend.app.services.gaps.verification_service import (
    GapVerificationEngine,
    ScientificNLIEngine,
    get_gap_verification_engine,
)

__all__ = [
    "GapSignalDetectors",
    "SignalType",
    "SignalResult",
    "GapPriorityScorer",
    "SIGNAL_WEIGHTS",
    "ResearchGapCandidateGenerator",
    "get_gap_candidate_generator",
    "GapBenchmarkEvaluator",
    "GapLifecycleTracker",
    "get_gap_lifecycle_tracker",
    "GapVerificationEngine",
    "ScientificNLIEngine",
    "get_gap_verification_engine",
]
