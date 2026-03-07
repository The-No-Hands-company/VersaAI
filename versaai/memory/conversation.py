"""
ConversationManager - Multi-turn conversation tracking with C++ backend

Provides intelligent conversation management with entity tracking, topic detection,
and efficient context storage using VersaAI's high-performance C++ ContextV2.

Features:
    - Multi-turn conversation tracking
    - Entity extraction across turns
    - Topic drift detection
    - Conversation summarization
    - C++ ContextV2 backend for fast access
    - Automatic pruning of old turns

Example:
    >>> from versaai.memory import ConversationManager
    >>> 
    >>> manager = ConversationManager(model_id="llama-3-8b")
    >>> manager.add_turn("user", "What is quantum computing?")
    >>> manager.add_turn("assistant", "Quantum computing uses quantum mechanics...")
    >>> 
    >>> # Get optimized context for generation
    >>> context = manager.get_context_for_generation(max_tokens=4096)
    >>> 
    >>> # Extract entities
    >>> entities = manager.get_entities()
    >>> print(entities)  # ['quantum computing', 'quantum mechanics']
"""

import time
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import re

try:
    from versaai import versaai_core
    CPP_AVAILABLE = True
except ImportError:
    versaai_core = None
    CPP_AVAILABLE = False


@dataclass
class ConversationTurn:
    """Represents a single turn in the conversation."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: float
    turn_id: int
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationTurn':
        """Create from dictionary."""
        return cls(**data)


class ConversationManager:
    """
    Manages multi-turn conversations with intelligent context management.
    
    Uses C++ ContextV2 for high-performance storage and retrieval.
    Tracks entities, detects topic drift, and optimizes context windows.
    
    Attributes:
        model_id: Model identifier for tokenization
        max_turns: Maximum number of turns to keep in memory
        context: C++ ContextV2 instance for fast storage
        turns: List of conversation turns
        entities: Extracted entities across conversation
        current_topic: Current conversation topic
    """
    
    def __init__(
        self,
        model_id: str,
        max_turns: int = 100,
        enable_cpp_backend: bool = True,
        namespace: str = "conversation"
    ):
        """
        Initialize ConversationManager.
        
        Args:
            model_id: Model identifier for tokenization
            max_turns: Maximum turns to keep in memory
            enable_cpp_backend: Use C++ ContextV2 for storage
            namespace: Namespace for context storage
        """
        self.model_id = model_id
        self.max_turns = max_turns
        self.namespace = namespace
        self.turn_counter = 0
        
        # Initialize C++ backend if available
        if CPP_AVAILABLE and enable_cpp_backend:
            self.context = versaai_core.ContextV2()
            self.use_cpp = True
        else:
            self.context = None
            self.use_cpp = False
            self._python_storage = {}
        
        # In-memory turn list for fast access
        self.turns: List[ConversationTurn] = []
        
        # Entity and topic tracking
        self.entities: Dict[str, int] = defaultdict(int)  # entity -> count
        self.current_topic: Optional[str] = None
        self.topic_history: List[Tuple[str, int]] = []  # (topic, turn_id)
        
        # Statistics
        self.stats = {
            'total_turns': 0,
            'user_turns': 0,
            'assistant_turns': 0,
            'topic_shifts': 0,
            'entities_extracted': 0
        }
    
    def add_turn(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Add a conversation turn.
        
        Args:
            role: "user" or "assistant"
            content: Turn content
            metadata: Optional metadata
        
        Returns:
            Turn ID
        
        Example:
            >>> turn_id = manager.add_turn("user", "Hello!")
            >>> manager.add_turn("assistant", "Hi! How can I help?")
        """
        turn = ConversationTurn(
            role=role,
            content=content,
            timestamp=time.time(),
            turn_id=self.turn_counter,
            metadata=metadata or {}
        )
        
        self.turns.append(turn)
        self.turn_counter += 1
        
        # Store in C++ backend for persistence
        if self.use_cpp:
            self._store_turn_cpp(turn)
        else:
            self._store_turn_python(turn)
        
        # Update statistics
        self.stats['total_turns'] += 1
        if role == 'user':
            self.stats['user_turns'] += 1
        elif role == 'assistant':
            self.stats['assistant_turns'] += 1
        
        # Extract entities from user turns
        if role == 'user':
            self._extract_entities(content, turn.turn_id)
        
        # Detect topic drift
        self._detect_topic_drift(content, turn.turn_id)
        
        # Prune old turns if necessary
        if len(self.turns) > self.max_turns:
            self._prune_old_turns()
        
        return turn.turn_id
    
    def get_turns(
        self,
        limit: Optional[int] = None,
        role_filter: Optional[str] = None
    ) -> List[ConversationTurn]:
        """
        Get conversation turns.
        
        Args:
            limit: Maximum number of turns to return (most recent first)
            role_filter: Filter by role ("user" or "assistant")
        
        Returns:
            List of conversation turns
        """
        turns = self.turns
        
        if role_filter:
            turns = [t for t in turns if t.role == role_filter]
        
        if limit:
            turns = turns[-limit:]
        
        return turns
    
    def get_context_for_generation(
        self,
        max_tokens: Optional[int] = None,
        include_system: bool = True,
        system_message: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Get optimized context for model generation.
        
        Args:
            max_tokens: Maximum tokens (None = all turns)
            include_system: Include system message
            system_message: Custom system message
        
        Returns:
            List of message dicts in OpenAI format
        
        Example:
            >>> context = manager.get_context_for_generation(max_tokens=2048)
            >>> # Use with model: model.generate(context)
        """
        messages = []
        
        # Add system message
        if include_system:
            sys_msg = system_message or self._get_default_system_message()
            messages.append({"role": "system", "content": sys_msg})
        
        # Add conversation turns
        for turn in self.turns:
            messages.append({
                "role": turn.role,
                "content": turn.content
            })
        
        # TODO: Token counting and truncation will be done by ContextWindowManager
        # For now, return all messages
        return messages
    
    def get_entities(self, min_count: int = 1) -> Dict[str, int]:
        """
        Get extracted entities.
        
        Args:
            min_count: Minimum occurrence count
        
        Returns:
            Dictionary of entity -> count
        """
        return {
            entity: count 
            for entity, count in self.entities.items() 
            if count >= min_count
        }
    
    def get_current_topic(self) -> Optional[str]:
        """Get the current conversation topic."""
        return self.current_topic
    
    def get_topic_history(self) -> List[Tuple[str, int]]:
        """Get topic history with turn IDs."""
        return self.topic_history
    
    def clear(self) -> None:
        """Clear all conversation history."""
        self.turns.clear()
        self.entities.clear()
        self.current_topic = None
        self.topic_history.clear()
        self.turn_counter = 0
        
        if self.use_cpp:
            self.context.clear()
        else:
            self._python_storage.clear()
        
        # Reset statistics
        for key in self.stats:
            self.stats[key] = 0
    
    def get_summary(self) -> str:
        """
        Get a summary of the conversation.
        
        Returns:
            Summary string
        """
        if not self.turns:
            return "No conversation yet."
        
        num_turns = len(self.turns)
        num_entities = len(self.entities)
        topics = len(self.topic_history)
        
        summary = f"Conversation Summary:\n"
        summary += f"- Turns: {num_turns} ({self.stats['user_turns']} user, {self.stats['assistant_turns']} assistant)\n"
        summary += f"- Entities: {num_entities}\n"
        summary += f"- Topic shifts: {topics}\n"
        
        if self.current_topic:
            summary += f"- Current topic: {self.current_topic}\n"
        
        if self.entities:
            top_entities = sorted(self.entities.items(), key=lambda x: x[1], reverse=True)[:5]
            summary += f"- Top entities: {', '.join([e for e, _ in top_entities])}\n"
        
        return summary
    
    def get_stats(self) -> Dict[str, Any]:
        """Get conversation statistics."""
        return {
            **self.stats,
            'turns_in_memory': len(self.turns),
            'entities_tracked': len(self.entities),
            'topics_tracked': len(self.topic_history),
            'using_cpp_backend': self.use_cpp
        }
    
    # Private methods
    
    def _store_turn_cpp(self, turn: ConversationTurn) -> None:
        """Store turn in C++ ContextV2."""
        key = f"turn_{turn.turn_id}"
        value = json.dumps(turn.to_dict())
        self.context.set(key, value, namespace=self.namespace, persistent=False)
    
    def _store_turn_python(self, turn: ConversationTurn) -> None:
        """Store turn in Python dict (fallback)."""
        key = f"turn_{turn.turn_id}"
        self._python_storage[key] = turn.to_dict()
    
    def _extract_entities(self, content: str, turn_id: int) -> None:
        """
        Extract entities from content.
        
        Simple extraction using capitalized words and common patterns.
        TODO: Integrate with NER model for better extraction.
        """
        # Extract capitalized words (simple NER)
        words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', content)
        
        # Extract quoted terms
        quoted = re.findall(r'"([^"]+)"', content)
        
        # Extract technical terms (words with specific patterns)
        technical = re.findall(r'\b(?:quantum|neural|machine|deep|AI|ML)\s+\w+', content, re.IGNORECASE)
        
        all_entities = words + quoted + [t.lower() for t in technical]
        
        for entity in all_entities:
            entity = entity.strip()
            if len(entity) > 2:  # Ignore short words
                self.entities[entity] += 1
                self.stats['entities_extracted'] += 1
    
    def _detect_topic_drift(self, content: str, turn_id: int) -> None:
        """
        Detect topic changes in conversation.
        
        Simple heuristic-based detection. 
        TODO: Integrate with embedding-based topic modeling.
        """
        # Keywords that indicate topic shift
        shift_indicators = [
            'speaking of', 'by the way', 'actually', 'anyway',
            'let me ask about', 'what about', 'moving on',
            'another question', 'different topic'
        ]
        
        content_lower = content.lower()
        
        # Check for explicit topic shift
        if any(indicator in content_lower for indicator in shift_indicators):
            # Simple topic extraction: first noun phrase after indicator
            new_topic = self._extract_topic_from_content(content)
            if new_topic and new_topic != self.current_topic:
                self.current_topic = new_topic
                self.topic_history.append((new_topic, turn_id))
                self.stats['topic_shifts'] += 1
        
        # If no current topic, set from first turn
        elif self.current_topic is None and len(self.turns) < 3:
            new_topic = self._extract_topic_from_content(content)
            if new_topic:
                self.current_topic = new_topic
                self.topic_history.append((new_topic, turn_id))
    
    def _extract_topic_from_content(self, content: str) -> Optional[str]:
        """Extract topic from content (simple heuristic)."""
        # Look for question patterns
        question_patterns = [
            r'what (?:is|are) ([\w\s]+)\?',
            r'tell me about ([\w\s]+)',
            r'explain ([\w\s]+)',
            r'how (?:does|do) ([\w\s]+)'
        ]
        
        for pattern in question_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                topic = match.group(1).strip()
                return topic[:50]  # Limit length
        
        # Fallback: use most common entity
        if self.entities:
            return max(self.entities.items(), key=lambda x: x[1])[0]
        
        return None
    
    def _prune_old_turns(self) -> None:
        """Remove oldest turns when exceeding max_turns."""
        if len(self.turns) > self.max_turns:
            num_to_remove = len(self.turns) - self.max_turns
            removed_turns = self.turns[:num_to_remove]
            self.turns = self.turns[num_to_remove:]
            
            # Remove from storage
            for turn in removed_turns:
                key = f"turn_{turn.turn_id}"
                if self.use_cpp:
                    self.context.remove(key, namespace=self.namespace)
                else:
                    self._python_storage.pop(key, None)
    
    def _get_default_system_message(self) -> str:
        """Get default system message."""
        return (
            f"You are a helpful AI assistant. "
            f"You are having a conversation with a user. "
            f"Current topic: {self.current_topic or 'general'}. "
            f"Be helpful, accurate, and concise."
        )
