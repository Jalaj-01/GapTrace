"""Integration Tests for Phase 4: Research Landscape and Topic Discovery Pipeline.

Verifies:
- End-to-end paper corpus topic discovery and persistence
- Database model integrity: DiscoveredTopic and PaperTopicAssignment
- Trajectory classifications (major, emerging, declining, persistent, outliers)
- REST API Endpoints:
  * POST /api/v1/topics/discover
  * GET  /api/v1/topics
  * GET  /api/v1/topics/overview
  * GET  /api/v1/topics/trends
  * GET  /api/v1/topics/{topic_id}
  * GET  /api/v1/topics/{topic_id}/trends
  * GET  /api/v1/topics/{topic_id}/papers
  * GET  /api/v1/topics/{topic_id}/evidence
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.paper import (
    DiscoveredTopic,
    Paper,
    PaperSection,
    PaperTopicAssignment,
)
from backend.app.services.landscape.landscape_service import get_landscape_service


class TestPhase4LandscapePipeline:
    """Verifies end-to-end landscape discovery pipeline and database persistence."""

    @pytest.fixture
    def seeded_papers(self, db_session: Session) -> list[Paper]:
        p1 = Paper(
            title="Domain Adaptation in Low-Resource Scientific NLP",
            file_hash="phase4_p1_hash",
            abstract="Investigates domain adaptation and out-of-distribution transfer learning.",
            publication_year=2024,
        )
        p2 = Paper(
            title="Adversarial Feature Alignment for Cross-Domain Classification",
            file_hash="phase4_p2_hash",
            abstract="Adversarial alignment for cross-domain representation learning in NLP.",
            publication_year=2025,
        )
        p3 = Paper(
            title="Efficient Attention Mechanisms for Long Contexts",
            file_hash="phase4_p3_hash",
            abstract="FlashAttention and quadratic computational overhead mitigation in transformers.",
            publication_year=2022,
        )
        p4 = Paper(
            title="Linear Attention with State Space Models",
            file_hash="phase4_p4_hash",
            abstract="Memory efficient sequence modeling replacing quadratic self-attention.",
            publication_year=2023,
        )
        p5 = Paper(
            title="Clinical Vision-Language Multimodal Data Mining",
            file_hash="phase4_p5_hash",
            abstract="Mitigating clinical medical imaging dataset scarcity through semi-supervised learning.",
            publication_year=2024,
        )
        papers = [p1, p2, p3, p4, p5]
        db_session.add_all(papers)
        db_session.commit()
        for p in papers:
            db_session.refresh(p)
        return papers

    def test_landscape_discovery_pipeline(self, db_session: Session, seeded_papers: list[Paper]):
        service = get_landscape_service()
        overview = service.discover_landscape(db=db_session, min_cluster_size=2)

        assert overview.total_papers_analyzed == 5
        assert overview.total_topics >= 2
        assert len(overview.all_topics) >= 2

        # Check DB tables
        db_topics = db_session.query(DiscoveredTopic).all()
        assert len(db_topics) == overview.total_topics

        db_assignments = db_session.query(PaperTopicAssignment).all()
        assert len(db_assignments) == 5

        for a in db_assignments:
            assert a.paper_id in [p.id for p in seeded_papers]
            assert a.probability > 0.0


class TestPhase4APISuite:
    """Verifies REST endpoints for Phase 4 landscape & topics."""

    @pytest.fixture
    def populated_db(self, client: TestClient, db_session: Session):
        # Insert papers and trigger discovery
        p1 = Paper(
            title="Contrastive Learning on Citation Graphs",
            file_hash="p4_api_p1",
            abstract="Graph contrastive learning with negative sampling strategies.",
            publication_year=2023,
        )
        p2 = Paper(
            title="Hard Negative Mining in Bibliometric Networks",
            file_hash="p4_api_p2",
            abstract="Addressing homophily in citation graph representation learning.",
            publication_year=2024,
        )
        p3 = Paper(
            title="Evaluation Metric Bias in Abstractive Summarization",
            file_hash="p4_api_p3",
            abstract="Factual hallucination detection beyond ROUGE lexical overlap.",
            publication_year=2022,
        )
        p4 = Paper(
            title="Factuality Verification in Scientific NLP",
            file_hash="p4_api_p4",
            abstract="Decomposing generated summaries into atomic entailing claims.",
            publication_year=2024,
        )
        db_session.add_all([p1, p2, p3, p4])
        db_session.commit()

        # Run discovery
        get_landscape_service().discover_landscape(db_session)

    def test_discover_endpoint(self, client: TestClient, populated_db):
        resp = client.post("/api/v1/topics/discover?min_cluster_size=2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_papers_analyzed"] == 4
        assert data["total_topics"] >= 1
        assert "major_topics" in data
        assert "emerging_topics" in data

    def test_list_topics_endpoint(self, client: TestClient, populated_db):
        resp = client.get("/api/v1/topics")
        assert resp.status_code == 200
        topics = resp.json()
        assert isinstance(topics, list)
        assert len(topics) >= 1
        first = topics[0]
        assert "topic_id" in first
        assert "topic_name" in first
        assert "representative_terms" in first
        assert "status" in first

    def test_overview_endpoint(self, client: TestClient, populated_db):
        resp = client.get("/api/v1/topics/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert "all_topics" in data
        assert "total_papers_analyzed" in data

    def test_topic_trends_endpoint(self, client: TestClient, populated_db):
        resp = client.get("/api/v1/topics/trends")
        assert resp.status_code == 200
        trends = resp.json()
        assert isinstance(trends, list)
        assert len(trends) >= 1
        assert "trends" in trends[0]

    def test_topic_detail_endpoint(self, client: TestClient, populated_db):
        # First list topics to get valid ID
        list_resp = client.get("/api/v1/topics")
        first_topic = list_resp.json()[0]
        t_id = first_topic["topic_id"]

        resp = client.get(f"/api/v1/topics/{t_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["topic_id"] == t_id
        assert "papers" in data
        assert "trends" in data
        assert "representative_terms" in data

    def test_topic_papers_and_evidence_endpoints(self, client: TestClient, populated_db):
        list_resp = client.get("/api/v1/topics")
        t_id = list_resp.json()[0]["topic_id"]

        # 1. Papers
        p_resp = client.get(f"/api/v1/topics/{t_id}/papers")
        assert p_resp.status_code == 200
        papers = p_resp.json()
        assert isinstance(papers, list)
        assert len(papers) >= 1

        # 2. Evidence
        e_resp = client.get(f"/api/v1/topics/{t_id}/evidence")
        assert e_resp.status_code == 200
        evidence = e_resp.json()
        assert isinstance(evidence, list)

    def test_topic_not_found_404(self, client: TestClient, populated_db):
        resp = client.get("/api/v1/topics/999999")
        assert resp.status_code == 404
