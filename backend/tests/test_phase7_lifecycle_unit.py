"""Unit Tests for Phase 7: Gap Genealogy and Gap Lifecycle Engine.

Validates:
- All 6 lifecycle states: EMERGING, PERSISTENT, PARTIALLY_ADDRESSED, ADDRESSED, REOPENED, UNCERTAIN.
- Strict multi-paper evidence requirement (never infer lifecycle from 1 paper or 1 unsupported sentence).
- Timeline chronological ordering and retrospective citation handling.
- Evolutionary genealogy chain consistency and provenance.
- Missing publication year handling and duplicate event deduplication.
"""

import pytest
from datetime import datetime, timezone

from backend.app.models.paper import (
    GapEvidenceItem,
    GapLifecycleStatus,
    ResearchGapCandidateResponse,
    TimelineEventItem,
)
from backend.app.services.gaps.lifecycle_service import (
    GapLifecycleTracker,
    get_gap_lifecycle_tracker,
)
from backend.app.services.graph.research_graph import ResearchKnowledgeGraph
from backend.app.services.graph.node_builder import NodeTypes
from backend.app.services.graph.relationship_builder import RelationTypes


@pytest.fixture
def lifecycle_tracker() -> GapLifecycleTracker:
    rkg = ResearchKnowledgeGraph()
    return GapLifecycleTracker(rkg=rkg)


class TestPhase7LifecycleStateUnit:
    """Tests for all 6 lifecycle states with synthetic chronological fixtures."""

    def test_emerging_gap_lifecycle(self, lifecycle_tracker: GapLifecycleTracker):
        """Emerging gap: first identified recently (2024-2025), >= 2 papers, no solutions proposed."""
        candidate = ResearchGapCandidateResponse(
            gap_id="gap-synthetic-emerging",
            title="Emergent Bottleneck: Multimodal Reasoning Hallucination",
            description="Recent multimodal models suffer from grounding hallucinations on spatial reasoning.",
            gap_type="repeated_limitation",
            supporting_papers=[
                {"paper_id": 101, "title": "Multimodal Spatial Reasoning 2024", "publication_year": 2024},
                {"paper_id": 102, "title": "Vision-Language Grounding 2025", "publication_year": 2025},
            ],
            supporting_evidence=[
                GapEvidenceItem(
                    paper_id=101,
                    paper_title="Multimodal Spatial Reasoning 2024",
                    source_text="Vision-language models consistently hallucinate spatial relations between small objects.",
                    confidence=0.92,
                ),
                GapEvidenceItem(
                    paper_id=102,
                    paper_title="Vision-Language Grounding 2025",
                    source_text="Spatial relation grounding remains an open bottleneck across all evaluated architectures.",
                    confidence=0.90,
                ),
            ],
            gap_priority_score=0.75,
            confidence=0.91,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        detail = lifecycle_tracker.analyze_lifecycle(candidate)
        assert detail.status == GapLifecycleStatus.EMERGING
        assert detail.evidence_paper_count == 2
        assert detail.has_attempted_solutions is False
        assert detail.is_addressed is False
        assert "recently" in detail.status_reasoning.lower()

    def test_persistent_gap_lifecycle(self, lifecycle_tracker: GapLifecycleTracker):
        """Persistent gap: spans >= 2 years across multiple papers without effective solutions."""
        candidate = ResearchGapCandidateResponse(
            gap_id="gap-synthetic-persistent",
            title="Empirical Bottleneck: Computational Memory Overhead",
            description="Quadratic self-attention scaling prevents scaling beyond 16k context lengths.",
            gap_type="repeated_limitation",
            supporting_papers=[
                {"paper_id": 1, "title": "Scaling Transformer Sequences 2021", "publication_year": 2021},
                {"paper_id": 2, "title": "Long-Context Attention 2023", "publication_year": 2023},
                {"paper_id": 3, "title": "Memory-Efficient Architectures 2025", "publication_year": 2025},
            ],
            supporting_evidence=[
                GapEvidenceItem(
                    paper_id=1,
                    paper_title="Scaling Transformer Sequences 2021",
                    source_text="Quadratic memory complexity during self-attention prevents scaling.",
                    confidence=0.95,
                ),
                GapEvidenceItem(
                    paper_id=2,
                    paper_title="Long-Context Attention 2023",
                    source_text="Peak GPU VRAM allocation remains quadratic with sequence length.",
                    confidence=0.92,
                ),
                GapEvidenceItem(
                    paper_id=3,
                    paper_title="Memory-Efficient Architectures 2025",
                    source_text="Attention memory bottleneck continues to constrain sequence lengths beyond 32k.",
                    confidence=0.90,
                ),
            ],
            gap_priority_score=0.85,
            confidence=0.92,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        detail = lifecycle_tracker.analyze_lifecycle(candidate)
        assert detail.status == GapLifecycleStatus.PERSISTENT
        assert detail.year_span >= 4
        assert detail.evidence_paper_count == 3
        assert detail.has_attempted_solutions is False
        assert "persistently" in detail.status_reasoning.lower()

    def test_partially_addressed_gap_lifecycle(self, lifecycle_tracker: GapLifecycleTracker):
        """Partially addressed gap: attempted solution exists, but residual limitations remain."""
        candidate = ResearchGapCandidateResponse(
            gap_id="gap-synthetic-partially-addressed",
            title="Empirical Bottleneck: Cross-Domain Degradation",
            description="Models degrade on out-of-distribution scientific abstracts.",
            gap_type="repeated_limitation",
            supporting_papers=[
                {"paper_id": 201, "title": "Cross-Domain NLP 2022", "publication_year": 2022},
                {"paper_id": 202, "title": "Adversarial Adaptation 2023", "publication_year": 2023},
                {"paper_id": 203, "title": "Benchmark Evaluation 2023", "publication_year": 2023},
            ],
            supporting_evidence=[
                GapEvidenceItem(
                    paper_id=201,
                    paper_title="Cross-Domain NLP 2022",
                    source_text="Supervised models suffer severe performance degradation on out-of-domain biomedical abstracts.",
                    confidence=0.92,
                ),
                GapEvidenceItem(
                    paper_id=202,
                    paper_title="Adversarial Adaptation 2023",
                    source_text="We propose domain-adversarial training to mitigate distribution shift and address transfer loss.",
                    confidence=0.85,
                ),
                GapEvidenceItem(
                    paper_id=203,
                    paper_title="Benchmark Evaluation 2023",
                    source_text="While adversarial training partially mitigates shift, remaining limitations persist in clinical subdomains.",
                    confidence=0.88,
                ),
            ],
            gap_priority_score=0.65,
            confidence=0.88,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        detail = lifecycle_tracker.analyze_lifecycle(candidate)
        assert detail.status == GapLifecycleStatus.PARTIALLY_ADDRESSED
        assert detail.has_attempted_solutions is True
        assert detail.is_addressed is False
        assert "mitigate" in detail.status_reasoning.lower()

    def test_addressed_gap_lifecycle(self, lifecycle_tracker: GapLifecycleTracker):
        """Addressed gap: high-confidence solution directly addresses limitation with no newer recurrences."""
        candidate = ResearchGapCandidateResponse(
            gap_id="gap-synthetic-addressed",
            title="Empirical Bottleneck: Positional Encoding Out-of-Bounds",
            description="Sinusoidal position encodings fail to extrapolate to longer lengths.",
            gap_type="repeated_limitation",
            supporting_papers=[
                {"paper_id": 301, "title": "Positional Extrapolation 2021", "publication_year": 2021},
                {"paper_id": 302, "title": "RoPE: Rotary Position Embedding 2022", "publication_year": 2022},
            ],
            supporting_evidence=[
                GapEvidenceItem(
                    paper_id=301,
                    paper_title="Positional Extrapolation 2021",
                    source_text="Sinusoidal encodings fail completely when evaluating sequences beyond trained length.",
                    confidence=0.90,
                ),
                GapEvidenceItem(
                    paper_id=302,
                    paper_title="RoPE: Rotary Position Embedding 2022",
                    source_text="We propose rotary position embeddings to solve the extrapolation bottleneck and overcome length limits.",
                    confidence=0.95,
                ),
            ],
            gap_priority_score=0.45,
            confidence=0.93,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        detail = lifecycle_tracker.analyze_lifecycle(candidate)
        assert detail.status == GapLifecycleStatus.ADDRESSED
        assert detail.is_addressed is True
        assert detail.is_reopened is False
        assert detail.has_attempted_solutions is True

    def test_reopened_gap_lifecycle(self, lifecycle_tracker: GapLifecycleTracker):
        """Reopened gap: limitation seemed addressed in earlier year, but later paper shows recurrence."""
        candidate = ResearchGapCandidateResponse(
            gap_id="gap-synthetic-reopened",
            title="Empirical Bottleneck: Catastrophic Forgetting in Continual Learning",
            description="Models forget previously acquired task representations during sequential adaptation.",
            gap_type="repeated_limitation",
            supporting_papers=[
                {"paper_id": 401, "title": "Continual Learning Limits 2020", "publication_year": 2020},
                {"paper_id": 402, "title": "Elastic Weight Consolidation 2021", "publication_year": 2021},
                {"paper_id": 403, "title": "Long-Term Adaptation Benchmark 2024", "publication_year": 2024},
            ],
            supporting_evidence=[
                GapEvidenceItem(
                    paper_id=401,
                    paper_title="Continual Learning Limits 2020",
                    source_text="Severe catastrophic forgetting occurs when updating deep representations sequentially.",
                    confidence=0.91,
                ),
                GapEvidenceItem(
                    paper_id=402,
                    paper_title="Elastic Weight Consolidation 2021",
                    source_text="We propose elastic weight consolidation to solve forgetting and overcome parameter drift.",
                    confidence=0.88,
                ),
                GapEvidenceItem(
                    paper_id=403,
                    paper_title="Long-Term Adaptation Benchmark 2024",
                    source_text="In practice, catastrophic forgetting re-emerges and persists when task sequences exceed 20 tasks.",
                    confidence=0.94,
                ),
            ],
            gap_priority_score=0.80,
            confidence=0.91,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        detail = lifecycle_tracker.analyze_lifecycle(candidate)
        assert detail.status == GapLifecycleStatus.REOPENED
        assert detail.is_reopened is True
        assert detail.has_attempted_solutions is True
        assert detail.is_addressed is False
        assert "re-emerged" in detail.status_reasoning.lower() or "continues" in detail.status_reasoning.lower()


class TestPhase7EvidenceRequirementsUnit:
    """Tests enforcing the strict multi-paper evidence invariant."""

    def test_single_paper_cannot_determine_lifecycle(self, lifecycle_tracker: GapLifecycleTracker):
        """CRITICAL: A single paper cannot determine lifecycle -> Must yield UNCERTAIN."""
        candidate = ResearchGapCandidateResponse(
            gap_id="gap-single-paper-candidate",
            title="Uncorroborated Assertion: Single Paper Bottleneck",
            description="A solitary paper claims a severe limitation.",
            gap_type="repeated_limitation",
            supporting_papers=[
                {"paper_id": 999, "title": "Solitary Paper 2024", "publication_year": 2024},
            ],
            supporting_evidence=[
                GapEvidenceItem(
                    paper_id=999,
                    paper_title="Solitary Paper 2024",
                    source_text="We observe an unexplained degradation on this proprietary benchmark.",
                    confidence=0.95,
                ),
            ],
            gap_priority_score=0.40,
            confidence=0.95,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        detail = lifecycle_tracker.analyze_lifecycle(candidate)
        assert detail.status == GapLifecycleStatus.UNCERTAIN
        assert "insufficient multi-paper temporal evidence" in detail.status_reasoning.lower()

    def test_single_unsupported_sentence_cannot_determine_lifecycle(self, lifecycle_tracker: GapLifecycleTracker):
        """CRITICAL: A single unsupported sentence without paper grounding yields UNCERTAIN."""
        candidate = ResearchGapCandidateResponse(
            gap_id="gap-unsupported-sentence",
            title="Unsupported Gap Candidate",
            description="Hypothetical bottleneck without publication consensus.",
            gap_type="repeated_limitation",
            supporting_papers=[],
            supporting_evidence=[
                GapEvidenceItem(
                    paper_id=None,
                    paper_title=None,
                    source_text="Single unsupported sentence without paper ID.",
                    confidence=0.70,
                )
            ],
            gap_priority_score=0.20,
            confidence=0.70,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        detail = lifecycle_tracker.analyze_lifecycle(candidate)
        assert detail.status == GapLifecycleStatus.UNCERTAIN
        assert detail.evidence_paper_count == 0

    def test_missing_publication_year_graceful_handling(self, lifecycle_tracker: GapLifecycleTracker):
        """Events lacking publication_year are assigned median year with year_estimated flag."""
        candidate = ResearchGapCandidateResponse(
            gap_id="gap-missing-years",
            title="Missing Years Candidate",
            description="Candidate with some missing metadata years.",
            gap_type="repeated_limitation",
            supporting_papers=[
                {"paper_id": 501, "title": "Paper Without Year", "publication_year": None},
                {"paper_id": 502, "title": "Paper With Year 2024", "publication_year": 2024},
            ],
            supporting_evidence=[
                GapEvidenceItem(
                    paper_id=501,
                    paper_title="Paper Without Year",
                    source_text="Limitation observed in unversioned preprint.",
                    confidence=0.85,
                ),
                GapEvidenceItem(
                    paper_id=502,
                    paper_title="Paper With Year 2024",
                    source_text="Limitation corroborated in published proceedings.",
                    confidence=0.90,
                ),
            ],
            gap_priority_score=0.60,
            confidence=0.88,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        timeline = lifecycle_tracker.build_timeline(candidate)
        assert timeline.total_events >= 2
        for ev in timeline.events:
            assert ev.year is not None

    def test_duplicate_events_deduplication(self, lifecycle_tracker: GapLifecycleTracker):
        """Duplicate evidence items from the same paper and sentence are deduplicated in timeline."""
        candidate = ResearchGapCandidateResponse(
            gap_id="gap-duplicates",
            title="Candidate With Duplicate Citations",
            description="Testing deduplication of repeated sentences.",
            gap_type="repeated_limitation",
            supporting_papers=[
                {"paper_id": 601, "title": "Duplicate Author Paper", "publication_year": 2023},
                {"paper_id": 602, "title": "Second Paper", "publication_year": 2024},
            ],
            supporting_evidence=[
                GapEvidenceItem(
                    paper_id=601,
                    paper_title="Duplicate Author Paper",
                    source_text="Quadratic attention scaling causes severe memory bottlenecks.",
                    confidence=0.92,
                ),
                # Exact identical duplicate
                GapEvidenceItem(
                    paper_id=601,
                    paper_title="Duplicate Author Paper",
                    source_text="Quadratic attention scaling causes severe memory bottlenecks.",
                    confidence=0.92,
                ),
                GapEvidenceItem(
                    paper_id=602,
                    paper_title="Second Paper",
                    source_text="Memory bottlenecks remain a hurdle for long contexts.",
                    confidence=0.88,
                ),
            ],
            gap_priority_score=0.65,
            confidence=0.90,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        timeline = lifecycle_tracker.build_timeline(candidate)
        # 2 distinct evidence events + 1 anchor candidate event = 3 total events
        assert timeline.total_events == 3


class TestPhase7TimelineAndGenealogyUnit:
    """Tests verifying timeline chronology, genealogy structure, and provenance."""

    def test_timeline_chronological_ordering(self, lifecycle_tracker: GapLifecycleTracker):
        """Timeline events must be strictly sorted by year in ascending order."""
        candidate = ResearchGapCandidateResponse(
            gap_id="gap-timeline-order",
            title="Chronology Test Candidate",
            description="Verifying chronological ordering.",
            gap_type="repeated_limitation",
            supporting_papers=[
                {"paper_id": 1, "title": "Paper 2025", "publication_year": 2025},
                {"paper_id": 2, "title": "Paper 2021", "publication_year": 2021},
                {"paper_id": 3, "title": "Paper 2023", "publication_year": 2023},
            ],
            supporting_evidence=[
                GapEvidenceItem(paper_id=1, source_text="Limitation observed in 2025.", confidence=0.9),
                GapEvidenceItem(paper_id=2, source_text="Limitation first reported in 2021.", confidence=0.9),
                GapEvidenceItem(paper_id=3, source_text="Limitation persists in 2023.", confidence=0.9),
            ],
            gap_priority_score=0.70,
            confidence=0.90,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        timeline = lifecycle_tracker.build_timeline(candidate)
        years = [ev.year for ev in timeline.events]
        assert years == sorted(years)

    def test_genealogy_chain_consistency(self, lifecycle_tracker: GapLifecycleTracker):
        """Genealogy reconstruction must form a multi-step chain with provenance and valid transitions."""
        candidate = ResearchGapCandidateResponse(
            gap_id="gap-genealogy-chain",
            title="Empirical Bottleneck: Computational Memory Overhead",
            description="Quadratic self-attention scaling prevents scaling beyond 16k context lengths.",
            gap_type="repeated_limitation",
            supporting_papers=[
                {"paper_id": 1, "title": "Paper A", "publication_year": 2021},
                {"paper_id": 2, "title": "Paper B", "publication_year": 2023},
            ],
            supporting_evidence=[
                GapEvidenceItem(paper_id=1, source_text="Quadratic complexity in self-attention.", confidence=0.95),
                GapEvidenceItem(paper_id=2, source_text="Memory overhead persists across benchmarks.", confidence=0.90),
            ],
            gap_priority_score=0.80,
            confidence=0.92,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        genealogy = lifecycle_tracker.build_genealogy(candidate)
        assert genealogy.total_transitions >= 4
        assert len(genealogy.evolutionary_chain) == genealogy.total_transitions
        assert "computational memory overhead" in genealogy.root_limitation.lower()

        # Verify transition step numbers and source provenance
        for idx, trans in enumerate(genealogy.transitions, 1):
            assert trans.step_number == idx
            assert trans.stage_name != ""
            assert trans.source_sentence != ""
            assert trans.confidence >= 0.50
            assert trans.year is not None

    def test_lifecycle_overview_aggregation(self, lifecycle_tracker: GapLifecycleTracker):
        """Overview computes accurate distribution across a mixed cohort of candidates."""
        candidates = [
            ResearchGapCandidateResponse(
                gap_id="cand-persistent",
                title="Bottleneck A",
                description="Long standing limitation.",
                gap_type="repeated_limitation",
                supporting_papers=[
                    {"paper_id": 1, "title": "P1", "publication_year": 2021},
                    {"paper_id": 2, "title": "P2", "publication_year": 2024},
                ],
                supporting_evidence=[
                    GapEvidenceItem(paper_id=1, source_text="Persistent limitation in 2021."),
                    GapEvidenceItem(paper_id=2, source_text="Still unresolved in 2024."),
                ],
                gap_priority_score=0.8,
                confidence=0.9,
                created_at=datetime.now(timezone.utc).isoformat(),
            ),
            ResearchGapCandidateResponse(
                gap_id="cand-single-paper",
                title="Bottleneck B",
                description="Single paper claim.",
                gap_type="repeated_limitation",
                supporting_papers=[{"paper_id": 3, "title": "P3", "publication_year": 2024}],
                supporting_evidence=[GapEvidenceItem(paper_id=3, source_text="Single mention.")],
                gap_priority_score=0.3,
                confidence=0.8,
                created_at=datetime.now(timezone.utc).isoformat(),
            ),
        ]

        overview = lifecycle_tracker.get_lifecycle_overview(candidates)
        assert overview.total_gaps == 2
        assert overview.status_counts[GapLifecycleStatus.PERSISTENT.value] == 1
        assert overview.status_counts[GapLifecycleStatus.UNCERTAIN.value] == 1
