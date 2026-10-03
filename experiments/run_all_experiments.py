"""Master Experiment Orchestration Pipeline (Phase 11).

Executes all 6 scientific evaluation experiments sequentially:
1. Experiment 1: TF-IDF vs Sentence Transformer Retrieval
2. Experiment 2: Baseline Clustering vs BERTopic
3. Experiment 3: Rule-based vs Transformer-based Limitation Detection
4. Experiment 4: Gap Detection Comparison (Frequency vs Semantic vs Hybrid)
5. Experiment 5: Counter-Evidence Verification Evaluation
6. Experiment 6: Static Gap Generation vs Temporal Lifecycle Framework

Generates CSV, JSON, and publication-ready plots in experiments/results/.
Validates artifact integrity and outputs an academic summary report.
"""

import json
import os
import sys
import time
from pathlib import Path

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite:///./data/metadata/gap_finder_dev.db")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from backend.app.core.logging import get_logger
from experiments.retrieval_comparison import run_retrieval_comparison
from experiments.topic_comparison import run_topic_comparison
from experiments.limitation_detection_comparison import run_limitation_detection_comparison
from experiments.gap_detection_comparison import run_gap_detection_comparison
from experiments.counter_evidence_evaluation import run_counter_evidence_evaluation
from experiments.lifecycle_evaluation import run_lifecycle_evaluation

logger = get_logger("experiments.runner")

RESULTS_DIR = Path("experiments/results")
PLOTS_DIR = RESULTS_DIR / "plots"


def run_all_experiments():
    start_total = time.time()
    print("\n" + "=" * 80)
    print(" ResearchGapX - Phase 11: Final Experimental Scientific Evaluation Suite")
    print("=" * 80)

    # 1. Experiment 1: Retrieval Comparison
    print("\n>>> Running Experiment 1: Retrieval Comparison (TF-IDF vs Sentence Transformer)...")
    t0 = time.time()
    res1 = run_retrieval_comparison()
    print(f"    Completed in {time.time() - t0:.2f}s.")
    print(f"    - TF-IDF Baseline:    P@5 = {res1['metrics']['tfidf_baseline']['precision@5_mean']:.3f}, R@5 = {res1['metrics']['tfidf_baseline']['recall@5_mean']:.3f}, MRR = {res1['metrics']['tfidf_baseline']['mrr_mean']:.3f}")
    print(f"    - Sentence Transf.:   P@5 = {res1['metrics']['sentence_transformer']['precision@5_mean']:.3f}, R@5 = {res1['metrics']['sentence_transformer']['recall@5_mean']:.3f}, MRR = {res1['metrics']['sentence_transformer']['mrr_mean']:.3f}")
    print(f"    - Paired t-test MRR:  t = {res1['metrics']['statistical_significance']['paired_t_test_mrr']['t_statistic']:.4f}, p = {res1['metrics']['statistical_significance']['paired_t_test_mrr']['p_value']:.4f} (Sig: {res1['metrics']['statistical_significance']['paired_t_test_mrr']['significant_p05']})")

    # 2. Experiment 2: Topic Comparison
    print("\n>>> Running Experiment 2: Topic Modeling Comparison (Baseline K-Means vs BERTopic)...")
    t0 = time.time()
    res2 = run_topic_comparison()
    print(f"    Completed in {time.time() - t0:.2f}s.")
    print(f"    - Baseline K-Means:   Coherence = {res2['metrics']['baseline_kmeans']['topic_coherence']:.3f}, Stability = {res2['metrics']['baseline_kmeans']['topic_stability_mean']:.3f}, Silhouette = {res2['metrics']['baseline_kmeans']['silhouette_score']:.3f}")
    print(f"    - BERTopic Semantic:  Coherence = {res2['metrics']['bertopic']['topic_coherence']:.3f}, Stability = {res2['metrics']['bertopic']['topic_stability_mean']:.3f}, Silhouette = {res2['metrics']['bertopic']['silhouette_score']:.3f}")
    print(f"    - Topic Stability t:  t = {res2['metrics']['statistical_significance']['stability_t_statistic']:.4f}, p = {res2['metrics']['statistical_significance']['stability_p_value']:.4f}")

    # 3. Experiment 3: Limitation Detection Comparison
    print("\n>>> Running Experiment 3: Limitation Detection Comparison (Rules vs Transformer vs Hybrid)...")
    t0 = time.time()
    res3 = run_limitation_detection_comparison()
    print(f"    Completed in {time.time() - t0:.2f}s.")
    print(f"    - Rule-based Detector:  Precision = {res3['models']['rule_based']['precision']:.3f}, Recall = {res3['models']['rule_based']['recall']:.3f}, F1 = {res3['models']['rule_based']['f1']:.3f}, Subtype Acc = {res3['models']['rule_based']['subtype_accuracy']:.3f}")
    print(f"    - Transformer Detector: Precision = {res3['models']['transformer_based']['precision']:.3f}, Recall = {res3['models']['transformer_based']['recall']:.3f}, F1 = {res3['models']['transformer_based']['f1']:.3f}")
    print(f"    - Hybrid Ensemble:      Precision = {res3['models']['hybrid_ensemble']['precision']:.3f}, Recall = {res3['models']['hybrid_ensemble']['recall']:.3f}, F1 = {res3['models']['hybrid_ensemble']['f1']:.3f}")
    print(f"    - McNemar Rule vs Trans: Chi2 = {res3['statistical_tests']['mcnemar_rule_vs_transformer']['statistic']:.4f}, p = {res3['statistical_tests']['mcnemar_rule_vs_transformer']['p_value']:.4f} (Sig: {res3['statistical_tests']['mcnemar_rule_vs_transformer']['significant_p05']})")

    # 4. Experiment 4: Gap Detection Comparison
    print("\n>>> Running Experiment 4: Gap Detection Comparison (Frequency vs Semantic vs Hybrid)...")
    t0 = time.time()
    res4 = run_gap_detection_comparison()
    print(f"    Completed in {time.time() - t0:.2f}s.")
    print(f"    - Frequency-only:       P@5 = {res4['approaches']['frequency_only']['precision@5']:.3f}, R@10 = {res4['approaches']['frequency_only']['recall@10']:.3f}, Spearman Rho = {res4['approaches']['frequency_only']['spearman_rho']:.3f}")
    print(f"    - Semantic-only:        P@5 = {res4['approaches']['semantic_only']['precision@5']:.3f}, R@10 = {res4['approaches']['semantic_only']['recall@10']:.3f}, Spearman Rho = {res4['approaches']['semantic_only']['spearman_rho']:.3f}")
    print(f"    - Hybrid Multi-Signal:  P@5 = {res4['approaches']['hybrid_multi_signal']['precision@5']:.3f}, R@10 = {res4['approaches']['hybrid_multi_signal']['recall@10']:.3f}, Spearman Rho = {res4['approaches']['hybrid_multi_signal']['spearman_rho']:.3f}, Cohen's Kappa = {res4['approaches']['hybrid_multi_signal']['cohens_kappa']:.3f}")

    # 5. Experiment 5: Counter-Evidence Evaluation
    print("\n>>> Running Experiment 5: Counter-Evidence Verification Evaluation...")
    t0 = time.time()
    res5 = run_counter_evidence_evaluation()
    print(f"    Completed in {time.time() - t0:.2f}s.")
    print(f"    - Without Counter-Evid: False Positives = {res5['without_counter_evidence']['false_positives']}, FPR = {res5['without_counter_evidence']['false_positive_rate']:.3f}, Actionable Precision = {res5['without_counter_evidence']['precision_actionable']:.3f}")
    print(f"    - With Counter-Evid:    False Positives = {res5['with_counter_evidence']['false_positives']}, FPR = {res5['with_counter_evidence']['false_positive_rate']:.3f}, Actionable Precision = {res5['with_counter_evidence']['precision_actionable']:.3f}, Verif Acc = {res5['with_counter_evidence']['verification_status_accuracy']:.3f}")
    print(f"    - Scientific NLI Acc:   {res5['scientific_nli_evaluation']['correct_classifications']}/{res5['scientific_nli_evaluation']['num_pairs']} ({res5['scientific_nli_evaluation']['nli_accuracy']:.3f})")

    # 6. Experiment 6: Lifecycle Framework Evaluation
    print("\n>>> Running Experiment 6: Gap Lifecycle Framework Evaluation...")
    t0 = time.time()
    res6 = run_lifecycle_evaluation()
    print(f"    Completed in {time.time() - t0:.2f}s.")
    print(f"    - Static Baseline:      Accuracy = {res6['static_baseline']['accuracy']:.3f}, Macro F1 = {res6['static_baseline']['macro_f1']:.3f}")
    print(f"    - Temporal Lifecycle:   Accuracy = {res6['temporal_lifecycle_framework']['accuracy']:.3f}, Macro F1 = {res6['temporal_lifecycle_framework']['macro_f1']:.3f} (95% CI: {res6['temporal_lifecycle_framework']['macro_f1_ci95']})")
    print(f"    - Per-State F1 Scores:  Persistent={res6['key_findings']['persistent_gap_detection_f1']:.2f}, Addressed={res6['key_findings']['addressed_gap_detection_f1']:.2f}, Reopened={res6['key_findings']['reopened_gap_detection_f1']:.2f}, Emerging={res6['key_findings']['emerging_gap_detection_f1']:.2f}")

    # Validate Artifact Generation
    expected_csvs = [
        "retrieval_comparison.csv",
        "topic_comparison.csv",
        "limitation_detection_comparison.csv",
        "gap_detection_comparison.csv",
        "counter_evidence_evaluation.csv",
        "lifecycle_evaluation.csv",
    ]
    expected_jsons = [
        "retrieval_comparison.json",
        "topic_comparison.json",
        "limitation_detection_comparison.json",
        "gap_detection_comparison.json",
        "counter_evidence_evaluation.json",
        "lifecycle_evaluation.json",
    ]
    expected_plots = [
        "retrieval_comparison.png",
        "topic_coherence.png",
        "classifier_performance.png",
        "gap_detection_performance.png",
        "counter_evidence_effect.png",
        "lifecycle_classification.png",
    ]

    print("\n" + "=" * 80)
    print(" Artifact Verification Audit")
    print("=" * 80)
    for csv_name in expected_csvs:
        p = RESULTS_DIR / csv_name
        assert p.exists(), f"Missing expected CSV artifact: {p}"
        print(f"  [CSV]  {csv_name:<36} ({p.stat().st_size} bytes)")

    for json_name in expected_jsons:
        p = RESULTS_DIR / json_name
        assert p.exists(), f"Missing expected JSON artifact: {p}"
        print(f"  [JSON] {json_name:<36} ({p.stat().st_size} bytes)")

    for plot_name in expected_plots:
        p = PLOTS_DIR / plot_name
        assert p.exists(), f"Missing expected Plot artifact: {p}"
        print(f"  [PLOT] {plot_name:<36} ({p.stat().st_size} bytes)")

    total_time = time.time() - start_total
    print("\n" + "=" * 80)
    print(f" ALL 6 EXPERIMENTS COMPLETED SUCCESSFULLY IN {total_time:.2f}s!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_all_experiments()
