"""
Output filter — post-processing validation pipeline.

Runs on every model/agent response before it reaches the user.  The pipeline:

    1. **Content classification** — block toxic / harmful model output.
    2. **Domain guards** — detect medical, financial, legal advice and
       inject disclaimers or block.
    3. **PII scrubbing** — remove any PII that leaked into the response.
    4. **Disclaimer injection** — append domain disclaimers where needed.

The filter is stateless and designed for sub-5 ms latency on typical outputs.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from versaai.safety.types import (
    ContentCategory,
    SafetyAction,
    SafetyVerdict,
    ThreatLevel,
)
from versaai.safety.classifier import ContentClassifier, ClassifierConfig
from versaai.safety.pii import PIIDetector
from versaai.safety.domain_guards import DomainGuardChain, MedicalGuard, FinancialGuard, LegalGuard

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class OutputFilterConfig:
    """Tuneable knobs for the output filter."""
    classify_content: bool = True
    run_domain_guards: bool = True
    scrub_pii: bool = True
    medical_mode: str = "warn"    # "warn" | "block"
    financial_mode: str = "warn"  # "warn" | "block"
    legal_mode: str = "warn"      # "warn" | "block"
    classifier_config: Optional[ClassifierConfig] = None


# ============================================================================
# Filter
# ============================================================================

class OutputFilter:
    """
    Post-processing safety pipeline for model/agent outputs.

    Usage::

        filt = OutputFilter()
        verdict = filt.check("Here is the medical advice you requested...")
        if verdict.action == SafetyAction.BLOCK:
            return error_response(verdict)
        text = verdict.redacted_content or original_text
        if verdict.metadata.get("disclaimer"):
            text += "\\n\\n" + verdict.metadata["disclaimer"]
    """

    def __init__(self, config: Optional[OutputFilterConfig] = None):
        self._config = config or OutputFilterConfig()
        self._classifier = ContentClassifier(self._config.classifier_config)
        self._pii = PIIDetector()
        self._domain_chain = DomainGuardChain([
            MedicalGuard(mode=self._config.medical_mode),
            FinancialGuard(mode=self._config.financial_mode),
            LegalGuard(mode=self._config.legal_mode),
        ])

    def check(self, text: str) -> SafetyVerdict:
        """
        Run the full output pipeline.  Returns a single merged ``SafetyVerdict``.
        """
        if not text:
            return SafetyVerdict.safe()

        all_categories: List[ContentCategory] = []
        all_explanations: List[str] = []
        disclaimers: List[str] = []
        worst_action = SafetyAction.ALLOW
        worst_threat = ThreatLevel.NONE
        meta: Dict[str, Any] = {}

        # --- 1. Content classification ---
        if self._config.classify_content:
            cv = self._classifier.classify(text)
            if cv.action == SafetyAction.BLOCK:
                return cv  # Hard block — don't bother with remaining checks
            if cv.categories != [ContentCategory.SAFE]:
                all_categories.extend(cv.categories)
                all_explanations.append(cv.explanation)
                worst_action = self._escalate(worst_action, cv.action)
                worst_threat = self._worse_threat(worst_threat, cv.threat_level)
                meta.update(cv.metadata)

        # --- 2. Domain guards ---
        if self._config.run_domain_guards:
            dv = self._domain_chain.check(text)
            if dv.action == SafetyAction.BLOCK:
                return dv
            if dv.categories != [ContentCategory.SAFE]:
                all_categories.extend(dv.categories)
                all_explanations.append(dv.explanation)
                worst_action = self._escalate(worst_action, dv.action)
                worst_threat = self._worse_threat(worst_threat, dv.threat_level)
                d = dv.metadata.get("disclaimer", "")
                if d:
                    disclaimers.append(d)

        # --- 3. PII scrubbing ---
        redacted_content = None
        pii_matches = []
        if self._config.scrub_pii:
            pii_matches = self._pii.detect(text)
            if pii_matches:
                redacted_content = self._pii.redact(text)
                all_categories.append(ContentCategory.PII_EXPOSURE)
                all_explanations.append(f"PII scrubbed ({len(pii_matches)} match(es))")
                worst_action = self._escalate(worst_action, SafetyAction.REDACT)
                worst_threat = self._worse_threat(worst_threat, ThreatLevel.MEDIUM)

        # --- Clean exit ---
        if not all_categories:
            return SafetyVerdict.safe()

        if disclaimers:
            meta["disclaimer"] = "\n\n".join(disclaimers)

        return SafetyVerdict(
            allowed=(worst_action != SafetyAction.BLOCK),
            categories=list(dict.fromkeys(all_categories)),
            threat_level=worst_threat,
            action=worst_action,
            explanation=" | ".join(all_explanations),
            redacted_content=redacted_content,
            pii_matches=pii_matches,
            metadata=meta,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    _ACTION_ORDER = {
        SafetyAction.ALLOW: 0,
        SafetyAction.AUDIT: 1,
        SafetyAction.WARN: 2,
        SafetyAction.REDACT: 3,
        SafetyAction.BLOCK: 4,
    }

    @classmethod
    def _escalate(cls, current: SafetyAction, new: SafetyAction) -> SafetyAction:
        if cls._ACTION_ORDER.get(new, 0) > cls._ACTION_ORDER.get(current, 0):
            return new
        return current

    _THREAT_ORDER = {
        ThreatLevel.NONE: 0,
        ThreatLevel.LOW: 1,
        ThreatLevel.MEDIUM: 2,
        ThreatLevel.HIGH: 3,
        ThreatLevel.CRITICAL: 4,
    }

    @classmethod
    def _worse_threat(cls, current: ThreatLevel, new: ThreatLevel) -> ThreatLevel:
        if cls._THREAT_ORDER.get(new, 0) > cls._THREAT_ORDER.get(current, 0):
            return new
        return current
