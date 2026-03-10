"""
PII (Personally Identifiable Information) detector and redactor.

Detects:
    - Email addresses
    - Phone numbers (international + US/UK/EU formats)
    - Social Security Numbers (US SSN)
    - Credit/debit card numbers (Luhn-validated)
    - IPv4 / IPv6 addresses
    - Dates of birth (common formats)
    - Passport numbers (generic)
    - US driver's license patterns

Design:
    - Pure regex + Luhn — no ML model required, sub-millisecond latency.
    - Returns ``List[PIIMatch]`` with character offsets for precise redaction.
    - ``redact()`` replaces each match with a typed placeholder:
      ``[EMAIL_REDACTED]``, ``[PHONE_REDACTED]``, etc.
    - Thread-safe and stateless.
"""

from __future__ import annotations

import re
from typing import List, Optional

from versaai.safety.types import PIIMatch, PIIType


# ============================================================================
# Compiled patterns
# ============================================================================

# Each tuple: (PIIType, compiled_regex, confidence, optional validator fn)

def _luhn_check(number_str: str) -> bool:
    """Validate a number string using the Luhn algorithm."""
    digits = [int(d) for d in number_str if d.isdigit()]
    if len(digits) < 13:
        return False
    checksum = 0
    reverse = digits[::-1]
    for i, d in enumerate(reverse):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


_PII_PATTERNS: list[tuple[PIIType, re.Pattern[str], float, Optional[callable]]] = [
    # Email — RFC 5321 simplified
    (
        PIIType.EMAIL,
        re.compile(
            r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b"
        ),
        0.95,
        None,
    ),
    # Phone — international (+1…), US (xxx-xxx-xxxx), parenthetical, dotted
    (
        PIIType.PHONE,
        re.compile(
            r"(?<!\d)"
            r"(?:\+?1[\s\-.]?)?"
            r"(?:\(?\d{3}\)?[\s\-.]?)"
            r"\d{3}[\s\-.]?\d{4}"
            r"(?!\d)"
        ),
        0.80,
        None,
    ),
    # Phone — international non-US (e.g. +44, +91, +49)
    (
        PIIType.PHONE,
        re.compile(r"\+(?:44|91|49|33|86|81|61|55|34|39)\s?\d[\d\s\-.]{7,14}\b"),
        0.75,
        None,
    ),
    # SSN — US format (xxx-xx-xxxx), reject 000, 666, 9xx area numbers
    (
        PIIType.SSN,
        re.compile(
            r"\b(?!000|666|9\d{2})\d{3}"
            r"[\-\s]?"
            r"(?!00)\d{2}"
            r"[\-\s]?"
            r"(?!0000)\d{4}\b"
        ),
        0.70,
        None,
    ),
    # Credit card — 13-19 digits with optional separators, Luhn validated
    (
        PIIType.CREDIT_CARD,
        re.compile(
            r"\b(?:\d[\s\-]?){13,19}\b"
        ),
        0.85,
        lambda m: _luhn_check(m),
    ),
    # IPv4
    (
        PIIType.IP_ADDRESS,
        re.compile(
            r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d\d?)\.){3}"
            r"(?:25[0-5]|2[0-4]\d|1?\d\d?)\b"
        ),
        0.70,
        # Exclude common non-PII IPs like 127.0.0.1, 0.0.0.0, 192.168.x.x, 10.x.x.x
        lambda m: not re.match(
            r"^(?:127\.0\.0\.1|0\.0\.0\.0|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|"
            r"172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+|255\.255\.255\.\d+|localhost)$",
            m,
        ),
    ),
    # Date of birth — MM/DD/YYYY, DD-MM-YYYY, YYYY-MM-DD (only flag near DOB keywords)
    (
        PIIType.DATE_OF_BIRTH,
        re.compile(
            r"(?:(?:born|dob|birth(?:day|date)?|d\.o\.b\.?)\s*[:=]?\s*)"
            r"(\d{1,2}[\-/\.]\d{1,2}[\-/\.]\d{2,4}|\d{4}[\-/\.]\d{1,2}[\-/\.]\d{1,2})",
            re.IGNORECASE,
        ),
        0.85,
        None,
    ),
    # Passport — generic (letter + 6-9 digits)
    (
        PIIType.PASSPORT,
        re.compile(
            r"(?:passport\s*(?:no|number|#|:)\s*)"
            r"([A-Z]{1,2}\d{6,9})",
            re.IGNORECASE,
        ),
        0.75,
        None,
    ),
    # Driver's license — context-dependent (US-centric)
    (
        PIIType.DRIVERS_LICENSE,
        re.compile(
            r"(?:driver'?s?\s*licen[sc]e\s*(?:no|number|#|:)\s*)"
            r"([A-Z0-9]{5,15})",
            re.IGNORECASE,
        ),
        0.70,
        None,
    ),
]


# ============================================================================
# Detector
# ============================================================================

class PIIDetector:
    """
    Stateless PII detector.

    Usage::

        detector = PIIDetector()
        matches = detector.detect("Email me at abc@example.com")
        cleaned = detector.redact("Email me at abc@example.com")
    """

    def __init__(self, *, min_confidence: float = 0.0):
        """
        Args:
            min_confidence: Minimum confidence to return a match (0.0–1.0).
        """
        self._min_confidence = min_confidence

    def detect(self, text: str) -> List[PIIMatch]:
        """Return all PII matches found in *text*, sorted by start offset."""
        if not text:
            return []

        matches: List[PIIMatch] = []

        for pii_type, pattern, confidence, validator in _PII_PATTERNS:
            if confidence < self._min_confidence:
                continue
            for m in pattern.finditer(text):
                value = m.group(1) if m.lastindex else m.group(0)
                # Run optional validator (e.g. Luhn check)
                if validator is not None:
                    raw_digits = re.sub(r"[^\d]", "", value)
                    if not validator(raw_digits if pii_type == PIIType.CREDIT_CARD else value):
                        continue
                matches.append(
                    PIIMatch(
                        pii_type=pii_type,
                        value=value,
                        start=m.start(),
                        end=m.end(),
                        confidence=confidence,
                    )
                )

        # Deduplicate overlapping matches — keep highest confidence
        matches = self._deduplicate(matches)
        matches.sort(key=lambda m: m.start)
        return matches

    def redact(self, text: str) -> str:
        """Return *text* with all PII replaced by typed placeholders."""
        matches = self.detect(text)
        if not matches:
            return text

        # Replace from end to start so offsets stay valid
        result = list(text)
        for m in reversed(matches):
            result[m.start : m.end] = list(m.redacted)
        return "".join(result)

    def has_pii(self, text: str) -> bool:
        """Quick check — returns True on first PII match."""
        for pii_type, pattern, confidence, validator in _PII_PATTERNS:
            if confidence < self._min_confidence:
                continue
            m = pattern.search(text)
            if m is None:
                continue
            if validator is not None:
                value = m.group(1) if m.lastindex else m.group(0)
                raw_digits = re.sub(r"[^\d]", "", value)
                if not validator(raw_digits if pii_type == PIIType.CREDIT_CARD else value):
                    continue
            return True
        return False

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _deduplicate(matches: List[PIIMatch]) -> List[PIIMatch]:
        """Remove overlapping matches, keeping the one with highest confidence."""
        if len(matches) <= 1:
            return matches

        matches_sorted = sorted(matches, key=lambda m: (m.start, -m.confidence))
        result: List[PIIMatch] = [matches_sorted[0]]

        for current in matches_sorted[1:]:
            prev = result[-1]
            # Overlap?
            if current.start < prev.end:
                # Keep higher confidence
                if current.confidence > prev.confidence:
                    result[-1] = current
            else:
                result.append(current)

        return result
