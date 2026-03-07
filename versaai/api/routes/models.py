"""
Models Route — /v1/models endpoint for listing available models.
"""

import logging

from fastapi import APIRouter, HTTPException

from versaai.api.schemas import ModelInfo, ModelListResponse
from versaai.api.provider_registry import get_registry

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/v1/models", response_model=ModelListResponse)
async def list_models():
    """
    List all available models across all providers.

    Returns OpenAI-compatible model list. Each model ID includes the
    provider prefix: "ollama/qwen2.5-coder:7b", "llamacpp/default".
    """
    try:
        registry = get_registry()
        raw_models = registry.list_models()

        models = [
            ModelInfo(
                id=m["id"],
                owned_by=m.get("provider", "versaai"),
                provider=m.get("provider", "unknown"),
                size=m.get("size"),
                description=f"{m.get('parameter_size', '')} {m.get('quantization', '')}".strip() or None,
            )
            for m in raw_models
        ]

        return ModelListResponse(data=models)

    except Exception as e:
        logger.error(f"Failed to list models: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list models: {e}")
