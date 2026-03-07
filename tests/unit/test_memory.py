"""
Unit tests for VersaAI Memory Systems

Tests ConversationManager, ContextWindowManager, and ConversationState
with comprehensive coverage of all features.
"""

import pytest
import time
import tempfile
from pathlib import Path

from versaai.memory import (
    ConversationManager,
    ConversationTurn,
    ContextWindowManager,
    MessagePriority,
    ConversationState,
    SessionInfo,
    UserPreferences
)


class TestConversationManager:
    """Tests for ConversationManager."""
    
    def test_initialization(self):
        """Test basic initialization."""
        manager = ConversationManager("llama-3-8b")
        assert manager.model_id == "llama-3-8b"
        assert len(manager.get_turns()) == 0
        assert manager.turn_counter == 0
    
    def test_add_turn(self):
        """Test adding conversation turns."""
        manager = ConversationManager("llama-3-8b")
        
        turn_id1 = manager.add_turn("user", "Hello!")
        turn_id2 = manager.add_turn("assistant", "Hi! How can I help?")
        
        assert turn_id1 == 0
        assert turn_id2 == 1
        assert len(manager.get_turns()) == 2
        
        turns = manager.get_turns()
        assert turns[0].role == "user"
        assert turns[0].content == "Hello!"
        assert turns[1].role == "assistant"
    
    def test_get_turns_with_limit(self):
        """Test getting limited number of turns."""
        manager = ConversationManager("llama-3-8b")
        
        for i in range(10):
            manager.add_turn("user" if i % 2 == 0 else "assistant", f"Message {i}")
        
        recent = manager.get_turns(limit=3)
        assert len(recent) == 3
        assert recent[-1].content == "Message 9"
    
    def test_get_turns_with_role_filter(self):
        """Test filtering turns by role."""
        manager = ConversationManager("llama-3-8b")
        
        manager.add_turn("user", "Question 1")
        manager.add_turn("assistant", "Answer 1")
        manager.add_turn("user", "Question 2")
        manager.add_turn("assistant", "Answer 2")
        
        user_turns = manager.get_turns(role_filter="user")
        assert len(user_turns) == 2
        assert all(t.role == "user" for t in user_turns)
    
    def test_entity_extraction(self):
        """Test entity extraction from conversation."""
        manager = ConversationManager("llama-3-8b")
        
        manager.add_turn("user", "Tell me about Python and Machine Learning")
        manager.add_turn("user", "What is Python used for?")
        
        entities = manager.get_entities()
        assert 'Python' in entities or 'python' in entities.values()
    
    def test_topic_detection(self):
        """Test topic drift detection."""
        manager = ConversationManager("llama-3-8b")
        
        manager.add_turn("user", "What is quantum computing?")
        assert manager.get_current_topic() is not None
    
    def test_context_for_generation(self):
        """Test getting context for model generation."""
        manager = ConversationManager("llama-3-8b")
        
        manager.add_turn("user", "Hello")
        manager.add_turn("assistant", "Hi!")
        
        context = manager.get_context_for_generation()
        assert isinstance(context, list)
        assert len(context) >= 2  # At least messages
        assert context[-2]['role'] == 'user'
        assert context[-1]['role'] == 'assistant'
    
    def test_statistics(self):
        """Test conversation statistics."""
        manager = ConversationManager("llama-3-8b")
        
        manager.add_turn("user", "Question")
        manager.add_turn("assistant", "Answer")
        
        stats = manager.get_stats()
        assert stats['total_turns'] == 2
        assert stats['user_turns'] == 1
        assert stats['assistant_turns'] == 1
        assert stats['turns_in_memory'] == 2
    
    def test_summary(self):
        """Test conversation summary."""
        manager = ConversationManager("llama-3-8b")
        
        manager.add_turn("user", "Hello")
        manager.add_turn("assistant", "Hi!")
        
        summary = manager.get_summary()
        assert "Turns: 2" in summary
        assert "1 user" in summary
        assert "1 assistant" in summary
    
    def test_clear(self):
        """Test clearing conversation."""
        manager = ConversationManager("llama-3-8b")
        
        manager.add_turn("user", "Hello")
        assert len(manager.get_turns()) == 1
        
        manager.clear()
        assert len(manager.get_turns()) == 0
        assert manager.turn_counter == 0


class TestContextWindowManager:
    """Tests for ContextWindowManager."""
    
    def test_initialization(self):
        """Test basic initialization."""
        cwm = ContextWindowManager("llama-3-8b")
        assert cwm.model_id == "llama-3-8b"
        assert cwm.max_context_length > 0
    
    def test_context_length_detection(self):
        """Test automatic context length detection."""
        # GPT-4
        cwm_gpt4 = ContextWindowManager("gpt-4")
        assert cwm_gpt4.max_context_length == 8192
        
        # GPT-4-32k
        cwm_gpt4_32k = ContextWindowManager("gpt-4-32k")
        assert cwm_gpt4_32k.max_context_length == 32768
        
        # Llama-3
        cwm_llama3 = ContextWindowManager("llama-3-8b")
        assert cwm_llama3.max_context_length == 8192
        
        # Unknown model (defaults to 4K)
        cwm_unknown = ContextWindowManager("unknown-model")
        assert cwm_unknown.max_context_length == 4096
    
    def test_token_counting(self):
        """Test token counting."""
        cwm = ContextWindowManager("llama-3-8b")
        
        text = "This is a test message with some words."
        tokens = cwm.count_tokens(text)
        
        # Should be roughly 1 token per 4 characters
        assert tokens > 0
        assert tokens < len(text)  # Tokens should be less than characters
    
    def test_optimize_context_no_truncation(self):
        """Test optimization when no truncation needed."""
        cwm = ContextWindowManager("llama-3-8b")
        
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi!"}
        ]
        
        optimized = cwm.optimize_context(messages, max_tokens=10000)
        assert len(optimized) == len(messages)
    
    def test_optimize_context_with_truncation(self):
        """Test optimization with truncation."""
        cwm = ContextWindowManager("llama-3-8b")
        
        # Create many messages
        messages = []
        for i in range(20):
            messages.append({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Message {i} " * 50  # Long messages
            })
        
        optimized = cwm.optimize_context(messages, max_tokens=500)
        assert len(optimized) < len(messages)
    
    def test_preserve_system_messages(self):
        """Test that system messages are preserved."""
        cwm = ContextWindowManager("llama-3-8b")
        
        messages = [
            {"role": "system", "content": "You are helpful."},
        ] + [
            {"role": "user", "content": f"Message {i} " * 100}
            for i in range(10)
        ]
        
        optimized = cwm.optimize_context(messages, max_tokens=200, preserve_system=True)
        assert any(m['role'] == 'system' for m in optimized)
    
    def test_preserve_recent_messages(self):
        """Test that recent messages are preserved."""
        cwm = ContextWindowManager("llama-3-8b")
        
        messages = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(10)
        ]
        
        optimized = cwm.optimize_context(messages, max_tokens=100, preserve_recent=2)
        
        # Last 2 messages should be preserved
        assert optimized[-1]['content'] == "Message 9"
        assert optimized[-2]['content'] == "Message 8"
    
    def test_compress_context(self):
        """Test context compression."""
        cwm = ContextWindowManager("llama-3-8b")
        
        messages = [
            {"role": "user", "content": "This is sentence one. This is sentence two. This is sentence three."}
        ]
        
        compressed = cwm.compress_context(messages, target_ratio=0.5)
        assert len(compressed) == len(messages)
        # Compressed content should be shorter
        assert len(compressed[0]['content']) <= len(messages[0]['content'])
    
    def test_remaining_tokens(self):
        """Test calculating remaining tokens."""
        cwm = ContextWindowManager("llama-3-8b", max_context_length=1000)
        
        messages = [
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi!"}
        ]
        
        remaining = cwm.get_remaining_tokens(messages, max_tokens=1000)
        assert remaining > 0
        assert remaining < 1000
    
    def test_can_fit_message(self):
        """Test checking if message can fit."""
        cwm = ContextWindowManager("llama-3-8b", max_context_length=1000)
        
        messages = []
        can_fit = cwm.can_fit_message(messages, "Short message", max_tokens=1000)
        assert can_fit == True
        
        # Very long message
        long_message = "word " * 10000
        can_fit = cwm.can_fit_message(messages, long_message, max_tokens=100)
        assert can_fit == False
    
    def test_statistics(self):
        """Test optimization statistics."""
        cwm = ContextWindowManager("llama-3-8b")
        
        messages = [{"role": "user", "content": "Hi " * 100}] * 10
        cwm.optimize_context(messages, max_tokens=200)
        
        stats = cwm.get_stats()
        assert stats['contexts_optimized'] == 1
        assert stats['model_id'] == "llama-3-8b"


class TestConversationState:
    """Tests for ConversationState."""
    
    def test_initialization(self):
        """Test basic initialization."""
        state = ConversationState(session_id="test_123")
        assert state.session_id == "test_123"
        assert state.session_info.access_count == 1
    
    def test_set_get_preference(self):
        """Test setting and getting preferences."""
        state = ConversationState(session_id="test_123")
        
        state.set_preference("theme", "dark")
        assert state.get_preference("theme") == "dark"
        
        # Custom preference
        state.set_preference("custom_pref", "value")
        assert state.get_preference("custom_pref") == "value"
    
    def test_custom_data(self):
        """Test custom data storage."""
        state = ConversationState(session_id="test_123")
        
        state.set_custom_data("key1", "value1")
        state.set_custom_data("key2", {"nested": "data"})
        
        assert state.get_custom_data("key1") == "value1"
        assert state.get_custom_data("key2")["nested"] == "data"
    
    def test_conversation_history(self):
        """Test conversation history management."""
        state = ConversationState(session_id="test_123")
        
        summary1 = {
            'topic': 'Python',
            'turns': 10,
            'summary': 'Discussed Python basics'
        }
        state.add_conversation_summary(summary1)
        
        summary2 = {
            'topic': 'AI',
            'turns': 15,
            'summary': 'Discussed AI concepts'
        }
        state.add_conversation_summary(summary2)
        
        history = state.get_conversation_history()
        assert len(history) == 2
        assert history[0]['topic'] == 'Python'
        assert history[1]['topic'] == 'AI'
    
    def test_history_limit(self):
        """Test getting limited history."""
        state = ConversationState(session_id="test_123")
        
        for i in range(10):
            state.add_conversation_summary({'topic': f'topic_{i}'})
        
        recent = state.get_conversation_history(limit=3)
        assert len(recent) == 3
        assert recent[-1]['topic'] == 'topic_9'
    
    def test_update_access(self):
        """Test access tracking."""
        state = ConversationState(session_id="test_123")
        
        initial_count = state.session_info.access_count
        initial_time = state.session_info.last_accessed
        
        time.sleep(0.01)  # Small delay
        state.update_access()
        
        assert state.session_info.access_count == initial_count + 1
        assert state.session_info.last_accessed > initial_time
    
    def test_reset(self):
        """Test state reset."""
        state = ConversationState(session_id="test_123")
        
        state.set_preference("theme", "dark")
        state.set_custom_data("key", "value")
        state.add_conversation_summary({'topic': 'test'})
        
        state.reset(keep_preferences=True)
        
        assert state.get_preference("theme") == "dark"  # Kept
        assert state.get_custom_data("key") is None  # Cleared
        assert len(state.get_conversation_history()) == 0  # Cleared
    
    def test_save_and_load(self):
        """Test saving and loading state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test_state.json"
            
            # Create and save state
            state1 = ConversationState(session_id="test_123")
            state1.set_preference("theme", "dark")
            state1.set_custom_data("key", "value")
            state1.add_conversation_summary({'topic': 'test'})
            state1.save(filepath)
            
            # Load state
            state2 = ConversationState.load(filepath)
            
            assert state2.session_id == "test_123"
            assert state2.get_preference("theme") == "dark"
            assert state2.get_custom_data("key") == "value"
            assert len(state2.get_conversation_history()) == 1
    
    def test_to_dict(self):
        """Test converting state to dictionary."""
        state = ConversationState(session_id="test_123")
        state.set_preference("theme", "dark")
        
        state_dict = state.to_dict()
        
        assert state_dict['session_id'] == "test_123"
        assert 'session_info' in state_dict
        assert 'preferences' in state_dict
        assert state_dict['version'] == '1.0.0'
    
    def test_from_dict(self):
        """Test creating state from dictionary."""
        original = ConversationState(session_id="test_123")
        original.set_preference("theme", "dark")
        original.set_custom_data("key", "value")
        
        state_dict = original.to_dict()
        restored = ConversationState.from_dict(state_dict)
        
        assert restored.session_id == "test_123"
        assert restored.get_preference("theme") == "dark"
        assert restored.get_custom_data("key") == "value"
    
    def test_summary(self):
        """Test getting state summary."""
        state = ConversationState(session_id="test_123")
        state.set_preference("theme", "dark")
        state.add_conversation_summary({'topic': 'test'})
        
        summary = state.get_summary()
        
        assert "test_123" in summary
        assert "Preferences:" in summary
        assert "Conversation history:" in summary
    
    def test_statistics(self):
        """Test state statistics."""
        state = ConversationState(session_id="test_123")
        state.set_preference("theme", "dark")
        
        stats = state.get_stats()
        
        assert stats['session_id'] == "test_123"
        assert stats['access_count'] >= 1
        assert 'using_cpp_backend' in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
