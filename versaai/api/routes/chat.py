"""
Chat Completions Route — OpenAI-compatible /v1/chat/completions endpoint.

Supports:
- Non-streaming: Returns full JSON response
- Streaming: Returns Server-Sent Events (SSE) with incremental chunks
- Provider routing: model="ollama/qwen2.5-coder:7b" or "llamacpp/default"
- Conversation persistence: optional conversation_id auto-saves messages
"""

import asyncio
import json
import logging
import time
import uuid
from typing import AsyncGenerator, Optional

import httpx
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
    UsageInfo,
)
from versaai.api.provider_registry import get_registry, retry_sync
from versaai.api.errors import (
    InvalidModelError,
    InferenceError,
    InferenceTimeoutError,
    ProviderUnavailableError,
)
from versaai.memory.persistence import ConversationDB

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Conversation persistence singleton
# ============================================================================

_conversation_db: Optional[ConversationDB] = None


async def _get_db() -> ConversationDB:
    global _conversation_db
    if _conversation_db is None:
        _conversation_db = ConversationDB()
        await _conversation_db.initialize()
    return _conversation_db


def _prepare_messages(req: ChatCompletionRequest) -> list[dict]:
    """Convert request messages to plain dicts, prepending system_prompt if needed."""
    messages = [m.model_dump(exclude_none=True) for m in req.messages]

    # If system_prompt extension is provided and first message isn't already system
    if req.system_prompt and (not messages or messages[0].get("role") != "system"):
        messages.insert(0, {"role": "system", "content": req.system_prompt})

    return messages


async def _load_history(conversation_id: str) -> list[dict]:
    """Load prior messages from persistence for a conversation."""
    db = await _get_db()
    rows = await db.get_messages(conversation_id, limit=200)
    return [{"role": r["role"], "content": r["content"]} for r in rows]


async def _ensure_conversation(conversation_id: str) -> bool:
    """Create the conversation record if it doesn't exist yet.

    Returns True if the conversation was newly created (needs a title).
    """
    db = await _get_db()
    existing = await db.get_conversation(conversation_id)
    if not existing:
        await db.create_conversation(
            title="", conversation_id=conversation_id,
        )
        return True
    # Existing but no title yet — still needs one
    return not existing.get("title")


async def _set_conversation_title(conversation_id: str, first_message: str):
    """Auto-generate a conversation title from the first user message."""
    title = first_message.strip().replace("\n", " ")
    if len(title) > 60:
        title = title[:57] + "…"
    db = await _get_db()
    await db.update_conversation_title(conversation_id, title)


async def _save_message(conversation_id: str, role: str, content: str):
    """Persist a single message to the conversation store."""
    db = await _get_db()
    await db.add_message(conversation_id, role=role, content=content)


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
    return _handle_ollama_sync_with_messages(provider, model_name, req, messages)


def _handle_ollama_sync_with_messages(
    provider, model_name: str, req: ChatCompletionRequest, messages: list[dict],
) -> ChatCompletionResponse:
    """Handle non-streaming chat via Ollama with pre-built message list."""
    response = retry_sync(lambda: provider.chat(
        messages=messages,
        model=model_name,
        temperature=req.temperature,
        top_p=req.top_p,
        stop=_normalize_stop(req.stop),
    ))

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
    return _handle_llamacpp_sync_with_messages(provider, model_name, req, messages)


def _handle_llamacpp_sync_with_messages(
    provider, model_name: str, req: ChatCompletionRequest, messages: list[dict],
) -> ChatCompletionResponse:
    """Handle non-streaming chat via llama.cpp server with pre-built message list."""
    response = retry_sync(lambda: provider.chat(
        messages=messages,
        temperature=req.temperature,
        max_tokens=req.max_tokens or 2048,
        top_p=req.top_p,
        stop=_normalize_stop(req.stop),
    ))

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
    async for chunk in _stream_ollama_core(provider, model_name, req, messages):
        yield chunk


async def _stream_ollama_with_persist(
    provider, model_name: str, req: ChatCompletionRequest,
    messages: list[dict], conv_id: Optional[str],
) -> AsyncGenerator[str, None]:
    """Streaming Ollama with post-stream persistence save."""
    collected: list[str] = []
    async for chunk in _stream_ollama_core(provider, model_name, req, messages):
        # Extract content from SSE data for persistence
        if chunk.startswith("data: {"):
            try:
                payload = json.loads(chunk[6:])
                delta = payload.get("choices", [{}])[0].get("delta", {})
                if delta.get("content"):
                    collected.append(delta["content"])
            except (json.JSONDecodeError, IndexError):
                pass
        yield chunk

    # Save the full assistant reply
    if conv_id and collected:
        try:
            await _save_message(conv_id, "assistant", "".join(collected))
        except Exception as exc:
            logger.warning(f"Persistence save (stream) failed: {exc}")


async def _stream_ollama_core(
    provider, model_name: str, req: ChatCompletionRequest, messages: list[dict],
) -> AsyncGenerator[str, None]:
    """Core Ollama SSE generator."""
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
    async for chunk in _stream_llamacpp_core(provider, model_name, req, messages):
        yield chunk


async def _stream_llamacpp_with_persist(
    provider, model_name: str, req: ChatCompletionRequest,
    messages: list[dict], conv_id: Optional[str],
) -> AsyncGenerator[str, None]:
    """Streaming llama.cpp with post-stream persistence save."""
    collected: list[str] = []
    async for chunk in _stream_llamacpp_core(provider, model_name, req, messages):
        if chunk.startswith("data: {"):
            try:
                payload = json.loads(chunk[6:])
                delta = payload.get("choices", [{}])[0].get("delta", {})
                if delta.get("content"):
                    collected.append(delta["content"])
            except (json.JSONDecodeError, IndexError):
                pass
        yield chunk

    if conv_id and collected:
        try:
            await _save_message(conv_id, "assistant", "".join(collected))
        except Exception as exc:
            logger.warning(f"Persistence save (stream) failed: {exc}")


async def _stream_llamacpp_core(
    provider, model_name: str, req: ChatCompletionRequest, messages: list[dict],
) -> AsyncGenerator[str, None]:
    """Core llama.cpp SSE generator."""
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

    Persistence (conversation_id is set):
        Prior history is prepended to messages, and both user + assistant
        messages are saved after completion.

    Streaming (stream=true):
        Returns text/event-stream with SSE chunks.

    Non-streaming (stream=false):
        Returns JSON ChatCompletionResponse.
    """
    # Apply runtime settings overrides when request doesn't specify values
    from versaai.api.routes.settings import _get_effective

    effective_model = req.model
    if not effective_model:
        override_model = _get_effective("default_model", None)
        if override_model:
            effective_model = override_model

    if req.temperature is None:
        override_temp = _get_effective("temperature", None)
        if override_temp is not None:
            req.temperature = override_temp

    if req.max_tokens is None:
        override_max = _get_effective("max_tokens", None)
        if override_max is not None:
            req.max_tokens = override_max

    try:
        registry = get_registry()
        provider, model_name = registry.get_provider_and_model(effective_model)
        provider_name, _ = registry.parse_model_id(effective_model)
    except ValueError as e:
        raise InvalidModelError(str(e), param="model")

    logger.info(
        f"Chat completion: provider={provider_name} model={model_name} "
        f"stream={req.stream} messages={len(req.messages)} "
        f"conversation_id={req.conversation_id}"
    )

    # --- Persistence: load history and merge ---------------------------------
    conv_id = req.conversation_id
    if conv_id:
        try:
            needs_title = await _ensure_conversation(conv_id)
            history = await _load_history(conv_id)
            # Save user messages from this request
            first_user_text = ""
            for m in req.messages:
                if m.role == "user" and m.content:
                    if not first_user_text:
                        first_user_text = m.content
                    await _save_message(conv_id, "user", m.content)
            # Auto-title from first user message
            if needs_title and first_user_text:
                await _set_conversation_title(conv_id, first_user_text)
        except Exception as exc:
            logger.warning(f"Persistence load failed (non-fatal): {exc}")
            history = []
    else:
        history = []

    # Merge: prepend stored history before current request messages
    current_messages = _prepare_messages(req)
    if history:
        # Avoid duplicating system prompts already in history
        if current_messages and current_messages[0].get("role") == "system":
            system_msg = current_messages[0]
            rest = current_messages[1:]
            # Deduplicate: drop history messages that overlap with new request
            history_contents = {(m["role"], m["content"]) for m in rest}
            unique_history = [m for m in history if (m["role"], m["content"]) not in history_contents]
            all_messages = [system_msg] + unique_history + rest
        else:
            history_contents = {(m["role"], m["content"]) for m in current_messages}
            unique_history = [m for m in history if (m["role"], m["content"]) not in history_contents]
            all_messages = unique_history + current_messages
    else:
        all_messages = current_messages

    try:
        if req.stream:
            # SSE streaming response
            if provider_name == "ollama":
                generator = _stream_ollama_with_persist(
                    provider, model_name, req, all_messages, conv_id,
                )
            elif provider_name == "llamacpp":
                generator = _stream_llamacpp_with_persist(
                    provider, model_name, req, all_messages, conv_id,
                )
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
            # Non-streaming response — run sync handlers off the event loop
            if provider_name == "ollama":
                resp = await asyncio.to_thread(
                    _handle_ollama_sync_with_messages, provider, model_name, req, all_messages,
                )
            elif provider_name == "llamacpp":
                resp = await asyncio.to_thread(
                    _handle_llamacpp_sync_with_messages, provider, model_name, req, all_messages,
                )
            else:
                raise HTTPException(status_code=400, detail="Unsupported provider")

            # Save assistant reply to persistence
            if conv_id:
                try:
                    assistant_content = resp.choices[0].message.content or ""
                    if assistant_content:
                        await _save_message(conv_id, "assistant", assistant_content)
                except Exception as exc:
                    logger.warning(f"Persistence save failed (non-fatal): {exc}")

            return resp

    except httpx.ConnectError:
        raise ProviderUnavailableError(provider_name)
    except httpx.TimeoutException:
        raise InferenceTimeoutError(
            timeout_seconds=getattr(provider, 'timeout', 120),
            provider=provider_name,
        )
    except Exception as e:
        logger.error(f"Chat completion error: {e}", exc_info=True)
        raise InferenceError(f"Inference failed: {e}")
