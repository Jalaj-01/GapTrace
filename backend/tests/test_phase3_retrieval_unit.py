"""Unit Tests for Phase 3: Semantic Representation and Evidence Retrieval.

Verifies:
- Embedding generation, dimensions, normalization, and deterministic reproducibility
- Empty query validation and error handling
- FAISS index creation, vector ingestion, and metadata mapping
- FAISS atomic save and load persistence
- Corrupted and missing index resilience
- Multi-field metadata filtering (paper_id, section, extraction_type, year)
- TF-IDF baseline search and ranking
- Retrieval benchmark metrics calculation (P@K, R@K, MRR)
"""

import tempfile
from pathlib import Path
import numpy as np
import pytest

from backend.app.core.errors import ValidationError
from backend.app.services.embeddings.embedding_service import (
    DeterministicEmbeddingService,
    SentenceTransformerEmbeddingService,
)
from backend.app.services.retrieval.faiss_index import FAISSIndexManager
from backend.app.services.retrieval.tfidf_search import TFIDFSearchService
from backend.app.services.retrieval.evaluator import RetrievalEvaluator


class TestEmbeddingService:
    """Tests for modular embedding service and deterministic fallback."""

    def test_deterministic_embedding_generation_and_dimensions(self):
        svc = DeterministicEmbeddingService(dimension=384)
        assert svc.dimension == 384
        assert svc.model_name == "deterministic-baseline-384"

        vec = svc.embed_query("cross-domain generalization in scientific NLP")
        assert isinstance(vec, np.ndarray)
        assert vec.shape == (384,)
        assert vec.dtype == np.float32

        # Verify unit normalization (L2 norm ~= 1.0)
        norm = np.linalg.norm(vec)
        assert np.isclose(norm, 1.0, atol=1e-4)

    def test_deterministic_reproducibility(self):
        svc = DeterministicEmbeddingService(dimension=384)
        text = "adversarial domain discrimination with gradient reversal layers"
        vec1 = svc.embed_query(text)
        vec2 = svc.embed_query(text)
        assert np.array_equal(vec1, vec2)

    def test_empty_query_raises_validation_error(self):
        svc = DeterministicEmbeddingService(dimension=384)
        with pytest.raises(ValidationError):
            svc.embed_query("")

        with pytest.raises(ValidationError):
            svc.embed_query("   \n\t  ")

    def test_batch_embedding_documents(self):
        svc = DeterministicEmbeddingService(dimension=384)
        docs = [
            "Limitation of quadratic self-attention complexity.",
            "FlashAttention accelerates inference throughput by 2.4x.",
            "Clinical dataset scarcity causes overfitting.",
        ]
        matrix = svc.embed_documents(docs)
        assert isinstance(matrix, np.ndarray)
        assert matrix.shape == (3, 384)
        assert matrix.dtype == np.float32

        # Check normalization for each row
        norms = np.linalg.norm(matrix, axis=1)
        for n in norms:
            assert np.isclose(n, 1.0, atol=1e-4)

    def test_empty_document_batch(self):
        svc = DeterministicEmbeddingService(dimension=384)
        matrix = svc.embed_documents([])
        assert matrix.shape == (0, 384)

    def test_configurable_model_name(self):
        svc = SentenceTransformerEmbeddingService(
            model_name="custom/scientific-scibert-v1",
            dimension=768,
            fallback_on_error=True,
        )
        assert svc.model_name == "custom/scientific-scibert-v1"


class TestFAISSIndexManager:
    """Tests for FAISS vector index management, persistence, and filtering."""

    @pytest.fixture
    def isolated_faiss(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            idx_path = Path(tmp_dir) / "test_faiss.bin"
            meta_path = Path(tmp_dir) / "test_meta.json"
            mgr = FAISSIndexManager(
                dimension=128,
                index_path=str(idx_path),
                metadata_path=str(meta_path),
                auto_load=False,
            )
            yield mgr

    def test_index_creation_and_empty_state(self, isolated_faiss):
        assert isolated_faiss.dimension == 128
        assert isolated_faiss.total_vectors == 0
        res = isolated_faiss.search(np.random.randn(128).astype(np.float32), top_k=5)
        assert res == []

    def test_add_vectors_and_metadata_mapping(self, isolated_faiss):
        vectors = np.random.randn(3, 128).astype(np.float32)
        metadata = [
            {"paper_id": 1, "source_text": "Sample text 1", "section": "Limitations"},
            {"paper_id": 1, "source_text": "Sample text 2", "section": "Methods"},
            {"paper_id": 2, "source_text": "Sample text 3", "section": "Results"},
        ]
        assigned_ids = isolated_faiss.add_vectors(vectors, metadata)
        assert len(assigned_ids) == 3
        assert isolated_faiss.total_vectors == 3

        # Verify mapping back to metadata
        for fid in assigned_ids:
            meta = isolated_faiss.id_to_metadata.get(fid)
            assert meta is not None
            assert "source_text" in meta

    def test_dimension_mismatch_error(self, isolated_faiss):
        wrong_vectors = np.random.randn(2, 64).astype(np.float32)
        meta = [{"paper_id": 1}, {"paper_id": 2}]
        with pytest.raises(ValidationError) as exc_info:
            isolated_faiss.add_vectors(wrong_vectors, meta)
        assert "Dimension mismatch" in str(exc_info.value)

    def test_vector_metadata_length_mismatch(self, isolated_faiss):
        vectors = np.random.randn(3, 128).astype(np.float32)
        meta = [{"paper_id": 1}]
        with pytest.raises(ValidationError):
            isolated_faiss.add_vectors(vectors, meta)

    def test_save_and_load_persistence(self, isolated_faiss):
        vectors = np.random.randn(2, 128).astype(np.float32)
        metadata = [
            {"paper_id": 10, "source_text": "Saved vector A", "section": "Intro"},
            {"paper_id": 20, "source_text": "Saved vector B", "section": "Conclusion"},
        ]
        isolated_faiss.add_vectors(vectors, metadata)
        isolated_faiss.save()

        # Load into brand new manager
        loaded_mgr = FAISSIndexManager(
            dimension=128,
            index_path=str(isolated_faiss.index_path),
            metadata_path=str(isolated_faiss.metadata_path),
            auto_load=True,
        )
        assert loaded_mgr.total_vectors == 2
        assert len(loaded_mgr.id_to_metadata) == 2
        assert loaded_mgr.id_to_metadata[0]["source_text"] == "Saved vector A"
        assert loaded_mgr.id_to_metadata[1]["source_text"] == "Saved vector B"

    def test_missing_index_and_corrupted_file_handling(self):
        mgr = FAISSIndexManager(dimension=64, auto_load=False)
        with pytest.raises(FileNotFoundError):
            mgr.load(index_path=Path("non_existent_file.bin"), metadata_path=Path("non_existent_meta.json"))

        with tempfile.TemporaryDirectory() as tmp_dir:
            empty_file = Path(tmp_dir) / "empty.bin"
            empty_meta = Path(tmp_dir) / "empty.json"
            empty_file.touch()
            empty_meta.touch()
            with pytest.raises(ValueError):
                mgr.load(index_path=empty_file, metadata_path=empty_meta)

    def test_search_with_metadata_filters(self, isolated_faiss):
        vectors = np.array([
            [1.0] + [0.0] * 127,  # Direction 1
            [0.0, 1.0] + [0.0] * 126,  # Direction 2
            [1.0] + [0.0] * 127,  # Direction 1 duplicate
        ], dtype=np.float32)

        metadata = [
            {"paper_id": 101, "year": 2024, "section": "Limitations", "extraction_type": "LIMITATION", "source_text": "Limitation 1"},
            {"paper_id": 102, "year": 2022, "section": "Methods", "extraction_type": "METHOD", "source_text": "Method 1"},
            {"paper_id": 103, "year": 2024, "section": "Limitations", "extraction_type": "LIMITATION", "source_text": "Limitation 2"},
        ]
        isolated_faiss.add_vectors(vectors, metadata)

        # Query matching Direction 1
        query_vec = np.array([1.0] + [0.0] * 127, dtype=np.float32)

        # 1. Filter by paper_id=101
        res_paper = isolated_faiss.search(query_vec, top_k=5, filters={"paper_id": 101})
        assert len(res_paper) == 1
        assert res_paper[0]["metadata"]["paper_id"] == 101

        # 2. Filter by extraction_type=LIMITATION
        res_type = isolated_faiss.search(query_vec, top_k=5, filters={"extraction_type": "LIMITATION"})
        assert len(res_type) == 2
        for r in res_type:
            assert r["metadata"]["extraction_type"] == "LIMITATION"

        # 3. Filter by year=2022
        res_year = isolated_faiss.search(query_vec, top_k=5, filters={"year": 2022})
        assert len(res_year) == 1
        assert res_year[0]["metadata"]["paper_id"] == 102


class TestTFIDFBaseline:
    """Tests for TF-IDF statistical retrieval baseline."""

    def test_tfidf_corpus_fit_and_search(self):
        svc = TFIDFSearchService()
        texts = [
            "Cross-domain generalization degrades without target domain adaptation.",
            "Quadratic memory complexity of self-attention in transformers.",
            "Hard negative mining in graph neural networks.",
        ]
        meta = [
            {"paper_id": 1, "source_text": texts[0], "section": "Limitations"},
            {"paper_id": 2, "source_text": texts[1], "section": "Limitations"},
            {"paper_id": 3, "source_text": texts[2], "section": "Methods"},
        ]
        svc.fit_corpus(texts, meta)
        assert svc.is_fitted
        assert svc.total_documents == 3

        # Query for cross-domain generalization
        res = svc.search("cross-domain generalization", top_k=2)
        assert len(res) > 0
        assert res[0]["metadata"]["paper_id"] == 1
        assert res[0]["similarity_score"] > 0.0

    def test_tfidf_empty_query_raises_validation_error(self):
        svc = TFIDFSearchService()
        with pytest.raises(ValidationError):
            svc.search("")

    def test_tfidf_filtering(self):
        svc = TFIDFSearchService()
        texts = [
            "Evaluation metric bias in summarization.",
            "Evaluation metric bias in machine translation.",
        ]
        meta = [
            {"paper_id": 1, "extraction_type": "LIMITATION", "year": 2024, "source_text": texts[0]},
            {"paper_id": 2, "extraction_type": "METHOD", "year": 2021, "source_text": texts[1]},
        ]
        svc.fit_corpus(texts, meta)

        res = svc.search("evaluation metric bias", top_k=5, filters={"year": 2024})
        assert len(res) == 1
        assert res[0]["metadata"]["paper_id"] == 1


class TestRetrievalEvaluator:
    """Tests for benchmark evaluation dataset and metric calculation."""

    def test_evaluator_metrics_calculation(self):
        evaluator = RetrievalEvaluator()
        metrics = evaluator.run_evaluation(k_values=[5, 10])

        assert "tfidf_baseline" in metrics
        assert "semantic_retrieval" in metrics

        tfidf = metrics["tfidf_baseline"]
        sem = metrics["semantic_retrieval"]

        # Verify all required metrics are present and non-negative
        for k in [5, 10]:
            assert f"precision@{k}" in tfidf
            assert f"recall@{k}" in tfidf
            assert f"precision@{k}" in sem
            assert f"recall@{k}" in sem
            assert 0.0 <= tfidf[f"precision@{k}"] <= 1.0
            assert 0.0 <= tfidf[f"recall@{k}"] <= 1.0
            assert 0.0 <= sem[f"precision@{k}"] <= 1.0
            assert 0.0 <= sem[f"recall@{k}"] <= 1.0

        assert "mrr" in tfidf
        assert "mrr" in sem
        assert 0.0 <= tfidf["mrr"] <= 1.0
        assert 0.0 <= sem["mrr"] <= 1.0
