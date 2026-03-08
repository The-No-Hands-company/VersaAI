"""
VersaAI API Schemas — Pydantic models for request/response validation.

Follows the OpenAI API specification for maximum client compatibility.
Any tool, library, or frontend that speaks OpenAI-compatible API
(LiteLLM, Open WebUI, Continue.dev, Cursor, etc.) works out of the box.
"""

import time
import uuid
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Chat Completions — Request
# ============================================================================

# Maximum size for a single message content (256 KB)
_MAX_MESSAGE_CONTENT_BYTES = 256 * 1024


class ChatMessage(BaseModel):
    """A single message in the conversation."""
    role: Literal["system", "user", "assistant", "tool"] = "user"
    content: Optional[str] = None
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None

    @field_validator("content")
    @classmethod
    def content_not_too_large(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v.encode("utf-8", errors="replace")) > _MAX_MESSAGE_CONTENT_BYTES:
            raise ValueError(
                f"Message content exceeds maximum size of {_MAX_MESSAGE_CONTENT_BYTES // 1024} KB"
            )
        return v


class ChatCompletionRequest(BaseModel):
    """
    OpenAI-compatible chat completion request.

    Maps to POST /v1/chat/completions. Supports both streaming
    (stream=True → SSE) and non-streaming (stream=False → JSON).
    """
    model: str = Field(
        description="Model identifier. For Ollama: 'ollama/qwen2.5-coder:7b'. "
        "For llama.cpp server: 'llamacpp/default'. Provider is inferred from prefix."
    )
    messages: List[ChatMessage] = Field(
        ..., min_length=1, max_length=500,
        description="Conversation messages (max 500 per request).",
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.95, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(default=2048, ge=1, le=128000)
    stream: bool = False
    stop: Optional[Union[str, List[str]]] = None
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    n: int = Field(default=1, ge=1, le=1, description="Only n=1 supported.")
    user: Optional[str] = None

    # VersaAI extensions (ignored by OpenAI-compatible clients)
    system_prompt: Optional[str] = Field(
        default=None,
        description="Convenience: prepended as system message if messages[0] is not system."
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="Conversation ID for persistence. If provided, messages are auto-saved "
        "and prior history is prepended. If omitted, no persistence."
    )


# ============================================================================
# Chat Completions — Response (Non-Streaming)
# ============================================================================

class UsageInfo(BaseModel):
    """Token usage statistics."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChoiceMessage(BaseModel):
    """The assistant's response message."""
    role: str = "assistant"
    content: Optional[str] = None


class ChatCompletionChoice(BaseModel):
    """A single completion choice."""
    index: int = 0
    message: ChoiceMessage
    finish_reason: Optional[str] = "stop"


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response."""
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:24]}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[ChatCompletionChoice]
    usage: UsageInfo = UsageInfo()


# ============================================================================
# Chat Completions — Response (Streaming / SSE)
# ============================================================================

class DeltaMessage(BaseModel):
    """Incremental content in a streaming chunk."""
    role: Optional[str] = None
    content: Optional[str] = None


class ChatCompletionStreamChoice(BaseModel):
    """A single streaming choice."""
    index: int = 0
    delta: DeltaMessage
    finish_reason: Optional[str] = None


class ChatCompletionStreamResponse(BaseModel):
    """OpenAI-compatible streaming chunk."""
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:24]}")
    object: str = "chat.completion.chunk"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[ChatCompletionStreamChoice]


# ============================================================================
# Completions (Raw / Legacy)
# ============================================================================

class CompletionRequest(BaseModel):
    """Raw text completion request (legacy /v1/completions)."""
    model: str
    prompt: Union[str, List[str]]
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.95, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(default=2048, ge=1, le=128000)
    stream: bool = False
    stop: Optional[Union[str, List[str]]] = None


class CompletionChoice(BaseModel):
    """A raw completion choice."""
    index: int = 0
    text: str = ""
    finish_reason: Optional[str] = "stop"


class CompletionResponse(BaseModel):
    """Raw completion response."""
    id: str = Field(default_factory=lambda: f"cmpl-{uuid.uuid4().hex[:24]}")
    object: str = "text_completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[CompletionChoice]
    usage: UsageInfo = UsageInfo()


# ============================================================================
# Models
# ============================================================================

class ModelInfo(BaseModel):
    """Information about an available model."""
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "versaai"
    provider: str = "ollama"
    size: Optional[int] = None
    description: Optional[str] = None


class ModelListResponse(BaseModel):
    """List of available models."""
    object: str = "list"
    data: List[ModelInfo] = []


# ============================================================================
# Health
# ============================================================================

class HealthResponse(BaseModel):
    """Server health check response."""
    status: str = "ok"
    version: str
    providers: Dict[str, bool] = {}
    uptime_seconds: float = 0.0


# ============================================================================
# Errors
# ============================================================================

class ErrorDetail(BaseModel):
    """OpenAI-compatible error response."""
    message: str
    type: str = "invalid_request_error"
    param: Optional[str] = None
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """Wrapper for error responses."""
    error: ErrorDetail
