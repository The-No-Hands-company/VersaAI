"""
Input filter — pre-processing validation pipeline.

Runs before any user input reaches an agent or model.  The pipeline is:

    1. **Size / encoding validation** — reject oversized or malformed input.
    2. **Control-character stripping** — remove zero-width and invisible chars.
    3. **Prompt-injection detection** — block jailbreak attempts.
    4. **Content classification** — block toxic / harmful / illegal content.
    5. **PII detection** — optionally redact PII in the user prompt.

The filter is stateless and designed for sub-5 ms latency on typical inputs.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from versaai.safety.types import (
    ContentCategory,
    SafetyAction,
    SafetyVerdict,
    ThreatLevel,
    AuditEntry,
)
from versaai.safety.classifier import ContentClassifier, ClassifierConfig
from versaai.safety.pii import PIIDetector
from versaai.safety.prompt_injection import PromptInjectionDetector

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class InputFilterConfig:
    """Tuneable knobs for the input filter."""
    max_input_length: int = 100_000  # characters
    strip_control_chars: bool = True
    detect_injection: bool = True
    classify_content: bool = True
    detect_pii: bool = True
    redact_pii: bool = False  # If True, PII is scrubbed before forwarding
    classifier_config: Optional[ClassifierConfig] = None
    injection_score_threshold: float = 0.5


# ============================================================================
# Filter
# ============================================================================

class InputFilter:
    """
    Pre-processing safety pipeline for user inputs.

    Usage::

        filt = InputFilter()
        verdict = filt.check("Hello, my SSN is 123-45-6789")
        if not verdict.allowed:
            return error_response(verdict)
        # Use verdict.redacted_content if PII was scrubbed
    """

    def __init__(self, config: Optional[InputFilterConfig] = None):
        self._config = config or InputFilterConfig()
        self._classifier = ContentClassifier(self._config.classifier_config)
        self._pii = PIIDetector()
        self._injection = PromptInjectionDetector(
            score_threshold=self._config.injection_score_threshold,
        )

    def check(self, text: str) -> SafetyVerdict:
        """
        Run the full input pipeline.  Returns a single merged ``SafetyVerdict``.
        """
        start = time.monotonic()

        # --- 1. Size validation ---
        if len(text) > self._config.max_input_length:
            return SafetyVerdict.blocked(
                categories=[ContentCategory.SAFE],
                explanation=(
                    f"Input too long: {len(text)} chars "
                    f"(max {self._config.max_input_length})"
                ),
                threat_level=ThreatLevel.LOW,
            )

        # --- 2. Strip control characters ---
        cleaned = self._strip_controls(text) if self._config.strip_control_chars else text

        # --- 3. Prompt-injection detection ---
        if self._config.detect_injection:
            injection_verdict = self._injection.check(cleaned)
            if not injection_verdict.allowed:
                return injection_verdict

        # --- 4. Content classification ---
        if self._config.classify_content:
            content_verdict = self._classifier.classify(cleaned)
            if not content_verdict.allowed:
                return content_verdict

        # --- 5. PII detection ---
        pii_matches = []
        redacted_content = None
        if self._config.detect_pii:
            pii_matches = self._pii.detect(cleaned)
            if pii_matches and self._config.redact_pii:
                redacted_content = self._pii.redact(cleaned)

        # --- Merge results ---
        if pii_matches:
            return SafetyVerdict.redacted(
                original=cleaned,
                cleaned=redacted_content or cleaned,
                pii_matches=pii_matches,
            )

        return SafetyVerdict.safe()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    _CONTROL_STRIP = str.maketrans(
        "",
        "",
        "".join(
            chr(cp)
            for cp in (
                0x200B, 0x200C, 0x200D, 0x200E, 0x200F,
                0x202A, 0x202B, 0x202C, 0x202D, 0x202E,
                0x2060, 0x2061, 0x2062, 0x2063, 0x2064,
                0xFEFF, 0x00AD,
            )
        ),
    )

    @classmethod
    def _strip_controls(cls, text: str) -> str:
        return text.translate(cls._CONTROL_STRIP)
