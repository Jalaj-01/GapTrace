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
    """BERTopic & c-TF-IDF scientific topic modeling implementation (Phase 4)."""

    def __init__(self, embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.embedding_model = embedding_model
        from backend.app.services.landscape.topic_modeler import ScientificTopicModeler
        self._modeler = ScientificTopicModeler()

    def fit_transform(self, documents: List[str]) -> Tuple[List[int], List[float]]:
        return self._modeler.fit_transform(documents)

    def get_topic_info(self) -> List[Dict[str, Any]]:
        return self._modeler.get_topic_info()
