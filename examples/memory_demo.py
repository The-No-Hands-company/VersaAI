"""
VersaAI Memory Systems Demo

Demonstrates the complete memory system with all three components:
- ConversationManager
- ContextWindowManager
- ConversationState
"""

from pathlib import Path
from versaai.memory import (
    ConversationManager,
    ContextWindowManager,
    ConversationState
)

print("=" * 70)
print("VersaAI MEMORY SYSTEMS DEMO")
print("=" * 70)

# ============================================================================
# Demo 1: ConversationManager - Multi-turn conversation tracking
# ============================================================================

print("\n📝 DEMO 1: ConversationManager")
print("-" * 70)

manager = ConversationManager("llama-3-8b", max_turns=50)

# Simulate a conversation about Python
manager.add_turn("user", "What is Python programming language?")
manager.add_turn("assistant", "Python is a high-level, interpreted programming language known for its simplicity and readability.")

manager.add_turn("user", "Tell me about Python's use in Machine Learning")
manager.add_turn("assistant", "Python is extensively used in Machine Learning due to libraries like TensorFlow, PyTorch, and scikit-learn.")

manager.add_turn("user", "What about quantum computing?")
manager.add_turn("assistant", "Quantum computing is an emerging field that uses quantum mechanics principles for computation.")

print(f"\n✅ Added {len(manager.get_turns())} conversation turns")

# Get conversation summary
print("\n📊 Conversation Summary:")
print(manager.get_summary())

# Get entities
entities = manager.get_entities(min_count=1)
print(f"\n🔍 Extracted Entities: {list(entities.keys())[:5]}")

# Get topic
topic = manager.get_current_topic()
print(f"\n💡 Current Topic: {topic}")

# Get context for generation
context = manager.get_context_for_generation(max_tokens=4096)
print(f"\n🎯 Context for Generation: {len(context)} messages")

# Statistics
stats = manager.get_stats()
print(f"\n📈 Statistics:")
for key, value in stats.items():
    print(f"   {key}: {value}")

# ============================================================================
# Demo 2: ContextWindowManager - Dynamic context optimization
# ============================================================================

print("\n\n🔧 DEMO 2: ContextWindowManager")
print("-" * 70)

cwm = ContextWindowManager(model_id="llama-3-8b")

# Create long conversation
long_messages = []
for i in range(20):
    role = "user" if i % 2 == 0 else "assistant"
    content = f"This is message number {i}. " * 20  # Long messages
    long_messages.append({"role": role, "content": content})

print(f"\n📝 Original messages: {len(long_messages)}")
total_tokens = sum(cwm.count_tokens(m['content']) for m in long_messages)
print(f"📊 Total tokens: {total_tokens}")

# Optimize to fit within 2048 tokens
optimized = cwm.optimize_context(long_messages, max_tokens=2048)
optimized_tokens = sum(cwm.count_tokens(m['content']) for m in optimized)

print(f"\n✅ Optimized messages: {len(optimized)}")
print(f"📊 Optimized tokens: {optimized_tokens}")
print(f"💾 Tokens saved: {total_tokens - optimized_tokens}")

# Test compression
print("\n🗜️  Testing context compression...")
test_msg = [{
    "role": "user",
    "content": "This is the first sentence. This is the second sentence. This is the third sentence. This is the fourth sentence."
}]

compressed = cwm.compress_context(test_msg, target_ratio=0.5)
print(f"Original length: {len(test_msg[0]['content'])} chars")
print(f"Compressed length: {len(compressed[0]['content'])} chars")

# Get stats
cwm_stats = cwm.get_stats()
print(f"\n📈 Context Window Manager Stats:")
for key, value in cwm_stats.items():
    print(f"   {key}: {value}")

# ============================================================================
# Demo 3: ConversationState - Persistent state management
# ============================================================================

print("\n\n💾 DEMO 3: ConversationState")
print("-" * 70)

state = ConversationState(session_id="demo_user_123")

# Set user preferences
print("\n⚙️  Setting user preferences...")
state.set_preference("theme", "dark")
state.set_preference("language", "en")
state.set_preference("verbosity", "detailed")

print(f"✅ Theme: {state.get_preference('theme')}")
print(f"✅ Language: {state.get_preference('language')}")
print(f"✅ Verbosity: {state.get_preference('verbosity')}")

# Add custom data
print("\n🔑 Adding custom data...")
state.set_custom_data("user_level", "advanced")
state.set_custom_data("topics_of_interest", ["AI", "ML", "Quantum"])

print(f"✅ User level: {state.get_custom_data('user_level')}")
print(f"✅ Topics: {state.get_custom_data('topics_of_interest')}")

# Add conversation summary
print("\n📚 Adding conversation summaries...")
state.add_conversation_summary({
    'topic': 'Python Programming',
    'turns': 4,
    'summary': 'Discussed Python basics and ML applications',
    'keywords': ['Python', 'Machine Learning']
})

state.add_conversation_summary({
    'topic': 'Quantum Computing',
    'turns': 2,
    'summary': 'Brief introduction to quantum computing',
    'keywords': ['quantum computing', 'quantum mechanics']
})

history = state.get_conversation_history()
print(f"✅ Conversation history entries: {len(history)}")

# Save state
print("\n💾 Saving state to disk...")
save_path = Path("/tmp/versaai_demo_state.json")
state.save(save_path)
print(f"✅ Saved to: {save_path}")

# Load state
print("\n📂 Loading state from disk...")
loaded_state = ConversationState.load(save_path)
print(f"✅ Loaded session: {loaded_state.session_id}")
print(f"✅ Theme preference: {loaded_state.get_preference('theme')}")
print(f"✅ History entries: {len(loaded_state.get_conversation_history())}")

# Get summary
print("\n📋 State Summary:")
print(state.get_summary())

# Get statistics
state_stats = state.get_stats()
print("\n📈 State Statistics:")
for key, value in state_stats.items():
    if key != 'last_backup':
        print(f"   {key}: {value}")

# Clean up
save_path.unlink()

# ============================================================================
# Demo 4: Integrated Usage - All components together
# ============================================================================

print("\n\n🔄 DEMO 4: Integrated Usage")
print("-" * 70)

# Create all components
conv_mgr = ConversationManager("llama-3-8b")
ctx_mgr = ContextWindowManager("llama-3-8b")
state_mgr = ConversationState(session_id="integrated_demo")

# Simulate conversation
print("\n💬 Simulating integrated conversation...")

# User message
user_msg = "What are the best practices for Python development?"
conv_mgr.add_turn("user", user_msg)

# Get optimized context
context = conv_mgr.get_context_for_generation()
optimized_context = ctx_mgr.optimize_context(context, max_tokens=4096)

print(f"✅ User message added")
print(f"✅ Context optimized: {len(optimized_context)} messages")

# Simulate assistant response
assistant_msg = "Here are the best practices for Python development: 1) Use virtual environments, 2) Follow PEP 8 style guide, 3) Write comprehensive tests..."
conv_mgr.add_turn("assistant", assistant_msg)

print(f"✅ Assistant response added")

# Update state with conversation summary
state_mgr.add_conversation_summary({
    'topic': conv_mgr.get_current_topic(),
    'turns': len(conv_mgr.get_turns()),
    'summary': conv_mgr.get_summary(),
    'entities': list(conv_mgr.get_entities().keys())[:5]
})

print(f"✅ State updated with conversation summary")

# Final statistics
print("\n📊 Integrated System Stats:")
print(f"   Conversation turns: {len(conv_mgr.get_turns())}")
print(f"   Context optimization performed: {ctx_mgr.get_stats()['contexts_optimized']}")
print(f"   State history entries: {len(state_mgr.get_conversation_history())}")

print("\n" + "=" * 70)
print("✅ DEMO COMPLETE - All Memory Systems Working!")
print("=" * 70)

print("\n🎯 Summary:")
print("   ✅ ConversationManager - Multi-turn tracking operational")
print("   ✅ ContextWindowManager - Dynamic optimization operational")
print("   ✅ ConversationState - Persistent state operational")
print("   ✅ Integrated usage - All components work together")

print("\n🚀 VersaAI Memory Systems: Production Ready!")
