"""Provenance Verification & Evidence Traceability Service (Phase 5).

Guarantees:
- Every node and relationship in the knowledge graph maintains strict provenance
- Grounded attribution linking back to source paper, section, page, sentence, and raw text
- Extraction confidence and method auditing for downstream graph validation.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProvenanceRecord(BaseModel):
    """Structured evidence attribution record for graph nodes and edges."""

    paper_id: Optional[int] = Field(None, description="Database ID of source paper")
    paper_title: Optional[str] = Field(None, description="Title of source paper")
    sentence_id: Optional[int] = Field(None, description="Sentence database ID")
    sentence_order: Optional[int] = Field(None, description="Order index of sentence in paper")
    section_name: Optional[str] = Field("Unknown", description="Paper structural section (e.g. Methodology)")
    page_number: Optional[int] = Field(1, description="Page number containing the evidence")
    source_text: Optional[str] = Field(None, description="Verbatim extracted scientific sentence/passage")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Extraction or relationship confidence score")
    extraction_method: str = Field("pipeline", description="Method used (e.g., rule_based, semantic_alignment, citation_match)")


class GraphProvenanceService:
    """Service auditing and resolving evidence provenance across knowledge graph entities."""

    @staticmethod
    def create_provenance(
        paper_id: Optional[int] = None,
        paper_title: Optional[str] = None,
        sentence_id: Optional[int] = None,
        sentence_order: Optional[int] = None,
        section_name: Optional[str] = "Unknown",
        page_number: Optional[int] = 1,
        source_text: Optional[str] = None,
        confidence: float = 1.0,
        extraction_method: str = "pipeline",
    ) -> Dict[str, Any]:
        """Generate a validated dictionary representation of a ProvenanceRecord."""
        rec = ProvenanceRecord(
            paper_id=paper_id,
            paper_title=paper_title,
            sentence_id=sentence_id,
            sentence_order=sentence_order,
            section_name=section_name or "Unknown",
            page_number=page_number or 1,
            source_text=source_text,
            confidence=max(0.0, min(1.0, float(confidence))),
            extraction_method=extraction_method,
        )
        return rec.model_dump()

    @staticmethod
    def format_citation_string(provenance: Dict[str, Any]) -> str:
        """Create a human-readable citation string from provenance attributes."""
        title = provenance.get("paper_title") or f"Paper #{provenance.get('paper_id', 'Unknown')}"
        section = provenance.get("section_name", "General")
        page = provenance.get("page_number", 1)
        conf = provenance.get("confidence", 1.0)
        return f"[{title} | Sec: {section} | p. {page} | Conf: {conf:.2f}]"

    @classmethod
    def verify_provenance_completeness(cls, data: Dict[str, Any]) -> bool:
        """Check whether a node or edge dictionary possesses non-empty provenance."""
        prov = data.get("provenance")
        if not isinstance(prov, dict):
            return False
        # Provenance must have at least source paper attribution or source text
        has_paper = prov.get("paper_id") is not None or bool(prov.get("paper_title"))
        has_text = bool(prov.get("source_text"))
        return has_paper or has_text
