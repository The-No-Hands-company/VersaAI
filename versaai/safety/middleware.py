"""
Safety ASGI middleware — intercepts every request/response through
the VersaAI API and applies guardrail screening.

Flow:
    1. Read the request body.
    2. Extract the user-facing text payload (prompt, messages, etc.).
    3. Run ``GuardrailEngine.screen_input()``.
    4. If blocked → return 403 immediately (never reaches the route handler).
    5. If allowed → pass through to the route handler.
    6. Capture the response body.
    7. Run ``GuardrailEngine.screen_output()``.
    8. If blocked → replace response with 403 error JSON.
    9. If output was redacted or has disclaimers → patch the response text.
   10. Forward (possibly modified) response to the client.

Architecture choices:
    - Pure ASGI middleware (no FastAPI dependency) for maximum compatibility.
    - Request body is buffered once, then replayed to the downstream app.
    - Only POST requests on known content-generation endpoints are screened.
      GETs, health checks, and static resources are passed through untouched.
    - Streaming responses (SSE) are screened chunk-by-chunk on a best-effort
      basis; a full block can stop the stream mid-flight.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Set

from versaai.safety.guardrails import GuardrailEngine, get_guardrail_engine
from versaai.safety.types import SafetyAction

logger = logging.getLogger(__name__)


# Endpoints where we inspect the body for user content
_SCREENED_ENDPOINTS: Set[str] = {
    "/v1/chat/completions",
    "/v1/agents/execute",
    "/v1/rag/query",
    "/v1/generate/image",
    "/v1/generate/video",
    "/v1/generate/3d",
}


def _extract_user_text(body: Dict[str, Any], path: str) -> str:
    """
    Pull the user-facing text out of a request body.

    Returns an empty string if no extractable text is found (which
    means the request will pass through without content screening).
    """
    # Chat completions — last user message
    messages = body.get("messages")
    if isinstance(messages, list):
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    return content
                # Multimodal messages: list of parts
                if isinstance(content, list):
                    texts = [p.get("text", "") for p in content if isinstance(p, dict)]
                    return " ".join(texts)

    # Agent execution
    if "task" in body:
        return str(body["task"])
    if "input" in body:
        return str(body["input"])

    # RAG / generation
    if "query" in body:
        return str(body["query"])
    if "prompt" in body:
        return str(body["prompt"])

    return ""


def _error_response(status: int, message: str, code: str) -> bytes:
    """Build an OpenAI-compatible error JSON body."""
    return json.dumps({
        "error": {
            "message": message,
            "type": "content_policy_violation",
            "param": None,
            "code": code,
        }
    }).encode("utf-8")


class SafetyMiddleware:
    """
    ASGI middleware that screens requests and responses through the
    ``GuardrailEngine``.

    Add to FastAPI::

        from versaai.safety.middleware import SafetyMiddleware
        app.add_middleware(SafetyMiddleware)
    """

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Dict[str, Any], receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        method: str = scope.get("method", "GET")

        # Only screen POST requests to known endpoints
        if method != "POST" or path not in _SCREENED_ENDPOINTS:
            await self.app(scope, receive, send)
            return

        engine = get_guardrail_engine()
        if not engine.enabled:
            await self.app(scope, receive, send)
            return

        # --- Extract client IP ---
        client = scope.get("client")
        source_ip = client[0] if client else ""

        # --- Buffer request body ---
        body_chunks: List[bytes] = []
        while True:
            message = await receive()
            body_chunks.append(message.get("body", b""))
            if not message.get("more_body", False):
                break
        raw_body = b"".join(body_chunks)

        # Parse JSON body
        parsed: Dict[str, Any] = {}
        try:
            if raw_body:
                parsed = json.loads(raw_body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass  # Not JSON — skip content screening

        user_text = _extract_user_text(parsed, path)

        # --- Screen input ---
        if user_text:
            input_verdict = await engine.ascreen_input(
                user_text, endpoint=path, source_ip=source_ip,
            )
            if not input_verdict.allowed:
                response_body = _error_response(
                    403,
                    f"Request blocked by content safety filter: {input_verdict.explanation}",
                    "content_filtered",
                )
                await send({
                    "type": "http.response.start",
                    "status": 403,
                    "headers": [
                        [b"content-type", b"application/json"],
                        [b"content-length", str(len(response_body)).encode()],
                    ],
                })
                await send({
                    "type": "http.response.body",
                    "body": response_body,
                })
                return

        # --- Replay body to downstream app ---
        body_sent = False

        async def replay_receive() -> Dict[str, Any]:
            nonlocal body_sent
            if not body_sent:
                body_sent = True
                return {"type": "http.request", "body": raw_body, "more_body": False}
            return {"type": "http.disconnect"}

        # --- Capture + screen response ---
        response_started = False
        response_status = 200
        response_headers: List[List[bytes]] = []
        response_body_chunks: List[bytes] = []
        is_streaming = False

        async def capture_send(message: Dict[str, Any]) -> None:
            nonlocal response_started, response_status, response_headers, is_streaming

            if message["type"] == "http.response.start":
                response_started = True
                response_status = message.get("status", 200)
                response_headers = list(message.get("headers", []))

                # Detect SSE streaming
                for h in response_headers:
                    if h[0] == b"content-type" and b"text/event-stream" in h[1]:
                        is_streaming = True
                        break

                if is_streaming:
                    # For streaming, pass headers through immediately
                    await send(message)
                return

            if message["type"] == "http.response.body":
                chunk = message.get("body", b"")

                if is_streaming:
                    # Screen streaming chunks individually
                    if chunk:
                        try:
                            text = chunk.decode("utf-8", errors="replace")
                            ov = await engine.ascreen_output(
                                text, endpoint=path, source_ip=source_ip,
                            )
                            if not ov.allowed:
                                # Stop the stream with an error event
                                error_event = (
                                    f"data: {json.dumps({'error': 'Content blocked by safety filter'})}\n\n"
                                ).encode("utf-8")
                                await send({"type": "http.response.body", "body": error_event, "more_body": False})
                                return
                        except Exception:
                            pass  # Don't break the stream on screening errors
                    await send(message)
                    return

                # Non-streaming: buffer body
                response_body_chunks.append(chunk)
                more = message.get("more_body", False)
                if not more:
                    # Full body captured — screen it
                    full_body = b"".join(response_body_chunks)
                    final_body = await self._screen_response_body(
                        engine, full_body, path, source_ip, response_status,
                    )
                    # Update content-length if body changed
                    patched_headers = self._patch_content_length(response_headers, len(final_body))
                    await send({
                        "type": "http.response.start",
                        "status": response_status,
                        "headers": patched_headers,
                    })
                    await send({
                        "type": "http.response.body",
                        "body": final_body,
                    })

        await self.app(scope, replay_receive, capture_send)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _screen_response_body(
        engine: GuardrailEngine,
        body: bytes,
        path: str,
        source_ip: str,
        status: int,
    ) -> bytes:
        """Screen response body; return (possibly modified) bytes."""
        if status >= 400:
            # Don't screen error responses
            return body

        try:
            data = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return body  # Not JSON — pass through

        # Extract model output text
        output_text = _extract_output_text(data)
        if not output_text:
            return body

        verdict = await engine.ascreen_output(
            output_text, endpoint=path, source_ip=source_ip,
        )

        if not verdict.allowed:
            return _error_response(
                403,
                f"Response blocked by content safety filter: {verdict.explanation}",
                "output_filtered",
            )

        modified = False

        # Apply PII redaction
        if verdict.redacted_content and verdict.action == SafetyAction.REDACT:
            data = _replace_output_text(data, verdict.redacted_content)
            modified = True

        # Inject disclaimers
        disclaimer = verdict.metadata.get("disclaimer", "")
        if disclaimer:
            data = _append_disclaimer(data, disclaimer)
            modified = True

        if modified:
            return json.dumps(data).encode("utf-8")
        return body

    @staticmethod
    def _patch_content_length(headers: List[List[bytes]], new_length: int) -> List[List[bytes]]:
        """Replace content-length header with new value."""
        patched = []
        found = False
        for h in headers:
            if h[0] == b"content-length":
                patched.append([b"content-length", str(new_length).encode()])
                found = True
            else:
                patched.append(h)
        if not found:
            patched.append([b"content-length", str(new_length).encode()])
        return patched


# ============================================================================
# Response text extraction / patching
# ============================================================================

def _extract_output_text(data: Dict[str, Any]) -> str:
    """Pull the model's generated text from a response JSON."""
    # OpenAI chat format
    choices = data.get("choices", [])
    if choices and isinstance(choices, list):
        msg = choices[0].get("message", {})
        if isinstance(msg, dict):
            return msg.get("content", "")
        # Agent/other format
        return choices[0].get("text", "")

    # Agent response format
    if "result" in data:
        return str(data["result"])

    # Generation format
    if "data_base64" in data:
        return ""  # Binary — no text to screen

    return ""


def _replace_output_text(data: Dict[str, Any], new_text: str) -> Dict[str, Any]:
    """Replace the model output text in a response dict."""
    choices = data.get("choices", [])
    if choices and isinstance(choices, list):
        msg = choices[0].get("message", {})
        if isinstance(msg, dict) and "content" in msg:
            msg["content"] = new_text
            return data

    if "result" in data:
        data["result"] = new_text

    return data


def _append_disclaimer(data: Dict[str, Any], disclaimer: str) -> Dict[str, Any]:
    """Append a disclaimer to the model output text."""
    choices = data.get("choices", [])
    if choices and isinstance(choices, list):
        msg = choices[0].get("message", {})
        if isinstance(msg, dict) and "content" in msg:
            msg["content"] = msg["content"] + "\n\n" + disclaimer
            return data

    if "result" in data:
        data["result"] = str(data["result"]) + "\n\n" + disclaimer

    return data
