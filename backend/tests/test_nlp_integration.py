"""Integration tests for Phase 2 Scientific NLP Processing pipeline and REST API.

Verifies end-to-end flow:
- Paper ingestion & section storage -> Phase 2 NLP processing -> sentences -> extractions -> database
- API query endpoints:
  - POST /api/v1/nlp/process/{paper_id}
  - GET  /api/v1/nlp/papers/{paper_id}/sentences
  - GET  /api/v1/nlp/papers/{paper_id}/extractions
  - GET  /api/v1/nlp/papers/{paper_id}/limitations
  - GET  /api/v1/nlp/papers/{paper_id}/future-work
- Idempotency & duplicate processing prevention
- Edge cases: missing abstract, missing sections, empty papers, special symbols, long documents, nonexistent paper ID
"""

import pytest
from sqlalchemy import select

from backend.app.models.paper import (
    Paper,
    PaperSection,
    ScientificExtraction,
    ScientificSentence,
)


def _seed_scientific_paper(db, sha_suffix: str = "1") -> Paper:
    """Helper to seed a realistic structured paper with parsed sections."""
    paper = Paper(
        title=f"Linear-Time Transformers via Kernelized Attention #{sha_suffix}",
        file_path=f"/mock/uploads/paper_{sha_suffix}.pdf",
        file_hash=f"sha256_mock_hash_{sha_suffix.zfill(48)}",
        file_size=1420500,
        abstract=(
            "Standard self-attention mechanisms suffer from quadratic computational and memory complexity. "
            "In this work, we propose LinearFormer, a novel architecture that achieves linear O(n) scaling. "
            "Our model achieves competitive BLEU scores on WMT'14 English-German translation."
        ),
        page_count=12,
        authors=["Vaswani, A.", "Shazeer, N."],
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)

    # Content for sections
    sec1_text = (
        "Transformer architectures have achieved remarkable results across diverse natural language processing domains. "
        "However, quadratic memory complexity remains a fundamental bottleneck for sequence lengths exceeding 4096 tokens. "
        "In this paper, our objective is to demonstrate that low-rank kernel approximations eliminate this memory wall."
    )
    sec1 = PaperSection(
        paper_id=paper.id,
        section_order=1,
        section_name="Introduction",
        page_start=1,
        page_end=2,
        content=sec1_text,
        paragraphs=[sec1_text],
    )

    sec2_text = (
        "We propose LinearFormer, replacing softmax self-attention with positive random feature maps. "
        "We optimize the network using the AdamW optimizer with cosine learning rate scheduling. "
        "The model consists of 12 layers with 768 hidden dimensions."
    )
    sec2 = PaperSection(
        paper_id=paper.id,
        section_order=2,
        section_name="Methodology",
        page_start=3,
        page_end=5,
        content=sec2_text,
        paragraphs=[sec2_text],
    )

    sec3_text = (
        "We evaluate our approach on the GLUE benchmark dataset and the WMT'14 translation corpus. "
        "LinearFormer achieves 88.6% accuracy on SST-2, outperforming the standard BERT baseline by 1.4%. "
        "We report standard evaluation metrics including accuracy, F1-score, and BLEU."
    )
    sec3 = PaperSection(
        paper_id=paper.id,
        section_order=3,
        section_name="Experiments & Results",
        page_start=6,
        page_end=9,
        content=sec3_text,
        paragraphs=[sec3_text],
    )

    sec4_text = (
        "A notable limitation of our method is that positive random feature approximations degrade when context is extremely sparse. "
        "Furthermore, our evaluation lacks extensive testing on low-resource morphologically rich languages."
    )
    sec4 = PaperSection(
        paper_id=paper.id,
        section_order=4,
        section_name="Limitations",
        page_start=10,
        page_end=11,
        content=sec4_text,
        paragraphs=[sec4_text],
    )

    sec5_text = (
        "We have presented LinearFormer, a linear complexity Transformer. "
        "In future work, we plan to extend this kernel formulation to autoregressive speech and multimodal vision tasks."
    )
    sec5 = PaperSection(
        paper_id=paper.id,
        section_order=5,
        section_name="Conclusion & Future Work",
        page_start=12,
        page_end=12,
        content=sec5_text,
        paragraphs=[sec5_text],
    )

    db.add_all([sec1, sec2, sec3, sec4, sec5])
    db.commit()
    return paper


class TestNLPIntegrationPipeline:
    """End-to-end integration tests for Phase 2 Scientific NLP pipeline."""

    def test_process_paper_endpoint_success(self, client, db_session):
        paper = _seed_scientific_paper(db_session, "success")

        # Call POST /api/v1/nlp/process/{paper_id}
        response = client.post(f"/api/v1/nlp/process/{paper.id}")
        assert response.status_code == 200

        data = response.json()
        assert data["paper_id"] == paper.id
        assert data["total_sentences"] >= 10
        assert data["total_extractions"] >= 5
        assert data["provenance_verified"] is True
        assert data["extractions_by_type"]["LIMITATION"] >= 1
        assert data["extractions_by_type"]["FUTURE_WORK"] >= 1
        assert data["extractions_by_type"]["METHOD"] >= 1

        # Check database records directly
        sentences = db_session.scalars(
            select(ScientificSentence).where(ScientificSentence.paper_id == paper.id)
        ).all()
        assert len(sentences) == data["total_sentences"]

        # Verify strict provenance: section_name and page_number must be preserved
        for s in sentences:
            assert s.section_name is not None and len(s.section_name) > 0
            assert s.page_number is not None and s.page_number >= 1
            assert s.sentence_order >= 1

    def test_get_paper_sentences_endpoint(self, client, db_session):
        paper = _seed_scientific_paper(db_session, "sents")
        client.post(f"/api/v1/nlp/process/{paper.id}")

        # Call GET /api/v1/nlp/papers/{paper_id}/sentences
        res = client.get(f"/api/v1/nlp/papers/{paper.id}/sentences")
        assert res.status_code == 200
        sentences = res.json()
        assert isinstance(sentences, list)
        assert len(sentences) > 0

        # Verify sequential sentence order
        orders = [s["sentence_order"] for s in sentences]
        assert orders == sorted(orders)

        # Verify classified metadata
        s0 = sentences[0]
        assert "source_text" in s0
        assert "section_name" in s0
        assert "page_number" in s0

    def test_get_paper_extractions_with_filtering(self, client, db_session):
        paper = _seed_scientific_paper(db_session, "ext")
        client.post(f"/api/v1/nlp/process/{paper.id}")

        # 1. Fetch all extractions
        res = client.get(f"/api/v1/nlp/papers/{paper.id}/extractions")
        assert res.status_code == 200
        all_exts = res.json()
        assert len(all_exts) > 0

        # Verify provenance on every extraction
        for ext in all_exts:
            assert ext["paper_id"] == paper.id
            assert ext["sentence_id"] is not None
            assert ext["extraction_type"] in [
                "PROBLEM", "OBJECTIVE", "METHOD", "DATASET", "METRIC", "RESULT", "LIMITATION", "FUTURE_WORK", "OTHER"
            ]
            assert "provenance" in ext
            assert "section_name" in ext["provenance"]
            assert "page_number" in ext["provenance"]

        # 2. Filter by METHOD
        res_m = client.get(f"/api/v1/nlp/papers/{paper.id}/extractions?extraction_type=METHOD")
        assert res_m.status_code == 200
        method_exts = res_m.json()
        assert len(method_exts) > 0
        assert all(e["extraction_type"] == "METHOD" for e in method_exts)

        # 3. Filter by DATASET
        res_d = client.get(f"/api/v1/nlp/papers/{paper.id}/extractions?extraction_type=DATASET")
        assert res_d.status_code == 200
        dataset_exts = res_d.json()
        assert all(e["extraction_type"] == "DATASET" for e in dataset_exts)

    def test_get_paper_limitations_endpoint(self, client, db_session):
        paper = _seed_scientific_paper(db_session, "lim")
        client.post(f"/api/v1/nlp/process/{paper.id}")

        # Call GET /api/v1/nlp/papers/{paper_id}/limitations
        res = client.get(f"/api/v1/nlp/papers/{paper.id}/limitations")
        assert res.status_code == 200
        limitations = res.json()
        assert len(limitations) >= 1

        for lim in limitations:
            assert lim["paper_id"] == paper.id
            assert "limitation_text" in lim
            assert "limitation_type" in lim
            assert "page_number" in lim
            assert lim["page_number"] >= 1

    def test_get_paper_future_work_endpoint(self, client, db_session):
        paper = _seed_scientific_paper(db_session, "fw")
        client.post(f"/api/v1/nlp/process/{paper.id}")

        # Call GET /api/v1/nlp/papers/{paper_id}/future-work
        res = client.get(f"/api/v1/nlp/papers/{paper.id}/future-work")
        assert res.status_code == 200
        fw_items = res.json()
        assert len(fw_items) >= 1

        for fw in fw_items:
            assert fw["paper_id"] == paper.id
            assert "future_work_text" in fw
            assert "future" in fw["future_work_text"].lower()

    def test_idempotent_reprocessing(self, client, db_session):
        """Verifies duplicate processing runs cleanly without duplicating sentences."""
        paper = _seed_scientific_paper(db_session, "idempotent")

        # First run
        res1 = client.post(f"/api/v1/nlp/process/{paper.id}")
        assert res1.status_code == 200
        count1 = res1.json()["total_sentences"]
        ext_count1 = res1.json()["total_extractions"]

        # Second run on same paper
        res2 = client.post(f"/api/v1/nlp/process/{paper.id}")
        assert res2.status_code == 200
        count2 = res2.json()["total_sentences"]
        ext_count2 = res2.json()["total_extractions"]

        # Counts must match exactly
        assert count1 == count2
        assert ext_count1 == ext_count2

        # Verify DB does not contain doubled rows
        total_in_db = db_session.scalars(
            select(ScientificSentence).where(ScientificSentence.paper_id == paper.id)
        ).all()
        assert len(total_in_db) == count1


class TestNLPEdgeCases:
    """Tests boundary conditions and edge cases in scientific NLP processing."""

    def test_nonexistent_paper_id_returns_404(self, client):
        res = client.post("/api/v1/nlp/process/999999")
        assert res.status_code == 404

    def test_paper_with_missing_sections_falls_back_to_abstract(self, client, db_session):
        """When sections are empty, the abstract is processed as a synthetic section."""
        paper = Paper(
            title="Abstract-Only Short Abstract",
            file_path="/mock/abstract_only.pdf",
            file_hash="mock_abstract_only_hash_000000000000000000000000000",
            file_size=42000,
            abstract="We introduce a simplified benchmark. It evaluates zero-shot robustness.",
            page_count=1,
            authors=["Anonymous"],
        )
        db_session.add(paper)
        db_session.commit()

        res = client.post(f"/api/v1/nlp/process/{paper.id}")
        assert res.status_code == 200
        data = res.json()
        assert data["total_sentences"] == 2

        sents = client.get(f"/api/v1/nlp/papers/{paper.id}/sentences").json()
        assert len(sents) == 2
        assert sents[0]["section_name"] == "Abstract"

    def test_paper_with_empty_abstract_and_no_sections(self, client, db_session):
        """Paper with zero text content completes gracefully without errors."""
        paper = Paper(
            title="Completely Blank Document",
            file_path="/mock/blank.pdf",
            file_hash="mock_blank_hash_0000000000000000000000000000000000000",
            file_size=1024,
            abstract=None,
            page_count=1,
            authors=[],
        )
        db_session.add(paper)
        db_session.commit()

        res = client.post(f"/api/v1/nlp/process/{paper.id}")
        assert res.status_code == 200
        data = res.json()
        assert data["total_sentences"] == 0
        assert data["total_extractions"] == 0

    def test_special_scientific_and_unicode_symbols(self, client, db_session):
        """Mathematical formulas, Greek letters, and LaTeX-style symbols."""
        paper = Paper(
            title="Quantum Neural Attention with Greek Glyphs",
            file_path="/mock/quantum.pdf",
            file_hash="mock_quantum_hash_00000000000000000000000000000000000",
            file_size=84000,
            abstract="Let \u03b1 and \u03b2 denote the learning decay rates. We test \u2211_{i=1}^N x_i \u2264 \u03b8.",
            page_count=1,
            authors=["Schroedinger, E."],
        )
        db_session.add(paper)
        db_session.commit()

        res = client.post(f"/api/v1/nlp/process/{paper.id}")
        assert res.status_code == 200

        sents = client.get(f"/api/v1/nlp/papers/{paper.id}/sentences").json()
        assert len(sents) == 2
        # Unicode Greek letters preserved
        assert "\u03b1" in sents[0]["source_text"] or "alpha" in sents[0]["source_text"]
        assert "\u03b2" in sents[0]["source_text"] or "beta" in sents[0]["source_text"]

    def test_very_long_paper_with_many_paragraphs(self, client, db_session):
        """Long paper spanning many pages and paragraphs distributes page numbers properly."""
        paper = Paper(
            title="Comprehensive Treatise on Large Foundation Architectures",
            file_path="/mock/long_survey.pdf",
            file_hash="mock_long_survey_hash_000000000000000000000000000000",
            file_size=5200000,
            abstract="A comprehensive 50-page survey analyzing modern deep learning.",
            page_count=50,
            authors=["Survey Team"],
        )
        db_session.add(paper)
        db_session.commit()

        # Generate 15 distinct sections with multiple paragraphs each
        sections = []
        for s_idx in range(1, 16):
            content_str = (
                f"Paragraph 1 in chapter {s_idx} explores architectural variations. "
                f"Paragraph 2 in chapter {s_idx} evaluates experimental stability across benchmarks. "
                f"Paragraph 3 in chapter {s_idx} analyzes computational complexity constraints."
            )
            sec = PaperSection(
                paper_id=paper.id,
                section_order=s_idx,
                section_name=f"Chapter {s_idx}: Advanced Topic",
                page_start=s_idx * 3 - 2,
                page_end=s_idx * 3,
                content=content_str,
                paragraphs=[content_str],
            )
            sections.append(sec)

        db_session.add_all(sections)
        db_session.commit()

        res = client.post(f"/api/v1/nlp/process/{paper.id}")
        assert res.status_code == 200
        data = res.json()
        assert data["total_sentences"] >= 45

        # Verify page progression
        sents = client.get(f"/api/v1/nlp/papers/{paper.id}/sentences").json()
        first_page = sents[0]["page_number"]
        last_page = sents[-1]["page_number"]
        assert first_page <= last_page
        assert last_page >= 40
