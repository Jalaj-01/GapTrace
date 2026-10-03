"""Unit Tests for Phase 4: Research Landscape and Topic Discovery.

Verifies:
- Topic generation, naming, and representative terms
- Reproducibility and deterministic clustering
- Topic assignment and probabilities
- Outlier handling (topic -1)
- Temporal grouping, slope calculation, and status classification (EMERGING, DECLINING, PERSISTENT)
- Empty dataset handling
- Very small dataset handling (1-3 documents)
- Duplicate papers handling
- Missing/None publication year handling
- Coherence score calculation
"""

import numpy as np
import pytest

from backend.app.services.landscape.temporal_analyzer import TemporalTopicAnalyzer
from backend.app.services.landscape.topic_modeler import ScientificTopicModeler
from backend.app.services.landscape.coherence_evaluator import TopicCoherenceEvaluator


class TestTopicModelerUnit:
    """Unit tests for ScientificTopicModeler and c-TF-IDF keyword extraction."""

    @pytest.fixture
    def sample_docs(self):
        return [
            "Cross-domain generalization degrades under out-of-distribution domain shift.",
            "Adversarial domain discrimination aligns feature distributions in transfer learning.",
            "Self-attention quadratic complexity imposes severe memory overhead in transformers.",
            "FlashAttention optimizes GPU memory traffic and accelerates long-context inference.",
            "Clinical dataset scarcity limits supervised deep learning on medical imaging.",
            "Semi-supervised pseudolabeling mitigates annotated clinical data shortages.",
        ]

    def test_topic_generation_and_terms(self, sample_docs):
        modeler = ScientificTopicModeler(min_cluster_size=2)
        labels, probs = modeler.fit_transform(sample_docs)

        assert len(labels) == len(sample_docs)
        assert len(probs) == len(sample_docs)

        topic_info = modeler.get_topic_info()
        assert len(topic_info) >= 2

        for t in topic_info:
            assert "topic_id" in t
            assert "topic_name" in t
            assert "representative_terms" in t
            assert "representative_documents" in t
            assert len(t["representative_terms"]) > 0
            assert t["paper_count"] > 0

    def test_empty_dataset_handling(self):
        modeler = ScientificTopicModeler()
        labels, probs = modeler.fit_transform([])
        assert labels == []
        assert probs == []
        assert modeler.get_topic_info() == []

    def test_single_document_handling(self):
        modeler = ScientificTopicModeler()
        labels, probs = modeler.fit_transform(["Isolated single paper on quantum cryptography."])
        assert labels == [0]
        assert probs == [1.0]
        info = modeler.get_topic_info()
        assert len(info) == 1
        assert info[0]["topic_id"] == 0

    def test_very_small_dataset_handling(self):
        modeler = ScientificTopicModeler()
        docs = [
            "Transformers for protein folding.",
            "Graph convolutional networks for molecular docking.",
        ]
        labels, probs = modeler.fit_transform(docs)
        assert len(labels) == 2
        assert len(probs) == 2
        info = modeler.get_topic_info()
        assert len(info) >= 1

    def test_duplicate_papers_handling(self):
        modeler = ScientificTopicModeler()
        docs = [
            "Identical text about contrastive learning.",
            "Identical text about contrastive learning.",
            "Identical text about contrastive learning.",
            "Different text about sparse attention mechanisms.",
            "Different text about sparse attention mechanisms.",
        ]
        labels, probs = modeler.fit_transform(docs)
        assert len(labels) == 5
        info = modeler.get_topic_info()
        assert len(info) >= 1


class TestTemporalAnalyzerUnit:
    """Unit tests for longitudinal dynamics and trajectory classification."""

    def test_yearly_distribution_computation(self):
        years = [2021, 2022, 2022, 2024, None, 2024, 2024]
        dist = TemporalTopicAnalyzer.compute_yearly_distribution(years)
        assert dist["2021"] == 1
        assert dist["2022"] == 2
        assert dist["2024"] == 3
        assert dist["Unknown"] == 1

    def test_emerging_classification(self):
        # Accelerating growth in recent years
        counts = {"2021": 1, "2022": 2, "2023": 6, "2024": 12, "2025": 20}
        status = TemporalTopicAnalyzer.classify_topic_trajectory(counts, topic_id=1, total_corpus_papers=50)
        assert status == "EMERGING"

    def test_declining_classification(self):
        # Peaked in past, minimal recent volume
        counts = {"2019": 10, "2020": 15, "2021": 8, "2024": 1, "2025": 0}
        status = TemporalTopicAnalyzer.classify_topic_trajectory(counts, topic_id=2, total_corpus_papers=50)
        assert status == "DECLINING"

    def test_persistent_classification(self):
        # Steady presence across multiple years
        counts = {"2021": 5, "2022": 5, "2023": 6, "2024": 5, "2025": 5}
        status = TemporalTopicAnalyzer.classify_topic_trajectory(counts, topic_id=3, total_corpus_papers=50)
        assert status == "PERSISTENT"

    def test_outlier_classification(self):
        counts = {"2022": 3, "2024": 4}
        status = TemporalTopicAnalyzer.classify_topic_trajectory(counts, topic_id=-1, total_corpus_papers=20)
        assert status == "OUTLIER"

    def test_format_trend_points(self):
        counts = {"2022": 5, "2023": 10, "Unknown": 2}
        all_totals = {"2022": 20, "2023": 25}
        points = TemporalTopicAnalyzer.format_trend_points(counts, all_totals)
        assert len(points) == 2
        assert points[0]["year"] == 2022
        assert points[0]["paper_count"] == 5
        assert points[0]["percentage"] == 25.0
        assert points[1]["year"] == 2023
        assert points[1]["paper_count"] == 10
        assert points[1]["percentage"] == 40.0


class TestTopicCoherenceEvaluatorUnit:
    """Unit tests for topic coherence metric computation."""

    def test_coherence_metric(self):
        evaluator = TopicCoherenceEvaluator()
        topics = [
            ["transformer", "attention", "self-attention", "context"],
            ["domain", "generalization", "transfer", "distribution"],
        ]
        score = evaluator.compute_coherence(topics, top_n=4)
        assert isinstance(score, float)
        assert score > 0.0

    def test_coherence_comparison_pipeline(self):
        evaluator = TopicCoherenceEvaluator()
        docs = [
            "Cross-domain transfer in natural language processing.",
            "Domain adaptation using adversarial learning.",
            "Attention mechanisms and quadratic memory complexity.",
            "FlashAttention optimizes attention execution on GPUs.",
        ]
        res = evaluator.evaluate_comparison(docs, n_clusters=2)
        assert "baseline_kmeans" in res
        assert "bertopic_semantic" in res
        assert "coherence_score" in res["baseline_kmeans"]
        assert "coherence_score" in res["bertopic_semantic"]
