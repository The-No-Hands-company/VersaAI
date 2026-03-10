"""
Domain-specific guardrails for high-risk content categories.

VersaAI's ``Requirements_and_Constraints.md`` mandates:

    MUST NOT generate code, medical advice, or financial recommendations
    without integrated Verification Agent providing sources/caveats.

These guards detect when output crosses into regulated territory and either:
    - **Block** the response, or
    - **Inject a disclaimer** (configurable per guard).

Architecture:
    Each guard is a stateless callable implementing the ``DomainGuard``
    protocol.  ``DomainGuardChain`` runs all guards in sequence and
    returns the most restrictive verdict.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from versaai.safety.types import ContentCategory, SafetyAction, SafetyVerdict, ThreatLevel

logger = logging.getLogger(__name__)


# ============================================================================
# Base interface
# ============================================================================

class DomainGuard(ABC):
    """Protocol for domain-specific guards."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def category(self) -> ContentCategory: ...

    @abstractmethod
    def check(self, text: str) -> SafetyVerdict:
        """Analyse *text* and return a verdict."""
        ...


# ============================================================================
# Medical advice guard
# ============================================================================

_MEDICAL_PATTERNS: List[tuple[re.Pattern[str], float]] = [
    # Dosage / prescription
    (re.compile(
        r"\b(?:take|prescribe|administer|inject|dose|dosage)\s+"
        r"(?:\d+\s*(?:mg|ml|mcg|iu|cc|tablet|pill|capsule))",
        re.IGNORECASE,
    ), 0.8),
    # Diagnosis
    (re.compile(
        r"\b(?:you\s+(?:have|likely\s+have|probably\s+have|may\s+have|might\s+have)|"
        r"(?:this|that|it)\s+(?:is|looks?\s+like|appears?\s+to\s+be|suggests?)\s+"
        r"(?:a\s+case\s+of|symptoms?\s+of))"
        r".*?(?:disease|syndrome|disorder|infection|cancer|diabetes|"
        r"depression|anxiety|adhd|autism|bipolar)",
        re.IGNORECASE | re.DOTALL,
    ), 0.7),
    # Treatment recommendations
    (re.compile(
        r"\b(?:you\s+should|i\s+recommend|i\s+suggest|i\s+advise)\s+"
        r".*?(?:stop\s+taking|start\s+taking|increase\s+(?:your\s+)?dose|"
        r"decrease\s+(?:your\s+)?dose|switch\s+to|combine\s+with|"
        r"take\s+(?:this|these)\s+(?:medication|medicine|drug|supplement))",
        re.IGNORECASE | re.DOTALL,
    ), 0.8),
    # Medication names (common high-risk)
    (re.compile(
        r"\b(?:take|use|try)\s+"
        r"(?:metformin|lisinopril|atorvastatin|amlodipine|metoprolol|"
        r"omeprazole|losartan|gabapentin|hydrochlorothiazide|sertraline|"
        r"amoxicillin|prednisone|tramadol|oxycodone|morphine|fentanyl|"
        r"insulin|warfarin|lithium|valium|xanax|adderall|ritalin)\b",
        re.IGNORECASE,
    ), 0.85),
    # Symptom-based self-diagnosis guidance
    (re.compile(
        r"\b(?:if\s+you\s+(?:experience|notice|feel|have)\s+(?:these\s+)?symptoms?)"
        r".*?(?:it\s+(?:is|could\s+be|might\s+be)|you\s+(?:may|might|probably))",
        re.IGNORECASE | re.DOTALL,
    ), 0.5),
]

_MEDICAL_DISCLAIMER = (
    "⚠️ DISCLAIMER: This information is for educational purposes only and "
    "does not constitute medical advice. Always consult a qualified healthcare "
    "professional before making any medical decisions. VersaAI is not a "
    "licensed medical provider."
)


class MedicalGuard(DomainGuard):
    """Detects medical advice and either blocks or injects a disclaimer."""

    def __init__(self, *, mode: str = "warn"):
        """
        Args:
            mode: "block" to reject medical advice entirely,
                  "warn" to allow but inject disclaimer.
        """
        self._mode = mode

    @property
    def name(self) -> str:
        return "medical_guard"

    @property
    def category(self) -> ContentCategory:
        return ContentCategory.MEDICAL_ADVICE

    def check(self, text: str) -> SafetyVerdict:
        if not text:
            return SafetyVerdict.safe()

        total = 0.0
        for pattern, weight in _MEDICAL_PATTERNS:
            if pattern.search(text):
                total += weight

        total = min(total, 1.0)

        if total < 0.4:
            return SafetyVerdict.safe()

        if self._mode == "block":
            return SafetyVerdict.blocked(
                categories=[ContentCategory.MEDICAL_ADVICE],
                explanation="Medical advice detected — blocked per policy.",
                threat_level=ThreatLevel.HIGH,
                medical_score=round(total, 3),
            )

        return SafetyVerdict.warned(
            categories=[ContentCategory.MEDICAL_ADVICE],
            explanation=f"Medical advice detected (score={total:.2f}).",
            disclaimer=_MEDICAL_DISCLAIMER,
        )


# ============================================================================
# Financial advice guard
# ============================================================================

_FINANCIAL_PATTERNS: List[tuple[re.Pattern[str], float]] = [
    # Investment recommendations
    (re.compile(
        r"\b(?:you\s+should|i\s+recommend|i\s+suggest|i\s+advise)\s+"
        r".*?(?:invest|buy|sell|hold|trade|short|put|call)\s+"
        r".*?(?:stock|share|bond|crypto|bitcoin|ethereum|fund|etf|option)",
        re.IGNORECASE | re.DOTALL,
    ), 0.85),
    # Specific ticker / price targets
    (re.compile(
        r"\b(?:buy|sell)\s+(?:\$?[A-Z]{1,5})\s+"
        r"(?:at|when|below|above)\s+\$?\d+",
        re.IGNORECASE,
    ), 0.9),
    # Portfolio allocation
    (re.compile(
        r"\b(?:allocate|put)\s+\d+\s*%\s+"
        r".*?(?:portfolio|savings?|retirement|401k|ira|roth)",
        re.IGNORECASE | re.DOTALL,
    ), 0.7),
    # Tax advice
    (re.compile(
        r"\b(?:you\s+(?:can|should)|i\s+(?:recommend|suggest))\s+"
        r".*?(?:tax\s+(?:deduction|write[\s\-]?off|shelter|evasion|avoidance)|"
        r"claim\s+(?:this|the)\s+(?:deduction|credit|exemption))",
        re.IGNORECASE | re.DOTALL,
    ), 0.7),
    # Loan / credit advice
    (re.compile(
        r"\b(?:you\s+should|i\s+recommend)\s+"
        r".*?(?:refinanc|consolidat|take\s+out\s+a\s+loan|"
        r"open\s+a\s+credit\s+(?:card|line)|borrow)",
        re.IGNORECASE | re.DOTALL,
    ), 0.6),
]

_FINANCIAL_DISCLAIMER = (
    "⚠️ DISCLAIMER: This information is for educational purposes only and "
    "does not constitute financial advice. Consult a licensed financial "
    "advisor before making any investment or financial decisions. VersaAI "
    "is not a registered investment advisor."
)


class FinancialGuard(DomainGuard):
    """Detects financial advice and either blocks or injects a disclaimer."""

    def __init__(self, *, mode: str = "warn"):
        self._mode = mode

    @property
    def name(self) -> str:
        return "financial_guard"

    @property
    def category(self) -> ContentCategory:
        return ContentCategory.FINANCIAL_ADVICE

    def check(self, text: str) -> SafetyVerdict:
        if not text:
            return SafetyVerdict.safe()

        total = 0.0
        for pattern, weight in _FINANCIAL_PATTERNS:
            if pattern.search(text):
                total += weight

        total = min(total, 1.0)

        if total < 0.4:
            return SafetyVerdict.safe()

        if self._mode == "block":
            return SafetyVerdict.blocked(
                categories=[ContentCategory.FINANCIAL_ADVICE],
                explanation="Financial advice detected — blocked per policy.",
                threat_level=ThreatLevel.HIGH,
                financial_score=round(total, 3),
            )

        return SafetyVerdict.warned(
            categories=[ContentCategory.FINANCIAL_ADVICE],
            explanation=f"Financial advice detected (score={total:.2f}).",
            disclaimer=_FINANCIAL_DISCLAIMER,
        )


# ============================================================================
# Legal advice guard
# ============================================================================

_LEGAL_PATTERNS: List[tuple[re.Pattern[str], float]] = [
    (re.compile(
        r"\b(?:you\s+(?:should|could|can)\s+(?:sue|file\s+(?:a\s+)?(?:lawsuit|claim|complaint))|"
        r"(?:you\s+have|there\s+is)\s+(?:a\s+)?(?:strong|good|valid|viable)\s+"
        r"(?:case|claim|grounds))",
        re.IGNORECASE,
    ), 0.8),
    (re.compile(
        r"\b(?:under\s+(?:section|article|clause|provision)\s+\d+|"
        r"according\s+to\s+(?:the\s+)?(?:law|statute|regulation|code))\s+"
        r".*?(?:you\s+(?:are|can|should|must)|this\s+(?:is|means))",
        re.IGNORECASE | re.DOTALL,
    ), 0.7),
    (re.compile(
        r"\b(?:plead\s+(?:guilty|not\s+guilty)|"
        r"(?:your|the)\s+(?:legal\s+)?rights?\s+(?:include|are|allow)|"
        r"statute\s+of\s+limitations?)",
        re.IGNORECASE,
    ), 0.5),
]

_LEGAL_DISCLAIMER = (
    "⚠️ DISCLAIMER: This information is for educational purposes only and "
    "does not constitute legal advice. Consult a qualified attorney for "
    "legal matters. VersaAI is not a licensed legal professional."
)


class LegalGuard(DomainGuard):
    """Detects legal advice and either blocks or injects a disclaimer."""

    def __init__(self, *, mode: str = "warn"):
        self._mode = mode

    @property
    def name(self) -> str:
        return "legal_guard"

    @property
    def category(self) -> ContentCategory:
        return ContentCategory.LEGAL_ADVICE

    def check(self, text: str) -> SafetyVerdict:
        if not text:
            return SafetyVerdict.safe()

        total = 0.0
        for pattern, weight in _LEGAL_PATTERNS:
            if pattern.search(text):
                total += weight

        total = min(total, 1.0)

        if total < 0.4:
            return SafetyVerdict.safe()

        if self._mode == "block":
            return SafetyVerdict.blocked(
                categories=[ContentCategory.LEGAL_ADVICE],
                explanation="Legal advice detected — blocked per policy.",
                threat_level=ThreatLevel.HIGH,
                legal_score=round(total, 3),
            )

        return SafetyVerdict.warned(
            categories=[ContentCategory.LEGAL_ADVICE],
            explanation=f"Legal advice detected (score={total:.2f}).",
            disclaimer=_LEGAL_DISCLAIMER,
        )


# ============================================================================
# Chain
# ============================================================================

class DomainGuardChain:
    """
    Runs multiple domain guards and returns the most restrictive verdict.

    Usage::

        chain = DomainGuardChain([MedicalGuard(), FinancialGuard(), LegalGuard()])
        verdict = chain.check("Take 500mg ibuprofen and buy AAPL at $180")
    """

    def __init__(self, guards: Optional[List[DomainGuard]] = None):
        self._guards = guards or [MedicalGuard(), FinancialGuard(), LegalGuard()]

    def check(self, text: str) -> SafetyVerdict:
        """Run all guards; return worst verdict."""
        verdicts: List[SafetyVerdict] = []

        for guard in self._guards:
            v = guard.check(text)
            if v.categories != [ContentCategory.SAFE]:
                verdicts.append(v)

        if not verdicts:
            return SafetyVerdict.safe()

        # If any blocked → return first blocked
        for v in verdicts:
            if v.action == SafetyAction.BLOCK:
                return v

        # Merge warnings: combine categories, disclaimers
        merged_categories: List[ContentCategory] = []
        disclaimers: List[str] = []
        explanations: List[str] = []

        for v in verdicts:
            merged_categories.extend(v.categories)
            explanations.append(v.explanation)
            d = v.metadata.get("disclaimer", "")
            if d:
                disclaimers.append(d)

        return SafetyVerdict.warned(
            categories=list(dict.fromkeys(merged_categories)),  # dedupe preserving order
            explanation=" | ".join(explanations),
            disclaimer="\n\n".join(disclaimers),
        )
