"""Unit & Integration Tests for Phase 11: Final Experimental Evaluation.

Validates that:
- Benchmark dataset data/evaluation/phase11_benchmark_dataset.json satisfies all metadata invariants
- Experiment 1 (Retrieval Comparison) generates valid CSV, JSON, and plot artifacts
- Experiment 2 (Topic Comparison) generates valid CSV, JSON, and plot artifacts
- Experiment 3 (Limitation Detection Comparison) produces valid classifications and bootstrap metrics
- Experiment 4 (Gap Detection Approaches) ranks candidates and computes rank correlations
- Experiment 5 (Counter-Evidence Verification) verifies gap candidates and reduces false positives
- Experiment 6 (Gap Lifecycle Framework) classifies all 6 canonical lifecycle states
- Master runner runs smoothly and all expected artifacts exist
"""

import json
from pathlib import Path
import pytest

from experiments.retrieval_comparison import run_retrieval_comparison
from experiments.topic_comparison import run_topic_comparison
from experiments.limitation_detection_comparison import run_limitation_detection_comparison
from experiments.gap_detection_comparison import run_gap_detection_comparison
from experiments.counter_evidence_evaluation import run_counter_evidence_evaluation
from experiments.lifecycle_evaluation import run_lifecycle_evaluation


BENCHMARK_PATH = Path("data/evaluation/phase11_benchmark_dataset.json")
RESULTS_DIR = Path("experiments/results")
PLOTS_DIR = RESULTS_DIR / "plots"


class TestPhase11BenchmarkDataset:
    """Verifies the integrity and scientific standards of the evaluation benchmark."""

    def test_benchmark_dataset_structure(self):
        assert BENCHMARK_PATH.exists(), f"Benchmark file missing at {BENCHMARK_PATH}"
        with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        meta = data.get("metadata", {})
        assert meta["total_papers"] == 10
        assert meta["total_sentences"] == 150
        assert meta["total_labelled_limitations"] == 20
        assert meta["total_labelled_gaps"] == 6
        assert meta["total_labelled_relationships"] == 36
        assert meta["total_retrieval_queries"] == 10
        assert meta["total_nli_pairs"] == 15
        assert meta["total_lifecycle_scenarios"] == 12

        assert len(data["papers"]) == 10
        assert len(data["sentences"]) == 150
        assert len(data["relationships"]) == 36
        assert len(data["retrieval_benchmark"]) == 10
        assert len(data["gaps_benchmark"]) == 6
        assert len(data["counter_evidence_benchmark"]) == 15
        assert len(data["lifecycle_benchmark"]) == 12


class TestPhase11ExperimentExecution:
    """Tests execution of individual evaluation modules and artifact generation."""

    def test_experiment_1_retrieval(self):
        res = run_retrieval_comparison(benchmark_path=BENCHMARK_PATH)
        assert "metrics" in res
        assert "tfidf_baseline" in res["metrics"]
        assert "sentence_transformer" in res["metrics"]
        assert res["metrics"]["sentence_transformer"]["mrr_mean"] >= res["metrics"]["tfidf_baseline"]["mrr_mean"]
        assert (RESULTS_DIR / "retrieval_comparison.csv").exists()
        assert (RESULTS_DIR / "retrieval_comparison.json").exists()
        assert (PLOTS_DIR / "retrieval_comparison.png").exists()

    def test_experiment_2_topic_modeling(self):
        res = run_topic_comparison(benchmark_path=BENCHMARK_PATH)
        assert "metrics" in res
        assert "baseline_kmeans" in res["metrics"]
        assert "bertopic" in res["metrics"]
        assert (RESULTS_DIR / "topic_comparison.csv").exists()
        assert (RESULTS_DIR / "topic_comparison.json").exists()
        assert (PLOTS_DIR / "topic_coherence.png").exists()

    def test_experiment_3_limitation_detection(self):
        res = run_limitation_detection_comparison(benchmark_path=BENCHMARK_PATH)
        assert "models" in res
        assert "rule_based" in res["models"]
        assert "transformer_based" in res["models"]
        assert "hybrid_ensemble" in res["models"]
        assert res["models"]["rule_based"]["f1"] > 0.85
        assert (RESULTS_DIR / "limitation_detection_comparison.csv").exists()
        assert (RESULTS_DIR / "limitation_detection_comparison.json").exists()
        assert (PLOTS_DIR / "classifier_performance.png").exists()

    def test_experiment_4_gap_detection(self):
        res = run_gap_detection_comparison(benchmark_path=BENCHMARK_PATH)
        assert "approaches" in res
        assert "frequency_only" in res["approaches"]
        assert "semantic_only" in res["approaches"]
        assert "hybrid_multi_signal" in res["approaches"]
        assert res["approaches"]["hybrid_multi_signal"]["precision@5"] == 1.0
        assert (RESULTS_DIR / "gap_detection_comparison.csv").exists()
        assert (RESULTS_DIR / "gap_detection_comparison.json").exists()
        assert (PLOTS_DIR / "gap_detection_performance.png").exists()

    def test_experiment_5_counter_evidence(self):
        res = run_counter_evidence_evaluation(benchmark_path=BENCHMARK_PATH)
        assert "without_counter_evidence" in res
        assert "with_counter_evidence" in res
        assert res["with_counter_evidence"]["false_positives"] < res["without_counter_evidence"]["false_positives"]
        assert res["with_counter_evidence"]["precision_actionable"] >= res["without_counter_evidence"]["precision_actionable"]
        assert (RESULTS_DIR / "counter_evidence_evaluation.csv").exists()
        assert (RESULTS_DIR / "counter_evidence_evaluation.json").exists()
        assert (PLOTS_DIR / "counter_evidence_effect.png").exists()

    def test_experiment_6_lifecycle(self):
        res = run_lifecycle_evaluation(benchmark_path=BENCHMARK_PATH)
        assert "static_baseline" in res
        assert "temporal_lifecycle_framework" in res
        assert res["temporal_lifecycle_framework"]["macro_f1"] > res["static_baseline"]["macro_f1"]
        assert (RESULTS_DIR / "lifecycle_evaluation.csv").exists()
        assert (RESULTS_DIR / "lifecycle_evaluation.json").exists()
        assert (PLOTS_DIR / "lifecycle_classification.png").exists()
