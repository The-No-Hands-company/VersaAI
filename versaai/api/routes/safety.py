"""
Safety status API routes — operational visibility into the guardrail system.

Endpoints:
    GET  /v1/safety/status    — Is safety enabled? Recent block counts.
    POST /v1/safety/check     — Dry-run: screen text without executing anything.
    GET  /v1/safety/audit     — Recent audit log entries (admin-only in production).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from versaai.safety.guardrails import get_guardrail_engine
from versaai.safety.types import SafetyAction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/safety")


# ============================================================================
# Schemas
# ============================================================================

class SafetyCheckRequest(BaseModel):
    """Dry-run safety check on arbitrary text."""
    text: str = Field(..., description="Text to screen.")
    direction: str = Field("input", description="'input' or 'output'.")


class SafetyCheckResponse(BaseModel):
    """Result of the dry-run safety check."""
    allowed: bool
    action: str
    threat_level: str
    categories: List[str]
    explanation: str
    pii_types_found: List[str] = []
    metadata: Dict[str, Any] = {}


class SafetyStatusResponse(BaseModel):
    """Current safety system status."""
    enabled: bool
    blocked_last_hour: int
    blocked_last_day: int
    audit_enabled: bool
    recent_audit_count: int


class AuditEntryResponse(BaseModel):
    """Single audit log entry."""
    id: str
    timestamp: float
    direction: str
    endpoint: str
    verdict_allowed: bool
    verdict_action: str
    verdict_categories: List[str]
    verdict_threat_level: str
    verdict_explanation: str
    pii_types_found: List[str]
    latency_ms: float


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/status", response_model=SafetyStatusResponse)
async def safety_status():
    """Current safety system health and block statistics."""
    engine = get_guardrail_engine()
    audit = engine.audit
    return SafetyStatusResponse(
        enabled=engine.enabled,
        blocked_last_hour=audit.count_blocked(3600) if audit else 0,
        blocked_last_day=audit.count_blocked(86400) if audit else 0,
        audit_enabled=audit is not None,
        recent_audit_count=len(audit.recent(500)) if audit else 0,
    )


@router.post("/check", response_model=SafetyCheckResponse)
async def safety_check(req: SafetyCheckRequest):
    """
    Dry-run safety screening on arbitrary text.

    Useful for testing / debugging without actually executing a model call.
    """
    engine = get_guardrail_engine()

    if req.direction == "output":
        verdict = engine.screen_output(req.text, endpoint="/v1/safety/check")
    else:
        verdict = engine.screen_input(req.text, endpoint="/v1/safety/check")

    return SafetyCheckResponse(
        allowed=verdict.allowed,
        action=verdict.action.value,
        threat_level=verdict.threat_level.value,
        categories=[c.value for c in verdict.categories],
        explanation=verdict.explanation,
        pii_types_found=[
            m.pii_type.value for m in verdict.pii_matches
        ],
        metadata=verdict.metadata,
    )


@router.get("/audit", response_model=List[AuditEntryResponse])
async def safety_audit(limit: int = 50):
    """Return recent audit trail entries (most recent first)."""
    engine = get_guardrail_engine()
    audit = engine.audit
    if not audit:
        return []

    entries = audit.recent(min(limit, 500))
    return [
        AuditEntryResponse(
            id=e.id,
            timestamp=e.timestamp,
            direction=e.direction,
            endpoint=e.endpoint,
            verdict_allowed=e.verdict_allowed,
            verdict_action=e.verdict_action,
            verdict_categories=e.verdict_categories,
            verdict_threat_level=e.verdict_threat_level,
            verdict_explanation=e.verdict_explanation,
            pii_types_found=e.pii_types_found,
            latency_ms=e.latency_ms,
        )
        for e in reversed(entries)  # Most recent first
    ]
