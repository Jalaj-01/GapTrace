"""Research Knowledge Graph API Endpoints (Phase 5).

Exposes:
- GET  /api/v1/graph/overview
- POST /api/v1/graph/build
- GET  /api/v1/graph/paper/{paper_id}
- GET  /api/v1/graph/limitation/{limitation_id}
- GET  /api/v1/graph/method/{method_id}
- GET  /api/v1/graph/query
- GET  /api/v1/graph/export/cypher
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.core.errors import NotFoundError, ValidationError
from backend.app.db.session import get_db
from backend.app.models.paper import (
    GraphOverviewResponse,
    GraphQueryResponse,
    GraphSubgraphResponse,
)
from backend.app.services.graph.graph_query import GraphQueryService
from backend.app.services.graph.node_builder import NodeBuilder, NodeTypes
from backend.app.services.graph.relationship_builder import RelationTypes
from backend.app.services.graph.research_graph import (
    ResearchKnowledgeGraph,
    get_research_graph,
)

router = APIRouter()


@router.get(
    "/overview",
    response_model=GraphOverviewResponse,
    summary="Knowledge Graph Overview & Topology",
    description="Retrieve graph-wide topology metrics, total nodes, total edges, and categorical counts.",
)
def get_graph_overview_endpoint(
    db: Session = Depends(get_db),
) -> GraphOverviewResponse:
    """Retrieve full knowledge graph summary overview."""
    rkg = get_research_graph()
    if rkg.graph.number_of_nodes() == 0:
        rkg.build_from_database(db)
    return GraphOverviewResponse(**rkg.get_overview())


@router.post(
    "/build",
    response_model=GraphOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Rebuild Knowledge Graph from Ingested Papers",
    description="Synchronize the in-memory directed graph with all papers, extractions, topics, and citations.",
)
def build_graph_endpoint(
    db: Session = Depends(get_db),
) -> GraphOverviewResponse:
    """Explicitly trigger full knowledge graph construction from database."""
    rkg = get_research_graph()
    res = rkg.build_from_database(db)
    return GraphOverviewResponse(**res)


@router.get(
    "/paper/{paper_id}",
    response_model=GraphSubgraphResponse,
    summary="Paper Ego-Subgraph with Provenance",
    description="Retrieve all claims, methods, datasets, findings, and citations connected to a specific paper.",
)
def get_paper_subgraph_endpoint(
    paper_id: int,
    hops: int = Query(1, ge=1, le=3, description="Expansion hops around paper node"),
    db: Session = Depends(get_db),
) -> GraphSubgraphResponse:
    """Retrieve ego-network subgraph for an ingested paper."""
    rkg = get_research_graph()
    if rkg.graph.number_of_nodes() == 0:
        rkg.build_from_database(db)

    subgraph = rkg.get_paper_subgraph(paper_id=paper_id, hops=hops)
    return GraphSubgraphResponse(**subgraph)


@router.get(
    "/limitation/{limitation_id}",
    summary="Limitation Subgraph & Provenance",
    description="Retrieve limitation details, papers limited by it, research directions, and papers addressing it.",
)
def get_limitation_graph_endpoint(
    limitation_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve a limitation node and its surrounding knowledge context."""
    rkg = get_research_graph()
    if rkg.graph.number_of_nodes() == 0:
        rkg.build_from_database(db)

    # Resolve node ID (allow raw limitation id e.g. '12' or 'limitation:1:12')
    target_nid = limitation_id
    if not rkg.graph.has_node(target_nid):
        # Search among limitation nodes
        for nid, data in rkg.graph.nodes(data=True):
            if data.get("type") == NodeTypes.LIMITATION:
                props = data.get("properties", {})
                if str(props.get("limitation_id")) == limitation_id or nid.endswith(f":{limitation_id}"):
                    target_nid = nid
                    break

    if not rkg.graph.has_node(target_nid):
        raise NotFoundError(f"Limitation node '{limitation_id}' not found in research graph.")

    node_data = rkg.graph.nodes[target_nid]
    query_svc = GraphQueryService(rkg)

    connected_papers = query_svc.papers_connected_to_candidate_limitation(limitation_id=target_nid)
    directions = query_svc.research_directions_related_to_limitation(limitation_id=target_nid)

    return {
        "node": dict(node_data),
        "papers_limited_by": connected_papers["papers_limited_by"],
        "papers_addressing": connected_papers["papers_addressing"],
        "research_directions": directions,
    }


@router.get(
    "/method/{method_id}",
    summary="Method Subgraph & Empirical Usage",
    description="Retrieve method node details, papers proposing/using/extending it, and datasets evaluated.",
)
def get_method_graph_endpoint(
    method_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve a method node and its usage in the scientific literature."""
    rkg = get_research_graph()
    if rkg.graph.number_of_nodes() == 0:
        rkg.build_from_database(db)

    target_nid = method_id
    if not rkg.graph.has_node(target_nid):
        # Try slugified or alias match
        slug = NodeBuilder.slugify(method_id)
        candidate = f"method:{slug}"
        if rkg.graph.has_node(candidate):
            target_nid = candidate
        else:
            for nid, data in rkg.graph.nodes(data=True):
                if data.get("type") == NodeTypes.METHOD:
                    if method_id.lower() in data.get("label", "").lower():
                        target_nid = nid
                        break

    if not rkg.graph.has_node(target_nid):
        raise NotFoundError(f"Method node '{method_id}' not found in research graph.")

    node_data = rkg.graph.nodes[target_nid]
    query_svc = GraphQueryService(rkg)
    extending_papers = query_svc.papers_extending_method(method_id=target_nid)

    # Find papers using or proposing this method
    using_papers = []
    proposing_papers = []
    for u, v, data in rkg.graph.in_edges(target_nid, data=True):
        p_node = rkg.graph.nodes[u]
        rel = data.get("relationship")
        entry = {
            "paper_id": p_node.get("properties", {}).get("paper_id"),
            "paper_title": p_node.get("properties", {}).get("title"),
            "confidence": data.get("confidence", 1.0),
            "evidence_text": data.get("provenance", {}).get("source_text"),
        }
        if rel == RelationTypes.PROPOSES:
            proposing_papers.append(entry)
        elif rel == RelationTypes.USES:
            using_papers.append(entry)

    return {
        "node": dict(node_data),
        "proposing_papers": proposing_papers,
        "using_papers": using_papers,
        "extending_papers": extending_papers,
    }


@router.get(
    "/query",
    response_model=GraphQueryResponse,
    summary="Targeted Research Knowledge Graph Queries",
    description="Execute any of the 8 canonical research queries (addressing_limitation, extending_method, methods_for_dataset, supporting_claims, contradicting_claims, papers_for_topic, papers_for_limitation, directions_for_limitation).",
)
def execute_graph_query_endpoint(
    query_type: str = Query(
        ...,
        description=(
            "Query mode: 'addressing_limitation', 'extending_method', 'methods_for_dataset', "
            "'supporting_claims', 'contradicting_claims', 'papers_for_topic', "
            "'papers_for_limitation', 'directions_for_limitation'"
        ),
    ),
    target_id: Optional[str] = Query(None, description="Target entity identifier or slug"),
    text: Optional[str] = Query(None, description="Free text or keyword filter"),
    topic_id: Optional[int] = Query(None, description="Topic ID for topic queries"),
    db: Session = Depends(get_db),
) -> GraphQueryResponse:
    """Execute directed scientific graph traversal query."""
    rkg = get_research_graph()
    if rkg.graph.number_of_nodes() == 0:
        rkg.build_from_database(db)

    query_svc = GraphQueryService(rkg)
    q_lower = query_type.strip().lower()
    results: List[Dict[str, Any]] = []

    if q_lower == "addressing_limitation":
        results = query_svc.papers_addressing_limitation(limitation_id=target_id, limitation_text=text)

    elif q_lower == "extending_method":
        results = query_svc.papers_extending_method(method_id=target_id, method_name=text)

    elif q_lower == "methods_for_dataset":
        results = query_svc.methods_used_for_dataset(dataset_id=target_id, dataset_name=text)

    elif q_lower == "supporting_claims":
        results = query_svc.claims_supporting_claim(claim_id=target_id, claim_text=text)

    elif q_lower == "contradicting_claims":
        results = query_svc.claims_contradicting_claim(claim_id=target_id, claim_text=text)

    elif q_lower == "papers_for_topic":
        t_id = topic_id if topic_id is not None else (int(target_id) if target_id and target_id.isdigit() else 0)
        results = query_svc.papers_connected_to_topic(topic_id=t_id)

    elif q_lower == "papers_for_limitation":
        raw_res = query_svc.papers_connected_to_candidate_limitation(limitation_id=target_id, limitation_text=text)
        results = [
            {"type": "limited_by", **item} for item in raw_res.get("papers_limited_by", [])
        ] + [
            {"type": "addresses", **item} for item in raw_res.get("papers_addressing", [])
        ]

    elif q_lower == "directions_for_limitation":
        results = query_svc.research_directions_related_to_limitation(limitation_id=target_id, limitation_text=text)

    else:
        raise ValidationError(
            f"Unsupported query_type '{query_type}'. Supported types: "
            "addressing_limitation, extending_method, methods_for_dataset, supporting_claims, "
            "contradicting_claims, papers_for_topic, papers_for_limitation, directions_for_limitation"
        )

    return GraphQueryResponse(
        query_type=q_lower,
        parameters={"target_id": target_id, "text": text, "topic_id": topic_id},
        total_results=len(results),
        results=results,
    )


@router.get(
    "/export/cypher",
    summary="Export Graph as Cypher Statements",
    description="Generates Neo4j / Memgraph Cypher ingestion statements for graph database migration.",
)
def export_cypher_endpoint(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Export graph as Cypher query statements."""
    rkg = get_research_graph()
    if rkg.graph.number_of_nodes() == 0:
        rkg.build_from_database(db)

    statements = rkg.export_cypher()
    return {
        "statement_count": len(statements),
        "target_database": "Neo4j / Memgraph",
        "statements": statements[:50],  # Return first 50 sample statements
    }
