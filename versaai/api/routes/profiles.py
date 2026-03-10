"""
VersaAI Profile API — persistent user profile management endpoints.

Endpoints:
    POST   /v1/profiles              — Create a profile
    GET    /v1/profiles              — List all profiles
    GET    /v1/profiles/{id}         — Get profile by ID
    PUT    /v1/profiles/{id}         — Update profile
    DELETE /v1/profiles/{id}         — Delete profile
    POST   /v1/profiles/{id}/learn   — Record interaction or learned fact
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from versaai.profiles import ProfileManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/profiles")

# ---------------------------------------------------------------------------
# Singleton manager
# ---------------------------------------------------------------------------

_manager: Optional[ProfileManager] = None


def _get_manager() -> ProfileManager:
    global _manager
    if _manager is None:
        _manager = ProfileManager()
    return _manager


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class CreateProfileRequest(BaseModel):
    profile_id: Optional[str] = Field(None, description="Custom ID or auto-generate")
    display_name: str = Field("", description="Display name")
    preferences: Dict[str, Any] = Field(default_factory=dict)


class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None
    goals: Optional[List[Dict[str, Any]]] = None
    custom: Optional[Dict[str, Any]] = None


class LearnRequest(BaseModel):
    category: str = Field(..., description="'topic', 'expertise', 'language', 'tool', 'domain'")
    value: str = Field(..., min_length=1)


class RecordInteractionRequest(BaseModel):
    agent_used: Optional[str] = None
    topics: Optional[List[str]] = None
    session_duration: float = 0.0


class ProfileSummary(BaseModel):
    profile_id: str
    display_name: str = ""
    created_at: float = 0.0
    last_active: float = 0.0
    interaction_count: int = 0


class ProfileFull(BaseModel):
    profile_id: str
    display_name: str = ""
    avatar_url: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0
    last_active: float = 0.0
    preferences: Dict[str, Any] = {}
    behavior: Dict[str, Any] = {}
    goals: List[Dict[str, Any]] = []
    connectors: Dict[str, Any] = {}
    custom: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", response_model=ProfileFull, status_code=201)
def create_profile(req: CreateProfileRequest):
    mgr = _get_manager()
    try:
        profile = mgr.create(
            profile_id=req.profile_id,
            display_name=req.display_name,
            preferences=req.preferences or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return ProfileFull(**profile.to_dict())


@router.get("", response_model=List[ProfileSummary])
def list_profiles(limit: int = 50, offset: int = 0):
    mgr = _get_manager()
    return [ProfileSummary(**p) for p in mgr.list_profiles(limit, offset)]


@router.get("/{profile_id}", response_model=ProfileFull)
def get_profile(profile_id: str):
    mgr = _get_manager()
    profile = mgr.get(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return ProfileFull(**profile.to_dict())


@router.put("/{profile_id}", response_model=ProfileFull)
def update_profile(profile_id: str, req: UpdateProfileRequest):
    mgr = _get_manager()
    profile = mgr.update(
        profile_id,
        display_name=req.display_name,
        preferences=req.preferences,
        goals=req.goals,
        custom=req.custom,
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return ProfileFull(**profile.to_dict())


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: str):
    mgr = _get_manager()
    if not mgr.delete(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")


@router.post("/{profile_id}/learn", status_code=204)
def learn_fact(profile_id: str, req: LearnRequest):
    mgr = _get_manager()
    profile = mgr.get(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    mgr.learn(profile_id, req.category, req.value)


@router.post("/{profile_id}/interaction", status_code=204)
def record_interaction(profile_id: str, req: RecordInteractionRequest):
    mgr = _get_manager()
    profile = mgr.get(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    mgr.record_interaction(
        profile_id,
        agent_used=req.agent_used,
        topics=req.topics,
        session_duration=req.session_duration,
    )
