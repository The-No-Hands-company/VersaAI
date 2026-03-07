"""
ConversationState - Persistent conversation state management

Provides persistent storage and management of conversation state including
session information, user preferences, and conversation history.

Features:
    - Session management with unique IDs
    - User preference tracking
    - Conversation history persistence
    - C++ ContextV2 backend for fast access
    - JSON serialization for disk storage
    - Automatic state backup

Example:
    >>> from versaai.memory import ConversationState
    >>> from pathlib import Path
    >>> 
    >>> # Create state for a session
    >>> state = ConversationState(session_id="user_123")
    >>> 
    >>> # Set preferences
    >>> state.set_preference("theme", "dark")
    >>> state.set_preference("language", "en")
    >>> 
    >>> # Save to disk
    >>> state.save(Path("~/.versaai/sessions/user_123.json"))
    >>> 
    >>> # Load from disk
    >>> loaded = ConversationState.load(Path("~/.versaai/sessions/user_123.json"))
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from datetime import datetime

try:
    from versaai import versaai_core
    CPP_AVAILABLE = True
except ImportError:
    versaai_core = None
    CPP_AVAILABLE = False


@dataclass
class SessionInfo:
    """Information about a conversation session."""
    session_id: str
    created_at: float
    last_accessed: float
    access_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionInfo':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class UserPreferences:
    """User preferences for conversation."""
    theme: str = "auto"
    language: str = "en"
    verbosity: str = "normal"  # minimal, normal, detailed
    formality: str = "casual"  # formal, casual, technical
    custom: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserPreferences':
        """Create from dictionary."""
        return cls(**data)


class ConversationState:
    """
    Manages persistent conversation state.
    
    Stores session information, user preferences, and conversation history
    with support for disk persistence and fast in-memory access via C++ backend.
    
    Attributes:
        session_id: Unique session identifier
        session_info: Session metadata
        preferences: User preferences
        context: C++ ContextV2 instance for fast storage
        conversation_history: List of conversation summaries
    """
    
    def __init__(
        self,
        session_id: str,
        enable_cpp_backend: bool = True,
        auto_backup: bool = True,
        backup_interval: int = 300  # 5 minutes
    ):
        """
        Initialize ConversationState.
        
        Args:
            session_id: Unique session identifier
            enable_cpp_backend: Use C++ ContextV2 for storage
            auto_backup: Automatically backup state
            backup_interval: Backup interval in seconds
        """
        self.session_id = session_id
        self.auto_backup = auto_backup
        self.backup_interval = backup_interval
        self.last_backup_time = time.time()
        
        # Initialize C++ backend if available
        if CPP_AVAILABLE and enable_cpp_backend:
            self.context = versaai_core.ContextV2()
            self.use_cpp = True
        else:
            self.context = None
            self.use_cpp = False
            self._python_storage = {}
        
        # Initialize session info
        current_time = time.time()
        self.session_info = SessionInfo(
            session_id=session_id,
            created_at=current_time,
            last_accessed=current_time,
            access_count=1
        )
        
        # Initialize preferences
        self.preferences = UserPreferences()
        
        # Conversation history (summaries of past conversations)
        self.conversation_history: List[Dict[str, Any]] = []
        
        # Custom state data
        self.custom_data: Dict[str, Any] = {}
        
        # Store initial state
        self._persist_state()
    
    def set_preference(self, key: str, value: Any) -> None:
        """
        Set a user preference.
        
        Args:
            key: Preference key
            value: Preference value
        
        Example:
            >>> state.set_preference("theme", "dark")
            >>> state.set_preference("language", "fr")
        """
        if hasattr(self.preferences, key):
            setattr(self.preferences, key, value)
        else:
            self.preferences.custom[key] = value
        
        self._persist_state()
        self._maybe_backup()
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference."""
        if hasattr(self.preferences, key):
            return getattr(self.preferences, key)
        return self.preferences.custom.get(key, default)
    
    def set_custom_data(self, key: str, value: Any) -> None:
        """Store custom data in the state."""
        self.custom_data[key] = value
        self._persist_state()
        self._maybe_backup()
    
    def get_custom_data(self, key: str, default: Any = None) -> Any:
        """Get custom data from the state."""
        return self.custom_data.get(key, default)
    
    def add_conversation_summary(self, summary: Dict[str, Any]) -> None:
        """
        Add a conversation summary to history.
        
        Args:
            summary: Dictionary with conversation summary
        
        Example:
            >>> summary = {
            ...     'timestamp': time.time(),
            ...     'turns': 10,
            ...     'topic': 'quantum computing',
            ...     'summary': 'Discussed quantum computing basics...'
            ... }
            >>> state.add_conversation_summary(summary)
        """
        summary['timestamp'] = summary.get('timestamp', time.time())
        self.conversation_history.append(summary)
        self._persist_state()
        self._maybe_backup()
    
    def get_conversation_history(
        self,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history.
        
        Args:
            limit: Maximum number of summaries to return (most recent)
        
        Returns:
            List of conversation summaries
        """
        if limit:
            return self.conversation_history[-limit:]
        return self.conversation_history
    
    def update_access(self) -> None:
        """Update session access information."""
        self.session_info.last_accessed = time.time()
        self.session_info.access_count += 1
        self._persist_state()
    
    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history.clear()
        self._persist_state()
    
    def reset(self, keep_preferences: bool = True) -> None:
        """
        Reset state.
        
        Args:
            keep_preferences: Whether to keep user preferences
        """
        if not keep_preferences:
            self.preferences = UserPreferences()
        
        self.conversation_history.clear()
        self.custom_data.clear()
        
        self.session_info.last_accessed = time.time()
        
        self._persist_state()
    
    def save(self, filepath: Path) -> None:
        """
        Save state to disk.
        
        Args:
            filepath: Path to save file
        
        Example:
            >>> state.save(Path("~/.versaai/sessions/user_123.json"))
        """
        filepath = Path(filepath).expanduser()
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        state_dict = self.to_dict()
        
        with open(filepath, 'w') as f:
            json.dump(state_dict, f, indent=2)
        
        self.last_backup_time = time.time()
    
    @classmethod
    def load(cls, filepath: Path) -> 'ConversationState':
        """
        Load state from disk.
        
        Args:
            filepath: Path to load from
        
        Returns:
            ConversationState instance
        
        Example:
            >>> state = ConversationState.load(Path("~/.versaai/sessions/user_123.json"))
        """
        filepath = Path(filepath).expanduser()
        
        with open(filepath, 'r') as f:
            state_dict = json.load(f)
        
        return cls.from_dict(state_dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert state to dictionary.
        
        Returns:
            Dictionary representation of state
        """
        # If using C++ backend, serialize from there
        cpp_data = {}
        if self.use_cpp:
            try:
                json_str = self.context.serialize_to_json()
                if json_str:
                    cpp_data = json.loads(json_str)
            except (json.JSONDecodeError, Exception):
                # If C++ serialization fails, use empty dict
                cpp_data = {}
        
        return {
            'session_id': self.session_id,
            'session_info': self.session_info.to_dict(),
            'preferences': self.preferences.to_dict(),
            'conversation_history': self.conversation_history,
            'custom_data': self.custom_data,
            'cpp_backend_data': cpp_data,
            'use_cpp': self.use_cpp,
            'version': '1.0.0',
            'saved_at': time.time()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationState':
        """
        Create state from dictionary.
        
        Args:
            data: Dictionary representation
        
        Returns:
            ConversationState instance
        """
        session_id = data['session_id']
        state = cls(session_id=session_id, enable_cpp_backend=data.get('use_cpp', True))
        
        # Restore session info
        if 'session_info' in data:
            state.session_info = SessionInfo.from_dict(data['session_info'])
        
        # Restore preferences
        if 'preferences' in data:
            state.preferences = UserPreferences.from_dict(data['preferences'])
        
        # Restore history
        if 'conversation_history' in data:
            state.conversation_history = data['conversation_history']
        
        # Restore custom data
        if 'custom_data' in data:
            state.custom_data = data['custom_data']
        
        # Restore C++ backend data
        if 'cpp_backend_data' in data and state.use_cpp:
            cpp_json = json.dumps(data['cpp_backend_data'])
            state.context.deserialize_from_json(cpp_json)
        
        state._persist_state()
        
        return state
    
    def get_summary(self) -> str:
        """Get a human-readable summary of the state."""
        created = datetime.fromtimestamp(self.session_info.created_at)
        accessed = datetime.fromtimestamp(self.session_info.last_accessed)
        
        summary = f"Session: {self.session_id}\n"
        summary += f"Created: {created.strftime('%Y-%m-%d %H:%M:%S')}\n"
        summary += f"Last accessed: {accessed.strftime('%Y-%m-%d %H:%M:%S')}\n"
        summary += f"Access count: {self.session_info.access_count}\n"
        summary += f"Preferences: {len(self.preferences.custom) + 4} set\n"
        summary += f"Conversation history: {len(self.conversation_history)} summaries\n"
        summary += f"Custom data: {len(self.custom_data)} items\n"
        summary += f"Using C++ backend: {self.use_cpp}\n"
        
        return summary
    
    def get_stats(self) -> Dict[str, Any]:
        """Get state statistics."""
        return {
            'session_id': self.session_id,
            'created_at': self.session_info.created_at,
            'last_accessed': self.session_info.last_accessed,
            'access_count': self.session_info.access_count,
            'num_preferences': len(self.preferences.custom) + 4,
            'num_history_entries': len(self.conversation_history),
            'num_custom_data': len(self.custom_data),
            'using_cpp_backend': self.use_cpp,
            'auto_backup_enabled': self.auto_backup,
            'last_backup': self.last_backup_time
        }
    
    # Private methods
    
    def _persist_state(self) -> None:
        """Persist state to C++ backend or Python storage."""
        if self.use_cpp:
            # Store in C++ ContextV2
            self.context.set('session_info', json.dumps(self.session_info.to_dict()),
                           namespace=f"session_{self.session_id}", persistent=True)
            self.context.set('preferences', json.dumps(self.preferences.to_dict()),
                           namespace=f"session_{self.session_id}", persistent=True)
            self.context.set('history', json.dumps(self.conversation_history),
                           namespace=f"session_{self.session_id}", persistent=True)
            self.context.set('custom', json.dumps(self.custom_data),
                           namespace=f"session_{self.session_id}", persistent=True)
        else:
            # Store in Python dict
            self._python_storage = {
                'session_info': self.session_info.to_dict(),
                'preferences': self.preferences.to_dict(),
                'history': self.conversation_history,
                'custom': self.custom_data
            }
    
    def _maybe_backup(self) -> None:
        """Backup state if auto-backup is enabled and interval has passed."""
        if not self.auto_backup:
            return
        
        current_time = time.time()
        if current_time - self.last_backup_time >= self.backup_interval:
            # Auto-backup to default location
            backup_dir = Path.home() / ".versaai" / "sessions" / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            backup_file = backup_dir / f"{self.session_id}_backup.json"
            self.save(backup_file)
