"""Expert-Labelled Research Gap Benchmark Evaluator (Phase 6).

Evaluates generated research gap candidates against manually curated ground-truth
potential research gaps across scientific publications.

Calculates:
- Precision@5
- Recall@10
- Mean Reciprocal Rank (MRR)
- False positive and false negative audit
"""

import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np

from backend.app.core.logging import get_logger
from backend.app.models.paper import ResearchGapCandidateResponse

logger = get_logger("app.gaps.benchmark")

# Expert-labelled Ground-Truth Benchmark Gaps (annotated from verified scientific literature)
GROUND_TRUTH_GAP_BENCHMARK: List[Dict[str, Any]] = [
    {
        "gt_id": "gt-1",
        "title": "Computational Memory Overhead in Long-Context Self-Attention",
        "keywords": ["memory", "quadratic", "overhead", "attention", "context length"],
        "gap_type": "repeated_limitation",
        "description": "Quadratic memory scaling bottleneck in self-attention prevents scaling beyond 16k tokens.",
    },
    {
        "gt_id": "gt-2",
        "title": "Cross-Domain Generalization Degradation in Low-Resource Scientific NLP",
        "keywords": ["cross-domain", "generalization", "transfer", "domain shift", "low-resource"],
        "gap_type": "repeated_limitation",
        "description": "Deep architectures suffer severe performance degradation when transferred to out-of-distribution biomedical abstracts.",
    },
    {
        "gt_id": "gt-3",
        "title": "Annotated Dataset Scarcity in Multimodal Clinical Evidence Extraction",
        "keywords": ["scarcity", "annotated", "clinical", "biomedical", "medical imaging"],
        "gap_type": "underexplored_area",
        "description": "High annotation costs and clinical privacy constraints result in severe data scarcity for multimodal extraction.",
    },
    {
        "gt_id": "gt-4",
        "title": "Evaluation Bias and Factual Hallucinations in Scientific Summarization",
        "keywords": ["factual", "hallucination", "evaluation bias", "summarization", "rouge"],
        "gap_type": "repeated_limitation",
        "description": "N-gram overlap metrics fail to penalize factual hallucinations in abstractive generation.",
    },
    {
        "gt_id": "gt-5",
        "title": "Homophily Assumption Failure in Scientific Citation Graphs",
        "keywords": ["citation", "homophily", "negative sampling", "contrastive", "subfields"],
        "gap_type": "underexplored_area",
        "description": "Citation graph representation learning assumes local homophily, failing for interdisciplinary citations.",
    },
]


class GapBenchmarkEvaluator:
    """Evaluates Precision@5, Recall@10, and signal efficacy against expert ground-truth."""

    @classmethod
    def evaluate(
        cls,
        generated_candidates: List[ResearchGapCandidateResponse],
        ground_truth: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Run benchmark evaluation and compute Precision@5, Recall@10, and error audit."""
        gt_list = ground_truth or GROUND_TRUTH_GAP_BENCHMARK
        total_gt = len(gt_list)

        matched_gt_ids: Set[str] = set()
        ranks_of_gt: List[int] = []

        top_5_matches = 0
        top_10_matches = 0

        candidate_audit = []

        for rank, cand in enumerate(generated_candidates, 1):
            cand_text = f"{cand.title} {cand.description}".lower()
            matched_gt = None

            for gt in gt_list:
                kw_matches = sum(1 for kw in gt["keywords"] if kw.lower() in cand_text)
                # Match threshold: at least 2 keyword matches or direct gap_type and keyphrase match
                if kw_matches >= 2 or (gt["gap_type"] == cand.gap_type and kw_matches >= 1):
                    matched_gt = gt
                    break

            is_match = matched_gt is not None
            if is_match:
                gt_id = matched_gt["gt_id"]
                if gt_id not in matched_gt_ids:
                    matched_gt_ids.add(gt_id)
                    ranks_of_gt.append(rank)

                if rank <= 5:
                    top_5_matches += 1
                if rank <= 10:
                    top_10_matches += 1

            candidate_audit.append({
                "rank": rank,
                "gap_id": cand.gap_id,
                "title": cand.title,
                "gap_priority_score": cand.gap_priority_score,
                "is_true_positive": is_match,
                "matched_gt_id": matched_gt["gt_id"] if matched_gt else None,
            })

        # Precision@5: True positives in top 5 / 5
        precision_at_5 = round(top_5_matches / min(5, max(1, len(generated_candidates))), 4)

        # Recall@10: Ground truth items retrieved in top 10 / total ground truth
        top_10_unique_gt = len({
            c["matched_gt_id"] for c in candidate_audit[:10] if c["matched_gt_id"] is not None
        })
        recall_at_10 = round(top_10_unique_gt / max(1, total_gt), 4)

        # Mean Reciprocal Rank
        mrr = round(float(np.mean([1.0 / r for r in ranks_of_gt])) if ranks_of_gt else 0.0, 4)

        # False positives and False negatives
        false_positives = [
            c for c in candidate_audit[:10] if not c["is_true_positive"]
        ]
        false_negatives = [
            gt for gt in gt_list if gt["gt_id"] not in matched_gt_ids
        ]

        result = {
            "total_ground_truth": total_gt,
            "total_generated_candidates": len(generated_candidates),
            "metrics": {
                "precision_at_5": precision_at_5,
                "recall_at_10": recall_at_10,
                "mean_reciprocal_rank": mrr,
            },
            "candidate_audit": candidate_audit[:10],
            "false_positive_count": len(false_positives),
            "false_negative_count": len(false_negatives),
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "evaluation_status": "PASSED" if precision_at_5 >= 0.60 and recall_at_10 >= 0.60 else "NEEDS_TUNING",
        }

        # Save benchmark evaluation artifact
        out_path = Path("data/evaluation/phase6_gap_benchmark.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

        logger.info(
            f"Phase 6 Benchmark Evaluation: Precision@5 = {precision_at_5:.4f}, "
            f"Recall@10 = {recall_at_10:.4f}, MRR = {mrr:.4f}"
        )
        return result
