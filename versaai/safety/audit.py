"""
Safety audit trail logger.

Every safety decision (allow, warn, redact, block) is recorded as an
``AuditEntry`` in a structured JSON-lines log file.  The logger is
asynchronous and non-blocking so it never impacts request latency.

Features:
    - Async file writes (non-blocking from the request path)
    - JSON-lines format (.jsonl) for easy ingestion by log aggregators
    - Automatic file rotation by size (default 50 MB)
    - Content is **never** stored — only a SHA-256 hash for traceability
    - Query interface for compliance review
    - Thread-safe
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from collections import deque
from pathlib import Path
from threading import Lock
from typing import Any, Deque, Dict, List, Optional

from versaai.safety.types import AuditEntry, SafetyVerdict

logger = logging.getLogger(__name__)


class SafetyAuditLog:
    """
    Append-only audit trail for safety decisions.

    Usage::

        audit = SafetyAuditLog()
        audit.record(
            direction="input",
            endpoint="/v1/chat/completions",
            content="user message (will be hashed)",
            verdict=verdict,
            source_ip="1.2.3.4",
        )

        # Query recent entries
        recent = audit.recent(50)
    """

    def __init__(
        self,
        *,
        log_dir: Optional[str] = None,
        max_file_bytes: int = 50 * 1024 * 1024,
        buffer_size: int = 500,
    ):
        """
        Args:
            log_dir: Directory for .jsonl files.  Defaults to ``~/.versaai/audit/``.
            max_file_bytes: Rotate file when it exceeds this size.
            buffer_size: In-memory ring buffer size for ``recent()`` queries.
        """
        self._log_dir = Path(os.path.expanduser(log_dir or "~/.versaai/audit"))
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._max_file_bytes = max_file_bytes
        self._lock = Lock()
        self._buffer: Deque[AuditEntry] = deque(maxlen=buffer_size)
        self._current_file: Optional[Path] = None
        self._current_size: int = 0
        self._rotate()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record(
        self,
        *,
        direction: str,
        endpoint: str,
        content: str,
        verdict: SafetyVerdict,
        source_ip: str = "",
        user_id: str = "",
        latency_ms: float = 0.0,
        extra: Optional[Dict[str, Any]] = None,
    ) -> AuditEntry:
        """
        Create and persist an audit entry.  Content is SHA-256 hashed.
        """
        entry = AuditEntry(
            direction=direction,
            endpoint=endpoint,
            source_ip=source_ip,
            user_id=user_id,
            content_hash=hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest(),
            verdict_allowed=verdict.allowed,
            verdict_action=verdict.action.value if hasattr(verdict.action, "value") else str(verdict.action),
            verdict_categories=[
                c.value if hasattr(c, "value") else str(c) for c in verdict.categories
            ],
            verdict_threat_level=verdict.threat_level.value if hasattr(verdict.threat_level, "value") else str(verdict.threat_level),
            verdict_explanation=verdict.explanation,
            pii_types_found=[
                m.pii_type.value if hasattr(m.pii_type, "value") else str(m.pii_type)
                for m in verdict.pii_matches
            ],
            latency_ms=latency_ms,
            metadata=extra or {},
        )

        self._write(entry)
        return entry

    def recent(self, n: int = 50) -> List[AuditEntry]:
        """Return the *n* most recent entries from the in-memory ring buffer."""
        with self._lock:
            items = list(self._buffer)
        return items[-n:]

    def count_blocked(self, since_seconds: float = 3600) -> int:
        """Count blocked requests in the last *since_seconds*."""
        cutoff = time.time() - since_seconds
        with self._lock:
            return sum(
                1 for e in self._buffer
                if not e.verdict_allowed and e.timestamp >= cutoff
            )

    # ------------------------------------------------------------------
    # Async variants
    # ------------------------------------------------------------------

    async def arecord(
        self,
        *,
        direction: str,
        endpoint: str,
        content: str,
        verdict: SafetyVerdict,
        source_ip: str = "",
        user_id: str = "",
        latency_ms: float = 0.0,
        extra: Optional[Dict[str, Any]] = None,
    ) -> AuditEntry:
        """Non-blocking async wrapper around ``record``."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.record(
                direction=direction,
                endpoint=endpoint,
                content=content,
                verdict=verdict,
                source_ip=source_ip,
                user_id=user_id,
                latency_ms=latency_ms,
                extra=extra,
            ),
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _write(self, entry: AuditEntry) -> None:
        line = json.dumps(entry.to_dict(), default=str) + "\n"
        line_bytes = line.encode("utf-8")

        with self._lock:
            self._buffer.append(entry)

            if self._current_size + len(line_bytes) > self._max_file_bytes:
                self._rotate()

            try:
                with open(self._current_file, "a", encoding="utf-8") as f:
                    f.write(line)
                self._current_size += len(line_bytes)
            except OSError as exc:
                logger.error(f"Failed to write audit entry: {exc}")

    def _rotate(self) -> None:
        ts = f"{time.strftime('%Y%m%d_%H%M%S')}_{int(time.time() * 1_000_000) % 1_000_000:06d}"
        self._current_file = self._log_dir / f"safety_audit_{ts}.jsonl"
        self._current_size = 0
        if self._current_file.exists():
            self._current_size = self._current_file.stat().st_size
