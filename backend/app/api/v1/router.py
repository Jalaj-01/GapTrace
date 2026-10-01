"""API v1 master router mounting all versioned endpoint collections."""

from fastapi import APIRouter
from backend.app.api.v1.endpoints import evidence, gaps, graph, health, nlp, papers, search, topics

api_v1_router = APIRouter()

api_v1_router.include_router(health.router, tags=["Health"])
api_v1_router.include_router(papers.router, prefix="/papers", tags=["Papers"])
api_v1_router.include_router(nlp.router, tags=["Scientific NLP"])
api_v1_router.include_router(search.router, prefix="/search", tags=["Semantic Search"])
api_v1_router.include_router(evidence.router, prefix="/evidence", tags=["Evidence Retrieval"])
api_v1_router.include_router(topics.router, prefix="/topics", tags=["Research Landscape & Topics"])
api_v1_router.include_router(graph.router, prefix="/graph", tags=["Research Knowledge Graph"])
api_v1_router.include_router(gaps.router, prefix="/gaps", tags=["Research Gap Engine"])

