"""Scientific Topic Modeler using Embeddings, HDBSCAN, and c-TF-IDF (Phase 4).

Implements:
- Topic discovery via BERTopic / HDBSCAN / UMAP
- Pure c-TF-IDF (Class-based TF-IDF) representative keyword extraction
- Automatic descriptive topic naming from dominant semantic terms
- Centroid-based representative document discovery with provenance
- Resilience across small datasets (N < 5), duplicate papers, and outlier handling.
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.cluster import HDBSCAN, KMeans, AgglomerativeClustering
from sklearn.decomposition import PCA, TruncatedSVD

from backend.app.core.logging import get_logger
from backend.app.nlp.topic_modeling import BaseTopicModeler
from backend.app.services.embeddings.embedding_service import (
    BaseEmbeddingService,
    get_embedding_service,
)

logger = get_logger("app.landscape.modeler")


class ScientificTopicModeler(BaseTopicModeler):
    """Modular scientific topic modeler combining dense embeddings with c-TF-IDF."""

    def __init__(
        self,
        min_cluster_size: int = 2,
        embedding_service: Optional[BaseEmbeddingService] = None,
        max_topics: int = 10,
    ):
        self.min_cluster_size = min_cluster_size
        self._embedding_service = embedding_service
        self.max_topics = max_topics

        self.documents: List[str] = []
        self.doc_metadata: List[Dict[str, Any]] = []
        self.embeddings: Optional[np.ndarray] = None
        self.labels: List[int] = []
        self.probabilities: List[float] = []
        self.topic_info: List[Dict[str, Any]] = []
        self.is_fitted: bool = False

    @property
    def embedding_service(self) -> BaseEmbeddingService:
        if self._embedding_service is None:
            self._embedding_service = get_embedding_service()
        return self._embedding_service

    def fit_transform(
        self,
        documents: List[str],
        doc_metadata: Optional[List[Dict[str, Any]]] = None,
        embeddings: Optional[np.ndarray] = None,
    ) -> Tuple[List[int], List[float]]:
        """Fit clustering model on corpus and extract topic assignments and probabilities."""
        if not documents:
            self.documents = []
            self.doc_metadata = []
            self.labels = []
            self.probabilities = []
            self.topic_info = []
            self.is_fitted = True
            return [], []

        self.documents = documents
        self.doc_metadata = doc_metadata or [{} for _ in documents]
        n_docs = len(documents)

        # 1. Obtain or generate embeddings
        if embeddings is not None:
            self.embeddings = embeddings
        else:
            self.embeddings = self.embedding_service.embed_documents(documents)

        # 2. Cluster Assignment
        if n_docs == 1:
            self.labels = [0]
            self.probabilities = [1.0]
        elif n_docs < 4:
            # Small dataset: Agglomerative clustering into 1-2 topics
            n_clusters = min(n_docs, 2)
            clusterer = AgglomerativeClustering(n_clusters=n_clusters)
            self.labels = clusterer.fit_predict(self.embeddings).tolist()
            self.probabilities = [1.0] * n_docs
        else:
            # Try HDBSCAN first
            labels, probs = self._cluster_hdbscan(self.embeddings)
            unique_labels = set(labels) - {-1}
            # Fallback to KMeans if HDBSCAN marked everything as outlier or single cluster
            if len(unique_labels) < 2 and n_docs >= 4:
                k = min(self.max_topics, max(2, n_docs // 3))
                labels, probs = self._cluster_kmeans(self.embeddings, n_clusters=k)

            self.labels = labels
            self.probabilities = probs

        # 3. Extract c-TF-IDF Representative Terms and Topic Profiles
        self._build_topic_profiles()
        self.is_fitted = True
        return self.labels, self.probabilities

    def _cluster_hdbscan(self, vectors: np.ndarray) -> Tuple[List[int], List[float]]:
        """Run HDBSCAN clustering on dense vector matrix."""
        try:
            # Dimensionality reduction with PCA if dimensions > 10 and n_docs > 5
            reduced = vectors
            if vectors.shape[0] > 6 and vectors.shape[1] > 10:
                n_comp = min(5, vectors.shape[0] - 1)
                pca = PCA(n_components=n_comp, random_state=42)
                reduced = pca.fit_transform(vectors)

            hdb = HDBSCAN(
                min_cluster_size=min(self.min_cluster_size, max(2, len(vectors) // 3)),
                metric="euclidean",
                copy=True,
            )
            labels = hdb.fit_predict(reduced).tolist()
            probs = getattr(hdb, "probabilities_", [1.0] * len(vectors)).tolist()
            return labels, [float(p) for p in probs]
        except Exception as exc:
            logger.warning(f"HDBSCAN clustering failed ({exc}). Using KMeans.")
            k = min(3, max(2, len(vectors) // 2))
            return self._cluster_kmeans(vectors, n_clusters=k)

    def _cluster_kmeans(self, vectors: np.ndarray, n_clusters: int) -> Tuple[List[int], List[float]]:
        """Run KMeans clustering fallback."""
        km = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
        labels = km.fit_predict(vectors).tolist()
        # Compute softmax probabilities based on distance to centroids
        distances = km.transform(vectors)
        probs = []
        for i, dists in enumerate(distances):
            assigned_c = labels[i]
            # Invert distance
            inv_dist = 1.0 / (1.0 + dists[assigned_c])
            probs.append(float(round(inv_dist, 4)))
        return labels, probs

    def _build_topic_profiles(self) -> None:
        """Construct c-TF-IDF keyword profiles and representative documents for each topic."""
        unique_labels = sorted(list(set(self.labels)))
        self.topic_info = []

        # Vectorizer for c-TF-IDF
        stop_words = "english"
        vec = CountVectorizer(stop_words=stop_words, ngram_range=(1, 2), max_features=5000)

        # Build class-concatenated documents
        class_docs: Dict[int, List[str]] = {lbl: [] for lbl in unique_labels}
        class_indices: Dict[int, List[int]] = {lbl: [] for lbl in unique_labels}

        for idx, lbl in enumerate(self.labels):
            class_docs[lbl].append(self.documents[idx])
            class_indices[lbl].append(idx)

        # Fit vocabulary on full corpus
        try:
            full_counts = vec.fit_transform(self.documents)
            vocab = np.array(vec.get_feature_names_out())
        except ValueError:
            vocab = np.array([])

        for lbl in unique_labels:
            doc_idx_list = class_indices[lbl]
            paper_ids = {
                self.doc_metadata[i].get("paper_id")
                for i in doc_idx_list
                if self.doc_metadata[i].get("paper_id") is not None
            }

            # Outlier topic (-1)
            if lbl == -1:
                self.topic_info.append({
                    "topic_id": -1,
                    "topic_name": "Outliers & Uncategorized",
                    "representative_terms": [{"term": "unclustered", "weight": 1.0}],
                    "representative_documents": [self.documents[i] for i in doc_idx_list[:3]],
                    "paper_count": len(paper_ids),
                    "sentence_count": len(doc_idx_list),
                    "topic_probability": 0.0,
                    "document_indices": doc_idx_list,
                })
                continue

            # Compute c-TF-IDF for cluster
            cluster_text = " ".join(class_docs[lbl])
            top_terms: List[Dict[str, Any]] = []

            if len(vocab) > 0 and cluster_text.strip():
                try:
                    c_vec = vec.transform([cluster_text]).toarray()[0]
                    # Total term frequency in class / total words
                    tf = c_vec / (np.sum(c_vec) + 1e-9)
                    # Global term frequency across all classes
                    global_f = full_counts.sum(axis=0).A1 + 1e-9
                    avg_words = np.mean([len(d.split()) for d in self.documents]) + 1.0
                    idf = np.log(1.0 + (avg_words / global_f))
                    c_tfidf = tf * idf

                    top_indices = np.argsort(c_tfidf)[::-1][:6]
                    for t_idx in top_indices:
                        if c_tfidf[t_idx] > 0:
                            top_terms.append({
                                "term": str(vocab[t_idx]),
                                "weight": float(round(c_tfidf[t_idx], 4)),
                            })
                except Exception as exc:
                    logger.debug(f"c-TF-IDF calculation fallback for topic {lbl}: {exc}")

            if not top_terms:
                top_terms = [{"term": f"scientific_theme_{lbl}", "weight": 1.0}]

            # Derive human-readable topic name from top 2-3 terms
            primary_words = [t["term"] for t in top_terms[:3] if len(t["term"]) > 2]
            if primary_words:
                title_name = " & ".join([w.title() for w in primary_words[:2]])
                topic_name = f"Topic {lbl}: {title_name}"
            else:
                topic_name = f"Topic {lbl}: Scientific Exploration"

            # Identify representative documents (nearest to cluster centroid)
            cluster_embs = self.embeddings[doc_idx_list]
            centroid = np.mean(cluster_embs, axis=0)
            norms = np.linalg.norm(cluster_embs, axis=1) * np.linalg.norm(centroid)
            norms[norms == 0] = 1.0
            similarities = np.dot(cluster_embs, centroid) / norms
            top_doc_order = np.argsort(similarities)[::-1]

            rep_docs = [self.documents[doc_idx_list[i]] for i in top_doc_order[:3]]

            # Average cluster probability
            avg_prob = float(np.mean([self.probabilities[i] for i in doc_idx_list]))

            self.topic_info.append({
                "topic_id": lbl,
                "topic_name": topic_name,
                "representative_terms": top_terms,
                "representative_documents": rep_docs,
                "paper_count": len(paper_ids) if paper_ids else len(doc_idx_list),
                "sentence_count": len(doc_idx_list),
                "topic_probability": round(avg_prob, 4),
                "document_indices": doc_idx_list,
            })

    def get_topic_info(self) -> List[Dict[str, Any]]:
        """Return discovered topic clusters with representative terms and frequencies."""
        return self.topic_info


# Global singleton
_topic_modeler_instance: Optional[ScientificTopicModeler] = None


def get_topic_modeler() -> ScientificTopicModeler:
    """Retrieve global ScientificTopicModeler singleton."""
    global _topic_modeler_instance
    if _topic_modeler_instance is None:
        _topic_modeler_instance = ScientificTopicModeler()
    return _topic_modeler_instance
