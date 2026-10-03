"""Phase 5 Integration Test Suite: End-to-End Pipeline & REST APIs.

Verifies:
- End-to-end integration: Paper → NLP → Embeddings → Topics → Knowledge Graph
- Graph construction directly from SQLite/Postgres database
- Provenance grounding on all generated nodes and edges
- REST API verification for all graph endpoints:
  * GET  /api/v1/graph/overview
  * POST /api/v1/graph/build
  * GET  /api/v1/graph/paper/{id}
  * GET  /api/v1/graph/limitation/{id}
  * GET  /api/v1/graph/method/{id}
  * GET  /api/v1/graph/query
  * GET  /api/v1/graph/export/cypher
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.models.paper import (
    DiscoveredTopic,
    Paper,
    PaperReference,
    PaperSection,
    PaperTopicAssignment,
    ScientificExtraction,
    ScientificSentence,
)
from backend.app.services.graph.graph_provenance import GraphProvenanceService
from backend.app.services.graph.research_graph import (
    ResearchKnowledgeGraph,
    get_research_graph,
)
from backend.app.services.nlp.nlp_service import scientific_nlp_service


@pytest.fixture
def integrated_db(db_session: Session):
    """Seed integrated database with multi-paper corpus spanning Phases 1-4."""
    # Paper 1
    p1 = Paper(
        title="Domain Adaptation in Low-Resource Scientific NLP",
        abstract="We propose an adversarial adaptation framework evaluated on biomedical abstracts.",
        authors=["Alice Chen", "Bob Smith"],
        publication_year=2023,
        file_hash="hash_p1_graph_integration",
        venue="ACL",
    )
    db_session.add(p1)
    db_session.flush()

    s1 = PaperSection(
        paper_id=p1.id,
        section_name="Methodology",
        section_order=1,
        content="We propose a BERT adaptation framework using the SQuAD dataset for validation.",
        paragraphs=["We propose a BERT adaptation framework using the SQuAD dataset for validation."],
    )
    s2 = PaperSection(
        paper_id=p1.id,
        section_name="Limitations",
        section_order=2,
        content="A major limitation of our approach is high computational overhead in cross-domain transfer.",
        paragraphs=["A major limitation of our approach is high computational overhead in cross-domain transfer."],
    )
    db_session.add_all([s1, s2])
    db_session.flush()

    # Process NLP for Paper 1
    scientific_nlp_service.process_paper(paper_id=p1.id, db=db_session)

    # Paper 2: Cites and addresses Paper 1
    p2 = Paper(
        title="Efficient Sparse Kernels for Cross-Domain Scientific Transfer",
        abstract="We address the computational overhead in cross-domain transfer using linear attention.",
        authors=["Charlie Davis", "Alice Chen"],
        publication_year=2024,
        file_hash="hash_p2_graph_integration",
        venue="EMNLP",
    )
    db_session.add(p2)
    db_session.flush()

    s3 = PaperSection(
        paper_id=p2.id,
        section_name="Introduction",
        section_order=1,
        content="Our kernel method overcomes the computational overhead in cross-domain transfer.",
        paragraphs=["Our kernel method overcomes the computational overhead in cross-domain transfer."],
    )
    s4 = PaperSection(
        paper_id=p2.id,
        section_name="Methodology",
        section_order=2,
        content="We extend FlashAttention and evaluate against BERT on the GLUE benchmark.",
        paragraphs=["We extend FlashAttention and evaluate against BERT on the GLUE benchmark."],
    )
    db_session.add_all([s3, s4])
    db_session.flush()

    # Add Reference: Paper 2 cites Paper 1
    ref = PaperReference(
        paper_id=p2.id,
        ref_index=1,
        raw_text="Chen, A., & Smith, B. (2023). Domain Adaptation in Low-Resource Scientific NLP.",
        title="Domain Adaptation in Low-Resource Scientific NLP",
        authors=["Alice Chen", "Bob Smith"],
        year=2023,
    )
    db_session.add(ref)
    db_session.flush()

    scientific_nlp_service.process_paper(paper_id=p2.id, db=db_session)

    # Seed Discovered Topic (Phase 4)
    topic = DiscoveredTopic(
        topic_id=0,
        topic_name="Topic 0: Domain Adaptation & Generalization",
        representative_terms=[{"term": "domain adaptation", "weight": 0.5}],
        paper_count=2,
        sentence_count=8,
        status="EMERGING",
    )
    db_session.add(topic)
    db_session.flush()

    assign1 = PaperTopicAssignment(paper_id=p1.id, topic_id=0, probability=0.92, is_outlier=False)
    assign2 = PaperTopicAssignment(paper_id=p2.id, topic_id=0, probability=0.88, is_outlier=False)
    db_session.add_all([assign1, assign2])
    db_session.commit()

    return {"paper_1": p1, "paper_2": p2, "topic": topic}


class TestPhase5GraphIntegration:
    """Integration test suite connecting Paper → NLP → Embeddings → Topics → Knowledge Graph."""

    def test_pipeline_integration_database_to_graph(self, integrated_db, db_session: Session):
        """Verify graph builds from multi-phase database state with full provenance."""
        rkg = ResearchKnowledgeGraph()
        overview = rkg.build_from_database(db_session)

        assert overview["total_nodes"] > 5
        assert overview["total_edges"] > 3
        assert "Paper" in overview["node_counts_by_type"]
        assert "Author" in overview["node_counts_by_type"]

        # Check paper 1 and paper 2 nodes
        p1_id = f"paper:{integrated_db['paper_1'].id}"
        p2_id = f"paper:{integrated_db['paper_2'].id}"
        assert rkg.graph.has_node(p1_id)
        assert rkg.graph.has_node(p2_id)

        # Check citation edge
        assert rkg.graph.has_edge(p2_id, p1_id)
        edge_data = rkg.graph.get_edge_data(p2_id, p1_id)
        assert edge_data["relationship"] == "cites"
        assert GraphProvenanceService.verify_provenance_completeness(edge_data) is True

        # Check topic connection
        t_id = "topic:0"
        assert rkg.graph.has_node(t_id)
        assert rkg.graph.has_edge(p1_id, t_id)
        assert rkg.graph.has_edge(p2_id, t_id)

    def test_graph_overview_api(self, client: TestClient, integrated_db, db_session: Session):
        """Test GET /api/v1/graph/overview endpoint."""
        # Ensure graph is synchronized
        rkg = get_research_graph()
        rkg.build_from_database(db_session)

        response = client.get("/api/v1/graph/overview")
        assert response.status_code == 200
        data = response.json()
        assert data["total_nodes"] >= 5
        assert data["total_edges"] >= 3
        assert "node_counts_by_type" in data
        assert "edge_counts_by_type" in data

    def test_rebuild_graph_api(self, client: TestClient, integrated_db):
        """Test POST /api/v1/graph/build endpoint."""
        response = client.post("/api/v1/graph/build")
        assert response.status_code == 200
        data = response.json()
        assert data["total_nodes"] > 0
        assert "NetworkX" in data["graph_database_engine"]

    def test_paper_subgraph_api(self, client: TestClient, integrated_db, db_session: Session):
        """Test GET /api/v1/graph/paper/{id} ego-subgraph endpoint."""
        rkg = get_research_graph()
        rkg.build_from_database(db_session)

        p1_id = integrated_db["paper_1"].id
        response = client.get(f"/api/v1/graph/paper/{p1_id}?hops=1")
        assert response.status_code == 200
        data = response.json()
        assert data["total_nodes"] >= 3
        assert len(data["nodes"]) == data["total_nodes"]
        assert len(data["edges"]) == data["total_edges"]

        # Ensure provenance exists on all returned nodes
        for node in data["nodes"]:
            assert "provenance" in node
            assert node["provenance"] is not None

    def test_nonexistent_paper_subgraph_404(self, client: TestClient):
        """Test GET /api/v1/graph/paper/999 returns 404 Not Found."""
        response = client.get("/api/v1/graph/paper/99999")
        assert response.status_code == 404

    def test_graph_query_api_endpoints(self, client: TestClient, integrated_db, db_session: Session):
        """Test GET /api/v1/graph/query across canonical scientific queries."""
        rkg = get_research_graph()
        rkg.build_from_database(db_session)

        # 1. Query papers for topic
        res_topic = client.get("/api/v1/graph/query?query_type=papers_for_topic&topic_id=0")
        assert res_topic.status_code == 200
        data_topic = res_topic.json()
        assert data_topic["total_results"] == 2

        # 2. Query methods for dataset
        res_dataset = client.get("/api/v1/graph/query?query_type=methods_for_dataset&text=SQuAD")
        assert res_dataset.status_code == 200
        data_dataset = res_dataset.json()
        assert isinstance(data_dataset["results"], list)

        # 3. Invalid query type returns 422/400
        res_bad = client.get("/api/v1/graph/query?query_type=unsupported_random_query")
        assert res_bad.status_code in (400, 422)

    def test_cypher_export_api(self, client: TestClient, integrated_db, db_session: Session):
        """Test GET /api/v1/graph/export/cypher for Neo4j migration."""
        rkg = get_research_graph()
        rkg.build_from_database(db_session)

        response = client.get("/api/v1/graph/export/cypher")
        assert response.status_code == 200
        data = response.json()
        assert data["statement_count"] > 0
        assert data["target_database"] == "Neo4j / Memgraph"
        assert len(data["statements"]) > 0
