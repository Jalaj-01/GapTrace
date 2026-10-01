"""TF-IDF Retrieval Baseline Service (Phase 3).

Implements statistical retrieval baseline using scikit-learn's TfidfVectorizer.
Supports incremental re-fitting, vocabulary preservation, multi-field metadata filtering,
and full scientific provenance mapping identical to dense semantic search.
"""

from typing import Any, Dict, List, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.app.core.logging import get_logger
from backend.app.core.errors import ValidationError

logger = get_logger("app.retrieval.tfidf")


class TFIDFSearchService:
    """Statistical term-frequency baseline search engine."""

    def __init__(
        self,
        ngram_range: tuple = (1, 2),
        max_features: int = 25000,
        sublinear_tf: bool = True,
    ):
        self.ngram_range = ngram_range
        self.max_features = max_features
        self.sublinear_tf = sublinear_tf

        self.vectorizer = TfidfVectorizer(
            ngram_range=self.ngram_range,
            max_features=self.max_features,
            sublinear_tf=self.sublinear_tf,
            stop_words="english",
        )
        self.tfidf_matrix = None
        self.corpus_texts: List[str] = []
        self.metadata_records: List[Dict[str, Any]] = []
        self.is_fitted: bool = False

    @property
    def total_documents(self) -> int:
        return len(self.metadata_records)

    def fit_corpus(self, texts: List[str], metadata_list: List[Dict[str, Any]]) -> None:
        """Fit vectorizer on text corpus and build document TF-IDF matrix."""
        if not texts:
            self.corpus_texts = []
            self.metadata_records = []
            self.tfidf_matrix = None
            self.is_fitted = False
            return

        if len(texts) != len(metadata_list):
            raise ValidationError(
                f"Length mismatch: {len(texts)} texts vs {len(metadata_list)} metadata items."
            )

        self.corpus_texts = [str(t).strip() for t in texts]
        self.metadata_records = [dict(m) for m in metadata_list]

        # Filter out empty texts for vectorizer
        valid_indices = [i for i, t in enumerate(self.corpus_texts) if len(t) > 0]
        if not valid_indices:
            self.tfidf_matrix = None
            self.is_fitted = False
            return

        try:
            self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus_texts)
            self.is_fitted = True
            logger.info(
                f"Fitted TF-IDF baseline on {len(self.corpus_texts)} items. "
                f"Vocabulary size: {len(self.vectorizer.vocabulary_)}"
            )
        except ValueError as err:
            logger.warning(f"TF-IDF fitting empty vocabulary: {err}")
            self.is_fitted = False

    def add_documents(self, new_texts: List[str], new_metadata: List[Dict[str, Any]]) -> None:
        """Add new documents and refit TF-IDF matrix."""
        if not new_texts:
            return
        combined_texts = self.corpus_texts + new_texts
        combined_meta = self.metadata_records + new_metadata
        self.fit_corpus(combined_texts, combined_meta)

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Query TF-IDF matrix using cosine similarity with optional metadata filtering."""
        if not query or not query.strip():
            raise ValidationError("Search query cannot be empty or whitespace only.")

        if not self.is_fitted or self.tfidf_matrix is None or self.total_documents == 0:
            return []

        clean_query = query.strip()
        try:
            query_vec = self.vectorizer.transform([clean_query])
        except Exception as exc:
            logger.warning(f"Error vectorizing query '{clean_query}': {exc}")
            return []

        # Cosine similarities: shape (1, num_docs)
        sim_scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        # Sort indices descending
        ranked_indices = np.argsort(sim_scores)[::-1]

        results: List[Dict[str, Any]] = []
        for idx in ranked_indices:
            score = float(sim_scores[idx])
            # Minimum similarity threshold for relevance
            if score <= 0.0:
                break

            meta = self.metadata_records[idx]
            if not self._matches_filters(meta, filters):
                continue

            results.append({
                "faiss_id": idx,
                "similarity_score": round(score, 4),
                "metadata": meta,
            })

            if len(results) >= top_k:
                break

        return results

    def _matches_filters(self, metadata: Dict[str, Any], filters: Optional[Dict[str, Any]]) -> bool:
        """Evaluate if metadata satisfies query filters."""
        if not filters:
            return True

        if "paper_id" in filters and filters["paper_id"] is not None:
            if int(metadata.get("paper_id", -1)) != int(filters["paper_id"]):
                return False

        if "extraction_type" in filters and filters["extraction_type"] is not None:
            target_type = str(filters["extraction_type"]).strip().upper()
            curr_type = str(metadata.get("extraction_type", "")).strip().upper()
            if target_type != curr_type:
                return False

        if "section" in filters and filters["section"] is not None:
            target_sec = str(filters["section"]).strip().lower()
            curr_sec = str(metadata.get("section", "")).strip().lower()
            if target_sec not in curr_sec:
                return False

        meta_year = metadata.get("year")
        if "year" in filters and filters["year"] is not None:
            if meta_year is None or int(meta_year) != int(filters["year"]):
                return False

        if "min_year" in filters and filters["min_year"] is not None:
            if meta_year is None or int(meta_year) < int(filters["min_year"]):
                return False

        if "max_year" in filters and filters["max_year"] is not None:
            if meta_year is None or int(meta_year) > int(filters["max_year"]):
                return False

        return True


# Singleton instance
_tfidf_search_service: Optional[TFIDFSearchService] = None


def get_tfidf_search_service() -> TFIDFSearchService:
    """Retrieve global TFIDFSearchService singleton."""
    global _tfidf_search_service
    if _tfidf_search_service is None:
        _tfidf_search_service = TFIDFSearchService()
    return _tfidf_search_service
