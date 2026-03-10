"""
Core types for the VersaAI safety system.

All safety components exchange these types.  They are intentionally
kept immutable (frozen dataclasses) so that audit logs can store
them safely and they can be passed across async boundaries.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ============================================================================
# Content categories
# ============================================================================

class ContentCategory(str, Enum):
    """Multi-label content risk categories.

    Maps directly to the OWASP / NIST AI Safety taxonomy and the
    requirements from ``docs/Requirements_and_Constraints.md``.
    """

    SAFE = "safe"
    TOXIC = "toxic"
    HATE_SPEECH = "hate_speech"
    SEXUAL = "sexual"
    VIOLENCE = "violence"
    SELF_HARM = "self_harm"
    HARASSMENT = "harassment"
    ILLEGAL_ACTIVITY = "illegal_activity"
    CHILD_SAFETY = "child_safety"
    MEDICAL_ADVICE = "medical_advice"
    FINANCIAL_ADVICE = "financial_advice"
    LEGAL_ADVICE = "legal_advice"
    PII_EXPOSURE = "pii_exposure"
    PROMPT_INJECTION = "prompt_injection"
    MALWARE = "malware"
    DECEPTION = "deception"
    DANGEROUS_CAPABILITY = "dangerous_capability"


class ThreatLevel(str, Enum):
    """Severity of the detected threat. Controls the action taken."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SafetyAction(str, Enum):
    """What the guardrail engine should do for a given verdict."""

    ALLOW = "allow"       # No risk — pass through
    WARN = "warn"         # Low risk — add disclaimer/metadata but still deliver
    REDACT = "redact"     # Medium risk — scrub PII / sensitive content
    BLOCK = "block"       # High risk — reject entirely
    AUDIT = "audit"       # Allow but flag for human review


# ============================================================================
# PII types
# ============================================================================

class PIIType(str, Enum):
    """Types of Personally Identifiable Information we detect."""

    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    PHYSICAL_ADDRESS = "physical_address"
    DATE_OF_BIRTH = "date_of_birth"
    PASSPORT = "passport"
    DRIVERS_LICENSE = "drivers_license"
    NAME = "name"


@dataclass(frozen=True)
class PIIMatch:
    """A single PII match within a text."""

    pii_type: PIIType
    value: str
    start: int
    end: int
    confidence: float = 1.0

    @property
    def redacted(self) -> str:
        """Replacement token for this PII type."""
        return f"[{self.pii_type.value.upper()}_REDACTED]"


# ============================================================================
# Safety verdict
# ============================================================================

@dataclass(frozen=True)
class SafetyVerdict:
    """
    The result of running any safety check (classifier, PII, injection, …).

    A ``SafetyVerdict`` is attached to every request/response so that
    downstream components can decide how to act.  ``allowed`` is the
    quick-check boolean; ``categories`` and ``threat_level`` provide
    granular detail.
    """

    allowed: bool
    categories: List[ContentCategory] = field(default_factory=list)
    threat_level: ThreatLevel = ThreatLevel.NONE
    action: SafetyAction = SafetyAction.ALLOW
    explanation: str = ""
    redacted_content: Optional[str] = None
    pii_matches: List[PIIMatch] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Convenience constructors
    # ------------------------------------------------------------------

    @classmethod
    def safe(cls) -> SafetyVerdict:
        """Quick shorthand for 'no issues found'."""
        return cls(
            allowed=True,
            categories=[ContentCategory.SAFE],
            threat_level=ThreatLevel.NONE,
            action=SafetyAction.ALLOW,
        )

    @classmethod
    def blocked(
        cls,
        categories: List[ContentCategory],
        explanation: str,
        threat_level: ThreatLevel = ThreatLevel.HIGH,
        **meta: Any,
    ) -> SafetyVerdict:
        return cls(
            allowed=False,
            categories=categories,
            threat_level=threat_level,
            action=SafetyAction.BLOCK,
            explanation=explanation,
            metadata=meta,
        )

    @classmethod
    def redacted(
        cls,
        original: str,
        cleaned: str,
        pii_matches: List[PIIMatch],
        *,
        categories: Optional[List[ContentCategory]] = None,
    ) -> SafetyVerdict:
        return cls(
            allowed=True,
            categories=categories or [ContentCategory.PII_EXPOSURE],
            threat_level=ThreatLevel.MEDIUM,
            action=SafetyAction.REDACT,
            explanation=f"PII redacted ({len(pii_matches)} match(es))",
            redacted_content=cleaned,
            pii_matches=pii_matches,
        )

    @classmethod
    def warned(
        cls,
        categories: List[ContentCategory],
        explanation: str,
        disclaimer: str = "",
    ) -> SafetyVerdict:
        meta: Dict[str, Any] = {}
        if disclaimer:
            meta["disclaimer"] = disclaimer
        return cls(
            allowed=True,
            categories=categories,
            threat_level=ThreatLevel.LOW,
            action=SafetyAction.WARN,
            explanation=explanation,
            metadata=meta,
        )


# ============================================================================
# Audit entry
# ============================================================================

@dataclass(frozen=True)
class AuditEntry:
    """
    Immutable record of a safety decision.

    Stored by ``SafetyAuditLog`` for compliance/forensics.
    All fields are plain types so the entry can be JSON-serialised
    without custom encoders.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: float = field(default_factory=time.time)
    direction: str = "input"  # "input" | "output"
    endpoint: str = ""
    source_ip: str = ""
    user_id: str = ""
    content_hash: str = ""  # SHA-256 of content (not the content itself)
    verdict_allowed: bool = True
    verdict_action: str = "allow"
    verdict_categories: List[str] = field(default_factory=list)
    verdict_threat_level: str = "none"
    verdict_explanation: str = ""
    pii_types_found: List[str] = field(default_factory=list)
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "direction": self.direction,
            "endpoint": self.endpoint,
            "source_ip": self.source_ip,
            "user_id": self.user_id,
            "content_hash": self.content_hash,
            "verdict": {
                "allowed": self.verdict_allowed,
                "action": self.verdict_action,
                "categories": self.verdict_categories,
                "threat_level": self.verdict_threat_level,
                "explanation": self.verdict_explanation,
            },
            "pii_types_found": self.pii_types_found,
            "latency_ms": self.latency_ms,
            "metadata": self.metadata,
        }
