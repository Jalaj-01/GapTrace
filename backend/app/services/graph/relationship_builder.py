"""Relationship Builder & Evidence-Grounded Edge Extractor (Phase 5).

Extracts and validates the 11 core research knowledge graph relationships:
cites, uses, proposes, extends, compares, supports, contradicts, limited_by, addresses, studies, belongs_to

Every relationship stores:
- source paper
- source sentence
- page
- section
- confidence
- extraction method
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from backend.app.core.logging import get_logger
from backend.app.services.graph.graph_provenance import GraphProvenanceService

logger = get_logger("app.graph.relationship_builder")


class RelationTypes:
    """Enumeration of knowledge graph edge types."""
    CITES = "cites"
    USES = "uses"
    PROPOSES = "proposes"
    EXTENDS = "extends"
    COMPARES = "compares"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    LIMITED_BY = "limited_by"
    ADDRESSES = "addresses"
    STUDIES = "studies"
    BELONGS_TO = "belongs_to"


# Intent & linguistic cue patterns for relationship classification
PROPOSES_CUES = re.compile(
    r"\b(we propose|we introduce|we present|we develop|our approach|our model|our framework|in this work we)\b",
    re.IGNORECASE,
)
EXTENDS_CUES = re.compile(
    r"\b(we extend|extends|building upon|build upon|modified version of|extension of|adapted from|following the formulation)\b",
    re.IGNORECASE,
)
COMPARES_CUES = re.compile(
    r"\b(compared (with|to)|baseline|outperforms|in comparison with|evaluated against|versus|vs\.?|competing methods)\b",
    re.IGNORECASE,
)
USES_CUES = re.compile(
    r"\b(we use|we employ|we utilize|trained on|fine-tuned on|evaluated on the|dataset|using the|tested on)\b",
    re.IGNORECASE,
)
ADDRESSES_CUES = re.compile(
    r"\b(address|addresses|addressing|to overcome|mitigates|resolves|tackles|alleviates|circumvents|solves the bottleneck)\b",
    re.IGNORECASE,
)
SUPPORTS_CUES = re.compile(
    r"\b(confirms|demonstrates|validates|supports the hypothesis|consistent with|corroborates|proves the efficacy)\b",
    re.IGNORECASE,
)
CONTRADICTS_CUES = re.compile(
    r"\b(contradicts|contrary to|disputes|fails to reproduce|in contrast to prior|does not hold|refutes|inconsistent with)\b",
    re.IGNORECASE,
)


class RelationshipBuilder:
    """Builder responsible for synthesizing evidence-grounded relationships between graph nodes."""

    @classmethod
    def create_edge_dict(
        cls,
        source: str,
        target: str,
        relationship: str,
        source_paper_id: Optional[int] = None,
        source_paper_title: Optional[str] = None,
        source_sentence_id: Optional[int] = None,
        section_name: Optional[str] = "General",
        page_number: Optional[int] = 1,
        source_text: Optional[str] = None,
        confidence: float = 0.85,
        extraction_method: str = "rule_based_relation",
    ) -> Dict[str, Any]:
        """Construct a validated edge record with strict provenance."""
        edge_id = f"{source}->{relationship}->{target}"
        return {
            "id": edge_id,
            "source": source,
            "target": target,
            "relationship": relationship,
            "confidence": round(max(0.0, min(1.0, float(confidence))), 4),
            "extraction_method": extraction_method,
            "provenance": GraphProvenanceService.create_provenance(
                paper_id=source_paper_id,
                paper_title=source_paper_title,
                sentence_id=source_sentence_id,
                section_name=section_name or "General",
                page_number=page_number or 1,
                source_text=source_text,
                confidence=confidence,
                extraction_method=extraction_method,
            ),
        }

    @classmethod
    def infer_method_relationship(
        cls,
        text: str,
    ) -> Tuple[str, float]:
        """Classify relationship type between Paper/Author and a mentioned Method.

        Returns:
            Tuple of (relation_type, confidence)
        """
        if PROPOSES_CUES.search(text):
            return RelationTypes.PROPOSES, 0.95
        if EXTENDS_CUES.search(text):
            return RelationTypes.EXTENDS, 0.90
        if COMPARES_CUES.search(text):
            return RelationTypes.COMPARES, 0.85
        if USES_CUES.search(text):
            return RelationTypes.USES, 0.88
        return RelationTypes.USES, 0.75

    @classmethod
    def build_citation_edge(
        cls,
        citing_paper_id: int,
        cited_paper_id: int,
        context_text: Optional[str] = None,
        citing_title: Optional[str] = None,
        page_number: int = 1,
    ) -> Dict[str, Any]:
        """Construct a 'cites' relationship between two papers."""
        source_node = f"paper:{citing_paper_id}"
        target_node = f"paper:{cited_paper_id}"
        return cls.create_edge_dict(
            source=source_node,
            target=target_node,
            relationship=RelationTypes.CITES,
            source_paper_id=citing_paper_id,
            source_paper_title=citing_title,
            section_name="References",
            page_number=page_number,
            source_text=context_text or f"Paper #{citing_paper_id} references Paper #{cited_paper_id}",
            confidence=0.98,
            extraction_method="bibliographic_citation_match",
        )

    @classmethod
    def build_topic_membership_edge(
        cls,
        paper_id: int,
        topic_id: int,
        probability: float = 1.0,
        paper_title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Construct a 'belongs_to' relationship between Paper and ResearchTopic."""
        source_node = f"paper:{paper_id}"
        target_node = f"topic:{topic_id}"
        return cls.create_edge_dict(
            source=source_node,
            target=target_node,
            relationship=RelationTypes.BELONGS_TO,
            source_paper_id=paper_id,
            source_paper_title=paper_title,
            section_name="Research Landscape",
            page_number=1,
            source_text=f"Assigned to discovered Topic #{topic_id} (prob: {probability:.2f})",
            confidence=max(0.60, min(1.0, float(probability))),
            extraction_method="bertopic_clustering",
        )

    @classmethod
    def build_limitation_edge(
        cls,
        paper_id: int,
        limitation_node_id: str,
        limitation_text: str,
        section_name: str = "Limitations",
        page_number: int = 1,
        sentence_id: Optional[int] = None,
        paper_title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Construct a 'limited_by' relationship between Paper and Limitation."""
        source_node = f"paper:{paper_id}"
        return cls.create_edge_dict(
            source=source_node,
            target=limitation_node_id,
            relationship=RelationTypes.LIMITED_BY,
            source_paper_id=paper_id,
            source_paper_title=paper_title,
            source_sentence_id=sentence_id,
            section_name=section_name,
            page_number=page_number,
            source_text=limitation_text,
            confidence=0.92,
            extraction_method="limitation_detector",
        )

    @classmethod
    def build_addresses_limitation_edge(
        cls,
        solving_paper_id: int,
        limitation_node_id: str,
        evidence_text: str,
        solving_title: Optional[str] = None,
        section_name: str = "Introduction",
        page_number: int = 1,
        confidence: float = 0.85,
    ) -> Dict[str, Any]:
        """Construct an 'addresses' relationship between a Paper and a Limitation."""
        source_node = f"paper:{solving_paper_id}"
        return cls.create_edge_dict(
            source=source_node,
            target=limitation_node_id,
            relationship=RelationTypes.ADDRESSES,
            source_paper_id=solving_paper_id,
            source_paper_title=solving_title,
            section_name=section_name,
            page_number=page_number,
            source_text=evidence_text,
            confidence=confidence,
            extraction_method="semantic_limitation_alignment",
        )

    @classmethod
    def build_claim_alignment_edge(
        cls,
        source_node_id: str,
        target_node_id: str,
        source_text: str,
        target_text: str,
        paper_id: Optional[int] = None,
        paper_title: Optional[str] = None,
        similarity_score: float = 0.80,
    ) -> Optional[Dict[str, Any]]:
        """Construct a 'supports' or 'contradicts' relationship based on polarity and semantic overlap."""
        # Polarity check
        is_contradiction = bool(CONTRADICTS_CUES.search(source_text) or CONTRADICTS_CUES.search(target_text))
        is_support = bool(SUPPORTS_CUES.search(source_text) or SUPPORTS_CUES.search(target_text)) or similarity_score >= 0.75

        if is_contradiction:
            rel = RelationTypes.CONTRADICTS
            conf = min(0.95, similarity_score + 0.1) if similarity_score > 0 else 0.85
        elif is_support:
            rel = RelationTypes.SUPPORTS
            conf = min(0.95, similarity_score)
        else:
            return None

        return cls.create_edge_dict(
            source=source_node_id,
            target=target_node_id,
            relationship=rel,
            source_paper_id=paper_id,
            source_paper_title=paper_title,
            section_name="Discussion",
            page_number=1,
            source_text=f"Claim: '{source_text[:100]}' {rel} target: '{target_text[:100]}'",
            confidence=conf,
            extraction_method="semantic_claim_verification",
        )
