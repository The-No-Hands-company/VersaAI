"""
VersaAI API Server — FastAPI application with OpenAI-compatible endpoints.

This is the central hub of VersaAI. All clients (CLI, Tauri desktop,
editor plugins, external tools) connect through this server.

Endpoints:
    POST /v1/chat/completions  — Chat (streaming & non-streaming)
    GET  /v1/models            — List available models
    GET  /health               — Health check

Usage:
    # Development (with auto-reload)
    uvicorn versaai.api.app:app --reload --host 0.0.0.0 --port 8000

    # Production
    uvicorn versaai.api.app:app --host 0.0.0.0 --port 8000 --workers 1

    # Or via CLI
    versaai serve
"""

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from versaai.config import settings
from versaai.api.provider_registry import get_registry
from versaai.api.routes import chat, models, health, agents, rag, memory

# ============================================================================
# Logging
# ============================================================================

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("versaai.api")


# ============================================================================
# Lifespan — startup/shutdown
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Startup:
    - Initialize provider registry
    - Check provider availability
    - Log status

    Shutdown:
    - Close all provider connections
    - Cleanup resources
    """
    # --- Startup ---
    logger.info(f"VersaAI API v{settings.version} starting...")
    logger.info(f"  Default provider: {settings.models.default_provider}")
    logger.info(f"  Debug mode: {settings.debug}")

    registry = get_registry()
    provider_status = registry.check_providers()

    for name, available in provider_status.items():
        status = "available" if available else "unavailable"
        logger.info(f"  Provider {name}: {status}")

    if not any(provider_status.values()):
        logger.warning(
            "No inference providers available. "
            "Start Ollama (ollama serve) or llama.cpp server."
        )

    logger.info(
        f"VersaAI API ready at http://{settings.server.host}:{settings.server.port}"
    )

    yield

    # --- Shutdown ---
    logger.info("VersaAI API shutting down...")
    await registry.close_async()
    logger.info("All providers closed. Goodbye.")


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="VersaAI",
    description=(
        "VersaAI API Server — OpenAI-compatible inference API. "
        "Supports Ollama and llama.cpp backends for local AI inference."
    ),
    version=settings.version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)


# ============================================================================
# Middleware
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.server.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Global exception handler
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions. Returns OpenAI-compatible error."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": f"Internal server error: {type(exc).__name__}",
                "type": "server_error",
                "param": None,
                "code": None,
            }
        },
    )


# ============================================================================
# Route registration
# ============================================================================

app.include_router(chat.router, tags=["Chat"])
app.include_router(models.router, tags=["Models"])
app.include_router(health.router, tags=["Health"])
app.include_router(agents.router, tags=["Agents"])
app.include_router(rag.router, tags=["RAG"])
app.include_router(memory.router, tags=["Memory"])


# ============================================================================
# Root
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint — basic info redirect."""
    return {
        "name": "VersaAI",
        "version": settings.version,
        "docs": "/docs" if settings.debug else "Enable debug mode for docs",
        "health": "/health",
        "api": "/v1/chat/completions",
    }
