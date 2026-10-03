"""Phase 6 Unit Test Suite: Research Gap Candidate Engine & Signal Detectors.

Covers:
- All 7 measurable signals:
  * Underexploration
  * Repeated Limitations
  * Methodological Concentration
  * Dataset Concentration
  * Temporal Opportunity
  * Cross-Domain Opportunity
  * Conflicting Evidence
- Explainable Prioritization Scoring (S_priority) and mathematical weights
- Insufficient evidence candidate rejection
- Candidate deduplication and reproducibility
- Expert-labeled benchmark evaluation (Precision@5, Recall@10, MRR)
"""

import pytest
from backend.app.models.paper import GapEvidenceItem, ResearchGapCandidateResponse
from backend.app.services.gaps.benchmark_evaluator import (
    GROUND_TRUTH_GAP_BENCHMARK,
    GapBenchmarkEvaluator,
)
from backend.app.services.gaps.candidate_generator import (
    ResearchGapCandidateGenerator,
)
from backend.app.services.gaps.priority_scorer import (
    SIGNAL_WEIGHTS,
    GapPriorityScorer,
)
from backend.app.services.gaps.signals import (
    GapSignalDetectors,
    SignalType,
)
from backend.app.services.graph.graph_provenance import GraphProvenanceService
from backend.app.services.graph.node_builder import NodeTypes
from backend.app.services.graph.relationship_builder import RelationTypes
from backend.app.services.graph.research_graph import ResearchKnowledgeGraph


class TestPhase6SignalsUnit:
    """Unit tests for the 7 empirical research gap signal detectors."""

    def test_signal_1_underexploration_activation(self):
        """Signal 1 activates when a topic has low paper volume relative to corpus mean."""
        # Active case: 1 paper when mean is 5.0
        res_active = GapSignalDetectors.detect_underexploration(topic_paper_count=1, mean_topic_papers=5.0)
        assert res_active.is_active is True
        assert res_active.raw_value > 0.50
        assert "underexplored" in res_active.explanation.lower()

        # Inactive case: 6 papers when mean is 4.0
        res_inactive = GapSignalDetectors.detect_underexploration(topic_paper_count=6, mean_topic_papers=4.0)
        assert res_inactive.is_active is False
        assert res_inactive.raw_value == 0.0

    def test_signal_2_repeated_limitations_activation(self):
        """Signal 2 activates when a limitation appears independently across >= 2 papers."""
        # Active case: 3 distinct papers cite the same bottleneck
        res_active = GapSignalDetectors.detect_repeated_limitations(
            distinct_paper_ids={101, 102, 103},
            limitation_count=4,
        )
        assert res_active.is_active is True
        assert res_active.raw_value >= 0.70
        assert "3 distinct publications" in res_active.explanation

        # Inactive case: only 1 paper
        res_inactive = GapSignalDetectors.detect_repeated_limitations(
            distinct_paper_ids={101},
            limitation_count=1,
        )
        assert res_inactive.is_active is False
        assert res_inactive.raw_value == 0.0

    def test_signal_3_methodological_concentration_activation(self):
        """Signal 3 activates when algorithmic concentration (HHI) >= 0.50."""
        # Active case: 80% BERT usage (Monoculture)
        res_active = GapSignalDetectors.detect_methodological_concentration({"BERT": 8, "Transformer": 1, "LSTM": 1})
        assert res_active.is_active is True
        assert res_active.metadata["hhi"] >= 0.60
        assert "BERT" in res_active.explanation

        # Inactive case: diverse methods
        res_inactive = GapSignalDetectors.detect_methodological_concentration(
            {"BERT": 2, "RoBERTa": 2, "Transformer": 2, "Mamba": 2}
        )
        assert res_inactive.is_active is False
        assert res_inactive.raw_value == 0.0

    def test_signal_4_dataset_concentration_activation(self):
        """Signal 4 activates when evaluations heavily rely on a single benchmark."""
        # Active case: SQuAD represents 85% of evaluations
        res_active = GapSignalDetectors.detect_dataset_concentration({"SQuAD": 17, "GLUE": 2, "MultiNLI": 1})
        assert res_active.is_active is True
        assert res_active.metadata["hhi"] >= 0.70
        assert "SQuAD" in res_active.explanation

        # Inactive case: balanced datasets
        res_inactive = GapSignalDetectors.detect_dataset_concentration({"SQuAD": 3, "GLUE": 3, "PubMed": 3})
        assert res_inactive.is_active is False
        assert res_inactive.raw_value == 0.0

    def test_signal_5_temporal_opportunity_activation(self):
        """Signal 5 activates when an unaddressed limitation spans multiple years."""
        # Active case: limitation documented in 2022, still cited in 2025 without resolution
        res_active = GapSignalDetectors.detect_temporal_opportunity(
            earliest_year=2022,
            latest_year=2025,
            is_addressed=False,
        )
        assert res_active.is_active is True
        assert res_active.raw_value >= 0.70
        assert res_active.metadata["span_years"] == 3

        # Inactive case: limitation has been resolved / addressed
        res_inactive = GapSignalDetectors.detect_temporal_opportunity(
            earliest_year=2022,
            latest_year=2025,
            is_addressed=True,
        )
        assert res_inactive.is_active is False
        assert res_inactive.raw_value == 0.0

    def test_signal_6_cross_domain_opportunity_activation(self):
        """Signal 6 activates when high performance is confined to a single domain."""
        res_active = GapSignalDetectors.detect_cross_domain_opportunity(
            domain_counts={"NaturalLanguage": 10},
            is_high_performing=True,
        )
        assert res_active.is_active is True
        assert res_active.raw_value >= 0.80

        res_inactive = GapSignalDetectors.detect_cross_domain_opportunity(
            domain_counts={"NaturalLanguage": 5, "Biomedical": 4, "ComputerVision": 3},
            is_high_performing=True,
        )
        assert res_inactive.is_active is False

    def test_signal_7_conflicting_evidence_activation(self):
        """Signal 7 activates when contradictory findings or claims are detected."""
        res_active = GapSignalDetectors.detect_conflicting_evidence(
            conflict_count=2,
            conflicting_paper_ids={1, 2},
        )
        assert res_active.is_active is True
        assert res_active.raw_value >= 0.75

        res_inactive = GapSignalDetectors.detect_conflicting_evidence(
            conflict_count=0,
            conflicting_paper_ids=set(),
        )
        assert res_inactive.is_active is False


class TestPhase6PriorityScorerUnit:
    """Unit tests for the explainable prioritization scoring formula."""

    def test_weights_sum_to_one(self):
        """Verify the canonical weights sum to exactly 1.00."""
        total_weight = sum(SIGNAL_WEIGHTS.values())
        assert round(total_weight, 4) == 1.00

    def test_score_reproducibility_and_bounds(self):
        """Verify priority scores are deterministic and strictly bounded within [0.0, 1.0]."""
        signals = {
            SignalType.REPEATED_LIMITATIONS: GapSignalDetectors.detect_repeated_limitations({1, 2}, 2),
            SignalType.UNDEREXPLORATION: GapSignalDetectors.detect_underexploration(1, 4.0),
        }

        score1, breakdown1, exp1 = GapPriorityScorer.calculate_priority(signals)
        score2, breakdown2, exp2 = GapPriorityScorer.calculate_priority(signals)

        assert score1 == score2
        assert 0.0 <= score1 <= 1.0
        assert len(breakdown1) == len(SIGNAL_WEIGHTS)
        assert exp1 == exp2
        assert "repeated_limitations" in exp1

    def test_all_signals_active_score_near_one(self):
        """When all signals are fully active at 1.0, priority score reaches 1.0."""
        active_signals = {
            sig_type: GapSignalDetectors.detect_repeated_limitations({1, 2, 3, 4, 5}, 10)
            for sig_type in SIGNAL_WEIGHTS.keys()
        }
        score, _, _ = GapPriorityScorer.calculate_priority(active_signals)
        assert score >= 0.90


class TestPhase6CandidateValidationUnit:
    """Unit tests for evidence requirements and candidate generation integrity."""

    def test_insufficient_evidence_rejection(self):
        """Generator must strictly reject candidate gaps lacking supporting papers or evidence."""
        rkg = ResearchKnowledgeGraph()
        gen = ResearchGapCandidateGenerator(rkg=rkg)

        # Empty graph should yield 0 candidates (no phantom or hallucinated gaps)
        candidates = gen.generate_candidates()
        assert len(candidates) == 0

    def test_status_marked_as_potential_gap(self):
        """Every generated candidate must explicitly declare status as 'potential_gap'."""
        rkg = ResearchKnowledgeGraph()

        # Add two papers with identical limitation
        for p_id, yr in [(1, 2023), (2, 2024)]:
            p_node = {
                "id": f"paper:{p_id}",
                "label": f"Paper {p_id}",
                "type": NodeTypes.PAPER,
                "properties": {"paper_id": p_id, "title": f"Paper {p_id}", "publication_year": yr},
                "provenance": GraphProvenanceService.create_provenance(paper_id=p_id, paper_title=f"Paper {p_id}"),
            }
            l_node = {
                "id": f"limitation:{p_id}:1",
                "label": "High computational memory overhead in long context lengths",
                "type": NodeTypes.LIMITATION,
                "properties": {"limitation_id": 1, "text": "High computational memory overhead in long context lengths", "paper_id": p_id},
                "provenance": GraphProvenanceService.create_provenance(
                    paper_id=p_id,
                    paper_title=f"Paper {p_id}",
                    source_text="High computational memory overhead in long context lengths prevents scaling.",
                    confidence=0.92,
                ),
            }
            rkg.add_node(p_node)
            rkg.add_node(l_node)
            rkg.add_edge({
                "source": f"paper:{p_id}",
                "target": f"limitation:{p_id}:1",
                "relationship": RelationTypes.LIMITED_BY,
                "confidence": 0.92,
                "provenance": l_node["provenance"],
            })

        gen = ResearchGapCandidateGenerator(rkg=rkg)
        candidates = gen.generate_candidates()

        assert len(candidates) >= 1
        cand = candidates[0]
        assert cand.verification_status == "potential_gap"
        assert len(cand.supporting_papers) == 2
        assert len(cand.supporting_evidence) >= 2
        assert cand.gap_priority_score > 0.0

    def test_benchmark_evaluation_precision_recall(self):
        """Evaluate synthetic generated candidates against expert ground truth benchmark."""
        synthetic_candidates = [
            ResearchGapCandidateResponse(
                gap_id="cand-1",
                title="Empirical Bottleneck: Computational Memory Overhead",
                description="Quadratic self-attention scaling prevents scaling beyond 16k context lengths.",
                gap_type="repeated_limitation",
                verification_status="potential_gap",
                supporting_papers=[{"paper_id": 1, "title": "Attention Paper"}],
                supporting_evidence=[GapEvidenceItem(source_text="Quadratic attention overhead")],
                signals={"repeated_limitations": 0.8},
                gap_priority_score=0.85,
                confidence=0.90,
                created_at="2026-10-01T00:00:00Z",
            ),
            ResearchGapCandidateResponse(
                gap_id="cand-2",
                title="Cross-Domain Generalization Degradation in Low-Resource Scientific NLP",
                description="Severe domain shift and performance drop when transferring models to biomedical abstracts.",
                gap_type="repeated_limitation",
                verification_status="potential_gap",
                supporting_papers=[{"paper_id": 2, "title": "Transfer Paper"}],
                supporting_evidence=[GapEvidenceItem(source_text="Cross-domain degradation")],
                signals={"repeated_limitations": 0.85, "cross_domain_opportunity": 0.80},
                gap_priority_score=0.82,
                confidence=0.92,
                created_at="2026-10-01T00:00:00Z",
            ),
            ResearchGapCandidateResponse(
                gap_id="cand-3",
                title="Annotated Dataset Scarcity in Multimodal Clinical Evidence Extraction",
                description="Severe scarcity of labeled biomedical datasets with multimodal imaging reports.",
                gap_type="underexplored_area",
                verification_status="potential_gap",
                supporting_papers=[{"paper_id": 3, "title": "Clinical Paper"}],
                supporting_evidence=[GapEvidenceItem(source_text="Dataset scarcity in clinical imaging")],
                signals={"underexploration": 0.80},
                gap_priority_score=0.78,
                confidence=0.89,
                created_at="2026-10-01T00:00:00Z",
            ),
        ]

        metrics = GapBenchmarkEvaluator.evaluate(synthetic_candidates)
        assert metrics["total_ground_truth"] == 5
        assert metrics["metrics"]["precision_at_5"] >= 0.60
        assert metrics["metrics"]["recall_at_10"] >= 0.50
        assert metrics["metrics"]["mean_reciprocal_rank"] > 0.0
