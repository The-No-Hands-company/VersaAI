"""
Health Route — /health and /v1/health endpoints.
"""

import logging
import time

from fastapi import APIRouter

from versaai.api.schemas import HealthResponse
from versaai.api.provider_registry import get_registry
from versaai.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

_start_time = time.time()


@router.get("/health", response_model=HealthResponse)
@router.get("/v1/health", response_model=HealthResponse)
async def health_check():
    """
    Server health check.

    Returns:
    - Server status
    - Version
    - Provider availability (Ollama, llama.cpp)
    - Uptime
    """
    registry = get_registry()
    providers = registry.check_providers()

    return HealthResponse(
        status="ok",
        version=settings.version,
        providers=providers,
        uptime_seconds=round(time.time() - _start_time, 2),
    )
