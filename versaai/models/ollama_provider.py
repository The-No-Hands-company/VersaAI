"""
Ollama Model Provider — HTTP client for Ollama inference server.

Ollama manages model downloads, quantization, and GPU acceleration automatically.
This provider communicates with the Ollama REST API.

Requirements:
    - Ollama installed and running: https://ollama.com
    - Pull a model: ollama pull qwen2.5-coder:7b

Usage:
    >>> from versaai.models.ollama_provider import OllamaProvider
    >>> provider = OllamaProvider()
    >>> response = provider.generate("Write a Python sort function")
    >>> for chunk in provider.generate_stream("Explain quicksort"):
    ...     print(chunk, end="", flush=True)
"""

import json
import logging
from typing import Any, Dict, Iterator, List, Optional
from dataclasses import dataclass, field

import httpx

from versaai.config import settings

logger = logging.getLogger(__name__)


@dataclass
class OllamaModel:
    """Metadata about an available Ollama model."""
    name: str
    size: int = 0  # bytes
    parameter_size: str = ""
    quantization: str = ""
    family: str = ""
    digest: str = ""
    modified_at: str = ""


class OllamaProvider:
    """
    Ollama HTTP API client for model inference.

    Supports:
    - Text generation (streaming and non-streaming)
    - Chat completions (multi-turn conversations)
    - Model listing, pulling, and management
    - Embedding generation
    - OpenAI-compatible /v1/chat/completions endpoint

    Configuration via versaai/config.py or environment variables:
        VERSAAI_MODELS__OLLAMA__BASE_URL=http://localhost:11434
        VERSAAI_MODELS__OLLAMA__DEFAULT_MODEL=qwen2.5-coder:7b
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        cfg = settings.models.ollama
        self.base_url = (base_url or cfg.base_url).rstrip("/")
        self.model = model or cfg.default_model
        self.timeout = timeout or cfg.timeout

        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout, connect=10.0),
        )
        self._async_client: Optional[httpx.AsyncClient] = None

        logger.info(f"OllamaProvider initialized: {self.base_url} (model: {self.model})")

    # ------------------------------------------------------------------
    # Async client (lazy init)
    # ------------------------------------------------------------------

    def _get_async_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._async_client is None or self._async_client.is_closed:
            self._async_client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout, connect=10.0),
            )
        return self._async_client

    # ------------------------------------------------------------------
    # Health & Model Management
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Check if Ollama server is reachable."""
        try:
            r = self._client.get("/", timeout=5.0)
            return r.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    async def is_available_async(self) -> bool:
        """Async check if Ollama server is reachable."""
        try:
            client = self._get_async_client()
            r = await client.get("/", timeout=5.0)
            return r.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    def list_models(self) -> List[OllamaModel]:
        """List locally available models."""
        try:
            r = self._client.get("/api/tags")
            r.raise_for_status()
            data = r.json()

            models = []
            for m in data.get("models", []):
                details = m.get("details", {})
                models.append(OllamaModel(
                    name=m["name"],
                    size=m.get("size", 0),
                    parameter_size=details.get("parameter_size", ""),
                    quantization=details.get("quantization_level", ""),
                    family=details.get("family", ""),
                    digest=m.get("digest", ""),
                    modified_at=m.get("modified_at", ""),
                ))
            return models
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []

    async def list_models_async(self) -> List[OllamaModel]:
        """Async list locally available models."""
        try:
            client = self._get_async_client()
            r = await client.get("/api/tags")
            r.raise_for_status()
            data = r.json()

            models = []
            for m in data.get("models", []):
                details = m.get("details", {})
                models.append(OllamaModel(
                    name=m["name"],
                    size=m.get("size", 0),
                    parameter_size=details.get("parameter_size", ""),
                    quantization=details.get("quantization_level", ""),
                    family=details.get("family", ""),
                    digest=m.get("digest", ""),
                    modified_at=m.get("modified_at", ""),
                ))
            return models
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []

    def pull_model(self, model: str) -> Iterator[Dict[str, Any]]:
        """Pull/download a model. Yields progress updates."""
        with self._client.stream(
            "POST",
            "/api/pull",
            json={"name": model},
            timeout=None,  # Downloads can take a long time
        ) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if line:
                    yield json.loads(line)

    def model_exists(self, model: Optional[str] = None) -> bool:
        """Check if a specific model is available locally."""
        model = model or self.model
        models = self.list_models()
        return any(m.name == model or m.name.startswith(model.split(":")[0]) for m in models)

    # ------------------------------------------------------------------
    # Generation (sync)
    # ------------------------------------------------------------------

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 0.95,
        stop: Optional[List[str]] = None,
        **kwargs,
    ) -> str:
        """
        Generate a completion (non-streaming).

        Args:
            prompt: The user prompt
            model: Model to use (default: self.model)
            system: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling threshold
            stop: Stop sequences

        Returns:
            Generated text
        """
        payload = {
            "model": model or self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "top_p": top_p,
            },
        }
        if system:
            payload["system"] = system
        if stop:
            payload["options"]["stop"] = stop

        r = self._client.post("/api/generate", json=payload)
        r.raise_for_status()
        return r.json()["response"]

    def generate_stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 0.95,
        stop: Optional[List[str]] = None,
        **kwargs,
    ) -> Iterator[str]:
        """
        Generate a completion with streaming.

        Yields text chunks as they arrive.
        """
        payload = {
            "model": model or self.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "top_p": top_p,
            },
        }
        if system:
            payload["system"] = system
        if stop:
            payload["options"]["stop"] = stop

        with self._client.stream("POST", "/api/generate", json=payload) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if line:
                    data = json.loads(line)
                    if "response" in data:
                        yield data["response"]

    # ------------------------------------------------------------------
    # Chat Completions (sync)
    # ------------------------------------------------------------------

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 0.95,
        stop: Optional[List[str]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Chat completion (non-streaming).

        Args:
            messages: List of {"role": "user"|"assistant"|"system", "content": "..."}
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens

        Returns:
            Response dict with 'message' key containing assistant response
        """
        payload = {
            "model": model or self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "top_p": top_p,
            },
        }
        if stop:
            payload["options"]["stop"] = stop

        r = self._client.post("/api/chat", json=payload)
        r.raise_for_status()
        return r.json()

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 0.95,
        stop: Optional[List[str]] = None,
        **kwargs,
    ) -> Iterator[Dict[str, Any]]:
        """
        Chat completion with streaming.

        Yields partial response dicts with 'message.content' chunks.
        """
        payload = {
            "model": model or self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "top_p": top_p,
            },
        }
        if stop:
            payload["options"]["stop"] = stop

        with self._client.stream("POST", "/api/chat", json=payload) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if line:
                    yield json.loads(line)

    # ------------------------------------------------------------------
    # Chat Completions (async)
    # ------------------------------------------------------------------

    async def chat_async(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 0.95,
        stop: Optional[List[str]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Async chat completion (non-streaming)."""
        payload = {
            "model": model or self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "top_p": top_p,
            },
        }
        if stop:
            payload["options"]["stop"] = stop

        client = self._get_async_client()
        r = await client.post("/api/chat", json=payload)
        r.raise_for_status()
        return r.json()

    async def chat_stream_async(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 0.95,
        stop: Optional[List[str]] = None,
        **kwargs,
    ):
        """
        Async chat completion with streaming.

        Yields partial response dicts as they arrive.
        """
        payload = {
            "model": model or self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "top_p": top_p,
            },
        }
        if stop:
            payload["options"]["stop"] = stop

        client = self._get_async_client()
        async with client.stream("POST", "/api/chat", json=payload) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if line:
                    yield json.loads(line)

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------

    def embed(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> List[float]:
        """Generate embedding for text."""
        payload = {
            "model": model or self.model,
            "input": text,
        }
        r = self._client.post("/api/embed", json=payload)
        r.raise_for_status()
        data = r.json()
        return data.get("embeddings", [[]])[0]

    async def embed_async(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> List[float]:
        """Async generate embedding for text."""
        payload = {
            "model": model or self.model,
            "input": text,
        }
        client = self._get_async_client()
        r = await client.post("/api/embed", json=payload)
        r.raise_for_status()
        data = r.json()
        return data.get("embeddings", [[]])[0]

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self):
        """Close HTTP clients."""
        self._client.close()
        if self._async_client and not self._async_client.is_closed:
            # Note: for async close, use close_async()
            pass

    async def close_async(self):
        """Close async HTTP client."""
        if self._async_client and not self._async_client.is_closed:
            await self._async_client.aclose()
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close_async()
