"""
Chat Completions Route — OpenAI-compatible /v1/chat/completions endpoint.

Supports:
- Non-streaming: Returns full JSON response
- Streaming: Returns Server-Sent Events (SSE) with incremental chunks
- Provider routing: model="ollama/qwen2.5-coder:7b" or "llamacpp/default"
"""

import json
import logging
import time
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from versaai.api.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatCompletionStreamResponse,
    ChatCompletionStreamChoice,
    ChoiceMessage,
    DeltaMessage,
    ErrorDetail,
    ErrorResponse,
    UsageInfo,
)
from versaai.api.provider_registry import get_registry

logger = logging.getLogger(__name__)

router = APIRouter()


def _prepare_messages(req: ChatCompletionRequest) -> list[dict]:
    """Convert request messages to plain dicts, prepending system_prompt if needed."""
    messages = [m.model_dump(exclude_none=True) for m in req.messages]

    # If system_prompt extension is provided and first message isn't already system
    if req.system_prompt and (not messages or messages[0].get("role") != "system"):
        messages.insert(0, {"role": "system", "content": req.system_prompt})

    return messages


def _normalize_stop(stop) -> list[str] | None:
    """Normalize stop sequences to a list."""
    if stop is None:
        return None
    if isinstance(stop, str):
        return [stop]
    return stop


# ============================================================================
# Non-streaming handler
# ============================================================================

def _handle_ollama_sync(provider, model_name: str, req: ChatCompletionRequest) -> ChatCompletionResponse:
    """Handle non-streaming chat via Ollama."""
    messages = _prepare_messages(req)
    response = provider.chat(
        messages=messages,
        model=model_name,
        temperature=req.temperature,
        top_p=req.top_p,
        stop=_normalize_stop(req.stop),
    )

    content = response.get("message", {}).get("content", "")

    return ChatCompletionResponse(
        model=f"ollama/{model_name}",
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChoiceMessage(role="assistant", content=content),
                finish_reason="stop",
            )
        ],
        usage=UsageInfo(
            prompt_tokens=response.get("prompt_eval_count", 0),
            completion_tokens=response.get("eval_count", 0),
            total_tokens=response.get("prompt_eval_count", 0) + response.get("eval_count", 0),
        ),
    )


def _handle_llamacpp_sync(provider, model_name: str, req: ChatCompletionRequest) -> ChatCompletionResponse:
    """Handle non-streaming chat via llama.cpp server."""
    messages = _prepare_messages(req)
    response = provider.chat(
        messages=messages,
        temperature=req.temperature,
        max_tokens=req.max_tokens or 2048,
        top_p=req.top_p,
        stop=_normalize_stop(req.stop),
    )

    # llama.cpp server returns OpenAI-format directly
    choices = response.get("choices", [{}])
    content = choices[0].get("message", {}).get("content", "") if choices else ""
    usage = response.get("usage", {})

    return ChatCompletionResponse(
        model=f"llamacpp/{model_name}",
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChoiceMessage(role="assistant", content=content),
                finish_reason=choices[0].get("finish_reason", "stop") if choices else "stop",
            )
        ],
        usage=UsageInfo(
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
        ),
    )


# ============================================================================
# Streaming handlers
# ============================================================================

async def _stream_ollama(provider, model_name: str, req: ChatCompletionRequest) -> AsyncGenerator[str, None]:
    """Yield SSE events from Ollama streaming chat."""
    messages = _prepare_messages(req)
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())

    # First chunk: role
    first_chunk = ChatCompletionStreamResponse(
        id=completion_id,
        created=created,
        model=f"ollama/{model_name}",
        choices=[
            ChatCompletionStreamChoice(
                index=0,
                delta=DeltaMessage(role="assistant"),
                finish_reason=None,
            )
        ],
    )
    yield f"data: {first_chunk.model_dump_json()}\n\n"

    # Content chunks via async streaming
    async for chunk in provider.chat_stream_async(
        messages=messages,
        model=model_name,
        temperature=req.temperature,
        top_p=req.top_p,
        stop=_normalize_stop(req.stop),
    ):
        content = chunk.get("message", {}).get("content", "")
        if content:
            stream_chunk = ChatCompletionStreamResponse(
                id=completion_id,
                created=created,
                model=f"ollama/{model_name}",
                choices=[
                    ChatCompletionStreamChoice(
                        index=0,
                        delta=DeltaMessage(content=content),
                        finish_reason=None,
                    )
                ],
            )
            yield f"data: {stream_chunk.model_dump_json()}\n\n"

    # Final chunk: finish reason
    final_chunk = ChatCompletionStreamResponse(
        id=completion_id,
        created=created,
        model=f"ollama/{model_name}",
        choices=[
            ChatCompletionStreamChoice(
                index=0,
                delta=DeltaMessage(),
                finish_reason="stop",
            )
        ],
    )
    yield f"data: {final_chunk.model_dump_json()}\n\n"
    yield "data: [DONE]\n\n"


async def _stream_llamacpp(provider, model_name: str, req: ChatCompletionRequest) -> AsyncGenerator[str, None]:
    """Yield SSE events from llama.cpp server streaming chat."""
    messages = _prepare_messages(req)
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())

    # First chunk: role
    first_chunk = ChatCompletionStreamResponse(
        id=completion_id,
        created=created,
        model=f"llamacpp/{model_name}",
        choices=[
            ChatCompletionStreamChoice(
                index=0,
                delta=DeltaMessage(role="assistant"),
                finish_reason=None,
            )
        ],
    )
    yield f"data: {first_chunk.model_dump_json()}\n\n"

    # llama.cpp server already returns OpenAI SSE format
    async for chunk in provider.chat_stream_async(
        messages=messages,
        temperature=req.temperature,
        max_tokens=req.max_tokens or 2048,
        top_p=req.top_p,
        stop=_normalize_stop(req.stop),
    ):
        choices = chunk.get("choices", [{}])
        delta_content = choices[0].get("delta", {}).get("content", "") if choices else ""
        finish = choices[0].get("finish_reason") if choices else None

        if delta_content:
            stream_chunk = ChatCompletionStreamResponse(
                id=completion_id,
                created=created,
                model=f"llamacpp/{model_name}",
                choices=[
                    ChatCompletionStreamChoice(
                        index=0,
                        delta=DeltaMessage(content=delta_content),
                        finish_reason=None,
                    )
                ],
            )
            yield f"data: {stream_chunk.model_dump_json()}\n\n"

        if finish:
            break

    # Final chunk
    final_chunk = ChatCompletionStreamResponse(
        id=completion_id,
        created=created,
        model=f"llamacpp/{model_name}",
        choices=[
            ChatCompletionStreamChoice(
                index=0,
                delta=DeltaMessage(),
                finish_reason="stop",
            )
        ],
    )
    yield f"data: {final_chunk.model_dump_json()}\n\n"
    yield "data: [DONE]\n\n"


# ============================================================================
# Endpoint
# ============================================================================

@router.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest, request: Request):
    """
    OpenAI-compatible chat completion endpoint.

    Model format: "<provider>/<model>" e.g. "ollama/qwen2.5-coder:7b"
    If no provider prefix, uses default from config.

    Streaming (stream=true):
        Returns text/event-stream with SSE chunks.

    Non-streaming (stream=false):
        Returns JSON ChatCompletionResponse.
    """
    try:
        registry = get_registry()
        provider, model_name = registry.get_provider_and_model(req.model)
        provider_name, _ = registry.parse_model_id(req.model)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error=ErrorDetail(message=str(e), type="invalid_request_error")
            ).model_dump(),
        )

    logger.info(
        f"Chat completion: provider={provider_name} model={model_name} "
        f"stream={req.stream} messages={len(req.messages)}"
    )

    try:
        if req.stream:
            # SSE streaming response
            if provider_name == "ollama":
                generator = _stream_ollama(provider, model_name, req)
            elif provider_name == "llamacpp":
                generator = _stream_llamacpp(provider, model_name, req)
            else:
                raise HTTPException(status_code=400, detail="Unsupported provider for streaming")

            return StreamingResponse(
                generator,
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            # Non-streaming response
            if provider_name == "ollama":
                return _handle_ollama_sync(provider, model_name, req)
            elif provider_name == "llamacpp":
                return _handle_llamacpp_sync(provider, model_name, req)
            else:
                raise HTTPException(status_code=400, detail="Unsupported provider")

    except Exception as e:
        logger.error(f"Chat completion error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error=ErrorDetail(
                    message=f"Inference error: {str(e)}",
                    type="server_error",
                )
            ).model_dump(),
        )
