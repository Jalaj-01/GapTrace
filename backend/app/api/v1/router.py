"""API v1 master router mounting all versioned endpoint collections."""

from fastapi import APIRouter
from backend.app.api.v1.endpoints import health, nlp, papers

api_v1_router = APIRouter()

api_v1_router.include_router(health.router, tags=["Health"])
api_v1_router.include_router(papers.router, prefix="/papers", tags=["Papers"])
api_v1_router.include_router(nlp.router, tags=["Scientific NLP"])

