"""Health check endpoint."""

import structlog
from fastapi import APIRouter, status
from pydantic import BaseModel

logger = structlog.get_logger()

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    version: str
    services: dict[str, str]


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check"
)
async def health_check() -> HealthResponse:
    """Check application health and service status.
    
    Returns:
        Health status with service availability
    """
    # TODO: Check Redis, ChromaDB, Ollama connectivity
    services = {
        "redis": "unknown",
        "chromadb": "unknown",
        "ollama": "unknown",
    }

    logger.debug("health_check_requested")

    return HealthResponse(
        status="healthy",
        version="0.1.0",
        services=services
    )
