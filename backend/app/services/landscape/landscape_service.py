"""Research Landscape & Topic Discovery Orchestration Service (Phase 4).

Coordinates:
- Paper corpus extraction and evidence aggregation
- Unsupervised topic discovery via embeddings and c-TF-IDF
- Longitudinal temporal analysis and trajectory classification
- Database persistence (DiscoveredTopic and PaperTopicAssignment)
- Visualization-ready REST API serialization
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.core.logging import get_logger
from backend.app.core.errors import NotFoundError, ValidationError
from backend.app.models.paper import (
    DiscoveredTopic,
    Paper,
    PaperSection,
    PaperTopicAssignment,
    RepresentativeTermSchema,
    ScientificSentence,
    TopicDetailResponse,
    TopicLandscapeOverviewResponse,
    TopicPaperItem,
    TopicSummaryResponse,
    TopicTrendPoint,
)
from backend.app.services.landscape.temporal_analyzer import TemporalTopicAnalyzer
from backend.app.services.landscape.topic_modeler import (
    ScientificTopicModeler,
    get_topic_modeler,
)

logger = get_logger("app.landscape.service")


class ResearchLandscapeService:
    """Full-stack service orchestrating research landscape discovery and trend analysis."""

    def __init__(self, topic_modeler: Optional[ScientificTopicModeler] = None):
        self._topic_modeler = topic_modeler

    @property
    def topic_modeler(self) -> ScientificTopicModeler:
        if self._topic_modeler is None:
            self._topic_modeler = get_topic_modeler()
        return self._topic_modeler

    def discover_landscape(
        self,
        db: Session,
        min_cluster_size: int = 2,
    ) -> TopicLandscapeOverviewResponse:
        """Execute unsupervised topic discovery and temporal trajectory analysis across all ingested papers."""
        papers = db.scalars(select(Paper).order_by(Paper.id)).all()

        if not papers:
            logger.info("No papers found in database for landscape discovery.")
            return TopicLandscapeOverviewResponse(
                total_topics=0,
                total_papers_analyzed=0,
                outlier_papers_count=0,
                major_topics=[],
                emerging_topics=[],
                declining_topics=[],
                persistent_topics=[],
                all_topics=[],
                algorithm_used="BERTopic",
                generated_at=datetime.now(timezone.utc).isoformat(),
            )

        logger.info(f"Initiating Phase 4 Topic Discovery across {len(papers)} papers...")

        # 1. Prepare Document Text Units per Paper
        documents: List[str] = []
        doc_metadata: List[Dict[str, Any]] = []

        all_years_list: List[Optional[int]] = []
        for p in papers:
            all_years_list.append(p.publication_year)
            # Combine title + abstract + key sections
            sec_texts = [s.content for s in p.sections[:3] if s.content]
            combined_text = f"{p.title}. {p.abstract or ''} {' '.join(sec_texts)}".strip()
            if not combined_text:
                combined_text = p.title

            documents.append(combined_text)
            doc_metadata.append({
                "paper_id": p.id,
                "title": p.title,
                "year": p.publication_year,
                "venue": p.venue,
            })

        all_yearly_totals = TemporalTopicAnalyzer.compute_yearly_distribution(all_years_list)

        # 2. Run Topic Modeler
        self.topic_modeler.min_cluster_size = min_cluster_size
        labels, probabilities = self.topic_modeler.fit_transform(
            documents=documents,
            doc_metadata=doc_metadata,
        )
        topic_infos = self.topic_modeler.get_topic_info()

        # 3. Clean up prior stored topics in DB
        db.execute(delete(PaperTopicAssignment))
        db.execute(delete(DiscoveredTopic))
        db.flush()

        all_topic_summaries: List[TopicSummaryResponse] = []
        major_topics: List[TopicSummaryResponse] = []
        emerging_topics: List[TopicSummaryResponse] = []
        declining_topics: List[TopicSummaryResponse] = []
        persistent_topics: List[TopicSummaryResponse] = []
        outlier_count = 0

        # Sort topics by paper_count descending
        sorted_topic_infos = sorted(topic_infos, key=lambda x: x["paper_count"], reverse=True)

        for t_info in sorted_topic_infos:
            t_id = t_info["topic_id"]
            doc_indices = t_info.get("document_indices", [])

            # Compute year distribution for papers in this topic
            topic_years = [doc_metadata[i]["year"] for i in doc_indices]
            yearly_dist = TemporalTopicAnalyzer.compute_yearly_distribution(topic_years)

            # Trajectory classification
            status = TemporalTopicAnalyzer.classify_topic_trajectory(
                yearly_counts=yearly_dist,
                topic_id=t_id,
                total_corpus_papers=len(papers),
            )

            if t_id == -1:
                status = "OUTLIER"
                outlier_count = t_info["paper_count"]

            # Store in DB
            db_topic = DiscoveredTopic(
                topic_id=t_id,
                topic_name=t_info["topic_name"],
                representative_terms=t_info["representative_terms"],
                representative_documents=[{"text": d} for d in t_info["representative_documents"]],
                paper_count=t_info["paper_count"],
                sentence_count=t_info["sentence_count"],
                status=status,
                topic_probability=t_info.get("topic_probability"),
                temporal_distribution=yearly_dist,
                model_name="BERTopic",
            )
            db.add(db_topic)

            # Store paper assignments
            for idx in doc_indices:
                p_meta = doc_metadata[idx]
                db_assign = PaperTopicAssignment(
                    paper_id=p_meta["paper_id"],
                    topic_id=t_id,
                    probability=probabilities[idx] if idx < len(probabilities) else 1.0,
                    is_outlier=1 if t_id == -1 else 0,
                )
                db.add(db_assign)

            summary_item = TopicSummaryResponse(
                topic_id=t_id,
                topic_name=t_info["topic_name"],
                status=status,
                paper_count=t_info["paper_count"],
                sentence_count=t_info["sentence_count"],
                representative_terms=[RepresentativeTermSchema(**tm) for tm in t_info["representative_terms"]],
                representative_documents=t_info["representative_documents"],
                temporal_distribution=yearly_dist,
                topic_probability=t_info.get("topic_probability"),
            )

            all_topic_summaries.append(summary_item)

            if status == "EMERGING":
                emerging_topics.append(summary_item)
            elif status == "DECLINING":
                declining_topics.append(summary_item)
            elif status == "PERSISTENT":
                persistent_topics.append(summary_item)

        db.commit()

        # Identify major topics: top clusters by paper count (excluding outliers)
        non_outliers = [t for t in all_topic_summaries if t.topic_id != -1]
        major_cutoff = max(2, len(papers) // 4)
        major_topics = [t for t in non_outliers if t.paper_count >= major_cutoff or t in non_outliers[:2]]

        logger.info(
            f"Phase 4 Topic Discovery completed: {len(all_topic_summaries)} topics identified "
            f"({len(emerging_topics)} emerging, {len(declining_topics)} declining, {len(persistent_topics)} persistent)."
        )

        return TopicLandscapeOverviewResponse(
            total_topics=len(all_topic_summaries),
            total_papers_analyzed=len(papers),
            outlier_papers_count=outlier_count,
            major_topics=major_topics,
            emerging_topics=emerging_topics,
            declining_topics=declining_topics,
            persistent_topics=persistent_topics,
            all_topics=all_topic_summaries,
            algorithm_used="BERTopic",
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def list_topics(self, db: Session) -> List[TopicSummaryResponse]:
        """List all discovered research topics from database."""
        db_topics = db.scalars(select(DiscoveredTopic).order_by(DiscoveredTopic.paper_count.desc())).all()
        summaries = []
        for t in db_topics:
            rep_terms = [
                RepresentativeTermSchema(term=item["term"], weight=item.get("weight", 1.0))
                for item in t.representative_terms
            ]
            rep_docs = [
                item["text"] if isinstance(item, dict) else str(item)
                for item in t.representative_documents
            ]
            summaries.append(TopicSummaryResponse(
                topic_id=t.topic_id,
                topic_name=t.topic_name,
                status=t.status,
                paper_count=t.paper_count,
                sentence_count=t.sentence_count,
                representative_terms=rep_terms,
                representative_documents=rep_docs,
                temporal_distribution=t.temporal_distribution,
                topic_probability=t.topic_probability,
            ))
        return summaries

    def get_topic_detail(self, topic_id: int, db: Session) -> TopicDetailResponse:
        """Retrieve complete topic detail with member papers, trends, and representative evidence."""
        db_topic = db.scalar(select(DiscoveredTopic).where(DiscoveredTopic.topic_id == topic_id))
        if not db_topic:
            raise NotFoundError(f"Topic with ID {topic_id} not found.")

        # Get assigned papers
        assignments = db.scalars(
            select(PaperTopicAssignment)
            .where(PaperTopicAssignment.topic_id == topic_id)
            .order_by(PaperTopicAssignment.probability.desc())
        ).all()

        paper_ids = [a.paper_id for a in assignments]
        papers = db.scalars(select(Paper).where(Paper.id.in_(paper_ids))).all() if paper_ids else []
        paper_map = {p.id: p for p in papers}

        topic_papers = []
        for a in assignments:
            p = paper_map.get(a.paper_id)
            if p:
                topic_papers.append(TopicPaperItem(
                    paper_id=p.id,
                    title=p.title,
                    year=p.publication_year,
                    venue=p.venue,
                    probability=a.probability,
                    is_outlier=bool(a.is_outlier),
                ))

        # Trends
        trends = TemporalTopicAnalyzer.format_trend_points(db_topic.temporal_distribution)

        rep_terms = [
            RepresentativeTermSchema(term=item["term"], weight=item.get("weight", 1.0))
            for item in db_topic.representative_terms
        ]

        return TopicDetailResponse(
            topic_id=db_topic.topic_id,
            topic_name=db_topic.topic_name,
            status=db_topic.status,
            paper_count=db_topic.paper_count,
            sentence_count=db_topic.sentence_count,
            representative_terms=rep_terms,
            representative_documents=db_topic.representative_documents,
            trends=[TopicTrendPoint(**tr) for tr in trends],
            papers=topic_papers,
        )

    def get_topic_trends(self, topic_id: Optional[int], db: Session) -> List[Dict[str, Any]]:
        """Retrieve year-by-year trend progressions for a specific topic or all topics."""
        if topic_id is not None:
            db_topic = db.scalar(select(DiscoveredTopic).where(DiscoveredTopic.topic_id == topic_id))
            if not db_topic:
                raise NotFoundError(f"Topic with ID {topic_id} not found.")
            trends = TemporalTopicAnalyzer.format_trend_points(db_topic.temporal_distribution)
            return [{
                "topic_id": db_topic.topic_id,
                "topic_name": db_topic.topic_name,
                "status": db_topic.status,
                "trends": trends,
            }]
        else:
            topics = db.scalars(select(DiscoveredTopic).order_by(DiscoveredTopic.paper_count.desc())).all()
            all_trends = []
            for t in topics:
                tr = TemporalTopicAnalyzer.format_trend_points(t.temporal_distribution)
                all_trends.append({
                    "topic_id": t.topic_id,
                    "topic_name": t.topic_name,
                    "status": t.status,
                    "trends": tr,
                })
            return all_trends

    def get_topic_papers(self, topic_id: int, db: Session) -> List[TopicPaperItem]:
        """List papers belonging to a specified topic."""
        detail = self.get_topic_detail(topic_id, db)
        return detail.papers

    def get_topic_evidence(self, topic_id: int, db: Session) -> List[Dict[str, Any]]:
        """Retrieve representative evidence snippets for a specified topic."""
        detail = self.get_topic_detail(topic_id, db)
        return detail.representative_documents


# Singleton instance
_landscape_service_instance: Optional[ResearchLandscapeService] = None


def get_landscape_service() -> ResearchLandscapeService:
    """Retrieve global ResearchLandscapeService singleton."""
    global _landscape_service_instance
    if _landscape_service_instance is None:
        _landscape_service_instance = ResearchLandscapeService()
    return _landscape_service_instance
