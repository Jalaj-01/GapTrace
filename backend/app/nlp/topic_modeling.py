"""Topic modeling and emerging theme detection interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple


class BaseTopicModeler(ABC):
    """Abstract interface for clustering scientific papers and finding themes (BERTopic/HDBSCAN)."""

    @abstractmethod
    def fit_transform(self, documents: List[str]) -> Tuple[List[int], List[float]]:
        """Fit topic model on corpus and return (topics, probabilities)."""
        pass

    @abstractmethod
    def get_topic_info(self) -> List[Dict[str, Any]]:
        """Return discovered topic clusters with representative terms and frequencies."""
        pass


class TopicModeler(BaseTopicModeler):
    """BERTopic topic modeling stub for Phase 1."""

    def __init__(self, embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.embedding_model = embedding_model

    def fit_transform(self, documents: List[str]) -> Tuple[List[int], List[float]]:
        raise NotImplementedError("Topic modeling pipeline will be implemented in Phase 1.")

    def get_topic_info(self) -> List[Dict[str, Any]]:
        raise NotImplementedError("Topic info extraction will be implemented in Phase 1.")
