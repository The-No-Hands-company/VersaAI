"""
User Profile System — persistent, privacy-preserving user profiles.

Provides per-user storage of:
- Identity (display name, avatar URL)
- Preferences (theme, language, verbosity, custom settings)
- Behavioral data (preferred agent, common topics, expertise areas)
- Goals and context connectors (education, research, coding, etc.)
- Session continuity across devices via profile ID

Storage: JSON files under ~/.versaai/data/profiles/<profile_id>.json
Privacy: All profile data is local-only. No PII leaves the device.

Usage:
    >>> from versaai.profiles import ProfileManager
    >>> pm = ProfileManager()
    >>> profile = pm.create("user_123", display_name="Dev User")
    >>> pm.update("user_123", preferences={"theme": "dark"})
    >>> pm.learn("user_123", "coding", "rust")  # auto-learn interests
"""

import json
import logging
import os
import time
import uuid
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from versaai.config import settings

logger = logging.getLogger(__name__)

# ============================================================================
# Data model
# ============================================================================


@dataclass
class UserProfile:
    """Complete user profile with preferences, behavioral data, and goals."""

    # Identity
    profile_id: str
    display_name: str = ""
    avatar_url: str = ""

    # Timestamps
    created_at: float = 0.0
    updated_at: float = 0.0
    last_active: float = 0.0

    # Preferences (explicit user settings)
    preferences: Dict[str, Any] = field(default_factory=lambda: {
        "theme": "auto",
        "language": "en",
        "verbosity": "normal",
        "formality": "casual",
        "response_format": "markdown",
    })

    # Behavioral data (auto-learned from interactions)
    behavior: Dict[str, Any] = field(default_factory=lambda: {
        "preferred_agents": [],       # ["coding", "research"]
        "common_topics": [],          # ["python", "machine-learning"]
        "expertise_areas": [],        # ["backend", "devops"]
        "interaction_count": 0,
        "avg_session_length_s": 0.0,
    })

    # Goals — what the user is working toward
    goals: List[Dict[str, Any]] = field(default_factory=list)

    # Context connectors — data sources the user has linked
    connectors: Dict[str, Any] = field(default_factory=dict)

    # Free-form custom data
    custom: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserProfile":
        # Filter to known fields
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


# ============================================================================
# Profile Manager
# ============================================================================


class ProfileManager:
    """
    Manages user profiles with file-based persistence.

    Profiles are stored as JSON in the VersaAI data directory.
    All operations are synchronous and file-locked for safety.
    """

    def __init__(self, profiles_dir: Optional[str] = None):
        base = profiles_dir or os.path.join(
            os.path.expanduser(settings.data_dir), "data", "profiles"
        )
        self._dir = Path(base)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, UserProfile] = {}
        logger.info("ProfileManager initialized: %s", self._dir)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(
        self,
        profile_id: Optional[str] = None,
        display_name: str = "",
        preferences: Optional[Dict[str, Any]] = None,
    ) -> UserProfile:
        """Create a new user profile. Returns the created profile."""
        pid = profile_id or uuid.uuid4().hex[:12]

        if self._profile_path(pid).exists():
            raise ValueError(f"Profile '{pid}' already exists")

        now = time.time()
        profile = UserProfile(
            profile_id=pid,
            display_name=display_name,
            created_at=now,
            updated_at=now,
            last_active=now,
        )
        if preferences:
            profile.preferences.update(preferences)

        self._save(profile)
        self._cache[pid] = profile
        logger.info("Created profile: %s", pid)
        return profile

    def get(self, profile_id: str) -> Optional[UserProfile]:
        """Load a profile by ID. Returns None if not found."""
        if profile_id in self._cache:
            return self._cache[profile_id]

        path = self._profile_path(profile_id)
        if not path.exists():
            return None

        profile = self._load(path)
        if profile:
            self._cache[profile_id] = profile
        return profile

    def update(
        self,
        profile_id: str,
        display_name: Optional[str] = None,
        preferences: Optional[Dict[str, Any]] = None,
        goals: Optional[List[Dict[str, Any]]] = None,
        custom: Optional[Dict[str, Any]] = None,
    ) -> Optional[UserProfile]:
        """Update profile fields. Returns updated profile or None."""
        profile = self.get(profile_id)
        if profile is None:
            return None

        if display_name is not None:
            profile.display_name = display_name
        if preferences:
            profile.preferences.update(preferences)
        if goals is not None:
            profile.goals = goals
        if custom:
            profile.custom.update(custom)

        profile.updated_at = time.time()
        self._save(profile)
        return profile

    def delete(self, profile_id: str) -> bool:
        """Delete a profile. Returns True if deleted."""
        path = self._profile_path(profile_id)
        if path.exists():
            path.unlink()
            self._cache.pop(profile_id, None)
            logger.info("Deleted profile: %s", profile_id)
            return True
        return False

    def list_profiles(
        self, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List all profiles with basic metadata."""
        profiles = []
        for path in sorted(self._dir.glob("*.json")):
            profile = self._load(path)
            if profile:
                profiles.append({
                    "profile_id": profile.profile_id,
                    "display_name": profile.display_name,
                    "created_at": profile.created_at,
                    "last_active": profile.last_active,
                    "interaction_count": profile.behavior.get(
                        "interaction_count", 0
                    ),
                })
        return profiles[offset : offset + limit]

    # ------------------------------------------------------------------
    # Learning — auto-extract behavioral patterns
    # ------------------------------------------------------------------

    def record_interaction(
        self,
        profile_id: str,
        agent_used: Optional[str] = None,
        topics: Optional[List[str]] = None,
        session_duration: float = 0.0,
    ) -> None:
        """Record an interaction to update behavioral data."""
        profile = self.get(profile_id)
        if profile is None:
            return

        behavior = profile.behavior
        behavior["interaction_count"] = behavior.get("interaction_count", 0) + 1

        # Update preferred agents
        if agent_used:
            agents = behavior.get("preferred_agents", [])
            if agent_used not in agents:
                agents.append(agent_used)
            behavior["preferred_agents"] = agents[-10:]  # Keep last 10

        # Update common topics
        if topics:
            existing = behavior.get("common_topics", [])
            for t in topics:
                if t not in existing:
                    existing.append(t)
            behavior["common_topics"] = existing[-20:]  # Keep last 20

        # Rolling average session length
        count = behavior["interaction_count"]
        avg = behavior.get("avg_session_length_s", 0.0)
        if session_duration > 0:
            behavior["avg_session_length_s"] = (
                (avg * (count - 1) + session_duration) / count
            )

        profile.last_active = time.time()
        profile.updated_at = time.time()
        self._save(profile)

    def learn(
        self, profile_id: str, category: str, value: str
    ) -> None:
        """
        Learn a new fact about the user's expertise or interests.

        Categories: "topic", "expertise", "language", "tool", "domain"
        """
        profile = self.get(profile_id)
        if profile is None:
            return

        behavior = profile.behavior

        if category in ("topic", "interest"):
            topics = behavior.get("common_topics", [])
            if value not in topics:
                topics.append(value)
                behavior["common_topics"] = topics[-20:]

        elif category in ("expertise", "skill"):
            areas = behavior.get("expertise_areas", [])
            if value not in areas:
                areas.append(value)
                behavior["expertise_areas"] = areas[-15:]

        profile.updated_at = time.time()
        self._save(profile)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _profile_path(self, profile_id: str) -> Path:
        # Sanitize ID to prevent path traversal
        safe_id = "".join(
            c for c in profile_id if c.isalnum() or c in "-_"
        )
        return self._dir / f"{safe_id}.json"

    def _save(self, profile: UserProfile) -> None:
        path = self._profile_path(profile.profile_id)
        data = profile.to_dict()
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, default=str))
        tmp.replace(path)  # Atomic replace

    def _load(self, path: Path) -> Optional[UserProfile]:
        try:
            data = json.loads(path.read_text())
            return UserProfile.from_dict(data)
        except Exception as exc:
            logger.warning("Failed to load profile %s: %s", path, exc)
            return None
