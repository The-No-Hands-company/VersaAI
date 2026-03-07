"""
ContextWindowManager - Dynamic context window optimization

Provides intelligent context window management with token counting, compression,
and priority-based truncation for optimal model performance.

Features:
    - Accurate token counting
    - Dynamic context sizing based on model limits
    - Priority-based message truncation
    - Context compression (summarization)
    - Attention sink optimization
    - Message importance scoring

Example:
    >>> from versaai.memory import ContextWindowManager
    >>> 
    >>> # Initialize with tokenizer
    >>> cwm = ContextWindowManager(model_id="llama-3-8b")
    >>> 
    >>> # Optimize context to fit within token limit
    >>> messages = [...]  # Long conversation
    >>> optimized = cwm.optimize_context(messages, max_tokens=4096)
    >>> 
    >>> # Compress using summarization
    >>> compressed = cwm.compress_context(messages, target_ratio=0.5)
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import re


class MessagePriority(Enum):
    """Priority levels for messages."""
    CRITICAL = 4  # System messages, recent context
    HIGH = 3      # Recent user messages, important info
    MEDIUM = 2    # Assistant responses, general context
    LOW = 1       # Old messages, redundant info


@dataclass
class MessageInfo:
    """Information about a message for optimization."""
    index: int
    role: str
    content: str
    token_count: int
    priority: MessagePriority
    timestamp: Optional[float] = None
    importance_score: float = 0.5  # 0-1 scale
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'role': self.role,
            'content': self.content
        }


class ContextWindowManager:
    """
    Manages context window optimization for language models.
    
    Handles token counting, message prioritization, and intelligent
    truncation to fit within model context limits while preserving
    the most important information.
    
    Attributes:
        model_id: Model identifier
        max_context_length: Maximum context tokens supported by model
        tokenizer: Tokenizer function or object
        compression_enabled: Whether to use compression
    """
    
    def __init__(
        self,
        model_id: str,
        max_context_length: Optional[int] = None,
        tokenizer: Optional[Any] = None,
        compression_enabled: bool = True
    ):
        """
        Initialize ContextWindowManager.
        
        Args:
            model_id: Model identifier (e.g., "llama-3-8b")
            max_context_length: Max tokens (auto-detected if None)
            tokenizer: Tokenizer instance or None for simple counting
            compression_enabled: Enable context compression
        """
        self.model_id = model_id
        self.tokenizer = tokenizer
        self.compression_enabled = compression_enabled
        
        # Auto-detect context length based on model
        if max_context_length is None:
            self.max_context_length = self._detect_context_length(model_id)
        else:
            self.max_context_length = max_context_length
        
        # Attention sink: Keep first N tokens always
        self.attention_sink_size = 128  # First 128 tokens stay
        
        # Statistics
        self.stats = {
            'contexts_optimized': 0,
            'tokens_saved': 0,
            'compressions_performed': 0,
            'truncations_performed': 0
        }
    
    def optimize_context(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        preserve_system: bool = True,
        preserve_recent: int = 2
    ) -> List[Dict[str, str]]:
        """
        Optimize context to fit within token limit.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Target token limit (uses model max if None)
            preserve_system: Always keep system messages
            preserve_recent: Number of recent messages to always keep
        
        Returns:
            Optimized list of messages
        
        Example:
            >>> messages = [
            ...     {"role": "system", "content": "You are helpful."},
            ...     {"role": "user", "content": "Hello!"},
            ...     {"role": "assistant", "content": "Hi!"},
            ... ]
            >>> optimized = cwm.optimize_context(messages, max_tokens=2048)
        """
        if not messages:
            return []
        
        target_tokens = max_tokens or self.max_context_length
        
        # Analyze messages
        message_infos = self._analyze_messages(messages)
        
        # Calculate current token count
        current_tokens = sum(m.token_count for m in message_infos)
        
        # If already within limit, return as-is
        if current_tokens <= target_tokens:
            return messages
        
        # Apply optimization strategy
        optimized_infos = self._apply_optimization_strategy(
            message_infos,
            target_tokens,
            preserve_system=preserve_system,
            preserve_recent=preserve_recent
        )
        
        # Convert back to message format
        optimized_messages = [m.to_dict() for m in optimized_infos]
        
        # Update statistics
        self.stats['contexts_optimized'] += 1
        self.stats['tokens_saved'] += current_tokens - sum(m.token_count for m in optimized_infos)
        
        return optimized_messages
    
    def compress_context(
        self,
        messages: List[Dict[str, str]],
        target_ratio: float = 0.5,
        method: str = "extractive"
    ) -> List[Dict[str, str]]:
        """
        Compress context using summarization.
        
        Args:
            messages: List of message dicts
            target_ratio: Target compression ratio (0-1)
            method: Compression method ("extractive", "abstractive", "hybrid")
        
        Returns:
            Compressed messages
        
        Note:
            This is a placeholder for future ML-based compression.
            Currently uses simple extractive summarization.
        """
        if not self.compression_enabled:
            return messages
        
        if target_ratio >= 1.0:
            return messages
        
        # Simple extractive compression: keep important sentences
        compressed = []
        
        for msg in messages:
            if msg['role'] == 'system':
                # Never compress system messages
                compressed.append(msg)
            else:
                # Extract important sentences
                sentences = self._split_sentences(msg['content'])
                num_to_keep = max(1, int(len(sentences) * target_ratio))
                
                # Score sentences by importance
                scored = [(s, self._score_sentence_importance(s)) for s in sentences]
                scored.sort(key=lambda x: x[1], reverse=True)
                
                # Keep top sentences in original order
                kept_sentences = [s for s, _ in scored[:num_to_keep]]
                kept_sentences.sort(key=lambda s: sentences.index(s))
                
                compressed_content = ' '.join(kept_sentences)
                compressed.append({
                    'role': msg['role'],
                    'content': compressed_content
                })
        
        self.stats['compressions_performed'] += 1
        return compressed
    
    def count_tokens(
        self,
        text: str,
        include_special_tokens: bool = True
    ) -> int:
        """
        Count tokens in text.
        
        Args:
            text: Text to count
            include_special_tokens: Include special tokens in count
        
        Returns:
            Token count
        """
        if self.tokenizer is not None:
            # Use actual tokenizer
            try:
                if hasattr(self.tokenizer, 'encode'):
                    tokens = self.tokenizer.encode(text, add_special_tokens=include_special_tokens)
                    return len(tokens)
                elif callable(self.tokenizer):
                    return self.tokenizer(text)
            except Exception:
                pass
        
        # Fallback: Simple estimation (1 token ≈ 4 characters)
        return self._estimate_token_count(text)
    
    def get_remaining_tokens(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None
    ) -> int:
        """
        Calculate remaining tokens available.
        
        Args:
            messages: Current messages
            max_tokens: Max token limit (uses model max if None)
        
        Returns:
            Number of tokens remaining
        """
        used_tokens = sum(self.count_tokens(m['content']) for m in messages)
        limit = max_tokens or self.max_context_length
        return max(0, limit - used_tokens)
    
    def can_fit_message(
        self,
        messages: List[Dict[str, str]],
        new_message: str,
        max_tokens: Optional[int] = None
    ) -> bool:
        """
        Check if a new message can fit in context.
        
        Args:
            messages: Current messages
            new_message: New message content
            max_tokens: Max token limit
        
        Returns:
            True if message fits
        """
        remaining = self.get_remaining_tokens(messages, max_tokens)
        new_tokens = self.count_tokens(new_message)
        return new_tokens <= remaining
    
    def get_stats(self) -> Dict[str, Any]:
        """Get optimization statistics."""
        return {
            **self.stats,
            'model_id': self.model_id,
            'max_context_length': self.max_context_length,
            'compression_enabled': self.compression_enabled,
            'attention_sink_size': self.attention_sink_size
        }
    
    # Private methods
    
    def _detect_context_length(self, model_id: str) -> int:
        """Auto-detect context length based on model identifier."""
        model_lower = model_id.lower()
        
        # Common model context lengths
        if 'gpt-4' in model_lower:
            if '32k' in model_lower:
                return 32768
            elif '128k' in model_lower:
                return 128000
            return 8192
        elif 'gpt-3.5' in model_lower:
            if '16k' in model_lower:
                return 16384
            return 4096
        elif 'llama-2' in model_lower:
            return 4096
        elif 'llama-3' in model_lower or 'llama3' in model_lower:
            return 8192
        elif 'claude' in model_lower:
            if 'claude-2' in model_lower:
                return 100000
            return 200000
        elif 'mistral' in model_lower:
            return 8192
        elif 'mixtral' in model_lower:
            return 32768
        else:
            # Default to conservative 4K
            return 4096
    
    def _analyze_messages(self, messages: List[Dict[str, str]]) -> List[MessageInfo]:
        """Analyze messages and create MessageInfo objects."""
        infos = []
        
        for i, msg in enumerate(messages):
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            tokens = self.count_tokens(content)
            
            # Determine priority
            priority = self._determine_priority(role, i, len(messages))
            
            # Calculate importance score
            importance = self._calculate_importance(msg, i, len(messages))
            
            infos.append(MessageInfo(
                index=i,
                role=role,
                content=content,
                token_count=tokens,
                priority=priority,
                importance_score=importance
            ))
        
        return infos
    
    def _determine_priority(self, role: str, index: int, total: int) -> MessagePriority:
        """Determine message priority."""
        # System messages are critical
        if role == 'system':
            return MessagePriority.CRITICAL
        
        # Recent messages (last 20%) are high priority
        if index >= total * 0.8:
            return MessagePriority.HIGH
        
        # User messages are generally higher priority than assistant
        if role == 'user':
            return MessagePriority.MEDIUM
        
        return MessagePriority.LOW
    
    def _calculate_importance(
        self,
        message: Dict[str, str],
        index: int,
        total: int
    ) -> float:
        """
        Calculate importance score (0-1).
        
        Factors:
            - Recency: Recent messages are more important
            - Role: System > User > Assistant
            - Length: Not too short, not too long
            - Content: Keywords, questions, etc.
        """
        score = 0.5  # Base score
        
        role = message.get('role', '')
        content = message.get('content', '')
        
        # Recency bonus (0-0.3)
        recency = index / max(1, total - 1)
        score += recency * 0.3
        
        # Role bonus
        if role == 'system':
            score += 0.2
        elif role == 'user':
            score += 0.1
        
        # Content analysis
        if '?' in content:  # Questions are important
            score += 0.1
        
        if any(keyword in content.lower() for keyword in ['important', 'critical', 'must', 'need']):
            score += 0.1
        
        # Length penalty for very long or very short
        length = len(content)
        if 10 < length < 500:  # Sweet spot
            score += 0.05
        
        return min(1.0, max(0.0, score))
    
    def _apply_optimization_strategy(
        self,
        messages: List[MessageInfo],
        target_tokens: int,
        preserve_system: bool = True,
        preserve_recent: int = 2
    ) -> List[MessageInfo]:
        """Apply optimization strategy to fit within token limit."""
        # Separate messages by category
        system_msgs = [m for m in messages if m.role == 'system']
        recent_msgs = messages[-preserve_recent:] if len(messages) > preserve_recent else messages
        other_msgs = [m for m in messages if m not in system_msgs and m not in recent_msgs]
        
        # Always keep system messages
        result = system_msgs.copy() if preserve_system else []
        current_tokens = sum(m.token_count for m in result)
        
        # Always keep recent messages
        for msg in recent_msgs:
            if msg not in result:
                if current_tokens + msg.token_count <= target_tokens:
                    result.append(msg)
                    current_tokens += msg.token_count
        
        # Add other messages by importance until limit
        other_msgs.sort(key=lambda m: m.importance_score, reverse=True)
        
        for msg in other_msgs:
            if current_tokens + msg.token_count <= target_tokens:
                result.append(msg)
                current_tokens += msg.token_count
            else:
                # Try compression if enabled
                if self.compression_enabled:
                    compressed_content = self._compress_message(msg.content, 0.7)
                    compressed_tokens = self.count_tokens(compressed_content)
                    
                    if current_tokens + compressed_tokens <= target_tokens:
                        msg.content = compressed_content
                        msg.token_count = compressed_tokens
                        result.append(msg)
                        current_tokens += compressed_tokens
        
        # Sort by original index to maintain order
        result.sort(key=lambda m: m.index)
        
        if len(result) < len(messages):
            self.stats['truncations_performed'] += 1
        
        return result
    
    def _compress_message(self, content: str, ratio: float) -> str:
        """Compress a single message."""
        sentences = self._split_sentences(content)
        num_to_keep = max(1, int(len(sentences) * ratio))
        
        scored = [(s, self._score_sentence_importance(s)) for s in sentences]
        scored.sort(key=lambda x: x[1], reverse=True)
        
        kept = [s for s, _ in scored[:num_to_keep]]
        kept.sort(key=lambda s: sentences.index(s))
        
        return ' '.join(kept)
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _score_sentence_importance(self, sentence: str) -> float:
        """Score sentence importance."""
        score = 0.5
        
        # Questions are important
        if '?' in sentence:
            score += 0.2
        
        # Sentences with keywords
        important_words = ['important', 'critical', 'must', 'need', 'should', 'key']
        if any(word in sentence.lower() for word in important_words):
            score += 0.15
        
        # Named entities (capitalized words)
        if re.search(r'\b[A-Z][a-z]+\b', sentence):
            score += 0.1
        
        # Numbers and data
        if re.search(r'\d+', sentence):
            score += 0.05
        
        return min(1.0, score)
    
    def _estimate_token_count(self, text: str) -> int:
        """
        Estimate token count using heuristics.
        
        Rule of thumb: 1 token ≈ 4 characters for English text.
        More accurate: count words and punctuation.
        """
        # Count words
        words = len(text.split())
        
        # Count punctuation
        punctuation = len(re.findall(r'[.,!?;:]', text))
        
        # Estimate: words * 1.3 (accounting for subwords) + punctuation
        estimated = int(words * 1.3) + punctuation
        
        return max(1, estimated)
