"""Evidence Retrieval and Retrieval-Augmented Generation (RAG) orchestrator interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from pydantic import BaseModel


class RetrievedEvidence(BaseModel):
    chunk_id: str
    paper_title: str
    section_name: str
    text_snippet: str
    relevance_score: float


class GroundedRAGResponse(BaseModel):
    answer: str
    cited_evidence: List[RetrievedEvidence]
    model_name: str
    confidence: float


class BaseRAGOrchestrator(ABC):
    """Abstract interface for RAG-based scientific question answering and gap synthesis."""

    @abstractmethod
    async def retrieve_evidence(self, query: str, top_k: int = 5) -> List[RetrievedEvidence]:
        """Retrieve grounded evidence passages from the scientific corpus."""
        pass

    @abstractmethod
    async def generate_grounded_answer(self, query: str, top_k: int = 5) -> GroundedRAGResponse:
        """Synthesize answer strictly conditioned on retrieved passages with citations."""
        pass


class RAGOrchestrator(BaseRAGOrchestrator):
    """RAG Orchestration service stub for Phase 1."""

    async def retrieve_evidence(self, query: str, top_k: int = 5) -> List[RetrievedEvidence]:
        raise NotImplementedError("Evidence retrieval will be implemented in Phase 1.")

    async def generate_grounded_answer(self, query: str, top_k: int = 5) -> GroundedRAGResponse:
        raise NotImplementedError("Grounded RAG generation will be implemented in Phase 1.")
