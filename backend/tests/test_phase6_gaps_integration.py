"""Phase 6 Integration Test Suite: Research Gap Candidate API & Database Pipeline.

Verifies:
- End-to-end integration: Database → NLP → Graph → Research Gap Candidates
- Distinguishing 'potential_gap' from 'verified_gap'
- REST API verification for all gap endpoints:
  * GET /api/v1/gaps/candidates
  * GET /api/v1/gaps/candidates?gap_type=...
  * GET /api/v1/gaps/candidates/{id}
  * GET /api/v1/gaps/candidates/{id}/evidence
  * GET /api/v1/gaps/signals
- Strict evidence enforcement and non-hallucination guarantees.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.models.paper import (
    DiscoveredTopic,
    Paper,
    PaperSection,
    PaperTopicAssignment,
)
from backend.app.services.gaps.candidate_generator import get_gap_candidate_generator
from backend.app.services.graph.research_graph import get_research_graph
from backend.app.services.nlp.nlp_service import scientific_nlp_service


@pytest.fixture
def gap_seeded_db(db_session: Session):
    """Seed multi-paper corpus with known recurring limitation and underexplored topic."""
    # Paper 1
    p1 = Paper(
        title="Attention Scaling Bottlenecks in Scientific NLP",
        abstract="We investigate long sequence attention overhead in transformer architectures.",
        authors=["Alice Chen", "David Miller"],
        publication_year=2023,
        file_hash="hash_p1_gaps_test",
        venue="ACL",
    )
    db_session.add(p1)
    db_session.flush()

    s1 = PaperSection(
        paper_id=p1.id,
        section_name="Limitations",
        section_order=1,
        content="A primary limitation of our approach is high computational memory overhead at long context lengths.",
        paragraphs=["A primary limitation of our approach is high computational memory overhead at long context lengths."],
    )
    db_session.add(s1)
    db_session.flush()
    scientific_nlp_service.process_paper(paper_id=p1.id, db=db_session)

    # Paper 2: Also shares the memory overhead limitation
    p2 = Paper(
        title="Sparse Approximate Attention for Document Retrieval",
        abstract="Evaluating approximate sparse kernel methods on long document retrieval.",
        authors=["Bob Smith", "Eva Garcia"],
        publication_year=2024,
        file_hash="hash_p2_gaps_test",
        venue="EMNLP",
    )
    db_session.add(p2)
    db_session.flush()

    s2 = PaperSection(
        paper_id=p2.id,
        section_name="Limitations",
        section_order=1,
        content="Despite sparse approximation, high computational memory overhead remains a severe bottleneck for large sequence batches.",
        paragraphs=["Despite sparse approximation, high computational memory overhead remains a severe bottleneck for large sequence batches."],
    )
    db_session.add(s2)
    db_session.flush()
    scientific_nlp_service.process_paper(paper_id=p2.id, db=db_session)

    # Paper 3: Ingested in an underexplored standalone topic
    p3 = Paper(
        title="Clinical Multimodal Information Extraction from Rare Pathology Reports",
        abstract="We investigate multimodal representation learning for rare clinical diseases.",
        authors=["Grace Hopper"],
        publication_year=2024,
        file_hash="hash_p3_gaps_test",
        venue="JAMIA",
    )
    db_session.add(p3)
    db_session.flush()

    s3 = PaperSection(
        paper_id=p3.id,
        section_name="Introduction",
        section_order=1,
        content="Multimodal evidence extraction from rare pathology reports remains extremely challenging.",
        paragraphs=["Multimodal evidence extraction from rare pathology reports remains extremely challenging."],
    )
    db_session.add(s3)
    db_session.flush()
    scientific_nlp_service.process_paper(paper_id=p3.id, db=db_session)

    # Topic 0 (Underexplored: only 1 paper)
    t0 = DiscoveredTopic(
        topic_id=0,
        topic_name="Topic 0: Clinical Multimodal Extraction",
        representative_terms=[{"term": "pathology", "weight": 0.6}, {"term": "multimodal", "weight": 0.4}],
        paper_count=1,
        sentence_count=4,
        status="EMERGING",
    )
    db_session.add(t0)
    db_session.flush()

    assign = PaperTopicAssignment(paper_id=p3.id, topic_id=0, probability=0.95, is_outlier=False)
    db_session.add(assign)
    db_session.commit()

    return {"p1": p1, "p2": p2, "p3": p3, "topic": t0}


class TestPhase6GapsIntegration:
    """Integration test suite for Research Gap Candidate Engine and REST APIs."""

    def test_pipeline_generate_candidates_from_database(self, gap_seeded_db, db_session: Session):
        """Verify candidate discovery runs on seeded multi-paper database and detects recurring bottleneck."""
        rkg = get_research_graph()
        rkg.build_from_database(db_session)

        gen = get_gap_candidate_generator(rkg=rkg)
        candidates = gen.generate_candidates(db=db_session)

        assert len(candidates) >= 1

        # Check candidate structure and potential_gap status
        for cand in candidates:
            assert cand.verification_status == "potential_gap"
            assert cand.gap_priority_score >= 0.0
            assert cand.confidence >= 0.50
            assert len(cand.supporting_papers) >= 1
            assert len(cand.supporting_evidence) >= 1

        # Check that repeated limitation on memory overhead was discovered
        rep_candidates = [c for c in candidates if "memory" in c.title.lower() or c.gap_type == "repeated_limitation"]
        assert len(rep_candidates) >= 1
        rep_cand = rep_candidates[0]
        assert len(rep_cand.supporting_papers) >= 2

    def test_get_candidates_api(self, client: TestClient, gap_seeded_db, db_session: Session):
        """Test GET /api/v1/gaps/candidates endpoint."""
        rkg = get_research_graph()
        rkg.build_from_database(db_session)

        response = client.get("/api/v1/gaps/candidates")
        assert response.status_code == 200
        data = response.json()

        assert "total_candidates" in data
        assert "scoring_formula" in data
        assert data["potential_gaps_count"] == data["total_candidates"]
        assert data["verified_gaps_count"] == 0  # Crucial distinction
        assert isinstance(data["candidates"], list)

    def test_get_candidates_api_filtering_by_type(self, client: TestClient, gap_seeded_db, db_session: Session):
        """Test GET /api/v1/gaps/candidates with gap_type filter."""
        rkg = get_research_graph()
        rkg.build_from_database(db_session)

        response = client.get("/api/v1/gaps/candidates?gap_type=repeated_limitation")
        assert response.status_code == 200
        data = response.json()
        for cand in data["candidates"]:
            assert cand["gap_type"] == "repeated_limitation"

    def test_get_candidate_detail_and_evidence_api(self, client: TestClient, gap_seeded_db, db_session: Session):
        """Test GET /api/v1/gaps/candidates/{id} and evidence sub-endpoint."""
        rkg = get_research_graph()
        rkg.build_from_database(db_session)

        # 1. Fetch candidates list first
        list_res = client.get("/api/v1/gaps/candidates")
        assert list_res.status_code == 200
        candidates = list_res.json()["candidates"]
        assert len(candidates) >= 1

        cand_id = candidates[0]["gap_id"]

        # 2. Fetch single candidate detail
        detail_res = client.get(f"/api/v1/gaps/candidates/{cand_id}")
        assert detail_res.status_code == 200
        detail_data = detail_res.json()
        assert detail_data["gap_id"] == cand_id
        assert detail_data["verification_status"] == "potential_gap"
        assert "signal_breakdown" in detail_data
        assert len(detail_data["signal_breakdown"]) >= 1

        # 3. Fetch evidence sub-endpoint
        evid_res = client.get(f"/api/v1/gaps/candidates/{cand_id}/evidence")
        assert evid_res.status_code == 200
        evid_data = evid_res.json()
        assert isinstance(evid_data, list)
        assert len(evid_data) >= 1
        assert "source_text" in evid_data[0]

    def test_nonexistent_candidate_returns_404(self, client: TestClient):
        """Test GET /api/v1/gaps/candidates/nonexistent returns HTTP 404."""
        response = client.get("/api/v1/gaps/candidates/nonexistent-gap-999")
        assert response.status_code == 404

    def test_signals_overview_api(self, client: TestClient):
        """Test GET /api/v1/gaps/signals endpoint."""
        response = client.get("/api/v1/gaps/signals")
        assert response.status_code == 200
        data = response.json()

        assert data["total_signals"] == 7
        assert "underexploration" in data["signal_definitions"]
        assert "repeated_limitations" in data["signal_definitions"]
        assert "weights" in data
        assert "scoring_formula" in data
        assert round(sum(data["weights"].values()), 2) == 1.00
