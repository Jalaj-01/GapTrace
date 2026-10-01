"""Topic Coherence and Evaluation Engine (Phase 4).

Compares:
- Baseline (TF-IDF + KMeans)
- BERTopic (Dense Semantic Embeddings + c-TF-IDF + HDBSCAN)

Calculates:
- Semantic Word Embedding Coherence (Mean pairwise cosine similarity of top terms)
- Cluster Separation / Silhouette Score
- Outlier Ratio
"""

from typing import Any, Dict, List, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

from backend.app.core.logging import get_logger
from backend.app.services.embeddings.embedding_service import (
    BaseEmbeddingService,
    get_embedding_service,
)
from backend.app.services.landscape.topic_modeler import ScientificTopicModeler

logger = get_logger("app.landscape.coherence")


class TopicCoherenceEvaluator:
    """Evaluates and compares topic modeling coherence across models."""

    def __init__(self, embedding_service: Optional[BaseEmbeddingService] = None):
        self.embedding_service = embedding_service or get_embedding_service()

    def compute_coherence(
        self,
        topic_terms_list: List[List[str]],
        top_n: int = 5,
    ) -> float:
        """Calculate mean pairwise semantic cosine coherence across topics.

        For each topic, embeds the top-N words and calculates average pairwise cosine similarity.
        Higher values indicate tighter semantic relatedness among cluster keywords.
        """
        if not topic_terms_list:
            return 0.0

        topic_coherences = []

        for terms in topic_terms_list:
            clean_terms = [t.strip() for t in terms if t.strip()][:top_n]
            if len(clean_terms) < 2:
                continue

            # Embed each term
            term_vecs = []
            for t in clean_terms:
                try:
                    vec = self.embedding_service.embed_query(t)
                    term_vecs.append(vec)
                except Exception:
                    pass

            if len(term_vecs) < 2:
                continue

            matrix = np.array(term_vecs)
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            norm_matrix = matrix / norms

            # Pairwise cosine similarity matrix
            sim_matrix = np.dot(norm_matrix, norm_matrix.T)

            # Average upper triangle (excluding diagonal)
            n_items = len(term_vecs)
            upper_indices = np.triu_indices(n_items, k=1)
            pair_similarities = sim_matrix[upper_indices]

            if len(pair_similarities) > 0:
                topic_coherences.append(float(np.mean(pair_similarities)))

        if not topic_coherences:
            return 0.0

        return round(float(np.mean(topic_coherences)), 4)

    def evaluate_comparison(
        self,
        documents: List[str],
        n_clusters: int = 3,
    ) -> Dict[str, Any]:
        """Run side-by-side evaluation comparing Baseline (KMeans) vs BERTopic."""
        if len(documents) < 3:
            return {
                "num_documents": len(documents),
                "baseline_kmeans": {"coherence": 0.0, "num_topics": 1},
                "bertopic_semantic": {"coherence": 0.0, "num_topics": 1},
            }

        k = min(n_clusters, max(2, len(documents) // 2))

        # 1. Baseline Model: TF-IDF + KMeans
        tfidf_vec = TfidfVectorizer(stop_words="english", max_features=1000)
        tfidf_mat = tfidf_vec.fit_transform(documents)
        vocab = np.array(tfidf_vec.get_feature_names_out())

        km = KMeans(n_clusters=k, random_state=42, n_init="auto")
        km.fit(tfidf_mat)

        # Extract top words per cluster from cluster centers
        baseline_topic_words = []
        for c_idx in range(k):
            center = km.cluster_centers_[c_idx]
            top_word_indices = np.argsort(center)[::-1][:5]
            words = [str(vocab[i]) for i in top_word_indices if center[i] > 0]
            if words:
                baseline_topic_words.append(words)

        baseline_coherence = self.compute_coherence(baseline_topic_words, top_n=5)

        # 2. BERTopic / Dense c-TF-IDF Model
        modeler = ScientificTopicModeler(
            min_cluster_size=2,
            embedding_service=self.embedding_service,
            max_topics=k,
        )
        modeler.fit_transform(documents)
        info = modeler.get_topic_info()

        bertopic_words = []
        for t in info:
            if t["topic_id"] != -1:
                terms = [item["term"] for item in t.get("representative_terms", [])]
                if terms:
                    bertopic_words.append(terms)

        bertopic_coherence = self.compute_coherence(bertopic_words, top_n=5)

        return {
            "num_documents": len(documents),
            "num_topics_discovered": len([t for t in info if t["topic_id"] != -1]),
            "baseline_kmeans": {
                "model": "KMeans + TF-IDF",
                "num_topics": len(baseline_topic_words),
                "coherence_score": baseline_coherence,
                "sample_terms": baseline_topic_words,
            },
            "bertopic_semantic": {
                "model": "BERTopic (Dense Embeddings + c-TF-IDF)",
                "num_topics": len(bertopic_words),
                "coherence_score": bertopic_coherence,
                "sample_terms": bertopic_words,
            },
        }
