"""
VersaAI Safety & Content Filtering — Phase 6

Layered guardrail system that protects all inputs and outputs flowing
through VersaAI.  Every request is screened before it reaches an agent or
model, and every response is screened before it is returned to the user.

Architecture
────────────
    Request
      ↓
    InputFilter  (PII, injection, content class)
      ↓           ╲ blocked → 403 + audit
    Agent / Model
      ↓
    OutputFilter (content class, domain guards, PII scrub)
      ↓           ╲ blocked / redacted → sanitised response + audit
    Response

Modules
───────
types            Core enums and dataclasses (ContentCategory, SafetyVerdict, …)
classifier       Multi-label text content classification
pii              PII detection and redaction
prompt_injection Prompt-injection / jailbreak detection
domain_guards    Medical, financial, legal advice guardrails
input_filter     Pre-processing validation pipeline
output_filter    Post-processing validation pipeline
guardrails       Central GuardrailEngine orchestrating all checks
audit            Async safety audit trail logger
"""

from versaai.safety.types import (
    ContentCategory,
    ThreatLevel,
    SafetyAction,
    SafetyVerdict,
    PIIType,
    PIIMatch,
    AuditEntry,
)
from versaai.safety.classifier import ContentClassifier
from versaai.safety.pii import PIIDetector
from versaai.safety.prompt_injection import PromptInjectionDetector
from versaai.safety.domain_guards import DomainGuardChain, MedicalGuard, FinancialGuard, LegalGuard
from versaai.safety.input_filter import InputFilter
from versaai.safety.output_filter import OutputFilter
from versaai.safety.guardrails import GuardrailEngine
from versaai.safety.audit import SafetyAuditLog

__all__ = [
    # Types
    "ContentCategory",
    "ThreatLevel",
    "SafetyAction",
    "SafetyVerdict",
    "PIIType",
    "PIIMatch",
    "AuditEntry",
    # Components
    "ContentClassifier",
    "PIIDetector",
    "PromptInjectionDetector",
    "DomainGuardChain",
    "MedicalGuard",
    "FinancialGuard",
    "LegalGuard",
    "InputFilter",
    "OutputFilter",
    # Engine
    "GuardrailEngine",
    "SafetyAuditLog",
]
