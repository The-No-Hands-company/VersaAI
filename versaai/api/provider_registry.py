"""
Provider Registry — resolves model identifiers to inference providers.

Model ID format:  <provider>/<model_name>
    Examples:
        ollama/qwen2.5-coder:7b       → OllamaProvider
        llamacpp/default               → LlamaCppServerProvider
        ollama/llama3.1:70b            → OllamaProvider

    If no prefix is given, the default provider from config is used:
        qwen2.5-coder:7b              → default_provider/qwen2.5-coder:7b
"""

import asyncio
import logging
import random
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

import httpx

from versaai.config import settings
from versaai.models.ollama_provider import OllamaProvider
from versaai.models.llamacpp_provider import LlamaCppServerProvider

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ============================================================================
# Retry helper
# ============================================================================

_RETRIABLE_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.RemoteProtocolError,
    httpx.ReadTimeout,
    ConnectionError,
    OSError,
)


def retry_sync(
    fn: Callable[..., T],
    *,
    max_retries: int = 3,
    base_delay: float = 0.2,
    max_delay: float = 5.0,
) -> T:
    """
    Execute `fn()` with exponential-backoff retries on transient errors.

    Only retries on connection/protocol errors. Lets HTTP 4xx errors
    and non-transient failures propagate immediately.
    """
    last_exc: Exception = RuntimeError("unreachable")
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except _RETRIABLE_EXCEPTIONS as exc:
            last_exc = exc
            if attempt == max_retries:
                break
            delay = min(base_delay * (2 ** attempt) + random.uniform(0, 0.1), max_delay)
            logger.warning(
                f"Retry {attempt + 1}/{max_retries} after {type(exc).__name__}: "
                f"waiting {delay:.2f}s"
            )
            time.sleep(delay)
        except httpx.HTTPStatusError as exc:
            # 5xx are retriable, 4xx are not
            if exc.response.status_code >= 500 and attempt < max_retries:
                last_exc = exc
                delay = min(base_delay * (2 ** attempt) + random.uniform(0, 0.1), max_delay)
                logger.warning(
                    f"Retry {attempt + 1}/{max_retries} after HTTP {exc.response.status_code}: "
                    f"waiting {delay:.2f}s"
                )
                time.sleep(delay)
            else:
                raise
    raise last_exc


async def retry_async(
    fn: Callable[..., Any],
    *,
    max_retries: int = 3,
    base_delay: float = 0.2,
    max_delay: float = 5.0,
) -> Any:
    """
    Execute `await fn()` with exponential-backoff retries on transient errors.
    """
    last_exc: Exception = RuntimeError("unreachable")
    for attempt in range(max_retries + 1):
        try:
            return await fn()
        except _RETRIABLE_EXCEPTIONS as exc:
            last_exc = exc
            if attempt == max_retries:
                break
            delay = min(base_delay * (2 ** attempt) + random.uniform(0, 0.1), max_delay)
            logger.warning(
                f"Async retry {attempt + 1}/{max_retries} after {type(exc).__name__}: "
                f"waiting {delay:.2f}s"
            )
            await asyncio.sleep(delay)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code >= 500 and attempt < max_retries:
                last_exc = exc
                delay = min(base_delay * (2 ** attempt) + random.uniform(0, 0.1), max_delay)
                logger.warning(
                    f"Async retry {attempt + 1}/{max_retries} after HTTP {exc.response.status_code}: "
                    f"waiting {delay:.2f}s"
                )
                await asyncio.sleep(delay)
            else:
                raise
    raise last_exc


class ProviderRegistry:
    """
    Singleton registry managing inference provider instances.

    Providers are lazily initialized on first use and cached for reuse.
    Thread-safe via Python's GIL for initialization.
    """

    _instance: Optional["ProviderRegistry"] = None

    def __new__(cls) -> "ProviderRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._ollama: Optional[OllamaProvider] = None
        self._llamacpp: Optional[LlamaCppServerProvider] = None

        logger.info("ProviderRegistry initialized")

    # ------------------------------------------------------------------
    # Provider accessors (lazy init)
    # ------------------------------------------------------------------

    @property
    def ollama(self) -> OllamaProvider:
        if self._ollama is None:
            cfg = settings.models.ollama
            self._ollama = OllamaProvider(
                base_url=cfg.base_url,
                model=cfg.default_model,
                timeout=cfg.timeout,
            )
        return self._ollama

    @property
    def llamacpp(self) -> LlamaCppServerProvider:
        if self._llamacpp is None:
            cfg = settings.models.llamacpp
            base_url = cfg.base_url or "http://localhost:8080"
            self._llamacpp = LlamaCppServerProvider(
                base_url=base_url,
                timeout=cfg.timeout,
            )
        return self._llamacpp

    # ------------------------------------------------------------------
    # Model ID resolution
    # ------------------------------------------------------------------

    def parse_model_id(self, model_id: str) -> Tuple[str, str]:
        """
        Parse a model identifier into (provider, model_name).

        "ollama/qwen2.5-coder:7b"  →  ("ollama", "qwen2.5-coder:7b")
        "llamacpp/default"          →  ("llamacpp", "default")
        "qwen2.5-coder:7b"         →  ("<default_provider>", "qwen2.5-coder:7b")
        """
        if "/" in model_id:
            parts = model_id.split("/", 1)
            provider = parts[0].lower()
            model_name = parts[1]
            if provider in ("ollama", "llamacpp", "openai", "anthropic", "huggingface"):
                return provider, model_name
        # No recognized prefix → use default provider
        return settings.models.default_provider, model_id

    def get_provider_and_model(self, model_id: str) -> Tuple[Any, str]:
        """
        Resolve model ID to (provider_instance, model_name).

        Raises ValueError if provider is unknown or disabled.
        """
        provider_name, model_name = self.parse_model_id(model_id)

        if provider_name == "ollama":
            if not settings.models.ollama.enabled:
                raise ValueError("Ollama provider is disabled in configuration")
            return self.ollama, model_name

        elif provider_name == "llamacpp":
            if not settings.models.llamacpp.enabled:
                raise ValueError("llama.cpp provider is disabled in configuration")
            return self.llamacpp, model_name

        else:
            raise ValueError(
                f"Unknown provider '{provider_name}'. "
                f"Supported: ollama, llamacpp. Model ID: '{model_id}'"
            )

    def get_fallback_chain(self, model_id: str) -> List[Tuple[str, Any, str]]:
        """
        Build a ranked list of (provider_name, provider_instance, model_name)
        to try for the given model_id.

        The primary provider/model comes first, followed by all other enabled
        providers using their default models.

        Returns:
            List of (provider_name, provider_instance, model_name) tuples.
            The primary target is always first; fallbacks are appended in
            priority order.
        """
        primary_provider, primary_model = self.parse_model_id(model_id)
        chain: List[Tuple[str, Any, str]] = []
        seen_providers: set[str] = set()

        # Primary
        try:
            provider, model_name = self.get_provider_and_model(model_id)
            chain.append((primary_provider, provider, model_name))
            seen_providers.add(primary_provider)
        except ValueError:
            pass

        # Fallbacks: other enabled providers with their default models
        fallback_order = [
            ("ollama", lambda: self.ollama, settings.models.ollama),
            ("llamacpp", lambda: self.llamacpp, settings.models.llamacpp),
        ]

        for name, get_instance, cfg in fallback_order:
            if name in seen_providers:
                continue
            if not cfg.enabled:
                continue
            try:
                instance = get_instance()
                default_model = getattr(cfg, "default_model", "default")
                chain.append((name, instance, default_model))
                seen_providers.add(name)
            except Exception as exc:
                logger.debug(f"Skipping fallback {name}: {exc}")

        return chain

    # ------------------------------------------------------------------
    # Health / discovery
    # ------------------------------------------------------------------

    def check_providers(self) -> Dict[str, bool]:
        """Check availability of all enabled providers."""
        status = {}

        if settings.models.ollama.enabled:
            try:
                status["ollama"] = self.ollama.is_available()
            except Exception:
                status["ollama"] = False

        if settings.models.llamacpp.enabled:
            try:
                status["llamacpp"] = self.llamacpp.is_available()
            except Exception:
                status["llamacpp"] = False

        return status

    def list_models(self) -> List[Dict[str, Any]]:
        """List all models from all available providers."""
        models = []

        if settings.models.ollama.enabled:
            try:
                for m in self.ollama.list_models():
                    models.append({
                        "id": f"ollama/{m.name}",
                        "provider": "ollama",
                        "name": m.name,
                        "size": m.size,
                        "parameter_size": m.parameter_size,
                        "quantization": m.quantization,
                    })
            except Exception as e:
                logger.warning(f"Failed to list Ollama models: {e}")

        if settings.models.llamacpp.enabled:
            try:
                info = self.llamacpp.get_model_info()
                for m in info.get("data", []):
                    models.append({
                        "id": f"llamacpp/{m.get('id', 'default')}",
                        "provider": "llamacpp",
                        "name": m.get("id", "default"),
                        "size": None,
                    })
            except Exception as e:
                logger.warning(f"Failed to list llama.cpp models: {e}")

        return models

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self):
        """Shut down all provider connections."""
        if self._ollama:
            self._ollama.close()
            self._ollama = None
        if self._llamacpp:
            self._llamacpp.close()
            self._llamacpp = None

    async def close_async(self):
        """Async shutdown of all provider connections."""
        if self._ollama:
            await self._ollama.close_async()
            self._ollama = None
        if self._llamacpp:
            await self._llamacpp.close_async()
            self._llamacpp = None


# Module-level singleton accessor
_registry: Optional[ProviderRegistry] = None


def get_registry() -> ProviderRegistry:
    """Get or create the provider registry singleton."""
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
    return _registry
