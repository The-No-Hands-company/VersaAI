"""
llama.cpp Server Provider — HTTP client for llama.cpp server mode.

This provider communicates with llama.cpp's built-in HTTP server,
which provides an OpenAI-compatible API when started with:
    ./llama-server -m model.gguf --port 8080

For direct in-process inference via llama-cpp-python, see the
existing LlamaCppCodeLLM in code_llm.py.

Usage:
    >>> from versaai.models.llamacpp_provider import LlamaCppServerProvider
    >>> provider = LlamaCppServerProvider(base_url="http://localhost:8080")
    >>> response = provider.chat([{"role": "user", "content": "Hello!"}])
"""

import json
import logging
from typing import Any, Dict, Iterator, List, Optional

import httpx

from versaai.config import settings

logger = logging.getLogger(__name__)


class LlamaCppServerProvider:
    """
    HTTP client for llama.cpp server's OpenAI-compatible API.

    llama.cpp server exposes endpoints:
    - POST /v1/chat/completions  (chat)
    - POST /v1/completions       (raw completion)
    - POST /v1/embeddings        (embeddings)
    - GET  /health               (health check)
    - GET  /v1/models            (model info)

    This is useful when running llama.cpp as a separate service,
    which enables sharing one model across multiple clients.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        timeout: int = 120,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout, connect=10.0),
        )
        self._async_client: Optional[httpx.AsyncClient] = None

        logger.info(f"LlamaCppServerProvider initialized: {self.base_url}")

    def _get_async_client(self) -> httpx.AsyncClient:
        if self._async_client is None or self._async_client.is_closed:
            self._async_client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout, connect=10.0),
            )
        return self._async_client

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        try:
            r = self._client.get("/health", timeout=5.0)
            return r.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    async def is_available_async(self) -> bool:
        try:
            client = self._get_async_client()
            r = await client.get("/health", timeout=5.0)
            return r.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """Get info about the loaded model."""
        r = self._client.get("/v1/models")
        r.raise_for_status()
        return r.json()

    # ------------------------------------------------------------------
    # Chat Completions
    # ------------------------------------------------------------------

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 0.95,
        stop: Optional[List[str]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Chat completion (non-streaming). Returns OpenAI-format response."""
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": False,
        }
        if stop:
            payload["stop"] = stop

        r = self._client.post("/v1/chat/completions", json=payload)
        r.raise_for_status()
        return r.json()

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 0.95,
        stop: Optional[List[str]] = None,
        **kwargs,
    ) -> Iterator[Dict[str, Any]]:
        """Chat completion with streaming. Yields OpenAI-format SSE chunks."""
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": True,
        }
        if stop:
            payload["stop"] = stop

        with self._client.stream("POST", "/v1/chat/completions", json=payload) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                line = line.strip()
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    yield json.loads(data_str)

    async def chat_async(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 0.95,
        stop: Optional[List[str]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Async chat completion."""
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": False,
        }
        if stop:
            payload["stop"] = stop

        client = self._get_async_client()
        r = await client.post("/v1/chat/completions", json=payload)
        r.raise_for_status()
        return r.json()

    async def chat_stream_async(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 0.95,
        stop: Optional[List[str]] = None,
        **kwargs,
    ):
        """Async chat completion with streaming."""
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": True,
        }
        if stop:
            payload["stop"] = stop

        client = self._get_async_client()
        async with client.stream("POST", "/v1/chat/completions", json=payload) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                line = line.strip()
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    yield json.loads(data_str)

    # ------------------------------------------------------------------
    # Raw Completions
    # ------------------------------------------------------------------

    def complete(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 0.95,
        stop: Optional[List[str]] = None,
        **kwargs,
    ) -> str:
        """Raw text completion."""
        payload = {
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": False,
        }
        if stop:
            payload["stop"] = stop

        r = self._client.post("/v1/completions", json=payload)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["text"]

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------

    def embed(self, text: str) -> List[float]:
        """Generate embedding vector."""
        payload = {"input": text}
        r = self._client.post("/v1/embeddings", json=payload)
        r.raise_for_status()
        data = r.json()
        return data["data"][0]["embedding"]

    async def embed_async(self, text: str) -> List[float]:
        """Async generate embedding vector."""
        payload = {"input": text}
        client = self._get_async_client()
        r = await client.post("/v1/embeddings", json=payload)
        r.raise_for_status()
        data = r.json()
        return data["data"][0]["embedding"]

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self):
        self._client.close()

    async def close_async(self):
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
