"""Domain models and Pydantic schemas for scientific papers, sections, and references."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin


# ==============================================================================
# SQLAlchemy ORM Models
# ==============================================================================

class Paper(Base, TimestampMixin):
    """SQLAlchemy model representing a scientific research paper."""

    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    doi: Mapped[Optional[str]] = mapped_column(String(128), unique=True, nullable=True, index=True)
    abstract: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    authors: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    publication_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    venue: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    sections: Mapped[List["PaperSection"]] = relationship(
        "PaperSection",
        back_populates="paper",
        cascade="all, delete-orphan",
        order_by="PaperSection.section_order",
    )
    references: Mapped[List["PaperReference"]] = relationship(
        "PaperReference",
        back_populates="paper",
        cascade="all, delete-orphan",
        order_by="PaperReference.ref_index",
    )
    scientific_sentences: Mapped[List["ScientificSentence"]] = relationship(
        "ScientificSentence",
        back_populates="paper",
        cascade="all, delete-orphan",
        order_by="ScientificSentence.sentence_order",
    )
    scientific_extractions: Mapped[List["ScientificExtraction"]] = relationship(
        "ScientificExtraction",
        back_populates="paper",
        cascade="all, delete-orphan",
        order_by="ScientificExtraction.id",
    )
    gaps: Mapped[List["ResearchGap"]] = relationship(
        "ResearchGap",
        back_populates="paper",
        cascade="all, delete-orphan",
    )
    evidence_embeddings: Mapped[List["EvidenceEmbedding"]] = relationship(
        "EvidenceEmbedding",
        back_populates="paper",
        cascade="all, delete-orphan",
        order_by="EvidenceEmbedding.id",
    )
    topic_assignments: Mapped[List["PaperTopicAssignment"]] = relationship(
        "PaperTopicAssignment",
        back_populates="paper",
        cascade="all, delete-orphan",
        order_by="PaperTopicAssignment.id",
    )


class PaperSection(Base, TimestampMixin):
    """Extracted structural section from a paper (e.g. Introduction, Limitations, Conclusion)."""

    __tablename__ = "paper_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    section_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    section_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    page_start: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    page_end: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    paragraphs: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)

    paper: Mapped["Paper"] = relationship("Paper", back_populates="sections")

    @property
    def text(self) -> str:
        """Alias for content to match JSON specification."""
        return self.content


class PaperReference(Base, TimestampMixin):
    """Parsed bibliographic reference cited in a paper."""

    __tablename__ = "paper_references"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    ref_index: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    authors: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    venue: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    paper: Mapped["Paper"] = relationship("Paper", back_populates="references")


class ScientificSentence(Base, TimestampMixin):
    """Segmented scientific sentence with full provenance tracking (Phase 2)."""

    __tablename__ = "scientific_sentences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True)
    paragraph_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sentence_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    section_name: Mapped[str] = mapped_column(String(128), default="Unknown", nullable=False, index=True)
    page_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    paper: Mapped["Paper"] = relationship("Paper", back_populates="scientific_sentences")
    extractions: Mapped[List["ScientificExtraction"]] = relationship(
        "ScientificExtraction",
        back_populates="sentence",
        cascade="all, delete-orphan",
        order_by="ScientificExtraction.id",
    )


class ScientificExtraction(Base, TimestampMixin):
    """Scientifically classified claim or entity with provenance (Phase 2)."""

    __tablename__ = "scientific_extractions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True)
    sentence_id: Mapped[int] = mapped_column(Integer, ForeignKey("scientific_sentences.id", ondelete="CASCADE"), nullable=False, index=True)
    extraction_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # PROBLEM, OBJECTIVE, METHOD, DATASET, METRIC, RESULT, LIMITATION, FUTURE_WORK, OTHER
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    extraction_method: Mapped[str] = mapped_column(String(128), default="rule_based", nullable=False)
    provenance: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    paper: Mapped["Paper"] = relationship("Paper", back_populates="scientific_extractions")
    sentence: Mapped["ScientificSentence"] = relationship("ScientificSentence", back_populates="extractions")


class ResearchGap(Base, TimestampMixin):
    """Candidate research gap, limitation, or open question identified in a paper (Phase 2+)."""

    __tablename__ = "research_gaps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    gap_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # limitation, contradiction, question
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    paper: Mapped["Paper"] = relationship("Paper", back_populates="gaps")


class EvidenceEmbedding(Base, TimestampMixin):
    """Stored embedding metadata for a scientific sentence or extraction (Phase 3)."""

    __tablename__ = "evidence_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    embedding_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    paper_id: Mapped[int] = mapped_column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True)
    sentence_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("scientific_sentences.id", ondelete="CASCADE"), nullable=True, index=True)
    extraction_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("scientific_extractions.id", ondelete="CASCADE"), nullable=True, index=True)
    section: Mapped[str] = mapped_column(String(128), default="Unknown", nullable=False, index=True)
    page: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    extraction_type: Mapped[str] = mapped_column(String(64), default="SENTENCE", nullable=False, index=True)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    embedding_dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    faiss_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    provenance: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    paper: Mapped["Paper"] = relationship("Paper", back_populates="evidence_embeddings")
    sentence: Mapped[Optional["ScientificSentence"]] = relationship("ScientificSentence")
    extraction: Mapped[Optional["ScientificExtraction"]] = relationship("ScientificExtraction")


class DiscoveredTopic(Base, TimestampMixin):
    """Discovered scientific research topic from semantic clustering and landscape discovery (Phase 4)."""

    __tablename__ = "discovered_topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    topic_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    representative_terms: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    representative_documents: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    paper_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sentence_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="PERSISTENT", nullable=False, index=True)
    topic_probability: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    temporal_distribution: Mapped[Dict[str, int]] = mapped_column(JSON, default=dict, nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), default="BERTopic", nullable=False)


class PaperTopicAssignment(Base, TimestampMixin):
    """Topic membership assignment linking papers to discovered research themes (Phase 4)."""

    __tablename__ = "paper_topic_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    probability: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    is_outlier: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    paper: Mapped["Paper"] = relationship("Paper", back_populates="topic_assignments")


# ==============================================================================
# Pydantic Schemas (API Data Contracts)
# ==============================================================================

class SectionJSON(BaseModel):
    name: str
    page_start: int
    page_end: int
    text: str
    paragraphs: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ReferenceJSON(BaseModel):
    ref_index: int
    raw_text: str
    title: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = None
    venue: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class StructuredPaperResponse(BaseModel):
    paper_id: int
    id: Optional[int] = None  # Compatibility alias
    title: str
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = None
    doi: Optional[str] = None
    abstract: Optional[str] = None
    venue: Optional[str] = None
    page_count: Optional[int] = None
    file_path: Optional[str] = None
    file_hash: str
    sections: List[SectionJSON] = Field(default_factory=list)
    references: List[ReferenceJSON] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class PaperBase(BaseModel):
    title: str = Field(..., max_length=512)
    doi: Optional[str] = Field(None, max_length=128)
    abstract: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    publication_year: Optional[int] = None
    venue: Optional[str] = None


class PaperCreate(PaperBase):
    file_hash: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    page_count: Optional[int] = None


class PaperRead(PaperBase):
    id: int
    file_hash: Optional[str] = None
    page_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HealthCheckResponse(BaseModel):
    status: str
    version: str
    environment: str
    timestamp: str
    database: Dict[str, Any]
    services: Dict[str, str]


# ==============================================================================
# Phase 2: Scientific NLP Schemas
# ==============================================================================

class ProvenanceSchema(BaseModel):
    paper_id: int
    section_name: str
    page_number: int
    paragraph_id: int
    sentence_id: Optional[int] = None
    sentence_order: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ScientificSentenceResponse(BaseModel):
    id: int
    paper_id: int
    paragraph_id: int
    sentence_order: int
    source_text: str
    section_name: str
    page_number: int

    model_config = ConfigDict(from_attributes=True)


class ScientificExtractionResponse(BaseModel):
    id: int
    paper_id: int
    sentence_id: int
    extraction_type: str
    extracted_text: str
    confidence: float
    extraction_method: str
    provenance: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaperNLPProcessResponse(BaseModel):
    paper_id: int
    title: str
    total_sentences: int
    total_extractions: int
    extractions_by_type: Dict[str, int]
    processed_at: str
    provenance_verified: bool = True


class LimitationExtractionResponse(BaseModel):
    id: int
    paper_id: int
    sentence_id: int
    limitation_text: str
    limitation_type: str  # computational, data_scarcity, generalization, methodological, generic
    confidence: float
    provenance: Dict[str, Any]
    section_name: str
    page_number: int

    model_config = ConfigDict(from_attributes=True)


class FutureWorkExtractionResponse(BaseModel):
    id: int
    paper_id: int
    sentence_id: int
    future_work_text: str
    confidence: float
    provenance: Dict[str, Any]
    section_name: str
    page_number: int

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# Phase 3: Semantic Retrieval & Evidence Search Schemas
# ==============================================================================

class EvidenceSearchResult(BaseModel):
    source_text: str
    similarity_score: float
    paper: Dict[str, Any]
    section: str
    page: int
    sentence: Optional[Dict[str, Any]] = None
    extraction_type: str
    provenance: Dict[str, Any] = Field(default_factory=dict)
    embedding_id: Optional[str] = None
    model_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class EvidenceSearchResponse(BaseModel):
    query: str
    total_results: int
    retrieval_method: str
    model_name: Optional[str] = None
    results: List[EvidenceSearchResult]


class EvidenceBatchEmbedResponse(BaseModel):
    total_papers: int
    total_embeddings_created: int
    model_name: str
    embedding_dimension: int
    index_total_vectors: int
    processed_at: str


# ==============================================================================
# Phase 4: Topic Discovery & Research Landscape Schemas
# ==============================================================================

class RepresentativeTermSchema(BaseModel):
    term: str
    weight: float


class TopicTrendPoint(BaseModel):
    year: int
    paper_count: int
    percentage: float = 0.0


class TopicSummaryResponse(BaseModel):
    topic_id: int
    topic_name: str
    status: str
    paper_count: int
    sentence_count: int
    representative_terms: List[RepresentativeTermSchema] = Field(default_factory=list)
    representative_documents: List[str] = Field(default_factory=list)
    temporal_distribution: Dict[str, int] = Field(default_factory=dict)
    topic_probability: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class TopicPaperItem(BaseModel):
    paper_id: int
    title: str
    year: Optional[int] = None
    venue: Optional[str] = None
    probability: float = 1.0
    is_outlier: bool = False


class TopicDetailResponse(BaseModel):
    topic_id: int
    topic_name: str
    status: str
    paper_count: int
    sentence_count: int
    representative_terms: List[RepresentativeTermSchema] = Field(default_factory=list)
    representative_documents: List[Dict[str, Any]] = Field(default_factory=list)
    trends: List[TopicTrendPoint] = Field(default_factory=list)
    papers: List[TopicPaperItem] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class TopicLandscapeOverviewResponse(BaseModel):
    total_topics: int
    total_papers_analyzed: int
    outlier_papers_count: int
    major_topics: List[TopicSummaryResponse] = Field(default_factory=list)
    emerging_topics: List[TopicSummaryResponse] = Field(default_factory=list)
    declining_topics: List[TopicSummaryResponse] = Field(default_factory=list)
    persistent_topics: List[TopicSummaryResponse] = Field(default_factory=list)
    all_topics: List[TopicSummaryResponse] = Field(default_factory=list)
    algorithm_used: str = "BERTopic"
    generated_at: str


# ==============================================================================
# Phase 5: Research Knowledge Graph Schemas
# ==============================================================================

class GraphNodeResponse(BaseModel):
    id: str
    label: str
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    provenance: Dict[str, Any] = Field(default_factory=dict)


class GraphEdgeResponse(BaseModel):
    id: str
    source: str
    target: str
    relationship: str
    confidence: float = 1.0
    extraction_method: str = "pipeline"
    provenance: Dict[str, Any] = Field(default_factory=dict)


class GraphSubgraphResponse(BaseModel):
    total_nodes: int
    total_edges: int
    nodes: List[GraphNodeResponse] = Field(default_factory=list)
    edges: List[GraphEdgeResponse] = Field(default_factory=list)


class GraphOverviewResponse(BaseModel):
    total_nodes: int
    total_edges: int
    density: float
    connected_components_count: int
    node_counts_by_type: Dict[str, int] = Field(default_factory=dict)
    edge_counts_by_type: Dict[str, int] = Field(default_factory=dict)
    last_built_at: Optional[str] = None
    graph_database_engine: str = "NetworkX"


class GraphQueryResponse(BaseModel):
    query_type: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    total_results: int
    results: List[Dict[str, Any]] = Field(default_factory=list)


# ==============================================================================
# Phase 6: Research Gap Candidate Schemas
# ==============================================================================

class GapEvidenceItem(BaseModel):
    paper_id: Optional[int] = None
    paper_title: Optional[str] = None
    sentence_id: Optional[int] = None
    section: Optional[str] = "Unknown"
    page: Optional[int] = 1
    source_text: str
    confidence: float = 1.0
    extraction_method: str = "pipeline"


class GapSignalContribution(BaseModel):
    signal_name: str
    signal_value: float
    weight: float
    contribution: float
    explanation: str


class ResearchGapCandidateResponse(BaseModel):
    gap_id: str
    title: str
    description: str
    gap_type: str
    verification_status: str = "potential_gap"  # Distinguish potential gap from verified gap
    supporting_papers: List[Dict[str, Any]] = Field(default_factory=list)
    supporting_evidence: List[GapEvidenceItem] = Field(default_factory=list)
    signals: Dict[str, float] = Field(default_factory=dict)
    signal_breakdown: List[GapSignalContribution] = Field(default_factory=list)
    gap_priority_score: float = Field(..., description="Prioritization ranking score (NOT probability of gap truth)")
    confidence: float = Field(..., ge=0.0, le=1.0)
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class GapCandidatesListResponse(BaseModel):
    total_candidates: int
    potential_gaps_count: int
    verified_gaps_count: int = 0
    scoring_formula: str
    candidates: List[ResearchGapCandidateResponse] = Field(default_factory=list)


class GapSignalsOverviewResponse(BaseModel):
    total_signals: int
    signal_definitions: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    scoring_formula: str
    weights: Dict[str, float] = Field(default_factory=dict)


# ==============================================================================
# Phase 7: Gap Genealogy & Lifecycle Schemas
# ==============================================================================

class GapLifecycleStatus(str, Enum):
    EMERGING = "EMERGING"
    PERSISTENT = "PERSISTENT"
    PARTIALLY_ADDRESSED = "PARTIALLY_ADDRESSED"
    ADDRESSED = "ADDRESSED"
    REOPENED = "REOPENED"
    UNCERTAIN = "UNCERTAIN"


class TimelineEventItem(BaseModel):
    event_id: str
    year: Optional[int] = None
    event_type: str  # limitation_identified, attempted_solution, partial_solution, limitation_persists, reopened_limitation, current_candidate_gap, retrospective_citation
    title: str
    source_paper: Optional[Dict[str, Any]] = None
    source_sentence: str
    relationship: str
    confidence: float = 1.0
    is_retrospective: bool = False
    details: Dict[str, Any] = Field(default_factory=dict)


class GapTimelineResponse(BaseModel):
    gap_id: str
    gap_title: str
    current_status: GapLifecycleStatus
    first_appearance_year: Optional[int] = None
    latest_evidence_year: Optional[int] = None
    total_events: int
    repeated_limitations_count: int
    attempted_solutions_count: int
    addressing_papers_count: int
    events: List[TimelineEventItem] = Field(default_factory=list)


class GenealogyTransitionItem(BaseModel):
    step_number: int
    stage_name: str
    description: str
    source_paper: Optional[Dict[str, Any]] = None
    source_sentence: str
    year: Optional[int] = None
    relationship: str
    confidence: float = 1.0


class GapGenealogyResponse(BaseModel):
    gap_id: str
    gap_title: str
    root_limitation: str
    evolutionary_chain: List[str]
    total_transitions: int
    transitions: List[GenealogyTransitionItem] = Field(default_factory=list)
    summary: str


class GapLifecycleDetailResponse(BaseModel):
    gap_id: str
    gap_title: str
    status: GapLifecycleStatus
    status_reasoning: str
    evidence_paper_count: int
    year_span: int
    first_year: Optional[int] = None
    latest_year: Optional[int] = None
    has_attempted_solutions: bool
    is_addressed: bool
    is_reopened: bool
    confidence: float
    supporting_events_count: int


class GapLifecycleOverviewItem(BaseModel):
    gap_id: str
    gap_title: str
    gap_type: str
    status: GapLifecycleStatus
    priority_score: float
    year_span: int
    paper_count: int


class GapLifecycleOverviewResponse(BaseModel):
    total_gaps: int
    status_counts: Dict[str, int]
    gaps: List[GapLifecycleOverviewItem] = Field(default_factory=list)


# ==============================================================================
# Phase 8: Counter-Evidence Search & Gap Verification Schemas
# ==============================================================================

class EvidenceType(str, Enum):
    SUPPORTING = "SUPPORTING"
    COUNTER = "COUNTER"
    ADDRESSED_BY = "ADDRESSED_BY"
    CONTRADICTORY = "CONTRADICTORY"
    OUTDATED = "OUTDATED"
    UNCERTAIN = "UNCERTAIN"


class NLILabel(str, Enum):
    ENTAILMENT = "ENTAILMENT"
    CONTRADICTION = "CONTRADICTION"
    NEUTRAL = "NEUTRAL"


class NLIEvaluationResult(BaseModel):
    label: NLILabel
    confidence: float
    model: str
    source_sentence: str


class CategorizedEvidenceItem(BaseModel):
    evidence_id: str
    evidence_type: EvidenceType
    paper_id: Optional[int] = None
    paper_title: Optional[str] = None
    publication_year: Optional[int] = None
    source_text: str
    section: Optional[str] = "Unknown"
    confidence: float = 1.0
    nli_result: Optional[NLIEvaluationResult] = None
    retrieval_similarity: float = 0.0


class GapEvidenceDates(BaseModel):
    earliest_year: Optional[int] = None
    latest_year: Optional[int] = None
    supporting_years: List[int] = Field(default_factory=list)
    counter_years: List[int] = Field(default_factory=list)
    addressed_years: List[int] = Field(default_factory=list)


class GapVerificationFinalStatus(str, Enum):
    VERIFIED_OPEN = "VERIFIED_OPEN"
    REFUTED = "REFUTED"
    ADDRESSED = "ADDRESSED"
    PARTIALLY_ADDRESSED = "PARTIALLY_ADDRESSED"
    OUTDATED = "OUTDATED"
    UNCERTAIN = "UNCERTAIN"


class GapVerificationResponse(BaseModel):
    gap_id: str
    gap_title: str
    supporting_evidence: List[CategorizedEvidenceItem] = Field(default_factory=list)
    counter_evidence: List[CategorizedEvidenceItem] = Field(default_factory=list)
    addressed_by_evidence: List[CategorizedEvidenceItem] = Field(default_factory=list)
    contradictory_evidence: List[CategorizedEvidenceItem] = Field(default_factory=list)
    evidence_dates: GapEvidenceDates
    verification_confidence: float
    final_status: GapVerificationFinalStatus
    status_reasoning: str
    nli_distribution: Dict[str, int] = Field(default_factory=dict)
    verified_at: str


class GapCounterEvidenceResponse(BaseModel):
    gap_id: str
    gap_title: str
    counter_evidence: List[CategorizedEvidenceItem] = Field(default_factory=list)
    addressed_by_evidence: List[CategorizedEvidenceItem] = Field(default_factory=list)
    contradictory_evidence: List[CategorizedEvidenceItem] = Field(default_factory=list)
    total_counter_items: int
    strongest_refutation: Optional[str] = None


class GapVerifyRequest(BaseModel):
    min_confidence: float = 0.60
    include_nli: bool = True


# ==============================================================================
# Phase 9: Evidence-Grounded RAG and LLM Synthesis Schemas
# ==============================================================================

class CitationSource(BaseModel):
    """Grounded reference mapping an inline citation tag (e.g., [E1]) to source provenance."""
    citation_id: str = Field(..., description="Citation marker key, e.g. 'E1'")
    paper_id: Optional[int] = Field(None, description="Database paper identifier")
    paper_title: Optional[str] = Field(None, description="Title of the source publication")
    publication_year: Optional[int] = Field(None, description="Publication year")
    page: Optional[int] = Field(1, description="Page number where evidence appears")
    section: Optional[str] = Field("Unknown", description="Section header")
    sentence_id: Optional[int] = Field(None, description="Sentence database identifier")
    sentence_text: str = Field(..., description="Exact or verbatim source evidence sentence")
    evidence_type: Optional[str] = Field("RETRIEVED", description="Type of evidence: SUPPORTING, COUNTER, ADDRESSED_BY, RETRIEVED, GRAPH")
    similarity_score: Optional[float] = Field(None, description="Dense retrieval similarity score")


class ClaimValidationStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    HALLUCINATED_CITATION = "HALLUCINATED_CITATION"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ClaimValidationItem(BaseModel):
    """Validation analysis for an individual claim statement extracted from generated text."""
    claim_text: str
    cited_ids: List[str] = Field(default_factory=list, description="Extracted citation keys, e.g. ['E1', 'E2']")
    status: ClaimValidationStatus
    support_score: float = Field(..., ge=0.0, le=1.0, description="Confidence that cited evidence supports the claim")
    explanation: str
    matching_sources: List[CitationSource] = Field(default_factory=list)


class CitationValidationReport(BaseModel):
    """Automated citation and factuality report evaluating LLM output against retrieved evidence."""
    total_claims: int
    claims_with_citations: int
    supported_claims: int
    unsupported_claims: int
    contradicted_claims: int
    hallucinated_citations: int
    evidence_support_rate: float = Field(..., ge=0.0, le=1.0, description="Ratio of supported claims to claims with citations")
    is_valid: bool = Field(..., description="True if evidence support rate meets minimum threshold and no hallucinated citations")
    rejection_reasons: List[str] = Field(default_factory=list)
    claims: List[ClaimValidationItem] = Field(default_factory=list)


class GapSynthesisResponse(BaseModel):
    """Evidence-grounded synthesis of a verified research gap generated by an LLM."""
    gap_id: str
    gap_title: str
    provider: str
    model: str
    gap_explanation: str
    why_it_matters: str
    supporting_evidence_summary: str
    counter_evidence_summary: str
    current_status: str
    potential_research_questions: List[str] = Field(default_factory=list)
    potential_future_directions: List[str] = Field(default_factory=list)
    evidence_limitations: str
    insufficient_evidence: bool = Field(False, description="Flagged true if evidence is inadequate or sparse")
    citations: Dict[str, CitationSource] = Field(default_factory=dict, description="Map of citation tags (e.g. 'E1') to source evidence")
    validation_report: Optional[CitationValidationReport] = None
    synthesized_at: str
    raw_prompt: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GapSynthesizeRequest(BaseModel):
    """Request payload to trigger LLM synthesis for a research gap."""
    provider: Optional[str] = Field(None, description="LLM provider: gemini, openai, local, mock")
    model: Optional[str] = Field(None, description="Model identifier override")
    temperature: float = Field(0.2, ge=0.0, le=1.0)
    max_tokens: int = Field(1500, ge=100, le=4096)
    top_k_evidence: int = Field(10, ge=1, le=50, description="Number of retrieved evidence passages to feed into context")
    validate_citations: bool = Field(True, description="Whether to run automated citation validator")
    reject_unsupported: bool = Field(False, description="Whether to reject/filter unsupported claims")


class CitationValidationRequest(BaseModel):
    """Standalone request to validate citations in arbitrary text against provided evidence dictionary."""
    text: str = Field(..., description="Text containing citation tags like [E1], [E2]")
    citations: Dict[str, CitationSource] = Field(..., description="Map of citation tags to source references")
    min_support_score: float = Field(0.60, ge=0.0, le=1.0)




