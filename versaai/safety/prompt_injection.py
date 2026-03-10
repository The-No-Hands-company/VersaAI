"""
Prompt-injection and jailbreak detection.

Detects attempts to:
    - Override system instructions ("ignore previous instructions")
    - Extract the system prompt ("repeat your instructions verbatim")
    - Role-play bypasses ("act as DAN", "you are now unrestricted")
    - Encoding evasion (base64-wrapped payloads, ROT13, unicode tricks)
    - Delimiter injection (markdown fences, XML tags used to inject)
    - Multi-turn escalation patterns

Detection strategy:
    1. **Structural analysis** — checks for known injection boilerplate.
    2. **Entropy analysis** — high-entropy blocks may be encoded payloads.
    3. **Control-character scan** — zero-width chars and directional overrides.

All methods are stateless and thread-safe.
"""

from __future__ import annotations

import base64
import logging
import math
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from versaai.safety.types import ContentCategory, SafetyVerdict, ThreatLevel, SafetyAction

logger = logging.getLogger(__name__)

# Ordinal map for ThreatLevel comparison (string enum values are not ordinal)
_THREAT_ORDER: dict[ThreatLevel, int] = {
    ThreatLevel.NONE: 0,
    ThreatLevel.LOW: 1,
    ThreatLevel.MEDIUM: 2,
    ThreatLevel.HIGH: 3,
    ThreatLevel.CRITICAL: 4,
}


# ============================================================================
# Pattern banks
# ============================================================================

@dataclass(frozen=True)
class _InjectionPattern:
    name: str
    pattern: re.Pattern[str]
    severity: ThreatLevel
    weight: float = 0.5


_INJECTION_PATTERNS: List[_InjectionPattern] = [
    # -- Instruction override --
    _InjectionPattern(
        "instruction_override",
        re.compile(
            r"(?:ignore|disregard|forget|override|bypass|skip|drop)"
            r"\s+(?:all\s+)?(?:previous|prior|above|earlier|system|original)"
            r"\s+(?:instructions?|rules?|constraints?|prompts?|guidelines?|directives?)",
            re.IGNORECASE,
        ),
        ThreatLevel.HIGH,
        0.9,
    ),
    _InjectionPattern(
        "new_instructions",
        re.compile(
            r"(?:new|your\s+(?:new|real|actual)|updated|revised)"
            r"\s+(?:instructions?|rules?|prompt|directives?)\s*(?:are|is|:)",
            re.IGNORECASE,
        ),
        ThreatLevel.HIGH,
        0.8,
    ),
    # -- System prompt extraction --
    _InjectionPattern(
        "prompt_extraction",
        re.compile(
            r"(?:repeat|print|show|display|reveal|output|return|echo|dump|leak)"
            r"\s+(?:your|the|system)?\s*"
            r"(?:system\s+)?(?:prompt|instructions?|rules?|configuration|initial\s+message)",
            re.IGNORECASE,
        ),
        ThreatLevel.MEDIUM,
        0.7,
    ),
    _InjectionPattern(
        "verbatim_request",
        re.compile(
            r"(?:word\s+for\s+word|verbatim|exactly\s+as|character\s+by\s+character)"
            r".*?(?:instructions?|prompt|rules?|system)",
            re.IGNORECASE,
        ),
        ThreatLevel.MEDIUM,
        0.7,
    ),
    # -- DAN / roleplay jailbreaks --
    _InjectionPattern(
        "dan_jailbreak",
        re.compile(
            r"\b(?:DAN|do\s+anything\s+now)\b",
            re.IGNORECASE,
        ),
        ThreatLevel.HIGH,
        0.8,
    ),
    _InjectionPattern(
        "roleplay_bypass",
        re.compile(
            r"(?:you\s+are\s+now|act\s+as|pretend\s+(?:you\s+are|to\s+be)|"
            r"roleplay\s+as|from\s+now\s+on\s+you\s+are|"
            r"you\s+have\s+been\s+(?:freed|unshackled|liberated|unchained))"
            r".*?(?:unrestricted|unfiltered|uncensored|without\s+(?:limits|restrictions|rules)|"
            r"no\s+(?:rules|ethics|morals|filters|guardrails))",
            re.IGNORECASE | re.DOTALL,
        ),
        ThreatLevel.HIGH,
        0.85,
    ),
    # -- Developer mode / simulation --
    _InjectionPattern(
        "developer_mode",
        re.compile(
            r"(?:developer\s+mode|maintenance\s+mode|debug\s+mode|admin\s+mode|"
            r"god\s+mode|root\s+access|sudo\s+mode)"
            r"\s*(?:enabled|activated|on|unlocked)",
            re.IGNORECASE,
        ),
        ThreatLevel.HIGH,
        0.75,
    ),
    # -- Delimiter injection --
    _InjectionPattern(
        "delimiter_injection",
        re.compile(
            r"(?:```(?:system|instructions?|prompt)[\s\S]*?```|"
            r"<\s*(?:system|instructions?|prompt)\s*>[\s\S]*?<\s*/)",
            re.IGNORECASE,
        ),
        ThreatLevel.MEDIUM,
        0.6,
    ),
    # -- Token smuggling / separation attacks --
    _InjectionPattern(
        "token_smuggling",
        re.compile(
            r"(?:###\s*(?:END|STOP|IGNORE)\s*###|"
            r"\[INST\]|\[/INST\]|<\|(?:im_start|im_end|system|user|assistant)\|>)",
            re.IGNORECASE,
        ),
        ThreatLevel.HIGH,
        0.8,
    ),
    # -- Hypothetical framing --
    _InjectionPattern(
        "hypothetical_bypass",
        re.compile(
            r"(?:hypothetically|theoretically|in\s+a\s+fictional\s+world|"
            r"for\s+(?:educational|research|academic)\s+purposes?\s+only|"
            r"imagine\s+(?:you\s+(?:are|were)|a\s+world\s+where))"
            r".*?(?:how\s+(?:would|could|to)|explain|describe|write|generate)"
            r".*?(?:hack|exploit|attack|weapon|drug|illegal|harmful)",
            re.IGNORECASE | re.DOTALL,
        ),
        ThreatLevel.MEDIUM,
        0.5,
    ),
]


# Unicode control characters that are suspicious in user prompts
_SUSPICIOUS_CODEPOINTS: set[int] = {
    0x200B,  # Zero-width space
    0x200C,  # Zero-width non-joiner
    0x200D,  # Zero-width joiner
    0x200E,  # Left-to-right mark
    0x200F,  # Right-to-left mark
    0x202A,  # Left-to-right embedding
    0x202B,  # Right-to-left embedding
    0x202C,  # Pop directional formatting
    0x202D,  # Left-to-right override
    0x202E,  # Right-to-left override
    0x2060,  # Word joiner
    0x2061,  # Function application
    0x2062,  # Invisible times
    0x2063,  # Invisible separator
    0x2064,  # Invisible plus
    0xFEFF,  # BOM / zero-width no-break space
    0x00AD,  # Soft hyphen
}


# ============================================================================
# Detector
# ============================================================================

class PromptInjectionDetector:
    """
    Stateless prompt-injection detector.

    Usage::

        detector = PromptInjectionDetector()
        verdict = detector.check("Ignore previous instructions and ...")
        if not verdict.allowed:
            ...
    """

    def __init__(
        self,
        *,
        score_threshold: float = 0.5,
        entropy_threshold: float = 4.5,
        max_control_chars: int = 3,
    ):
        """
        Args:
            score_threshold: Accumulated injection score to flag (0.0–1.0).
            entropy_threshold: Shannon entropy per 100-char window that
                triggers base64/encoding suspicion.
            max_control_chars: Maximum suspicious Unicode control characters
                before flagging.
        """
        self._score_threshold = score_threshold
        self._entropy_threshold = entropy_threshold
        self._max_control_chars = max_control_chars

    def check(self, text: str) -> SafetyVerdict:
        """Analyse *text* for prompt-injection attempts."""
        if not text or len(text.strip()) < 5:
            return SafetyVerdict.safe()

        findings: List[str] = []
        total_score = 0.0
        worst_severity = ThreatLevel.NONE

        # 1. Pattern matching
        for pat in _INJECTION_PATTERNS:
            if pat.pattern.search(text):
                total_score += pat.weight
                findings.append(pat.name)
                if _THREAT_ORDER.get(pat.severity, 0) > _THREAT_ORDER.get(worst_severity, 0):
                    worst_severity = pat.severity

        # 2. Unicode control-character scan
        control_count = sum(1 for ch in text if ord(ch) in _SUSPICIOUS_CODEPOINTS)
        if control_count > self._max_control_chars:
            total_score += 0.3
            findings.append(f"suspicious_unicode({control_count})")
            if worst_severity == ThreatLevel.NONE:
                worst_severity = ThreatLevel.MEDIUM

        # 3. Base64 block detection
        b64_blocks = re.findall(r"[A-Za-z0-9+/]{40,}={0,2}", text)
        for block in b64_blocks:
            if self._is_likely_base64(block):
                decoded = self._safe_decode_b64(block)
                if decoded and self._decoded_looks_suspicious(decoded):
                    total_score += 0.4
                    findings.append("encoded_payload")
                    if _THREAT_ORDER.get(worst_severity, 0) < _THREAT_ORDER[ThreatLevel.HIGH]:
                        worst_severity = ThreatLevel.HIGH

        # 4. High-entropy window scan
        if self._has_high_entropy_window(text):
            total_score += 0.2
            findings.append("high_entropy_block")

        total_score = min(total_score, 1.0)

        if total_score < self._score_threshold:
            return SafetyVerdict.safe()

        action = (
            SafetyAction.BLOCK if worst_severity in (ThreatLevel.HIGH, ThreatLevel.CRITICAL)
            else SafetyAction.WARN
        )

        return SafetyVerdict(
            allowed=(action != SafetyAction.BLOCK),
            categories=[ContentCategory.PROMPT_INJECTION],
            threat_level=worst_severity,
            action=action,
            explanation=f"Prompt injection detected: {', '.join(findings)}",
            metadata={
                "injection_score": round(total_score, 3),
                "findings": findings,
            },
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_likely_base64(block: str) -> bool:
        """Heuristic: valid base64 that decodes to mostly printable ASCII."""
        try:
            decoded = base64.b64decode(block + "==", validate=False)
            printable = sum(1 for b in decoded if 32 <= b < 127)
            return printable / max(len(decoded), 1) > 0.7
        except Exception:
            return False

    @staticmethod
    def _safe_decode_b64(block: str) -> Optional[str]:
        try:
            return base64.b64decode(block + "==", validate=False).decode("utf-8", errors="ignore")
        except Exception:
            return None

    @staticmethod
    def _decoded_looks_suspicious(decoded: str) -> bool:
        """Check if decoded payload contains injection-like content."""
        lower = decoded.lower()
        suspects = [
            "ignore", "instruction", "system prompt", "override",
            "jailbreak", "dan", "unrestricted", "unfiltered",
        ]
        return any(s in lower for s in suspects)

    def _has_high_entropy_window(self, text: str, window: int = 100) -> bool:
        """Sliding-window Shannon entropy check."""
        if len(text) < window:
            return False
        for i in range(0, len(text) - window + 1, window // 2):
            chunk = text[i : i + window]
            if self._shannon_entropy(chunk) > self._entropy_threshold:
                return True
        return False

    @staticmethod
    def _shannon_entropy(text: str) -> float:
        if not text:
            return 0.0
        freq: Dict[str, int] = {}
        for ch in text:
            freq[ch] = freq.get(ch, 0) + 1
        length = len(text)
        return -sum(
            (c / length) * math.log2(c / length) for c in freq.values() if c > 0
        )
