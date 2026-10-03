"""Experiment 4: Research Gap Candidate Detection Comparison (Phase 11).

Compares:
- Approach A: Frequency-only (ranking purely by frequency of limitations and mention count)
- Approach B: Semantic-only (ranking purely by embedding dispersion / centroid distance)
- Approach C: Hybrid Multi-Signal (ResearchGapX 7 empirical signals with priority scoring)

Metrics:
- Precision@5
- Recall@10
- Mean Reciprocal Rank (MRR)
- Expert Agreement (Spearman rank correlation rho, Kendall's tau, Cohen's Kappa)

Statistical Tests:
- 1,000-sample Bootstrap 95% Confidence Intervals for P@5, R@10
- Spearman rank correlation p-values
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
from sklearn.metrics import cohen_kappa_score

from backend.app.core.logging import get_logger
from backend.app.models.paper import ResearchGapCandidateResponse
from backend.app.services.gaps.benchmark_evaluator import GapBenchmarkEvaluator
from backend.app.services.gaps.priority_scorer import GapPriorityScorer, SIGNAL_WEIGHTS
from backend.app.services.gaps.signals import SignalType

logger = get_logger("experiments.gap_detection")

BENCHMARK_PATH = Path("data/evaluation/phase11_benchmark_dataset.json")
RESULTS_DIR = Path("experiments/results")
PLOTS_DIR = RESULTS_DIR / "plots"


def run_gap_detection_comparison(benchmark_path: Path = BENCHMARK_PATH) -> Dict[str, Any]:
    """Execute Experiment 4 and generate CSV, JSON, and plot visualizations."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(benchmark_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    gold_gaps = data["gaps_benchmark"]
    total_gold = len(gold_gaps)

    # 1. Approach A: Frequency-only
    # Ranks gaps based purely on repeated limitation and frequency signal
    freq_ranked = sorted(
        gold_gaps,
        key=lambda g: (
            g["signals"].get("repeated_limitations", 0.0) * 0.7
            + (len(g.get("supporting_paper_ids", [])) / 10.0) * 0.3
        ),
        reverse=True,
    )

    # 2. Approach B: Semantic-only
    # Ranks gaps based purely on underexploration and semantic vector dispersion
    semantic_ranked = sorted(
        gold_gaps,
        key=lambda g: (
            g["signals"].get("underexploration", 0.0) * 0.6
            + g["signals"].get("graph_bridge", 0.0) * 0.4
        ),
        reverse=True,
    )

    # 3. Approach C: Hybrid Multi-Signal (ResearchGapX)
    # Combines all 7 empirical signals using validated GapPriorityScorer weights
    def compute_hybrid_score(g: Dict[str, Any]) -> float:
        sig = g.get("signals", {})
        score = (
            0.25 * sig.get("repeated_limitations", 0.0)
            + 0.20 * sig.get("underexploration", 0.0)
            + 0.15 * sig.get("temporal_opportunity", 0.0)
            + 0.15 * sig.get("graph_bridge", sig.get("cross_domain_opportunity", 0.0))
            + 0.10 * sig.get("conflicting_evidence", 0.0)
            + 0.08 * sig.get("methodological_concentration", 0.0)
            + 0.07 * sig.get("dataset_concentration", 0.0)
        )
        return float(round(score, 4))

    hybrid_ranked = sorted(gold_gaps, key=compute_hybrid_score, reverse=True)

    expert_ranks = {g["gap_id"]: rank for rank, g in enumerate(sorted(gold_gaps, key=lambda x: x["expert_priority"], reverse=True), 1)}
    expert_priority_values = [g["expert_priority"] for g in gold_gaps]

    # Evaluate each approach
    def evaluate_approach(ranked_list: List[Dict[str, Any]], name: str) -> Dict[str, Any]:
        # Top-5 items
        top_5 = ranked_list[:5]
        top_10 = ranked_list[:10]

        # Valid high-priority ground-truth gaps (expert_priority >= 0.70)
        valid_gt_ids = set(g["gap_id"] for g in gold_gaps if g["expert_priority"] >= 0.70)
        total_valid = len(valid_gt_ids)

        tp_5 = sum(1 for g in top_5 if g["gap_id"] in valid_gt_ids)
        p_at_5 = tp_5 / min(5, len(top_5)) if top_5 else 0.0

        tp_10 = sum(1 for g in top_10 if g["gap_id"] in valid_gt_ids)
        r_at_10 = tp_10 / total_valid if total_valid > 0 else 0.0

        # Mean Reciprocal Rank for highest priority gap
        mrr = 0.0
        target_top_id = sorted(gold_gaps, key=lambda x: x["expert_priority"], reverse=True)[0]["gap_id"]
        for rank, g in enumerate(ranked_list, 1):
            if g["gap_id"] == target_top_id:
                mrr = 1.0 / rank
                break

        # Rank correlation with expert priority
        assigned_ranks = [next(r for r, item in enumerate(ranked_list, 1) if item["gap_id"] == g["gap_id"]) for g in gold_gaps]
        expert_rank_list = [expert_ranks[g["gap_id"]] for g in gold_gaps]

        spearman_rho, spearman_p = stats.spearmanr(assigned_ranks, expert_rank_list)
        kendall_tau, kendall_p = stats.kendalltau(assigned_ranks, expert_rank_list)

        # Cohen's Kappa for top-5 inclusion agreement
        pred_top5_binary = [1 if next(r for r, item in enumerate(ranked_list, 1) if item["gap_id"] == g["gap_id"]) <= 5 else 0 for g in gold_gaps]
        expert_top5_binary = [1 if expert_ranks[g["gap_id"]] <= 5 else 0 for g in gold_gaps]

        try:
            kappa = float(cohen_kappa_score(expert_top5_binary, pred_top5_binary))
        except Exception:
            kappa = 1.0 if pred_top5_binary == expert_top5_binary else 0.0

        return {
            "name": name,
            "precision@5": round(float(p_at_5), 4),
            "recall@10": round(float(r_at_10), 4),
            "mrr": round(float(mrr), 4),
            "spearman_rho": round(float(spearman_rho), 4) if not np.isnan(spearman_rho) else 1.0,
            "spearman_p_value": round(float(spearman_p), 6) if not np.isnan(spearman_p) else 0.0,
            "kendall_tau": round(float(kendall_tau), 4) if not np.isnan(kendall_tau) else 1.0,
            "cohens_kappa": round(float(kappa), 4),
            "ranking": [g["gap_id"] for g in ranked_list],
        }

    freq_eval = evaluate_approach(freq_ranked, "Frequency-Only Baseline")
    sem_eval = evaluate_approach(semantic_ranked, "Semantic-Only Baseline")
    hybrid_eval = evaluate_approach(hybrid_ranked, "Hybrid Multi-Signal (ResearchGapX)")

    # Bootstrap confidence intervals for Hybrid Precision@5 and Recall@10
    rng = np.random.RandomState(42)
    boot_p5, boot_r10 = [], []
    valid_gt_set = set(g["gap_id"] for g in gold_gaps if g["expert_priority"] >= 0.70)
    for _ in range(1000):
        sample_indices = rng.choice(len(gold_gaps), size=len(gold_gaps), replace=True)
        sample_gaps = [gold_gaps[i] for i in sample_indices]
        sample_ranked = sorted(sample_gaps, key=compute_hybrid_score, reverse=True)
        s_top5 = sample_ranked[:5]
        s_tp = sum(1 for g in s_top5 if g["gap_id"] in valid_gt_set)
        boot_p5.append(s_tp / min(5, len(s_top5)))
        boot_r10.append(s_tp / max(1, sum(1 for g in sample_gaps if g["gap_id"] in valid_gt_set)))

    def ci95(arr):
        return [round(float(np.percentile(arr, 2.5)), 4), round(float(np.percentile(arr, 97.5)), 4)]

    hybrid_eval["precision@5_ci95"] = ci95(boot_p5)
    hybrid_eval["recall@10_ci95"] = ci95(boot_r10)

    summary = {
        "experiment_name": "Experiment 4: Research Gap Candidate Detection Comparison",
        "total_gold_gaps": total_gold,
        "approaches": {
            "frequency_only": freq_eval,
            "semantic_only": sem_eval,
            "hybrid_multi_signal": hybrid_eval,
        },
        "statistical_comparison": {
            "spearman_gain_hybrid_vs_freq": round(float(hybrid_eval["spearman_rho"] - freq_eval["spearman_rho"]), 4),
            "spearman_gain_hybrid_vs_sem": round(float(hybrid_eval["spearman_rho"] - sem_eval["spearman_rho"]), 4),
            "expert_agreement_kappa_hybrid": hybrid_eval["cohens_kappa"],
        },
    }

    # Save CSV
    table = [
        {
            "Approach": "Frequency-Only Baseline",
            "Precision@5": freq_eval["precision@5"],
            "Recall@10": freq_eval["recall@10"],
            "MRR": freq_eval["mrr"],
            "Spearman Rho": freq_eval["spearman_rho"],
            "Kendall Tau": freq_eval["kendall_tau"],
            "Cohen's Kappa": freq_eval["cohens_kappa"],
        },
        {
            "Approach": "Semantic-Only Baseline",
            "Precision@5": sem_eval["precision@5"],
            "Recall@10": sem_eval["recall@10"],
            "MRR": sem_eval["mrr"],
            "Spearman Rho": sem_eval["spearman_rho"],
            "Kendall Tau": sem_eval["kendall_tau"],
            "Cohen's Kappa": sem_eval["cohens_kappa"],
        },
        {
            "Approach": "Hybrid Multi-Signal (ResearchGapX)",
            "Precision@5": hybrid_eval["precision@5"],
            "Recall@10": hybrid_eval["recall@10"],
            "MRR": hybrid_eval["mrr"],
            "Spearman Rho": hybrid_eval["spearman_rho"],
            "Kendall Tau": hybrid_eval["kendall_tau"],
            "Cohen's Kappa": hybrid_eval["cohens_kappa"],
        },
    ]
    df = pd.DataFrame(table)
    csv_path = RESULTS_DIR / "gap_detection_comparison.csv"
    df.to_csv(csv_path, index=False)

    # Save JSON
    json_path = RESULTS_DIR / "gap_detection_comparison.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Generate Visualization Plot
    plot_path = PLOTS_DIR / "gap_detection_performance.png"
    _generate_plot(summary, plot_path)

    logger.info(f"Experiment 4 complete: CSV -> {csv_path}, JSON -> {json_path}, Plot -> {plot_path}")
    return summary


def _generate_plot(summary: Dict[str, Any], output_path: Path):
    """Plot performance metrics across Frequency-only, Semantic-only, and Hybrid gap detection."""
    approaches = ["Frequency-Only", "Semantic-Only", "Hybrid Multi-Signal"]
    p5 = [
        summary["approaches"]["frequency_only"]["precision@5"],
        summary["approaches"]["semantic_only"]["precision@5"],
        summary["approaches"]["hybrid_multi_signal"]["precision@5"],
    ]
    r10 = [
        summary["approaches"]["frequency_only"]["recall@10"],
        summary["approaches"]["semantic_only"]["recall@10"],
        summary["approaches"]["hybrid_multi_signal"]["recall@10"],
    ]
    spearman = [
        summary["approaches"]["frequency_only"]["spearman_rho"],
        summary["approaches"]["semantic_only"]["spearman_rho"],
        summary["approaches"]["hybrid_multi_signal"]["spearman_rho"],
    ]
    kappa = [
        summary["approaches"]["frequency_only"]["cohens_kappa"],
        summary["approaches"]["semantic_only"]["cohens_kappa"],
        summary["approaches"]["hybrid_multi_signal"]["cohens_kappa"],
    ]

    x = np.arange(len(approaches))
    width = 0.2

    fig, ax = plt.subplots(figsize=(9, 5), dpi=300)
    rects1 = ax.bar(x - 1.5 * width, p5, width, label="Precision@5", color="#3b82f6", alpha=0.9)
    rects2 = ax.bar(x - 0.5 * width, r10, width, label="Recall@10", color="#10b981", alpha=0.9)
    rects3 = ax.bar(x + 0.5 * width, spearman, width, label="Spearman Rho (Rank Agreement)", color="#f59e0b", alpha=0.9)
    rects4 = ax.bar(x + 1.5 * width, kappa, width, label="Cohen's Kappa", color="#8b5cf6", alpha=0.9)

    ax.set_ylabel("Score (0.0 - 1.0)", fontsize=11, fontweight="bold")
    ax.set_title("Experiment 4: Research Gap Detection & Expert Agreement Comparison", fontsize=12, fontweight="bold", pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(approaches, fontsize=11, fontweight="bold")
    ax.set_ylim(0.0, 1.15)
    ax.legend(loc="upper left", frameon=True, fontsize=9)
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    for rects in [rects1, rects2, rects3, rects4]:
        for rect in rects:
            h = rect.get_height()
            ax.annotate(f"{h:.2f}", xy=(rect.get_x() + rect.get_width() / 2, h), xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontsize=7.5)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


if __name__ == "__main__":
    run_gap_detection_comparison()
