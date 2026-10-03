"""Unit Tests for Phase 8: Counter-Evidence Search and Gap Verification.

Validates:
- Scientific NLI Engine (ENTAILMENT, CONTRADICTION, NEUTRAL).
- 7 synthetic test scenarios:
  1. Genuine persistent gap (VERIFIED_OPEN).
  2. Outdated gap (OUTDATED).
  3. Partially addressed gap (PARTIALLY_ADDRESSED).
  4. Contradictory literature (UNCERTAIN).
  5. Insufficient evidence (UNCERTAIN).
  6. Gap supported only by one paper (UNCERTAIN).
  7. Gap with strong counter-evidence (REFUTED with reduced confidence).
- Temporal date comparison and active counter-evidence retrieval.
- Multi-category evidence extraction and provenance.
"""

import pytest
from datetime import datetime, timezone

from backend.app.models.paper import (
    CategorizedEvidenceItem,
    EvidenceType,
    GapEvidenceItem,
    GapVerificationFinalStatus,
    NLILabel,
    ResearchGapCandidateResponse,
)
from backend.app.services.gaps.verification_service import (
    GapVerificationEngine,
    ScientificNLIEngine,
    get_gap_verification_engine,
)
from backend.app.services.graph.research_graph import ResearchKnowledgeGraph
from backend.app.services.graph.relationship_builder import RelationTypes
from backend.app.services.graph.node_builder import NodeTypes


@pytest.fixture
def verification_engine() -> GapVerificationEngine:
    rkg = ResearchKnowledgeGraph()
    return GapVerificationEngine(rkg=rkg)


class TestPhase8NLIEngineUnit:
    """Unit tests for Scientific Natural Language Inference classification."""

    def test_nli_entailment_classification(self):
        """Sentence confirming the limitation is classified as ENTAILMENT."""
        premise = "Self-attention computational memory complexity scales quadratically."
        hypothesis = "We confirm the bottleneck: attention memory overhead remains quadratic across all models."

        res = ScientificNLIEngine.evaluate(premise, hypothesis)
        assert res.label == NLILabel.ENTAILMENT
        assert res.confidence >= 0.85
        assert res.model == ScientificNLIEngine.MODEL_NAME

    def test_nli_contradiction_refutation_classification(self):
        """Sentence refuting or disproving the limitation is classified as CONTRADICTION."""
        premise = "Quadratic attention memory bottleneck prevents long-context scaling."
        hypothesis = "Contrary to prior claims, quadratic scaling is no longer a bottleneck in our linear kernel architecture."

        res = ScientificNLIEngine.evaluate(premise, hypothesis)
        assert res.label == NLILabel.CONTRADICTION
        assert res.confidence >= 0.85

    def test_nli_neutral_classification(self):
        """Descriptive sentence without strong confirmation or refutation is NEUTRAL."""
        premise = "Cross-domain generalization degradation in clinical NLP."
        hypothesis = "We evaluated the models using standard cross-entropy loss on biomedical abstracts."

        res = ScientificNLIEngine.evaluate(premise, hypothesis)
        assert res.label == NLILabel.NEUTRAL
        assert res.confidence >= 0.50


class TestPhase8SyntheticScenariosUnit:
    """Unit tests covering the 7 synthetic scenario datasets."""

    def test_scenario_1_genuine_persistent_gap(self, verification_engine: GapVerificationEngine):
        """Scenario 1: Multi-paper consistent support without counter-evidence -> VERIFIED_OPEN."""
        candidate = ResearchGapCandidateResponse(
            gap_id="gap-syn-persistent-open",
            title="Empirical Bottleneck: Memory Overhead in Self-Attention",
            description="Quadratic self-attention scaling prevents scaling beyond 16k context lengths.",
            gap_type="repeated_limitation",
            supporting_papers=[
                {"paper_id": 1, "title": "Paper 2022", "publication_year": 2022},
                {"paper_id": 2, "title": "Paper 2024", "publication_year": 2024},
            ],
            supporting_evidence=[
                GapEvidenceItem(paper_id=1, source_text="Peak GPU VRAM allocation remains quadratic with sequence length.", confidence=0.92),
                GapEvidenceItem(paper_id=2, source_text="Attention memory bottleneck continues to constrain sequence lengths beyond 32k.", confidence=0.90),
            ],
            gap_priority_score=0.85,
            confidence=0.91,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        res = verification_engine.verify_candidate_gap(candidate)
        assert res.final_status == GapVerificationFinalStatus.VERIFIED_OPEN
        assert res.verification_confidence >= 0.70
        assert len(res.supporting_evidence) == 2
        assert len(res.counter_evidence) == 0

    def test_scenario_2_outdated_gap(self, verification_engine: GapVerificationEngine):
        """Scenario 2: Historically valid bottleneck (> 3 years ago) superseded by modern models -> OUTDATED."""
        candidate = ResearchGapCandidateResponse(
            gap_id="gap-syn-outdated",
            title="Historical Bottleneck: Fixed Embedding Table Memory",
            description="Static word embedding tables consume excessive static memory in word2vec architectures.",
            gap_type="repeated_limitation",
            supporting_papers=[
                {"paper_id": 11, "title": "Old Paper 2018", "publication_year": 2018},
                {"paper_id": 12, "title": "Old Paper 2019", "publication_year": 2019},
            ],
            supporting_evidence=[
                GapEvidenceItem(paper_id=11, source_text="Large vocabulary embedding matrices require excessive RAM.", confidence=0.85),
                GapEvidenceItem(paper_id=12, source_text="Fixed vocabulary lookup tables limit scalability on low-end devices.", confidence=0.82),
            ],
            gap_priority_score=0.40,
            confidence=0.83,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        res = verification_engine.verify_candidate_gap(candidate)
        assert res.final_status == GapVerificationFinalStatus.OUTDATED
        assert "outdated" in res.status_reasoning.lower()

    def test_scenario_3_partially_addressed_gap(self, verification_engine: GapVerificationEngine):
        """Scenario 3: Proposed solutions exist, but residual domain constraints remain -> PARTIALLY_ADDRESSED."""
        candidate = ResearchGapCandidateResponse(
            gap_id="gap-syn-partially-addressed",
            title="Empirical Bottleneck: Cross-Domain Degradation",
            description="Models degrade on out-of-distribution scientific abstracts.",
            gap_type="repeated_limitation",
            supporting_papers=[
                {"paper_id": 21, "title": "Paper 2023", "publication_year": 2023},
                {"paper_id": 22, "title": "Paper 2024", "publication_year": 2024},
                {"paper_id": 23, "title": "Paper 2024", "publication_year": 2024},
            ],
            supporting_evidence=[
                GapEvidenceItem(paper_id=21, source_text="Models degrade severely on out-of-domain biomedical abstracts.", confidence=0.90),
                GapEvidenceItem(paper_id=23, source_text="Transfer loss remains a significant obstacle in clinical subdomains.", confidence=0.88),
                GapEvidenceItem(paper_id=22, source_text="We propose domain-adversarial fine-tuning to mitigate transfer loss.", confidence=0.75),
            ],
            gap_priority_score=0.65,
            confidence=0.85,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        res = verification_engine.verify_candidate_gap(candidate)
        assert res.final_status == GapVerificationFinalStatus.PARTIALLY_ADDRESSED
        assert len(res.addressed_by_evidence) >= 1

    def test_scenario_4_contradictory_literature(self, verification_engine: GapVerificationEngine):
        """Scenario 4: Direct empirical contradictions in knowledge graph -> UNCERTAIN."""
        candidate = ResearchGapCandidateResponse(
            gap_id="gap-syn-contradictory",
            title="Contradictory Claim: Quantization Preserves Reasoning",
            description="4-bit weight quantization causes catastrophic degradation on reasoning tasks.",
            gap_type="conflicting_evidence",
            supporting_papers=[
                {"paper_id": 31, "title": "Paper A 2024", "publication_year": 2024},
                {"paper_id": 32, "title": "Paper B 2024", "publication_year": 2024},
            ],
            supporting_evidence=[
                GapEvidenceItem(paper_id=31, source_text="Severe reasoning degradation occurs when models are quantized to 4 bits.", confidence=0.90),
                GapEvidenceItem(paper_id=32, source_text="4-bit quantization degrades complex math reasoning accuracy.", confidence=0.88),
            ],
            gap_priority_score=0.70,
            confidence=0.89,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Add explicit contradiction edge into graph with pre-created endpoint nodes
        rkg = ResearchKnowledgeGraph()
        rkg.add_node({"id": "paper:33", "type": NodeTypes.PAPER, "properties": {"paper_id": 33, "title": "Paper C 2024"}})
        rkg.add_node({"id": "paper:31", "type": NodeTypes.PAPER, "properties": {"paper_id": 31, "title": "Paper A 2024"}})
        rkg.add_edge({
            "source": "paper:33",
            "target": "paper:31",
            "relationship": RelationTypes.CONTRADICTS,
            "confidence": 0.92,
            "provenance": {
                "paper_id": 33,
                "paper_title": "Paper C 2024",
                "source_text": "Quantization preserves reasoning without degradation on multi-step reasoning benchmarks.",
            },
        })

        res = verification_engine.verify_candidate_gap(candidate, rkg=rkg)
        assert res.final_status == GapVerificationFinalStatus.UNCERTAIN
        assert len(res.contradictory_evidence) >= 1
        assert "contradiction" in res.status_reasoning.lower()

    def test_scenario_5_insufficient_evidence(self, verification_engine: GapVerificationEngine):
        """Scenario 5: Zero evidence -> UNCERTAIN with low confidence."""
        candidate = ResearchGapCandidateResponse(
            gap_id="gap-syn-no-evidence",
            title="Hypothetical Unsubstantiated Gap",
            description="Pure hypothetical gap without evidence.",
            gap_type="repeated_limitation",
            supporting_papers=[],
            supporting_evidence=[],
            gap_priority_score=0.10,
            confidence=0.40,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        res = verification_engine.verify_candidate_gap(candidate)
        assert res.final_status == GapVerificationFinalStatus.UNCERTAIN
        assert res.verification_confidence <= 0.40
        assert "insufficient" in res.status_reasoning.lower()

    def test_scenario_6_gap_supported_only_by_one_paper(self, verification_engine: GapVerificationEngine):
        """Scenario 6: Solitary paper support -> UNCERTAIN (cannot verify from one paper)."""
        candidate = ResearchGapCandidateResponse(
            gap_id="gap-syn-single-paper",
            title="Solitary Paper Gap Candidate",
            description="Single uncorroborated report.",
            gap_type="repeated_limitation",
            supporting_papers=[{"paper_id": 41, "title": "Solitary Paper 2024", "publication_year": 2024}],
            supporting_evidence=[
                GapEvidenceItem(paper_id=41, source_text="We report an anomalous slowdown under proprietary conditions.", confidence=0.85),
            ],
            gap_priority_score=0.45,
            confidence=0.85,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        res = verification_engine.verify_candidate_gap(candidate)
        assert res.final_status == GapVerificationFinalStatus.UNCERTAIN
        assert "cannot be verified from a solitary publication" in res.status_reasoning.lower()

    def test_scenario_7_gap_with_strong_counter_evidence(self, verification_engine: GapVerificationEngine):
        """Scenario 7: Strong counter-evidence refuting claim -> REFUTED and reduced confidence."""
        candidate = ResearchGapCandidateResponse(
            gap_id="gap-syn-refuted",
            title="Alleged Bottleneck: Transformer Inference Latency",
            description="Transformer attention inference latency cannot be reduced below quadratic bounds.",
            gap_type="repeated_limitation",
            supporting_papers=[
                {"paper_id": 51, "title": "Paper 2021", "publication_year": 2021},
                {"paper_id": 52, "title": "Paper 2022", "publication_year": 2022},
                {"paper_id": 53, "title": "Counter Paper 2024", "publication_year": 2024},
            ],
            supporting_evidence=[
                GapEvidenceItem(paper_id=51, source_text="Inference latency scales quadratically with length.", confidence=0.88),
                GapEvidenceItem(paper_id=52, source_text="Latency constraints remain severe for long sequences.", confidence=0.86),
                # Strong refutation excerpt
                GapEvidenceItem(
                    paper_id=53,
                    source_text="We disprove this assumption: FlashAttention-2 completely resolves the latency overhead without loss.",
                    confidence=0.95,
                ),
            ],
            gap_priority_score=0.75,
            confidence=0.90,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        res = verification_engine.verify_candidate_gap(candidate)
        assert res.final_status == GapVerificationFinalStatus.REFUTED
        assert len(res.counter_evidence) >= 1
        # Confidence must be reduced
        assert res.verification_confidence <= 0.40
        assert "refutes" in res.status_reasoning.lower()


class TestPhase8TemporalAndCounterRetrievalUnit:
    """Unit tests for temporal date aggregation and active counter-evidence queries."""

    def test_temporal_dates_breakdown(self, verification_engine: GapVerificationEngine):
        """Dates are properly partitioned into earliest, latest, supporting, and counter."""
        candidate = ResearchGapCandidateResponse(
            gap_id="gap-dates-test",
            title="Temporal Dates Gap",
            description="Testing temporal date aggregation.",
            gap_type="repeated_limitation",
            supporting_papers=[
                {"paper_id": 1, "title": "P1", "publication_year": 2021},
                {"paper_id": 2, "title": "P2", "publication_year": 2024},
            ],
            supporting_evidence=[
                GapEvidenceItem(paper_id=1, source_text="Limitation observed in 2021.", confidence=0.9),
                GapEvidenceItem(paper_id=2, source_text="Limitation persists in 2024.", confidence=0.9),
            ],
            gap_priority_score=0.70,
            confidence=0.90,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        res = verification_engine.verify_candidate_gap(candidate)
        assert res.evidence_dates.earliest_year == 2021
        assert res.evidence_dates.latest_year == 2024
        assert 2021 in res.evidence_dates.supporting_years
        assert 2024 in res.evidence_dates.supporting_years

    def test_get_counter_evidence_method(self, verification_engine: GapVerificationEngine):
        """get_counter_evidence returns dedicated counter-evidence response."""
        candidate = ResearchGapCandidateResponse(
            gap_id="gap-counter-endpoint-test",
            title="Bottleneck With Solution",
            description="Testing counter endpoint.",
            gap_type="repeated_limitation",
            supporting_papers=[
                {"paper_id": 1, "publication_year": 2022},
                {"paper_id": 2, "publication_year": 2023},
            ],
            supporting_evidence=[
                GapEvidenceItem(paper_id=1, source_text="Limitation observed in 2022.", confidence=0.88),
                GapEvidenceItem(paper_id=2, source_text="We propose an algorithm to solve the bottleneck.", confidence=0.90),
            ],
            gap_priority_score=0.60,
            confidence=0.89,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        resp = verification_engine.get_counter_evidence(candidate)
        assert resp.gap_id == candidate.gap_id
        assert resp.total_counter_items >= 1
        assert resp.strongest_refutation is not None
