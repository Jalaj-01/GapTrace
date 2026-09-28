"""Domain models and Pydantic schemas for scientific papers, sections, and references."""

from datetime import datetime
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
    gaps: Mapped[List["ResearchGap"]] = relationship(
        "ResearchGap",
        back_populates="paper",
        cascade="all, delete-orphan",
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
