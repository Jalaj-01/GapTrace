"""Research Topics and Scientific Landscape API Endpoints (Phase 4).

Exposes:
- POST /api/v1/topics/discover
- GET  /api/v1/topics
- GET  /api/v1/topics/overview
- GET  /api/v1/topics/trends
- GET  /api/v1/topics/{topic_id}
- GET  /api/v1/topics/{topic_id}/trends
- GET  /api/v1/topics/{topic_id}/papers
- GET  /api/v1/topics/{topic_id}/evidence
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.paper import (
    TopicDetailResponse,
    TopicLandscapeOverviewResponse,
    TopicPaperItem,
    TopicSummaryResponse,
)
from backend.app.services.landscape.landscape_service import get_landscape_service

router = APIRouter()


@router.post(
    "/discover",
    response_model=TopicLandscapeOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Discover Research Landscape & Topic Themes",
    description="Executes semantic clustering on scientific papers to identify major, emerging, declining, and persistent topics.",
)
def discover_topics_endpoint(
    min_cluster_size: int = Query(2, ge=2, le=20, description="Minimum papers per cluster"),
    db: Session = Depends(get_db),
) -> TopicLandscapeOverviewResponse:
    """Discover research themes, trends, and trajectory classifications across the ingested paper corpus."""
    landscape_svc = get_landscape_service()
    return landscape_svc.discover_landscape(db=db, min_cluster_size=min_cluster_size)


@router.get(
    "",
    response_model=List[TopicSummaryResponse],
    summary="List Discovered Research Topics",
    description="Retrieve all discovered research topics with representative terms, paper counts, and trajectories.",
)
def list_topics_endpoint(
    db: Session = Depends(get_db),
) -> List[TopicSummaryResponse]:
    """List all discovered research topics."""
    landscape_svc = get_landscape_service()
    return landscape_svc.list_topics(db=db)


@router.get(
    "/overview",
    response_model=TopicLandscapeOverviewResponse,
    summary="Landscape Overview & Categorized Themes",
    description="Returns categorized topics (major, emerging, declining, persistent, and outliers) for dashboard visualization.",
)
def get_landscape_overview_endpoint(
    db: Session = Depends(get_db),
) -> TopicLandscapeOverviewResponse:
    """Retrieve full research landscape categorized overview."""
    landscape_svc = get_landscape_service()
    # If no topics discovered yet, run initial discovery
    existing = landscape_svc.list_topics(db)
    if not existing:
        return landscape_svc.discover_landscape(db=db)
    # Re-run or return structured overview
    return landscape_svc.discover_landscape(db=db)


@router.get(
    "/trends",
    summary="Longitudinal Topic Trends Across Years",
    description="Retrieve year-by-year paper volume progression for all topics or a specific topic.",
)
def get_topic_trends_endpoint(
    topic_id: Optional[int] = Query(None, description="Optional topic ID to filter trends"),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Retrieve temporal trend timeseries points."""
    landscape_svc = get_landscape_service()
    return landscape_svc.get_topic_trends(topic_id=topic_id, db=db)


@router.get(
    "/{topic_id}",
    response_model=TopicDetailResponse,
    summary="Topic Details, Papers & Evidence",
    description="Retrieve comprehensive detail for a single topic including member papers, trends, and evidence snippets.",
)
def get_topic_detail_endpoint(
    topic_id: int,
    db: Session = Depends(get_db),
) -> TopicDetailResponse:
    """Retrieve comprehensive topic detail."""
    landscape_svc = get_landscape_service()
    return landscape_svc.get_topic_detail(topic_id=topic_id, db=db)


@router.get(
    "/{topic_id}/trends",
    summary="Topic Temporal Trends",
    description="Retrieve year-by-year paper counts and percentages for a specific topic.",
)
def get_single_topic_trends_endpoint(
    topic_id: int,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve yearly progression for a specific topic."""
    landscape_svc = get_landscape_service()
    trends = landscape_svc.get_topic_trends(topic_id=topic_id, db=db)
    return trends[0] if trends else {"topic_id": topic_id, "trends": []}


@router.get(
    "/{topic_id}/papers",
    response_model=List[TopicPaperItem],
    summary="Papers Belonging to Topic",
    description="Retrieve list of papers assigned to a given research topic with membership probability.",
)
def get_topic_papers_endpoint(
    topic_id: int,
    db: Session = Depends(get_db),
) -> List[TopicPaperItem]:
    """Retrieve papers assigned to topic."""
    landscape_svc = get_landscape_service()
    return landscape_svc.get_topic_papers(topic_id=topic_id, db=db)


@router.get(
    "/{topic_id}/evidence",
    summary="Representative Evidence in Topic",
    description="Retrieve representative text snippets and evidence grounded in the topic cluster.",
)
def get_topic_evidence_endpoint(
    topic_id: int,
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Retrieve representative evidence in topic."""
    landscape_svc = get_landscape_service()
    return landscape_svc.get_topic_evidence(topic_id=topic_id, db=db)
