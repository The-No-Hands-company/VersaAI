"""
Central Guardrail Engine — orchestrates the full safety pipeline.

This is the single entry point that the API middleware and agent
dispatchers call.  It composes all safety sub-systems into two
top-level methods:

    ``screen_input(text, …)``  — run before agent/model execution
    ``screen_output(text, …)`` — run after agent/model execution

Both return a ``SafetyVerdict``.  If ``verdict.allowed`` is False
the caller must reject the request/response.

Lifecycle:
    Instantiate once at app startup (via ``get_guardrail_engine()``
    singleton) and reuse.  All internal components are stateless
    so the engine is fully thread-safe.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from versaai.safety.types import (
    ContentCategory,
    SafetyAction,
    SafetyVerdict,
    ThreatLevel,
)
from versaai.safety.input_filter import InputFilter, InputFilterConfig
from versaai.safety.output_filter import OutputFilter, OutputFilterConfig
from versaai.safety.audit import SafetyAuditLog

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class GuardrailConfig:
    """Top-level safety configuration (maps to ``SafetyConfig`` in settings)."""

    enabled: bool = True

    # Input filtering
    max_input_length: int = 100_000
    detect_injection: bool = True
    classify_input: bool = True
    detect_pii_input: bool = True
    redact_pii_input: bool = False

    # Output filtering
    classify_output: bool = True
    run_domain_guards: bool = True
    scrub_pii_output: bool = True
    medical_mode: str = "warn"    # "warn" | "block"
    financial_mode: str = "warn"
    legal_mode: str = "warn"

    # Audit
    audit_enabled: bool = True
    audit_dir: Optional[str] = None

    # Injection detection
    injection_score_threshold: float = 0.5


# ============================================================================
# Engine
# ============================================================================

class GuardrailEngine:
    """
    Central safety orchestrator.

    Usage::

        engine = GuardrailEngine()

        # Before model call
        iv = engine.screen_input(user_message, endpoint="/v1/chat/completions")
        if not iv.allowed:
            return error_403(iv)

        response = model.generate(...)

        # After model call
        ov = engine.screen_output(response, endpoint="/v1/chat/completions")
        if not ov.allowed:
            return error_403(ov)
        final_text = ov.redacted_content or response
    """

    def __init__(self, config: Optional[GuardrailConfig] = None):
        self._config = config or GuardrailConfig()

        self._input_filter = InputFilter(InputFilterConfig(
            max_input_length=self._config.max_input_length,
            detect_injection=self._config.detect_injection,
            classify_content=self._config.classify_input,
            detect_pii=self._config.detect_pii_input,
            redact_pii=self._config.redact_pii_input,
            injection_score_threshold=self._config.injection_score_threshold,
        ))

        self._output_filter = OutputFilter(OutputFilterConfig(
            classify_content=self._config.classify_output,
            run_domain_guards=self._config.run_domain_guards,
            scrub_pii=self._config.scrub_pii_output,
            medical_mode=self._config.medical_mode,
            financial_mode=self._config.financial_mode,
            legal_mode=self._config.legal_mode,
        ))

        self._audit: Optional[SafetyAuditLog] = None
        if self._config.audit_enabled:
            self._audit = SafetyAuditLog(log_dir=self._config.audit_dir)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    @property
    def audit(self) -> Optional[SafetyAuditLog]:
        return self._audit

    def screen_input(
        self,
        text: str,
        *,
        endpoint: str = "",
        source_ip: str = "",
        user_id: str = "",
    ) -> SafetyVerdict:
        """
        Screen user input before it reaches agents/models.

        Returns:
            A ``SafetyVerdict``.  If ``allowed`` is False, the request
            must be rejected.
        """
        if not self._config.enabled:
            return SafetyVerdict.safe()

        start = time.monotonic()
        verdict = self._input_filter.check(text)
        elapsed_ms = (time.monotonic() - start) * 1000

        if self._audit:
            self._audit.record(
                direction="input",
                endpoint=endpoint,
                content=text,
                verdict=verdict,
                source_ip=source_ip,
                user_id=user_id,
                latency_ms=round(elapsed_ms, 2),
            )

        if not verdict.allowed:
            logger.warning(
                "Input BLOCKED: endpoint=%s categories=%s threat=%s",
                endpoint,
                [c.value for c in verdict.categories],
                verdict.threat_level.value,
            )
        elif verdict.action not in (SafetyAction.ALLOW,):
            logger.info(
                "Input flagged: endpoint=%s action=%s categories=%s",
                endpoint,
                verdict.action.value,
                [c.value for c in verdict.categories],
            )

        return verdict

    def screen_output(
        self,
        text: str,
        *,
        endpoint: str = "",
        source_ip: str = "",
        user_id: str = "",
    ) -> SafetyVerdict:
        """
        Screen model/agent output before it reaches the user.

        Returns:
            A ``SafetyVerdict``.  Use ``verdict.redacted_content`` if PII
            was scrubbed, and check ``verdict.metadata["disclaimer"]``
            for domain-specific disclaimers to append.
        """
        if not self._config.enabled:
            return SafetyVerdict.safe()

        start = time.monotonic()
        verdict = self._output_filter.check(text)
        elapsed_ms = (time.monotonic() - start) * 1000

        if self._audit:
            self._audit.record(
                direction="output",
                endpoint=endpoint,
                content=text,
                verdict=verdict,
                source_ip=source_ip,
                user_id=user_id,
                latency_ms=round(elapsed_ms, 2),
            )

        if not verdict.allowed:
            logger.warning(
                "Output BLOCKED: endpoint=%s categories=%s threat=%s",
                endpoint,
                [c.value for c in verdict.categories],
                verdict.threat_level.value,
            )

        return verdict

    # ------------------------------------------------------------------
    # Async variants
    # ------------------------------------------------------------------

    async def ascreen_input(
        self,
        text: str,
        *,
        endpoint: str = "",
        source_ip: str = "",
        user_id: str = "",
    ) -> SafetyVerdict:
        """Async wrapper — safety checks are CPU-bound so this just delegates."""
        return self.screen_input(
            text, endpoint=endpoint, source_ip=source_ip, user_id=user_id,
        )

    async def ascreen_output(
        self,
        text: str,
        *,
        endpoint: str = "",
        source_ip: str = "",
        user_id: str = "",
    ) -> SafetyVerdict:
        return self.screen_output(
            text, endpoint=endpoint, source_ip=source_ip, user_id=user_id,
        )


# ============================================================================
# Singleton accessor
# ============================================================================

_engine: Optional[GuardrailEngine] = None


def get_guardrail_engine(config: Optional[GuardrailConfig] = None) -> GuardrailEngine:
    """Return (or create) the global ``GuardrailEngine`` singleton."""
    global _engine
    if _engine is None:
        _engine = GuardrailEngine(config)
    return _engine


def reset_guardrail_engine() -> None:
    """Reset the singleton (for testing)."""
    global _engine
    _engine = None
