"""
Settings API routes — runtime configuration management.

Endpoints:
    GET   /v1/settings          — Return current runtime configuration
    PATCH /v1/settings          — Update runtime settings (validated)
    GET   /v1/settings/models   — List available models from active providers
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator

from versaai.config import settings
from versaai.api.provider_registry import get_registry
from versaai.api.errors import InvalidRequestError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/settings")


# ============================================================================
# Schemas
# ============================================================================

class ProviderSettingsView(BaseModel):
    """Read-only view of a provider's settings."""
    enabled: bool
    base_url: Optional[str] = None
    default_model: Optional[str] = None
    timeout: int = 120


class SettingsView(BaseModel):
    """Current runtime settings snapshot."""
    default_provider: str
    default_model: str
    temperature: float
    max_tokens: int
    providers: Dict[str, ProviderSettingsView]
    rag_enabled: bool
    rag_top_k: int


class SettingsUpdate(BaseModel):
    """Mutable runtime settings. All fields are optional — only provided fields are applied."""
    default_provider: Optional[str] = Field(
        default=None, description="Switch active provider: 'ollama', 'llamacpp'"
    )
    default_model: Optional[str] = Field(
        default=None, description="Default model for the active provider"
    )
    temperature: Optional[float] = Field(
        default=None, ge=0.0, le=2.0, description="Sampling temperature"
    )
    max_tokens: Optional[int] = Field(
        default=None, ge=1, le=131072, description="Max tokens per generation"
    )
    rag_enabled: Optional[bool] = Field(
        default=None, description="Enable/disable RAG pipeline"
    )
    rag_top_k: Optional[int] = Field(
        default=None, ge=1, le=50, description="RAG retrieval top-k"
    )

    @field_validator("default_provider")
    @classmethod
    def validate_provider(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("ollama", "llamacpp", "openai", "anthropic"):
            raise ValueError(f"Unknown provider: '{v}'")
        return v


class ModelInfo(BaseModel):
    """Information about an available model."""
    name: str
    provider: str
    size: Optional[str] = None
    quantization: Optional[str] = None
    modified_at: Optional[str] = None


class ModelsListResponse(BaseModel):
    """List of available models."""
    models: List[ModelInfo]


# ============================================================================
# Runtime state (mutable overrides on top of file-based config)
# ============================================================================

_runtime_overrides: Dict[str, Any] = {}


def _get_effective(key: str, default: Any) -> Any:
    """Return runtime override if set, else fall back to config default."""
    return _runtime_overrides.get(key, default)


# ============================================================================
# Endpoints
# ============================================================================

@router.get("", response_model=SettingsView)
async def get_settings():
    """Return the current runtime configuration snapshot."""
    registry = get_registry()
    provider_status = registry.check_providers()

    providers = {}
    for name in ("ollama", "llamacpp"):
        cfg = getattr(settings.models, name, None)
        if cfg:
            providers[name] = ProviderSettingsView(
                enabled=provider_status.get(name, False),
                base_url=getattr(cfg, "base_url", None),
                default_model=getattr(cfg, "default_model", None),
                timeout=getattr(cfg, "timeout", 120),
            )

    return SettingsView(
        default_provider=_get_effective(
            "default_provider", settings.models.default_provider,
        ),
        default_model=_get_effective(
            "default_model",
            getattr(
                getattr(settings.models, settings.models.default_provider, None),
                "default_model", "unknown",
            ),
        ),
        temperature=_get_effective("temperature", 0.7),
        max_tokens=_get_effective("max_tokens", 4096),
        providers=providers,
        rag_enabled=_get_effective("rag_enabled", settings.rag.enabled),
        rag_top_k=_get_effective("rag_top_k", settings.rag.top_k),
    )


@router.patch("", response_model=SettingsView)
async def update_settings(update: SettingsUpdate):
    """
    Update runtime settings. Only provided (non-null) fields are applied.

    Changes are effective immediately but do NOT persist across server restarts.
    """
    changes: Dict[str, Any] = {}

    if update.default_provider is not None:
        registry = get_registry()
        status = registry.check_providers()
        if not status.get(update.default_provider, False):
            raise InvalidRequestError(
                f"Provider '{update.default_provider}' is not available",
                param="default_provider",
            )
        _runtime_overrides["default_provider"] = update.default_provider
        changes["default_provider"] = update.default_provider

    if update.default_model is not None:
        _runtime_overrides["default_model"] = update.default_model
        changes["default_model"] = update.default_model

    if update.temperature is not None:
        _runtime_overrides["temperature"] = update.temperature
        changes["temperature"] = update.temperature

    if update.max_tokens is not None:
        _runtime_overrides["max_tokens"] = update.max_tokens
        changes["max_tokens"] = update.max_tokens

    if update.rag_enabled is not None:
        _runtime_overrides["rag_enabled"] = update.rag_enabled
        changes["rag_enabled"] = update.rag_enabled

    if update.rag_top_k is not None:
        _runtime_overrides["rag_top_k"] = update.rag_top_k
        changes["rag_top_k"] = update.rag_top_k

    logger.info(f"Settings updated: {changes}")

    return await get_settings()


@router.get("/models", response_model=ModelsListResponse)
async def list_models():
    """List models available from all active providers."""
    registry = get_registry()
    models_list: List[ModelInfo] = []

    try:
        raw_models = registry.list_models()
        for m in raw_models:
            size = None
            if m.get("size") and isinstance(m["size"], (int, float)):
                size = f"{m['size'] / (1024**3):.1f}GB"
            elif isinstance(m.get("size"), str):
                size = m["size"]

            models_list.append(ModelInfo(
                name=m.get("name", m.get("id", "unknown")),
                provider=m.get("provider", "unknown"),
                size=size,
                quantization=m.get("quantization"),
                modified_at=m.get("modified_at"),
            ))
    except Exception as exc:
        logger.warning(f"Failed to list models: {exc}")

    return ModelsListResponse(models=models_list)
