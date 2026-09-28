"""Citation and research graph manager using NetworkX."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List
import networkx as nx


class BaseGraphStore(ABC):
    """Abstract interface for scientific citation and topic graph representations."""

    @abstractmethod
    def add_paper_node(self, paper_id: int, metadata: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def add_citation_edge(self, source_paper_id: int, target_paper_id: int, weight: float = 1.0) -> None:
        pass

    @abstractmethod
    def get_central_papers(self, top_k: int = 10) -> List[Dict[str, Any]]:
        pass


class CitationGraphStore(BaseGraphStore):
    """NetworkX-based citation and concept co-occurrence graph."""

    def __init__(self):
        self.graph = nx.DiGraph()

    def add_paper_node(self, paper_id: int, metadata: Dict[str, Any]) -> None:
        self.graph.add_node(paper_id, **metadata)

    def add_citation_edge(self, source_paper_id: int, target_paper_id: int, weight: float = 1.0) -> None:
        self.graph.add_edge(source_paper_id, target_paper_id, weight=weight)

    def get_central_papers(self, top_k: int = 10) -> List[Dict[str, Any]]:
        if not self.graph.nodes:
            return []
        pagerank = nx.pagerank(self.graph)
        sorted_nodes = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [{"paper_id": node, "score": score, "metadata": self.graph.nodes[node]} for node, score in sorted_nodes]
