"""
VersaAI API Error Handling — OpenAI-compatible structured errors.

Provides domain-specific exception classes that map to HTTP status codes
and the OpenAI error response format:

    {
        "error": {
            "message": "...",
            "type": "invalid_request_error|server_error|...",
            "param": null,
            "code": "provider_unavailable|context_overflow|..."
        }
    }

Usage:
    from versaai.api.errors import ProviderUnavailableError, raise_api_error

    raise ProviderUnavailableError("ollama")
    # → HTTP 503, type="server_error", code="provider_unavailable"
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# ============================================================================
# Base API error
# ============================================================================

class VersaAPIError(HTTPException):
    """
    Base class for all VersaAI API errors.

    Maps to the OpenAI error response format with structured JSON body.
    Subclasses define default status_code, error_type, and error_code.
    """

    status_code: int = 500
    error_type: str = "server_error"
    error_code: Optional[str] = None

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        error_type: Optional[str] = None,
        error_code: Optional[str] = None,
        param: Optional[str] = None,
    ):
        code = status_code or self.__class__.status_code
        detail = {
            "error": {
                "message": message,
                "type": error_type or self.__class__.error_type,
                "param": param,
                "code": error_code or self.__class__.error_code,
            }
        }
        super().__init__(status_code=code, detail=detail)


# ============================================================================
# 4xx — Client errors
# ============================================================================

class InvalidRequestError(VersaAPIError):
    """The request was malformed or missing required fields."""
    status_code = 400
    error_type = "invalid_request_error"
    error_code = "invalid_request"


class InvalidModelError(VersaAPIError):
    """The requested model ID is invalid or unrecognized."""
    status_code = 400
    error_type = "invalid_request_error"
    error_code = "model_not_found"


class ContextOverflowError(VersaAPIError):
    """The combined prompt + history exceeds the context window."""
    status_code = 400
    error_type = "invalid_request_error"
    error_code = "context_length_exceeded"


class ContentTooLargeError(VersaAPIError):
    """The request payload exceeds size limits."""
    status_code = 413
    error_type = "invalid_request_error"
    error_code = "content_too_large"


class RateLimitError(VersaAPIError):
    """Too many requests in the given time window."""
    status_code = 429
    error_type = "rate_limit_error"
    error_code = "rate_limit_exceeded"


# ============================================================================
# 5xx — Server errors
# ============================================================================

class ProviderUnavailableError(VersaAPIError):
    """The requested inference provider is not reachable."""
    status_code = 503
    error_type = "server_error"
    error_code = "provider_unavailable"

    def __init__(self, provider: str, detail: str = ""):
        msg = f"Provider '{provider}' is unavailable"
        if detail:
            msg += f": {detail}"
        super().__init__(msg)


class InferenceError(VersaAPIError):
    """The inference provider returned an error during generation."""
    status_code = 502
    error_type = "server_error"
    error_code = "inference_error"


class InferenceTimeoutError(VersaAPIError):
    """The inference request did not complete within the time limit."""
    status_code = 504
    error_type = "server_error"
    error_code = "inference_timeout"

    def __init__(self, timeout_seconds: float, provider: str = ""):
        msg = f"Inference timed out after {timeout_seconds}s"
        if provider:
            msg += f" (provider: {provider})"
        super().__init__(msg)


class PersistenceError(VersaAPIError):
    """Database or persistence layer failure (non-fatal in most contexts)."""
    status_code = 500
    error_type = "server_error"
    error_code = "persistence_error"


# ============================================================================
# Exception handlers for FastAPI
# ============================================================================

async def versaai_error_handler(request: Request, exc: VersaAPIError) -> JSONResponse:
    """Handle VersaAI errors — already structured, just return detail."""
    return JSONResponse(status_code=exc.status_code, content=exc.detail)


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle Pydantic/FastAPI validation errors in OpenAI format."""
    from fastapi.exceptions import RequestValidationError
    if isinstance(exc, RequestValidationError):
        errors = exc.errors()
        first = errors[0] if errors else {}
        loc = " → ".join(str(l) for l in first.get("loc", []))
        msg = first.get("msg", "Validation error")
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "message": f"Validation error: {msg} (field: {loc})",
                    "type": "invalid_request_error",
                    "param": loc or None,
                    "code": "validation_error",
                }
            },
        )
    # Fallback
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": f"Internal error: {type(exc).__name__}",
                "type": "server_error",
                "param": None,
                "code": None,
            }
        },
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last-resort handler for unhandled exceptions."""
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
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
# Request size guard middleware
# ============================================================================

class RequestSizeMiddleware:
    """
    ASGI middleware that rejects requests exceeding a body size limit.

    Prevents memory exhaustion from oversized payloads before
    they're fully read into memory.
    """

    def __init__(self, app, max_body_bytes: int = 10 * 1024 * 1024):
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Check Content-Length header if present
        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                length = int(content_length)
                if length > self.max_body_bytes:
                    response = JSONResponse(
                        status_code=413,
                        content={
                            "error": {
                                "message": (
                                    f"Request body too large: {length} bytes "
                                    f"(max {self.max_body_bytes} bytes)"
                                ),
                                "type": "invalid_request_error",
                                "param": None,
                                "code": "content_too_large",
                            }
                        },
                    )
                    await response(scope, receive, send)
                    return
            except (ValueError, TypeError):
                pass

        await self.app(scope, receive, send)


# ============================================================================
# Rate limiter (in-memory, per-IP)
# ============================================================================

import time
from collections import defaultdict
from threading import Lock


class _TokenBucket:
    """Simple token bucket rate limiter."""
    __slots__ = ("rate", "capacity", "tokens", "last_refill")

    def __init__(self, rate: float, capacity: int):
        self.rate = rate  # tokens per second
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last_refill = time.monotonic()

    def consume(self) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.last_refill = now
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


class RateLimitMiddleware:
    """
    ASGI middleware implementing per-IP token-bucket rate limiting.

    Only applies to POST endpoints (inference routes). GET requests
    (health, model listing) are not rate-limited.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 120,
        burst: int = 20,
    ):
        self.app = app
        self.rate = requests_per_minute / 60.0  # tokens per second
        self.burst = burst
        self._buckets: dict[str, _TokenBucket] = defaultdict(
            lambda: _TokenBucket(self.rate, self.burst)
        )
        self._lock = Lock()

    def _get_client_ip(self, scope) -> str:
        """Extract client IP from ASGI scope."""
        client = scope.get("client")
        return client[0] if client else "unknown"

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("method", "GET") != "POST":
            await self.app(scope, receive, send)
            return

        ip = self._get_client_ip(scope)
        with self._lock:
            bucket = self._buckets[ip]
            allowed = bucket.consume()

        if not allowed:
            response = JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "message": "Rate limit exceeded. Please slow down.",
                        "type": "rate_limit_error",
                        "param": None,
                        "code": "rate_limit_exceeded",
                    }
                },
                headers={"Retry-After": str(int(60 / max(self.rate, 0.01)))},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
