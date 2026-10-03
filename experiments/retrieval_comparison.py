"""Experiment 1: Retrieval Comparison (Phase 11).

Compares:
- TF-IDF retrieval (lexical baseline)
- Sentence Transformer retrieval (dense semantic vector embeddings + FAISS)

Metrics:
- Precision@5
- Recall@5
- Mean Reciprocal Rank (MRR)

Statistical Tests:
- Paired Student's t-test
- Wilcoxon signed-rank test
- 95% Confidence Intervals
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
from backend.app.services.retrieval.faiss_index import FAISSIndexManager
from backend.app.services.retrieval.tfidf_search import TFIDFSearchService

logger = get_logger("experiments.retrieval")

BENCHMARK_PATH = Path("data/evaluation/phase11_benchmark_dataset.json")
RESULTS_DIR = Path("experiments/results")
PLOTS_DIR = RESULTS_DIR / "plots"


def run_retrieval_comparison(benchmark_path: Path = BENCHMARK_PATH) -> Dict[str, Any]:
    """Execute Experiment 1 and generate CSV, JSON, and plot visualizations."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(benchmark_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    sentences = data["sentences"]
    queries = data["retrieval_benchmark"]

    texts = [s["text"] for s in sentences]
    metadata_list = [
        {
            "embedding_id": f"sent-{s['sentence_id']}",
            "paper_id": s["paper_id"],
            "sentence_id": s["sentence_id"],
            "section": s.get("section_name", "Content"),
            "source_text": s["text"],
            "extraction_type": s.get("gold_label", "OTHER"),
        }
        for s in sentences
    ]

    # Initialize Embedding Service and FAISS
    embed_svc = get_embedding_service()
    faiss_mgr = FAISSIndexManager(dimension=embed_svc.dimension, auto_load=False)
    doc_vectors = embed_svc.embed_documents(texts)
    faiss_mgr.add_vectors(doc_vectors, metadata_list)

    # Initialize TF-IDF Search Baseline
    tfidf_svc = TFIDFSearchService()
    tfidf_svc.fit_corpus(texts, metadata_list)

    k = 5
    per_query_results = []

    tfidf_p5 = []
    tfidf_r5 = []
    tfidf_mrr = []

    sem_p5 = []
    sem_r5 = []
    sem_mrr = []

    for q_item in queries:
        qid = q_item["query_id"]
        qtext = q_item["query"]
        rel_ids = set(q_item["relevant_sentence_ids"])
        total_rel = len(rel_ids)

        # 1. TF-IDF Search
        tfidf_res = tfidf_svc.search(qtext, top_k=k)
        tfidf_retrieved = [r["metadata"]["sentence_id"] for r in tfidf_res if "metadata" in r and "sentence_id" in r["metadata"]]
        t_rel_found = sum(1 for s_id in tfidf_retrieved if s_id in rel_ids)
        t_p5 = t_rel_found / k
        t_r5 = t_rel_found / total_rel if total_rel > 0 else 0.0

        t_mrr = 0.0
        for rank, s_id in enumerate(tfidf_retrieved, 1):
            if s_id in rel_ids:
                t_mrr = 1.0 / rank
                break

        tfidf_p5.append(t_p5)
        tfidf_r5.append(t_r5)
        tfidf_mrr.append(t_mrr)

        # 2. Dense Semantic Search
        q_vec = embed_svc.embed_query(qtext)
        sem_res = faiss_mgr.search(q_vec, top_k=k)
        sem_retrieved = [r["metadata"]["sentence_id"] for r in sem_res if "metadata" in r and "sentence_id" in r["metadata"]]
        s_rel_found = sum(1 for s_id in sem_retrieved if s_id in rel_ids)
        s_p5 = s_rel_found / k
        s_r5 = s_rel_found / total_rel if total_rel > 0 else 0.0

        s_mrr = 0.0
        for rank, s_id in enumerate(sem_retrieved, 1):
            if s_id in rel_ids:
                s_mrr = 1.0 / rank
                break

        sem_p5.append(s_p5)
        sem_r5.append(s_r5)
        sem_mrr.append(s_mrr)

        per_query_results.append({
            "query_id": qid,
            "domain": q_item.get("domain", "General"),
            "tfidf_precision@5": round(t_p5, 4),
            "semantic_precision@5": round(s_p5, 4),
            "tfidf_recall@5": round(t_r5, 4),
            "semantic_recall@5": round(s_r5, 4),
            "tfidf_mrr": round(t_mrr, 4),
            "semantic_mrr": round(s_mrr, 4),
        })

    # Statistical significance calculations
    t_stat_p, p_val_p = stats.ttest_rel(sem_p5, tfidf_p5)
    t_stat_r, p_val_r = stats.ttest_rel(sem_r5, tfidf_r5)
    t_stat_m, p_val_m = stats.ttest_rel(sem_mrr, tfidf_mrr)

    # Non-parametric Wilcoxon signed-rank test
    try:
        w_stat_m, w_pval_m = stats.wilcoxon(sem_mrr, tfidf_mrr)
    except Exception:
        w_stat_m, w_pval_m = float("nan"), float("nan")

    def calc_ci(values: List[float]) -> Tuple[float, float]:
        mean_v = float(np.mean(values))
        sem_v = float(stats.sem(values)) if len(values) > 1 else 0.0
        ci = stats.t.interval(0.95, df=len(values) - 1, loc=mean_v, scale=sem_v) if sem_v > 0 else (mean_v, mean_v)
        return round(ci[0], 4), round(ci[1], 4)

    summary = {
        "experiment_name": "Experiment 1: TF-IDF vs Sentence Transformer Retrieval",
        "num_queries": len(queries),
        "corpus_sentences": len(sentences),
        "embedding_model": embed_svc.model_name,
        "metrics": {
            "tfidf_baseline": {
                "precision@5_mean": round(float(np.mean(tfidf_p5)), 4),
                "precision@5_std": round(float(np.std(tfidf_p5, ddof=1)), 4),
                "precision@5_ci95": list(calc_ci(tfidf_p5)),
                "recall@5_mean": round(float(np.mean(tfidf_r5)), 4),
                "recall@5_std": round(float(np.std(tfidf_r5, ddof=1)), 4),
                "recall@5_ci95": list(calc_ci(tfidf_r5)),
                "mrr_mean": round(float(np.mean(tfidf_mrr)), 4),
                "mrr_std": round(float(np.std(tfidf_mrr, ddof=1)), 4),
                "mrr_ci95": list(calc_ci(tfidf_mrr)),
            },
            "sentence_transformer": {
                "precision@5_mean": round(float(np.mean(sem_p5)), 4),
                "precision@5_std": round(float(np.std(sem_p5, ddof=1)), 4),
                "precision@5_ci95": list(calc_ci(sem_p5)),
                "recall@5_mean": round(float(np.mean(sem_r5)), 4),
                "recall@5_std": round(float(np.std(sem_r5, ddof=1)), 4),
                "recall@5_ci95": list(calc_ci(sem_r5)),
                "mrr_mean": round(float(np.mean(sem_mrr)), 4),
                "mrr_std": round(float(np.std(sem_mrr, ddof=1)), 4),
                "mrr_ci95": list(calc_ci(sem_mrr)),
            },
            "statistical_significance": {
                "paired_t_test_p@5": {"t_statistic": round(float(t_stat_p), 4), "p_value": round(float(p_val_p), 6), "significant_p05": bool(p_val_p < 0.05)},
                "paired_t_test_recall@5": {"t_statistic": round(float(t_stat_r), 4), "p_value": round(float(p_val_r), 6), "significant_p05": bool(p_val_r < 0.05)},
                "paired_t_test_mrr": {"t_statistic": round(float(t_stat_m), 4), "p_value": round(float(p_val_m), 6), "significant_p05": bool(p_val_m < 0.05)},
                "wilcoxon_mrr": {"w_statistic": round(float(w_stat_m), 4) if not np.isnan(w_stat_m) else None, "p_value": round(float(w_pval_m), 6) if not np.isnan(w_pval_m) else None},
            },
        },
        "query_level_audit": per_query_results,
    }

    # Save CSV
    df = pd.DataFrame(per_query_results)
    csv_path = RESULTS_DIR / "retrieval_comparison.csv"
    df.to_csv(csv_path, index=False)

    # Save JSON
    json_path = RESULTS_DIR / "retrieval_comparison.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Generate Visualization Plot
    plot_path = PLOTS_DIR / "retrieval_comparison.png"
    _generate_plot(summary, plot_path)

    logger.info(f"Experiment 1 complete: CSV -> {csv_path}, JSON -> {json_path}, Plot -> {plot_path}")
    return summary


def _generate_plot(summary: Dict[str, Any], output_path: Path):
    """Plot bar chart comparing TF-IDF vs Sentence Transformer retrieval with error bars."""
    metrics = ["Precision@5", "Recall@5", "MRR"]
    tfidf_means = [
        summary["metrics"]["tfidf_baseline"]["precision@5_mean"],
        summary["metrics"]["tfidf_baseline"]["recall@5_mean"],
        summary["metrics"]["tfidf_baseline"]["mrr_mean"],
    ]
    tfidf_errors = [
        summary["metrics"]["tfidf_baseline"]["precision@5_std"],
        summary["metrics"]["tfidf_baseline"]["recall@5_std"],
        summary["metrics"]["tfidf_baseline"]["mrr_std"],
    ]
    sem_means = [
        summary["metrics"]["sentence_transformer"]["precision@5_mean"],
        summary["metrics"]["sentence_transformer"]["recall@5_mean"],
        summary["metrics"]["sentence_transformer"]["mrr_mean"],
    ]
    sem_errors = [
        summary["metrics"]["sentence_transformer"]["precision@5_std"],
        summary["metrics"]["sentence_transformer"]["recall@5_std"],
        summary["metrics"]["sentence_transformer"]["mrr_std"],
    ]

    x = np.arange(len(metrics))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
    rects1 = ax.bar(x - width / 2, tfidf_means, width, yerr=tfidf_errors, label="TF-IDF Baseline", color="#64748b", capsize=5, alpha=0.9)
    rects2 = ax.bar(x + width / 2, sem_means, width, yerr=sem_errors, label="Sentence Transformer (SciBERT / MiniLM)", color="#3b82f6", capsize=5, alpha=0.9)

    ax.set_ylabel("Score (0.0 - 1.0)", fontsize=11, fontweight="bold")
    ax.set_title("Experiment 1: Evidence Retrieval Performance Comparison", fontsize=12, fontweight="bold", pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(metrics, fontsize=11, fontweight="bold")
    ax.set_ylim(0.0, 1.15)
    ax.legend(loc="upper left", frameon=True)
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    # Bar value labels
    for rect in rects1:
        h = rect.get_height()
        ax.annotate(f"{h:.3f}", xy=(rect.get_x() + rect.get_width() / 2, h), xytext=(0, 6), textcoords="offset points", ha="center", va="bottom", fontsize=9)
    for rect in rects2:
        h = rect.get_height()
        ax.annotate(f"{h:.3f}", xy=(rect.get_x() + rect.get_width() / 2, h), xytext=(0, 6), textcoords="offset points", ha="center", va="bottom", fontsize=9, fontweight="bold")

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


if __name__ == "__main__":
    run_retrieval_comparison()
