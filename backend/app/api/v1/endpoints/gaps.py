"""Research Gap Candidate API Endpoints (Phase 6).

Exposes:
- GET /api/v1/gaps/candidates
- GET /api/v1/gaps/candidates/{gap_id}
- GET /api/v1/gaps/candidates/{gap_id}/evidence
- GET /api/v1/gaps/signals
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.core.errors import NotFoundError, ValidationError
from backend.app.db.session import get_db
from backend.app.models.paper import (
    GapCandidatesListResponse,
    GapCounterEvidenceResponse,
    GapEvidenceItem,
    GapGenealogyResponse,
    GapLifecycleDetailResponse,
    GapLifecycleOverviewResponse,
    GapSignalsOverviewResponse,
    GapTimelineResponse,
    GapVerificationResponse,
    GapVerifyRequest,
    ResearchGapCandidateResponse,
    CitationValidationReport,
    CitationValidationRequest,
    GapSynthesisResponse,
    GapSynthesizeRequest,
)
from backend.app.services.gaps.candidate_generator import get_gap_candidate_generator
from backend.app.services.gaps.lifecycle_service import get_gap_lifecycle_tracker
from backend.app.services.gaps.verification_service import get_gap_verification_engine
from backend.app.services.llm import get_gap_rag_synthesizer, get_citation_validator
from backend.app.services.gaps.priority_scorer import (
    SCORING_FORMULA_DOCUMENTATION,
    SIGNAL_WEIGHTS,
)
from backend.app.services.gaps.signals import SignalType

router = APIRouter()


def _find_candidate_or_404(gap_id: str, db: Session) -> ResearchGapCandidateResponse:
    """Helper to locate a research gap candidate by exact ID or suffix."""
    generator = get_gap_candidate_generator()
    candidates = generator.generate_candidates(db=db)

    for cand in candidates:
        if cand.gap_id == gap_id or cand.gap_id.endswith(gap_id):
            return cand

    raise NotFoundError(f"Research gap candidate '{gap_id}' not found.")


@router.get(
    "/candidates",
    response_model=GapCandidatesListResponse,
    summary="List Grounded Research Gap Candidates",
    description="Retrieve ranked candidate research gaps generated from empirical NLP, topic, and graph signals.",
)
def list_gap_candidates_endpoint(
    gap_type: Optional[str] = Query(None, description="Filter by gap type (repeated_limitation, underexplored_area, etc.)"),
    min_priority: float = Query(0.0, ge=0.0, le=1.0, description="Minimum priority score threshold"),
    min_confidence: float = Query(0.50, ge=0.0, le=1.0, description="Minimum evidence confidence threshold"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of candidates to return"),
    db: Session = Depends(get_db),
) -> GapCandidatesListResponse:
    """Retrieve prioritized list of potential research gap candidates."""
    generator = get_gap_candidate_generator()
    candidates = generator.generate_candidates(
        db=db,
        min_priority=min_priority,
        min_confidence=min_confidence,
    )

    if gap_type:
        gt_clean = gap_type.strip().lower()
        candidates = [c for c in candidates if c.gap_type.lower() == gt_clean]

    truncated = candidates[:limit]

    return GapCandidatesListResponse(
        total_candidates=len(candidates),
        potential_gaps_count=len(candidates),
        verified_gaps_count=0,  # Emphasizes that these are potential candidates, not confirmed facts
        scoring_formula=SCORING_FORMULA_DOCUMENTATION,
        candidates=truncated,
    )


@router.get(
    "/candidates/{gap_id}",
    response_model=ResearchGapCandidateResponse,
    summary="Research Gap Candidate Detail",
    description="Retrieve comprehensive detail for a single candidate gap including component signal breakdown.",
)
def get_gap_candidate_detail_endpoint(
    gap_id: str,
    db: Session = Depends(get_db),
) -> ResearchGapCandidateResponse:
    """Retrieve a single research gap candidate by identifier."""
    return _find_candidate_or_404(gap_id, db)


@router.get(
    "/candidates/{gap_id}/evidence",
    response_model=List[GapEvidenceItem],
    summary="Supporting Evidence for Research Gap Candidate",
    description="Retrieve all grounded source sentences, paper sections, and page numbers supporting this candidate.",
)
def get_gap_candidate_evidence_endpoint(
    gap_id: str,
    db: Session = Depends(get_db),
) -> List[GapEvidenceItem]:
    """Retrieve all supporting evidence excerpts for a candidate gap."""
    cand = _find_candidate_or_404(gap_id, db)
    return cand.supporting_evidence


@router.get(
    "/signals",
    response_model=GapSignalsOverviewResponse,
    summary="Overview of Research Gap Signals & Scoring Formula",
    description="Retrieve definitions, canonical weights, and documentation for the 7 empirical signals.",
)
def get_signals_overview_endpoint() -> GapSignalsOverviewResponse:
    """Retrieve definitions and weights for all 7 gap signals."""
    signal_definitions = {
        SignalType.UNDEREXPLORATION.value: {
            "description": "Detects research areas with low paper volume relative to corpus average.",
            "mathematical_basis": "Normalized negative deviation from corpus topic mean.",
            "weight": SIGNAL_WEIGHTS[SignalType.UNDEREXPLORATION],
        },
        SignalType.REPEATED_LIMITATIONS.value: {
            "description": "Detects recurrent bottlenecks independently stated across multiple publications.",
            "mathematical_basis": "Linear scaling starting at k >= 2 distinct papers.",
            "weight": SIGNAL_WEIGHTS[SignalType.REPEATED_LIMITATIONS],
        },
        SignalType.METHODOLOGICAL_CONCENTRATION.value: {
            "description": "Detects algorithmic monoculture and high concentration within a domain.",
            "mathematical_basis": "Herfindahl-Hirschman Index (HHI) >= 0.50.",
            "weight": SIGNAL_WEIGHTS[SignalType.METHODOLOGICAL_CONCENTRATION],
        },
        SignalType.DATASET_CONCENTRATION.value: {
            "description": "Detects empirical over-reliance on limited benchmark datasets.",
            "mathematical_basis": "Herfindahl-Hirschman Index (HHI) >= 0.50.",
            "weight": SIGNAL_WEIGHTS[SignalType.DATASET_CONCENTRATION],
        },
        SignalType.TEMPORAL_OPPORTUNITY.value: {
            "description": "Detects persistent limitations unaddressed across multiple publication years.",
            "mathematical_basis": "Multi-year span (Delta Y >= 1) with zero incoming 'addresses' edges.",
            "weight": SIGNAL_WEIGHTS[SignalType.TEMPORAL_OPPORTUNITY],
        },
        SignalType.CROSS_DOMAIN_OPPORTUNITY.value: {
            "description": "Detects techniques with strong performance but absent cross-domain evaluation.",
            "mathematical_basis": "Single-domain confinement with high empirical validation.",
            "weight": SIGNAL_WEIGHTS[SignalType.CROSS_DOMAIN_OPPORTUNITY],
        },
        SignalType.CONFLICTING_EVIDENCE.value: {
            "description": "Detects empirical contradictions and disputed claims between publications.",
            "mathematical_basis": "Presence of 'contradicts' relationships in the knowledge graph.",
            "weight": SIGNAL_WEIGHTS[SignalType.CONFLICTING_EVIDENCE],
        },
    }

    return GapSignalsOverviewResponse(
        total_signals=len(signal_definitions),
        signal_definitions=signal_definitions,
        scoring_formula=SCORING_FORMULA_DOCUMENTATION,
        weights={k.value: v for k, v in SIGNAL_WEIGHTS.items()},
    )


# ==============================================================================
# Phase 7: Gap Genealogy & Gap Lifecycle Endpoints
# ==============================================================================

@router.get(
    "/lifecycle/overview",
    response_model=GapLifecycleOverviewResponse,
    summary="Overview of Gap Lifecycle Distribution",
    description="Aggregate lifecycle state distribution (EMERGING, PERSISTENT, PARTIALLY_ADDRESSED, ADDRESSED, REOPENED, UNCERTAIN) across all candidates.",
)
def get_lifecycle_overview_endpoint(
    db: Session = Depends(get_db),
) -> GapLifecycleOverviewResponse:
    """Retrieve overview of gap lifecycle states across the scientific corpus."""
    generator = get_gap_candidate_generator()
    candidates = generator.generate_candidates(db=db)
    tracker = get_gap_lifecycle_tracker()
    return tracker.get_lifecycle_overview(candidates)


@router.get(
    "/{gap_id}/timeline",
    response_model=GapTimelineResponse,
    summary="Chronological Timeline of Research Gap Evolution",
    description="Retrieve chronologically ordered events (first appearance, repeated limitations, attempted solutions, later evidence).",
)
@router.get(
    "/candidates/{gap_id}/timeline",
    response_model=GapTimelineResponse,
    include_in_schema=False,
)
def get_gap_timeline_endpoint(
    gap_id: str,
    db: Session = Depends(get_db),
) -> GapTimelineResponse:
    """Construct chronological progression timeline for a candidate research gap."""
    cand = _find_candidate_or_404(gap_id, db)
    tracker = get_gap_lifecycle_tracker()
    return tracker.build_timeline(cand)


@router.get(
    "/{gap_id}/genealogy",
    response_model=GapGenealogyResponse,
    summary="Evolutionary Genealogy Chain for Research Gap",
    description="Reconstruct developmental sequence: Root problem -> Attempted mitigation -> Secondary bottleneck -> Current candidate gap.",
)
@router.get(
    "/candidates/{gap_id}/genealogy",
    response_model=GapGenealogyResponse,
    include_in_schema=False,
)
def get_gap_genealogy_endpoint(
    gap_id: str,
    db: Session = Depends(get_db),
) -> GapGenealogyResponse:
    """Reconstruct step-by-step evolutionary genealogy chain for a research gap."""
    cand = _find_candidate_or_404(gap_id, db)
    tracker = get_gap_lifecycle_tracker()
    return tracker.build_genealogy(cand)


@router.get(
    "/{gap_id}/lifecycle",
    response_model=GapLifecycleDetailResponse,
    summary="Lifecycle Status & Temporal Evidence Analysis",
    description="Determine lifecycle status (EMERGING, PERSISTENT, PARTIALLY_ADDRESSED, ADDRESSED, REOPENED, UNCERTAIN) backed by multi-paper evidence.",
)
@router.get(
    "/candidates/{gap_id}/lifecycle",
    response_model=GapLifecycleDetailResponse,
    include_in_schema=False,
)
def get_gap_lifecycle_endpoint(
    gap_id: str,
    db: Session = Depends(get_db),
) -> GapLifecycleDetailResponse:
    """Retrieve lifecycle status and temporal reasoning for a research gap."""
    cand = _find_candidate_or_404(gap_id, db)
    tracker = get_gap_lifecycle_tracker()
    return tracker.analyze_lifecycle(cand)


# ==============================================================================
# Phase 8: Counter-Evidence Search & Gap Verification Endpoints
# ==============================================================================

@router.get(
    "/{gap_id}/verification",
    response_model=GapVerificationResponse,
    summary="Evidence-Grounded Gap Verification",
    description="Expose supporting, counter, addressed, and contradictory evidence with NLI and temporal verification.",
)
@router.get(
    "/candidates/{gap_id}/verification",
    response_model=GapVerificationResponse,
    include_in_schema=False,
)
def get_gap_verification_endpoint(
    gap_id: str,
    db: Session = Depends(get_db),
) -> GapVerificationResponse:
    """Retrieve multi-category verification analysis and confidence for a research gap."""
    cand = _find_candidate_or_404(gap_id, db)
    engine = get_gap_verification_engine()
    return engine.verify_candidate_gap(cand)


@router.get(
    "/{gap_id}/counter-evidence",
    response_model=GapCounterEvidenceResponse,
    summary="Active Counter-Evidence for Research Gap",
    description="Retrieve opposing arguments, refutations, mitigations, and empirical contradictions.",
)
@router.get(
    "/candidates/{gap_id}/counter-evidence",
    response_model=GapCounterEvidenceResponse,
    include_in_schema=False,
)
def get_gap_counter_evidence_endpoint(
    gap_id: str,
    db: Session = Depends(get_db),
) -> GapCounterEvidenceResponse:
    """Retrieve counter, addressed, and contradictory evidence for a candidate gap."""
    cand = _find_candidate_or_404(gap_id, db)
    engine = get_gap_verification_engine()
    return engine.get_counter_evidence(cand)


@router.post(
    "/{gap_id}/verify",
    response_model=GapVerificationResponse,
    summary="Trigger Active Gap Verification & NLI Inference",
    description="Actively search literature and knowledge graph for supporting and counter evidence and update verification status.",
)
@router.post(
    "/candidates/{gap_id}/verify",
    response_model=GapVerificationResponse,
    include_in_schema=False,
)
def verify_gap_candidate_endpoint(
    gap_id: str,
    request: Optional[GapVerifyRequest] = None,
    db: Session = Depends(get_db),
) -> GapVerificationResponse:
    """Trigger active verification and NLI classification for a research gap."""
    cand = _find_candidate_or_404(gap_id, db)
    engine = get_gap_verification_engine()
    req = request or GapVerifyRequest()
    return engine.verify_candidate_gap(
        gap=cand,
        min_confidence=req.min_confidence,
        include_nli=req.include_nli,
    )


# ==============================================================================
# Phase 9: Evidence-Grounded RAG and LLM Synthesis Endpoints
# ==============================================================================

@router.post(
    "/{gap_id}/synthesize",
    response_model=GapSynthesisResponse,
    summary="Generate Grounded LLM Synthesis for Verified Gap",
    description="Synthesize structured gap explanation, practical importance, evidence summary, research questions, and limitations grounded in retrieved passages.",
)
@router.post(
    "/candidates/{gap_id}/synthesize",
    response_model=GapSynthesisResponse,
    include_in_schema=False,
)
async def synthesize_gap_endpoint(
    gap_id: str,
    request: Optional[GapSynthesizeRequest] = None,
    db: Session = Depends(get_db),
) -> GapSynthesisResponse:
    """Trigger LLM synthesis for a research gap grounded in retrieved multi-paper evidence."""
    synthesizer = get_gap_rag_synthesizer()
    return await synthesizer.synthesize_gap(
        gap_id=gap_id,
        db=db,
        request=request,
    )


@router.get(
    "/{gap_id}/synthesis",
    response_model=GapSynthesisResponse,
    summary="Get Cached or On-Demand Synthesis for Gap",
    description="Retrieve previously generated synthesis or generate a new grounded synthesis on demand.",
)
@router.get(
    "/candidates/{gap_id}/synthesis",
    response_model=GapSynthesisResponse,
    include_in_schema=False,
)
async def get_gap_synthesis_endpoint(
    gap_id: str,
    db: Session = Depends(get_db),
) -> GapSynthesisResponse:
    """Retrieve existing synthesis or generate on demand."""
    synthesizer = get_gap_rag_synthesizer()
    cached = synthesizer.get_cached_synthesis(gap_id)
    if cached:
        return cached

    # Generate on demand
    return await synthesizer.synthesize_gap(
        gap_id=gap_id,
        db=db,
    )


@router.post(
    "/validate-citations",
    response_model=CitationValidationReport,
    summary="Validate Grounded Evidence Citations in Synthesis",
    description="Perform automated factuality and citation check, identify hallucinated citations, and calculate Evidence Support Rate.",
)
def validate_citations_endpoint(
    request: CitationValidationRequest,
) -> CitationValidationReport:
    """Validate citations against provided source evidence map."""
    validator = get_citation_validator(min_support_score=request.min_support_score)
    return validator.validate_text(
        text=request.text,
        citations=request.citations,
    )



