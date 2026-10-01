"""Research Knowledge Graph Services Package (Phase 5).

Provides:
- Core ResearchKnowledgeGraph (NetworkX abstraction with graph DB readiness)
- NodeBuilder (Entity normalization, deduplication, provenance tracking)
- RelationshipBuilder (Citation, methodological, claim, and topic edge extraction)
- GraphQueryService (8 targeted scientific research graph queries)
- GraphProvenanceService (Traceability and evidence grounding)
"""

from backend.app.services.graph.research_graph import (
    ResearchKnowledgeGraph,
    get_research_graph,
)
from backend.app.services.graph.node_builder import NodeBuilder
from backend.app.services.graph.relationship_builder import RelationshipBuilder
from backend.app.services.graph.graph_query import GraphQueryService
from backend.app.services.graph.graph_provenance import GraphProvenanceService

__all__ = [
    "ResearchKnowledgeGraph",
    "get_research_graph",
    "NodeBuilder",
    "RelationshipBuilder",
    "GraphQueryService",
    "GraphProvenanceService",
]
