"""Retrieval Evaluation Engine (Phase 3).

Calculates standard Information Retrieval evaluation metrics:
- Precision@K (K=5, K=10)
- Recall@K (K=5, K=10)
- Mean Reciprocal Rank (MRR)

Compares dense Semantic Retrieval (Sentence Transformers + FAISS)
against statistical TF-IDF Baseline on the ground-truth scientific benchmark.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

from backend.app.core.logging import get_logger
from backend.app.services.embeddings.embedding_service import (
    BaseEmbeddingService,
    get_embedding_service,
)
from backend.app.services.retrieval.faiss_index import FAISSIndexManager
from backend.app.services.retrieval.tfidf_search import TFIDFSearchService

logger = get_logger("app.retrieval.evaluator")

DEFAULT_BENCHMARK_PATH = Path("./data/evaluation/phase3_retrieval_benchmark.json")


class RetrievalEvaluator:
    """Evaluates and compares retrieval models against scientific benchmark ground truth."""

    def __init__(
        self,
        benchmark_path: Optional[Path] = None,
        embedding_service: Optional[BaseEmbeddingService] = None,
    ):
        self.benchmark_path = Path(benchmark_path or DEFAULT_BENCHMARK_PATH)
        self.embedding_service = embedding_service or get_embedding_service()
        self.benchmark_data = self._load_benchmark()

    def _load_benchmark(self) -> Dict[str, Any]:
        if not self.benchmark_path.exists():
            raise FileNotFoundError(f"Benchmark file not found at {self.benchmark_path}")
        with open(self.benchmark_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def run_evaluation(self, k_values: List[int] = [5, 10]) -> Dict[str, Any]:
        """Run full evaluation suite across TF-IDF baseline and Semantic Retrieval."""
        corpus = self.benchmark_data.get("corpus", [])
        queries = self.benchmark_data.get("queries", [])

        if not corpus or not queries:
            raise ValueError("Corpus or queries list in benchmark is empty.")

        texts = [item["text"] for item in corpus]
        metadata_list = []
        for item in corpus:
            metadata_list.append({
                "embedding_id": f"eval-{item['id']}",
                "paper_id": item["paper_id"],
                "sentence_id": item["sentence_id"],
                "extraction_id": None,
                "section": item["section"],
                "page": item["page"],
                "extraction_type": item["extraction_type"],
                "source_text": item["text"],
                "paper_title": item["paper_title"],
                "year": item["year"],
                "provenance": {
                    "paper_id": item["paper_id"],
                    "sentence_id": item["sentence_id"],
                    "section_name": item["section"],
                    "page_number": item["page"],
                },
            })

        # 1. Setup Isolated FAISS Manager
        faiss_mgr = FAISSIndexManager(
            dimension=self.embedding_service.dimension,
            auto_load=False,
        )
        vectors = self.embedding_service.embed_documents(texts)
        faiss_mgr.add_vectors(vectors, metadata_list)

        # 2. Setup Isolated TF-IDF Baseline Service
        tfidf_svc = TFIDFSearchService()
        tfidf_svc.fit_corpus(texts, metadata_list)

        # 3. Evaluate both engines
        max_k = max(k_values)
        tfidf_metrics = self._evaluate_engine(
            engine_name="TF-IDF Baseline",
            search_fn=lambda q, k: tfidf_svc.search(q, top_k=k),
            queries=queries,
            k_values=k_values,
            max_k=max_k,
        )

        semantic_metrics = self._evaluate_engine(
            engine_name=f"Semantic Retrieval ({self.embedding_service.model_name})",
            search_fn=lambda q, k: self._semantic_search_fn(faiss_mgr, q, k),
            queries=queries,
            k_values=k_values,
            max_k=max_k,
        )

        return {
            "embedding_model": self.embedding_service.model_name,
            "embedding_dimension": self.embedding_service.dimension,
            "corpus_size": len(corpus),
            "num_queries": len(queries),
            "k_values": k_values,
            "tfidf_baseline": tfidf_metrics,
            "semantic_retrieval": semantic_metrics,
        }

    def _semantic_search_fn(
        self,
        faiss_mgr: FAISSIndexManager,
        query: str,
        k: int,
    ) -> List[Dict[str, Any]]:
        query_vec = self.embedding_service.embed_query(query)
        return faiss_mgr.search(query_vec, top_k=k)

    def _evaluate_engine(
        self,
        engine_name: str,
        search_fn,
        queries: List[Dict[str, Any]],
        k_values: List[int],
        max_k: int,
    ) -> Dict[str, Any]:
        """Compute P@K, R@K, and MRR for a retrieval function."""
        precisions_at_k: Dict[int, List[float]] = {k: [] for k in k_values}
        recalls_at_k: Dict[int, List[float]] = {k: [] for k in k_values}
        reciprocal_ranks: List[float] = []

        for q_item in queries:
            query_text = q_item["query"]
            rel_sentence_ids = set(q_item.get("relevant_sentence_ids", []))
            total_relevant = len(rel_sentence_ids)

            # Retrieve top max_k results
            raw_results = search_fn(query_text, max_k)
            retrieved_sentence_ids = [
                r.get("metadata", {}).get("sentence_id") for r in raw_results
            ]

            # Calculate MRR
            rr = 0.0
            for rank, s_id in enumerate(retrieved_sentence_ids, start=1):
                if s_id in rel_sentence_ids:
                    rr = 1.0 / rank
                    break
            reciprocal_ranks.append(rr)

            # Calculate Precision@K and Recall@K
            for k in k_values:
                top_k_ids = retrieved_sentence_ids[:k]
                rel_retrieved = sum(1 for s_id in top_k_ids if s_id in rel_sentence_ids)
                p_at_k = rel_retrieved / k if k > 0 else 0.0
                r_at_k = rel_retrieved / total_relevant if total_relevant > 0 else 0.0

                precisions_at_k[k].append(p_at_k)
                recalls_at_k[k].append(r_at_k)

        summary = {
            "mrr": round(float(np.mean(reciprocal_ranks)), 4),
        }
        for k in k_values:
            summary[f"precision@{k}"] = round(float(np.mean(precisions_at_k[k])), 4)
            summary[f"recall@{k}"] = round(float(np.mean(recalls_at_k[k])), 4)

        logger.info(f"Evaluation for {engine_name}: {summary}")
        return summary


def run_benchmark_and_print() -> Dict[str, Any]:
    """Run retrieval evaluation and print comparative benchmark table."""
    evaluator = RetrievalEvaluator()
    res = evaluator.run_evaluation(k_values=[5, 10])

    print("\n" + "=" * 70)
    print("ResearchGapX Phase 3 - Retrieval Benchmark Evaluation Results")
    print("=" * 70)
    print(f"Embedding Model:     {res['embedding_model']}")
    print(f"Embedding Dimension: {res['embedding_dimension']}")
    print(f"Corpus Size:         {res['corpus_size']} evidence units")
    print(f"Total Queries:       {res['num_queries']} annotated queries\n")

    print(f"{'Metric':<18} | {'TF-IDF Baseline':<16} | {'Semantic Retrieval':<18}")
    print("-" * 60)
    tfidf = res["tfidf_baseline"]
    sem = res["semantic_retrieval"]

    for metric in ["mrr", "precision@5", "recall@5", "precision@10", "recall@10"]:
        t_val = tfidf.get(metric, 0.0)
        s_val = sem.get(metric, 0.0)
        print(f"{metric.upper():<18} | {t_val:<16.4f} | {s_val:<18.4f}")
    print("=" * 70 + "\n")

    return res


if __name__ == "__main__":
    run_benchmark_and_print()
