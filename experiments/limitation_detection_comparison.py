"""Experiment 3: Limitation Detection Comparison (Phase 11).

Compares:
- Approach 1: Rule-based limitation detection (lexical pattern matching with LimitationDetector)
- Approach 2: Transformer-based limitation detection (dense semantic embeddings + prototypical limitation vectors)
- Approach 3: Hybrid Ensembled detection (rules + semantic confirmation)

Metrics:
- Precision
- Recall
- F1 Score
- Subtype Accuracy (computational, data_scarcity, generalization, methodological, generic)

Statistical Tests:
- 1,000-sample Bootstrap 95% Confidence Intervals for P, R, F1
- McNemar's test for paired classification significance
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite:///./data/metadata/gap_finder_dev.db")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from backend.app.core.logging import get_logger
from backend.app.services.embeddings.embedding_service import get_embedding_service
from backend.app.services.nlp.limitation_detector import LimitationDetector

logger = get_logger("experiments.limitation")

BENCHMARK_PATH = Path("data/evaluation/phase11_benchmark_dataset.json")
RESULTS_DIR = Path("experiments/results")
PLOTS_DIR = RESULTS_DIR / "plots"

# Prototypical scientific limitation anchor phrases for transformer zero-shot/dense scoring
PROTOTYPE_LIMITATION_ANCHORS = [
    "A major limitation of our method is quadratic computational and memory complexity.",
    "Data scarcity and shortage of expert-annotated training samples severely constrain model performance.",
    "The model fails to generalize well to out-of-distribution domains and unseen benchmark distributions.",
    "A methodological constraint is our reliance on heuristic filtering and simplifying independence assumptions.",
    "Our evaluation has notable limitations and does not account for temporal shifts.",
]


def _bootstrap_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    n_bootstraps: int = 1000,
    seed: int = 42,
) -> Dict[str, Tuple[float, float]]:
    """Compute 95% bootstrap confidence intervals for Precision, Recall, and F1."""
    rng = np.random.RandomState(seed)
    n = len(y_true)
    p_boot, r_boot, f1_boot = [], [], []

    for _ in range(n_bootstraps):
        idx = rng.choice(n, size=n, replace=True)
        yt_sample = y_true[idx]
        yp_sample = y_pred[idx]

        tp = np.sum((yt_sample == 1) & (yp_sample == 1))
        fp = np.sum((yt_sample == 0) & (yp_sample == 1))
        fn = np.sum((yt_sample == 1) & (yp_sample == 0))

        p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f = (2 * p * r) / (p + r) if (p + r) > 0 else 0.0

        p_boot.append(p)
        r_boot.append(r)
        f1_boot.append(f)

    def ci95(arr):
        return round(float(np.percentile(arr, 2.5)), 4), round(float(np.percentile(arr, 97.5)), 4)

    return {
        "precision_ci95": ci95(p_boot),
        "recall_ci95": ci95(r_boot),
        "f1_ci95": ci95(f1_boot),
    }


def _mcnemar_test(y_true: np.ndarray, y_pred1: np.ndarray, y_pred2: np.ndarray) -> Dict[str, Any]:
    """Calculate McNemar test contingency table and p-value between two classifiers."""
    # b: clf1 correct, clf2 wrong; c: clf1 wrong, clf2 correct
    b = np.sum((y_pred1 == y_true) & (y_pred2 != y_true))
    c = np.sum((y_pred1 != y_true) & (y_pred2 == y_true))
    total_disc = b + c
    if total_disc == 0:
        return {"b": int(b), "c": int(c), "statistic": 0.0, "p_value": 1.0}
    # With continuity correction
    stat = (abs(b - c) - 1.0) ** 2 / total_disc
    p_val = stats.chi2.sf(stat, df=1)
    return {
        "b": int(b),
        "c": int(c),
        "statistic": round(float(stat), 4),
        "p_value": round(float(p_val), 6),
        "significant_p05": bool(p_val < 0.05),
    }


def run_limitation_detection_comparison(benchmark_path: Path = BENCHMARK_PATH) -> Dict[str, Any]:
    """Execute Experiment 3 and generate CSV, JSON, and plot visualizations."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(benchmark_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    sentences = data["sentences"]
    texts = [s["text"] for s in sentences]
    sections = [s.get("section_name", "") for s in sentences]
    gold_is_lim = np.array([1 if s.get("is_limitation") else 0 for s in sentences])
    gold_subtypes = [s.get("limitation_subtype") for s in sentences]

    total_sentences = len(sentences)
    total_gold_lims = int(np.sum(gold_is_lim))

    # 1. Rule-based Limitation Detection
    rule_detector = LimitationDetector()
    rule_preds = []
    rule_detected_subtypes = []

    for text, sec in zip(texts, sections):
        res = rule_detector.detect(text, section_name=sec)
        if res is not None:
            rule_preds.append(1)
            rule_detected_subtypes.append(res.get("subtype", "generic"))
        else:
            rule_preds.append(0)
            rule_detected_subtypes.append(None)

    rule_preds = np.array(rule_preds)

    # 2. Transformer-based Limitation Detection (Embedding Prototype Cosine Similarity)
    embed_svc = get_embedding_service()
    doc_vectors = embed_svc.embed_documents(texts)
    anchor_vectors = embed_svc.embed_documents(PROTOTYPE_LIMITATION_ANCHORS)

    # Pairwise max cosine similarity against limitation prototype anchors
    # Both sets of vectors are normalized by embed_svc
    sim_matrix = np.dot(doc_vectors, anchor_vectors.T)
    max_sims = np.max(sim_matrix, axis=1)

    # Calibrated threshold for limitation classification
    transformer_threshold = 0.52
    transformer_preds = (max_sims >= transformer_threshold).astype(int)

    # 3. Hybrid Ensembled Limitation Detection
    # Hybrid triggers if rules detect limitation OR high transformer confidence in limitation section
    hybrid_preds = []
    for i in range(total_sentences):
        in_lim_sec = any(kw in sections[i].lower() for kw in ["limitation", "weakness", "threats"])
        rule_hit = bool(rule_preds[i] == 1)
        trans_hit = bool(max_sims[i] >= 0.50)
        strong_trans_hit = bool(max_sims[i] >= 0.58)

        # Ensembled decision rule
        if rule_hit:
            hybrid_preds.append(1)
        elif in_lim_sec and trans_hit:
            hybrid_preds.append(1)
        elif strong_trans_hit:
            hybrid_preds.append(1)
        else:
            hybrid_preds.append(0)

    hybrid_preds = np.array(hybrid_preds)

    def compute_metrics(y_p: np.ndarray, name: str) -> Dict[str, Any]:
        tp = int(np.sum((gold_is_lim == 1) & (y_p == 1)))
        fp = int(np.sum((gold_is_lim == 0) & (y_p == 1)))
        fn = int(np.sum((gold_is_lim == 1) & (y_p == 0)))
        tn = int(np.sum((gold_is_lim == 0) & (y_p == 0)))

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        acc = (tp + tn) / len(gold_is_lim)

        boot = _bootstrap_metrics(gold_is_lim, y_p)

        return {
            "model_name": name,
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "true_negatives": tn,
            "precision": round(float(prec), 4),
            "precision_ci95": list(boot["precision_ci95"]),
            "recall": round(float(rec), 4),
            "recall_ci95": list(boot["recall_ci95"]),
            "f1": round(float(f1), 4),
            "f1_ci95": list(boot["f1_ci95"]),
            "accuracy": round(float(acc), 4),
        }

    rule_metrics = compute_metrics(rule_preds, "Rule-based Classifier")
    trans_metrics = compute_metrics(transformer_preds, "Transformer-based Classifier")
    hybrid_metrics = compute_metrics(hybrid_preds, "Hybrid Ensemble Classifier")

    # Subtype performance for rule detector on true limitation items
    subtype_total = 0
    subtype_correct = 0
    for i in range(total_sentences):
        if gold_is_lim[i] == 1:
            subtype_total += 1
            if rule_detected_subtypes[i] == gold_subtypes[i]:
                subtype_correct += 1

    subtype_acc = subtype_correct / subtype_total if subtype_total > 0 else 0.0
    rule_metrics["subtype_accuracy"] = round(float(subtype_acc), 4)

    # McNemar tests
    mcnemar_rule_trans = _mcnemar_test(gold_is_lim, rule_preds, transformer_preds)
    mcnemar_rule_hybrid = _mcnemar_test(gold_is_lim, rule_preds, hybrid_preds)

    summary = {
        "experiment_name": "Experiment 3: Rule-based vs Transformer-based Limitation Detection",
        "total_sentences": total_sentences,
        "total_gold_limitations": total_gold_lims,
        "models": {
            "rule_based": rule_metrics,
            "transformer_based": trans_metrics,
            "hybrid_ensemble": hybrid_metrics,
        },
        "statistical_tests": {
            "mcnemar_rule_vs_transformer": mcnemar_rule_trans,
            "mcnemar_rule_vs_hybrid": mcnemar_rule_hybrid,
        },
    }

    # Save CSV
    table_rows = [
        {
            "Model": "Rule-based Detector",
            "Precision": rule_metrics["precision"],
            "Recall": rule_metrics["recall"],
            "F1 Score": rule_metrics["f1"],
            "Accuracy": rule_metrics["accuracy"],
            "F1 95% CI Lower": rule_metrics["f1_ci95"][0],
            "F1 95% CI Upper": rule_metrics["f1_ci95"][1],
            "TP": rule_metrics["true_positives"],
            "FP": rule_metrics["false_positives"],
            "FN": rule_metrics["false_negatives"],
        },
        {
            "Model": "Transformer-based Detector",
            "Precision": trans_metrics["precision"],
            "Recall": trans_metrics["recall"],
            "F1 Score": trans_metrics["f1"],
            "Accuracy": trans_metrics["accuracy"],
            "F1 95% CI Lower": trans_metrics["f1_ci95"][0],
            "F1 95% CI Upper": trans_metrics["f1_ci95"][1],
            "TP": trans_metrics["true_positives"],
            "FP": trans_metrics["false_positives"],
            "FN": trans_metrics["false_negatives"],
        },
        {
            "Model": "Hybrid Ensemble Detector",
            "Precision": hybrid_metrics["precision"],
            "Recall": hybrid_metrics["recall"],
            "F1 Score": hybrid_metrics["f1"],
            "Accuracy": hybrid_metrics["accuracy"],
            "F1 95% CI Lower": hybrid_metrics["f1_ci95"][0],
            "F1 95% CI Upper": hybrid_metrics["f1_ci95"][1],
            "TP": hybrid_metrics["true_positives"],
            "FP": hybrid_metrics["false_positives"],
            "FN": hybrid_metrics["false_negatives"],
        },
    ]
    df = pd.DataFrame(table_rows)
    csv_path = RESULTS_DIR / "limitation_detection_comparison.csv"
    df.to_csv(csv_path, index=False)

    # Save JSON
    json_path = RESULTS_DIR / "limitation_detection_comparison.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Generate Visualization Plot
    plot_path = PLOTS_DIR / "classifier_performance.png"
    _generate_plot(summary, plot_path)

    logger.info(f"Experiment 3 complete: CSV -> {csv_path}, JSON -> {json_path}, Plot -> {plot_path}")
    return summary


def _generate_plot(summary: Dict[str, Any], output_path: Path):
    """Plot grouped bar chart of Precision, Recall, and F1 across limitation detection approaches."""
    models = ["Rule-based", "Transformer", "Hybrid Ensemble"]
    precisions = [
        summary["models"]["rule_based"]["precision"],
        summary["models"]["transformer_based"]["precision"],
        summary["models"]["hybrid_ensemble"]["precision"],
    ]
    recalls = [
        summary["models"]["rule_based"]["recall"],
        summary["models"]["transformer_based"]["recall"],
        summary["models"]["hybrid_ensemble"]["recall"],
    ]
    f1s = [
        summary["models"]["rule_based"]["f1"],
        summary["models"]["transformer_based"]["f1"],
        summary["models"]["hybrid_ensemble"]["f1"],
    ]

    x = np.arange(len(models))
    width = 0.25

    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
    rects1 = ax.bar(x - width, precisions, width, label="Precision", color="#0284c7", alpha=0.9)
    rects2 = ax.bar(x, recalls, width, label="Recall", color="#10b981", alpha=0.9)
    rects3 = ax.bar(x + width, f1s, width, label="F1 Score", color="#f59e0b", alpha=0.9)

    ax.set_ylabel("Score (0.0 - 1.0)", fontsize=11, fontweight="bold")
    ax.set_title("Experiment 3: Scientific Limitation Detection Performance", fontsize=12, fontweight="bold", pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(models, fontsize=11, fontweight="bold")
    ax.set_ylim(0.0, 1.15)
    ax.legend(loc="upper left", frameon=True)
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    for rects in [rects1, rects2, rects3]:
        for rect in rects:
            h = rect.get_height()
            ax.annotate(f"{h:.3f}", xy=(rect.get_x() + rect.get_width() / 2, h), xytext=(0, 5), textcoords="offset points", ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


if __name__ == "__main__":
    run_limitation_detection_comparison()
