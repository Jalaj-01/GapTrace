"""Evidence Retriever and Representation Orchestrator (Phase 3).

Coordinates end-to-end evidence embedding generation, incremental indexing,
batch processing across paper collections, database persistence, FAISS synchronization,
and hybrid search dispatching (Dense Semantic vs. TF-IDF Baseline).
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
import numpy as np
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from backend.app.core.errors import NotFoundError, ValidationError
from backend.app.models.paper import (
    EvidenceBatchEmbedResponse,
    EvidenceEmbedding,
    Paper,
    ScientificExtraction,
    ScientificSentence,
)
from backend.app.services.embeddings.embedding_service import (
    BaseEmbeddingService,
    get_embedding_service,
)
from backend.app.services.retrieval.faiss_index import (
    FAISSIndexManager,
    get_faiss_index_manager,
)
from backend.app.services.retrieval.semantic_search import (
    SemanticSearchService,
    get_semantic_search_service,
)
from backend.app.services.retrieval.tfidf_search import (
    TFIDFSearchService,
    get_tfidf_search_service,
)

logger = get_logger("app.retrieval.orchestrator")


class EvidenceRetrieverService:
    """Orchestrator for scientific evidence embeddings and multi-modal retrieval."""

    def __init__(
        self,
        embedding_service: Optional[BaseEmbeddingService] = None,
        faiss_manager: Optional[FAISSIndexManager] = None,
        tfidf_service: Optional[TFIDFSearchService] = None,
        semantic_search: Optional[SemanticSearchService] = None,
    ):
        self._embedding_service = embedding_service
        self._faiss_manager = faiss_manager
        self._tfidf_service = tfidf_service
        self._semantic_search = semantic_search

    @property
    def embedding_service(self) -> BaseEmbeddingService:
        if self._embedding_service is None:
            self._embedding_service = get_embedding_service()
        return self._embedding_service

    @property
    def faiss_manager(self) -> FAISSIndexManager:
        if self._faiss_manager is None:
            self._faiss_manager = get_faiss_index_manager()
        return self._faiss_manager

    @property
    def tfidf_service(self) -> TFIDFSearchService:
        if self._tfidf_service is None:
            self._tfidf_service = get_tfidf_search_service()
        return self._tfidf_service

    @property
    def semantic_search(self) -> SemanticSearchService:
        if self._semantic_search is None:
            self._semantic_search = get_semantic_search_service()
        return self._semantic_search

    def embed_paper_evidence(
        self,
        paper_id: int,
        db: Session,
        save_index: bool = True,
    ) -> Dict[str, Any]:
        """Generate and store embeddings for all sentences and extractions of a paper.

        Ensures incremental updates:
        - Cleans up prior embeddings for this paper in DB
        - Generates dense vectors in batch
        - Stores metadata in DB and FAISS index
        - Fits/updates TF-IDF baseline index
        """
        paper = db.scalar(select(Paper).where(Paper.id == paper_id))
        if not paper:
            raise NotFoundError(f"Paper with ID {paper_id} not found.")

        logger.info(f"Generating Phase 3 embeddings for paper {paper_id}: '{paper.title}'")

        # 1. Gather all sentences
        sentences = db.scalars(
            select(ScientificSentence)
            .where(ScientificSentence.paper_id == paper_id)
            .order_by(ScientificSentence.sentence_order)
        ).all()

        # 2. Gather all extractions
        extractions = db.scalars(
            select(ScientificExtraction)
            .where(ScientificExtraction.paper_id == paper_id)
            .order_by(ScientificExtraction.id)
        ).all()

        evidence_items: List[Dict[str, Any]] = []

        # A. Embed each scientific sentence
        for s in sentences:
            if not s.source_text or not s.source_text.strip():
                continue
            emb_id = f"emb-{paper_id}-s{s.id}-{uuid.uuid4().hex[:8]}"
            evidence_items.append({
                "embedding_id": emb_id,
                "paper_id": paper_id,
                "sentence_id": s.id,
                "extraction_id": None,
                "section": s.section_name or "Unknown",
                "page": s.page_number or 1,
                "extraction_type": "SENTENCE",
                "source_text": s.source_text.strip(),
                "model_name": self.embedding_service.model_name,
                "embedding_dimension": self.embedding_service.dimension,
                "paper_title": paper.title,
                "year": paper.publication_year,
                "provenance": {
                    "paper_id": paper_id,
                    "section_name": s.section_name or "Unknown",
                    "page_number": s.page_number or 1,
                    "paragraph_id": s.paragraph_id,
                    "sentence_id": s.id,
                    "sentence_order": s.sentence_order,
                },
            })

        # B. Embed each classified extraction (LIMITATION, METHOD, RESULT, etc.)
        for ext in extractions:
            if not ext.extracted_text or not ext.extracted_text.strip():
                continue
            # Look up sentence provenance if available
            parent_sent = next((s for s in sentences if s.id == ext.sentence_id), None)
            sec_name = parent_sent.section_name if parent_sent else "Unknown"
            page_num = parent_sent.page_number if parent_sent else 1
            s_order = parent_sent.sentence_order if parent_sent else None

            prov = dict(ext.provenance) if ext.provenance else {}
            prov.setdefault("paper_id", paper_id)
            prov.setdefault("sentence_id", ext.sentence_id)
            prov.setdefault("extraction_id", ext.id)
            prov.setdefault("section_name", sec_name)
            prov.setdefault("page_number", page_num)
            if s_order is not None:
                prov.setdefault("sentence_order", s_order)

            emb_id = f"emb-{paper_id}-e{ext.id}-{uuid.uuid4().hex[:8]}"
            evidence_items.append({
                "embedding_id": emb_id,
                "paper_id": paper_id,
                "sentence_id": ext.sentence_id,
                "extraction_id": ext.id,
                "section": sec_name,
                "page": page_num,
                "extraction_type": ext.extraction_type,
                "source_text": ext.extracted_text.strip(),
                "model_name": self.embedding_service.model_name,
                "embedding_dimension": self.embedding_service.dimension,
                "paper_title": paper.title,
                "year": paper.publication_year,
                "provenance": prov,
            })

        if not evidence_items:
            logger.warning(f"No text items to embed for paper {paper_id}.")
            return {
                "paper_id": paper_id,
                "embeddings_created": 0,
                "model_name": self.embedding_service.model_name,
            }

        # 3. Clean up existing DB embeddings for this paper to ensure idempotency
        db.execute(delete(EvidenceEmbedding).where(EvidenceEmbedding.paper_id == paper_id))
        db.flush()

        # 4. Generate embeddings in batch
        texts_to_embed = [item["source_text"] for item in evidence_items]
        vectors = self.embedding_service.embed_documents(texts_to_embed)

        # 5. Add to FAISS index (incremental update)
        assigned_faiss_ids = self.faiss_manager.add_vectors(vectors, evidence_items)

        # 6. Store in Database
        for item, fid in zip(evidence_items, assigned_faiss_ids):
            db_record = EvidenceEmbedding(
                embedding_id=item["embedding_id"],
                paper_id=item["paper_id"],
                sentence_id=item["sentence_id"],
                extraction_id=item["extraction_id"],
                section=item["section"],
                page=item["page"],
                extraction_type=item["extraction_type"],
                source_text=item["source_text"],
                model_name=item["model_name"],
                embedding_dimension=item["embedding_dimension"],
                faiss_id=fid,
                provenance=item["provenance"],
            )
            db.add(db_record)

        db.commit()

        # 7. Update TF-IDF baseline index
        self.tfidf_service.add_documents(texts_to_embed, evidence_items)

        # 8. Persist FAISS index if requested
        if save_index:
            try:
                self.faiss_manager.save()
            except Exception as exc:
                logger.error(f"Failed to persist FAISS index to disk: {exc}")

        logger.info(
            f"Successfully embedded {len(evidence_items)} evidence units for paper {paper_id}. "
            f"FAISS total: {self.faiss_manager.total_vectors}"
        )

        return {
            "paper_id": paper_id,
            "embeddings_created": len(evidence_items),
            "model_name": self.embedding_service.model_name,
            "embedding_dimension": self.embedding_service.dimension,
            "index_total_vectors": self.faiss_manager.total_vectors,
        }

    def batch_embed_collection(
        self,
        db: Session,
        paper_ids: Optional[List[int]] = None,
    ) -> EvidenceBatchEmbedResponse:
        """Batch process and generate semantic embeddings for an entire collection of papers."""
        if paper_ids is not None:
            papers = db.scalars(select(Paper).where(Paper.id.in_(paper_ids))).all()
        else:
            papers = db.scalars(select(Paper).order_by(Paper.id)).all()

        if not papers:
            return EvidenceBatchEmbedResponse(
                total_papers=0,
                total_embeddings_created=0,
                model_name=self.embedding_service.model_name,
                embedding_dimension=self.embedding_service.dimension,
                index_total_vectors=self.faiss_manager.total_vectors,
                processed_at=datetime.now(timezone.utc).isoformat(),
            )

        total_created = 0
        for p in papers:
            res = self.embed_paper_evidence(p.id, db, save_index=False)
            total_created += res.get("embeddings_created", 0)

        # Save index once after batch completion
        try:
            self.faiss_manager.save()
        except Exception as exc:
            logger.error(f"Failed to save FAISS index after batch embedding: {exc}")

        return EvidenceBatchEmbedResponse(
            total_papers=len(papers),
            total_embeddings_created=total_created,
            model_name=self.embedding_service.model_name,
            embedding_dimension=self.embedding_service.dimension,
            index_total_vectors=self.faiss_manager.total_vectors,
            processed_at=datetime.now(timezone.utc).isoformat(),
        )

    def search_evidence(
        self,
        query: str,
        method: str = "semantic",
        top_k: int = 5,
        paper_id: Optional[int] = None,
        section: Optional[str] = None,
        extraction_type: Optional[str] = None,
        year: Optional[int] = None,
        min_year: Optional[int] = None,
        max_year: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Perform evidence search using either dense semantic search or TF-IDF baseline."""
        if not query or not query.strip():
            raise ValidationError("Search query cannot be empty or whitespace only.")

        clean_query = query.strip()
        method_normalized = method.lower().strip()

        if method_normalized in ("tfidf", "tfidf_baseline", "baseline", "lexical"):
            filters: Dict[str, Any] = {}
            if paper_id is not None:
                filters["paper_id"] = paper_id
            if section is not None:
                filters["section"] = section
            if extraction_type is not None:
                filters["extraction_type"] = extraction_type
            if year is not None:
                filters["year"] = year
            if min_year is not None:
                filters["min_year"] = min_year
            if max_year is not None:
                filters["max_year"] = max_year

            raw_results = self.tfidf_service.search(clean_query, top_k=top_k, filters=filters)
            formatted = []
            for item in raw_results:
                meta = item["metadata"]
                prov = meta.get("provenance", {})
                p_id = meta.get("paper_id")
                s_id = meta.get("sentence_id")
                s_order = meta.get("sentence_order", prov.get("sentence_order"))
                formatted.append({
                    "source_text": meta.get("source_text", ""),
                    "similarity_score": item["similarity_score"],
                    "paper": {
                        "id": p_id,
                        "title": meta.get("paper_title", "Unknown"),
                        "year": meta.get("year"),
                    },
                    "section": meta.get("section", "Unknown"),
                    "page": meta.get("page", 1),
                    "sentence": {
                        "id": s_id,
                        "order": s_order,
                    } if s_id is not None else None,
                    "extraction_type": meta.get("extraction_type", "SENTENCE"),
                    "provenance": {
                        "paper_id": p_id,
                        "section_name": meta.get("section", "Unknown"),
                        "page_number": meta.get("page", 1),
                        "paragraph_id": prov.get("paragraph_id", 0),
                        "sentence_id": s_id,
                        "sentence_order": s_order,
                        "extraction_id": meta.get("extraction_id"),
                    },
                    "embedding_id": meta.get("embedding_id"),
                    "model_name": "tfidf_baseline",
                })

            return {
                "query": clean_query,
                "total_results": len(formatted),
                "retrieval_method": "tfidf_baseline",
                "model_name": "tfidf_baseline",
                "results": formatted,
            }

        else:
            # Default to dense semantic search
            results = self.semantic_search.search(
                query=clean_query,
                top_k=top_k,
                paper_id=paper_id,
                section=section,
                extraction_type=extraction_type,
                year=year,
                min_year=min_year,
                max_year=max_year,
            )
            return {
                "query": clean_query,
                "total_results": len(results),
                "retrieval_method": "faiss_semantic",
                "model_name": self.embedding_service.model_name,
                "results": results,
            }


# Singleton instance
_evidence_retriever_service: Optional[EvidenceRetrieverService] = None


def get_evidence_retriever_service() -> EvidenceRetrieverService:
    """Retrieve global EvidenceRetrieverService singleton."""
    global _evidence_retriever_service
    if _evidence_retriever_service is None:
        _evidence_retriever_service = EvidenceRetrieverService()
    return _evidence_retriever_service
