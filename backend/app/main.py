"""FastAPI Application Entry Point."""

from contextlib import asynccontextmanager
from pathlib import Path
import sys
from typing import AsyncGenerator

# Ensure repository root is on sys.path for direct execution or script invocation
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.app.api.v1.router import api_v1_router
from backend.app.core.config import settings
from backend.app.core.errors import register_error_handlers
from backend.app.core.logging import get_logger, setup_logging
from backend.app.db.base import Base
from backend.app.db.session import engine
import backend.app.models.paper  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for application startup and shutdown events."""
    # 1. Initialize logging
    setup_logging(level=settings.LOG_LEVEL, log_format=settings.LOG_FORMAT)
    logger = get_logger("app.main")
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]")

    # 2. Initialize database schema tables if needed
    try:
        logger.info(f"Checking/initializing database tables (Dialect: {engine.dialect.name})...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema initialized successfully.")
    except Exception as exc:
        logger.warning(f"Could not automatically create database tables during startup: {exc}")

    yield

    logger.info("Application shutdown completed.")


def create_application() -> FastAPI:
    """Application factory for FastAPI instance."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=(
            "Evidence-grounded NLP system analyzing scientific papers to identify "
            "potential research gaps, limitations, emerging topics, and candidate questions."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # 1. Configure CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Register Centralized Error Handlers
    register_error_handlers(app)

    # 3. Mount Versioned API Routers
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    # 4. Root information endpoint
    @app.get("/", tags=["Root"])
    async def root_info() -> JSONResponse:
        return JSONResponse(
            content={
                "project": settings.PROJECT_NAME,
                "version": settings.VERSION,
                "environment": settings.ENVIRONMENT,
                "documentation": "/docs",
                "health_check": f"{settings.API_V1_PREFIX}/health",
                "phase": "Phase 11 - Final Experimental Evaluation (Phases 0-11 Complete)",
            }
        )

    return app


app = create_application()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
