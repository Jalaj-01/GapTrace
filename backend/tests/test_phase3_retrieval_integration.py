"""Integration Tests for Phase 3: Semantic Representation and Evidence Retrieval Pipeline.

Verifies end-to-end integration:
Paper Ingestion -> NLP Extraction -> Embedding Generation -> FAISS Indexing ->
Semantic Search -> Provenance Verification.

Also tests:
- GET /api/v1/search/semantic
- GET /api/v1/evidence/search (semantic and tfidf baseline)
- POST /api/v1/evidence/embed/{paper_id}
- POST /api/v1/evidence/batch-embed
- GET /api/v1/evidence/stats
- Metadata filters and provenance preservation
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.paper import (
    Paper,
    PaperSection,
    ScientificSentence,
    ScientificExtraction,
    EvidenceEmbedding,
)
from backend.app.services.nlp.nlp_service import scientific_nlp_service
from backend.app.services.retrieval.evidence_retriever import get_evidence_retriever_service


class TestPhase3EndToEndPipeline:
    """Verifies complete chain from Paper to semantic evidence search."""

    @pytest.fixture
    def sample_paper(self, db_session: Session) -> Paper:
        paper = Paper(
            title="Adversarial Adaptation in Cross-Domain Scientific NLP",
            file_hash="phase3_test_hash_001",
            abstract="We investigate cross-domain generalization limitations in scientific text classification.",
            authors=["Jane Doe", "Alan Turing"],
            publication_year=2024,
            venue="ACL 2024",
        )
        db_session.add(paper)
        db_session.flush()

        sec1 = PaperSection(
            paper_id=paper.id,
            section_name="Introduction",
            section_order=1,
            page_start=1,
            page_end=1,
            content="Cross-domain transfer remains an open problem in modern natural language processing.",
            paragraphs=["Cross-domain transfer remains an open problem in modern natural language processing."],
        )
        sec2 = PaperSection(
            paper_id=paper.id,
            section_name="Limitations",
            section_order=2,
            page_start=2,
            page_end=2,
            content="A primary limitation of our approach is severe sensitivity to target domain shift and high computational overhead.",
            paragraphs=["A primary limitation of our approach is severe sensitivity to target domain shift and high computational overhead."],
        )
        sec3 = PaperSection(
            paper_id=paper.id,
            section_name="Methods",
            section_order=3,
            page_start=3,
            page_end=3,
            content="We propose FactoFormer, a factored self-attention architecture for low-resource transfer.",
            paragraphs=["We propose FactoFormer, a factored self-attention architecture for low-resource transfer."],
        )
        db_session.add_all([sec1, sec2, sec3])
        db_session.commit()
        db_session.refresh(paper)
        return paper

    def test_pipeline_nlp_to_embeddings_to_search(self, db_session: Session, sample_paper: Paper):
        # 1. Trigger NLP extraction pipeline
        nlp_res = scientific_nlp_service.process_paper(sample_paper.id, db_session)
        assert nlp_res.total_sentences > 0
        assert nlp_res.provenance_verified is True

        # 2. Trigger embedding generation and FAISS ingestion
        retriever = get_evidence_retriever_service()
        emb_res = retriever.embed_paper_evidence(sample_paper.id, db_session)
        assert emb_res["embeddings_created"] > 0
        assert emb_res["index_total_vectors"] > 0

        # Verify database records
        db_embs = db_session.query(EvidenceEmbedding).filter(EvidenceEmbedding.paper_id == sample_paper.id).all()
        assert len(db_embs) == emb_res["embeddings_created"]
        for emb in db_embs:
            assert emb.embedding_id is not None
            assert emb.paper_id == sample_paper.id
            assert emb.source_text is not None
            assert emb.model_name is not None
            assert emb.embedding_dimension > 0
            assert "paper_id" in emb.provenance

        # 3. Perform semantic search
        search_res = retriever.search_evidence(
            query="sensitivity to domain shift and computational overhead",
            method="semantic",
            top_k=3,
        )

        assert search_res["total_results"] > 0
        assert search_res["retrieval_method"] == "faiss_semantic"

        top_match = search_res["results"][0]
        # Validate full provenance structure
        assert "source_text" in top_match
        assert "similarity_score" in top_match
        assert top_match["paper"]["id"] == sample_paper.id
        assert top_match["paper"]["title"] == sample_paper.title
        assert "section" in top_match
        assert "page" in top_match
        assert "extraction_type" in top_match
        assert "provenance" in top_match
        assert top_match["provenance"]["paper_id"] == sample_paper.id
        assert top_match["provenance"]["section_name"] is not None


class TestPhase3APISuite:
    """Verifies REST endpoints for Phase 3 retrieval layer."""

    @pytest.fixture
    def seeded_paper_id(self, client: TestClient, db_session: Session) -> int:
        paper = Paper(
            title="FactoFormer: Efficient Self-Attention Representation",
            file_hash="phase3_api_hash_456",
            abstract="FactoFormer reduces memory footprint while achieving state-of-the-art accuracy.",
            authors=["Facto Team"],
            publication_year=2023,
            venue="NeurIPS 2023",
        )
        db_session.add(paper)
        db_session.flush()

        sec = PaperSection(
            paper_id=paper.id,
            section_name="Limitations",
            section_order=1,
            page_start=1,
            page_end=1,
            content="The main limitation is that scaling beyond 32 layers requires distributed tensor parallelism.",
            paragraphs=["The main limitation is that scaling beyond 32 layers requires distributed tensor parallelism."],
        )
        db_session.add(sec)
        db_session.commit()

        # Run NLP & embedding
        scientific_nlp_service.process_paper(paper.id, db_session)
        get_evidence_retriever_service().embed_paper_evidence(paper.id, db_session)
        return paper.id

    def test_semantic_search_endpoint(self, client: TestClient, seeded_paper_id: int):
        resp = client.get("/api/v1/search/semantic?q=distributed+tensor+parallelism+scaling&top_k=3")
        assert resp.status_code == 200
        data = resp.json()
        assert data["query"] == "distributed tensor parallelism scaling"
        assert data["retrieval_method"] == "faiss_semantic"
        assert len(data["results"]) > 0

        first = data["results"][0]
        assert "source_text" in first
        assert "similarity_score" in first
        assert "paper" in first
        assert "provenance" in first
        assert first["provenance"]["paper_id"] == seeded_paper_id

    def test_semantic_search_empty_query_400(self, client: TestClient):
        resp = client.get("/api/v1/search/semantic?q=")
        # FastAPI query validation or custom validation error (400 or 422)
        assert resp.status_code in (400, 422)

    def test_evidence_search_endpoint_with_filters(self, client: TestClient, seeded_paper_id: int):
        # 1. Semantic method with section filter
        resp = client.get(f"/api/v1/evidence/search?q=scaling&method=semantic&section=Limitations")
        assert resp.status_code == 200
        data = resp.json()
        assert data["retrieval_method"] == "faiss_semantic"
        for item in data["results"]:
            assert "limitations" in item["section"].lower()

        # 2. Filter by paper_id
        resp_p = client.get(f"/api/v1/evidence/search?q=scaling&paper_id={seeded_paper_id}")
        assert resp_p.status_code == 200
        for item in resp_p.json()["results"]:
            assert item["paper"]["id"] == seeded_paper_id

        # 3. TF-IDF method baseline
        resp_tfidf = client.get(f"/api/v1/evidence/search?q=distributed+parallelism&method=tfidf")
        assert resp_tfidf.status_code == 200
        data_tfidf = resp_tfidf.json()
        assert data_tfidf["retrieval_method"] == "tfidf_baseline"

    def test_embed_paper_endpoint(self, client: TestClient, seeded_paper_id: int):
        resp = client.post(f"/api/v1/evidence/embed/{seeded_paper_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["paper_id"] == seeded_paper_id
        assert data["embeddings_created"] >= 0

    def test_batch_embed_endpoint(self, client: TestClient):
        resp = client.post("/api/v1/evidence/batch-embed")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_papers" in data
        assert "total_embeddings_created" in data
        assert "index_total_vectors" in data

    def test_retrieval_stats_endpoint(self, client: TestClient):
        resp = client.get("/api/v1/evidence/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "model_name" in data
        assert "embedding_dimension" in data
        assert "total_faiss_vectors" in data
        assert data["status"] == "operational"
