"""Health check endpoint providing runtime diagnostics."""

from datetime import datetime, timezone
import platform
from fastapi import APIRouter, status
from backend.app.core.config import settings
from backend.app.db.session import check_db_connection
from backend.app.models.paper import HealthCheckResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Service Health Diagnostics",
    description="Returns backend health, database connectivity status, and system metadata.",
)
async def get_health() -> HealthCheckResponse:
    db_diagnostics = check_db_connection()
    overall_status = "healthy" if db_diagnostics.get("status") == "connected" else "degraded"

    return HealthCheckResponse(
        status=overall_status,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc).isoformat(),
        database=db_diagnostics,
        services={
            "api": "operational",
            "llm_provider": settings.LLM_PROVIDER,
            "os": f"{platform.system()} {platform.release()}",
            "python": platform.python_version(),
        },
    )
