"""
VersaAI Memory Systems

Provides short-term and long-term memory capabilities for VersaAI agents.

Short-term Memory (Phase 3.1):
    - ConversationManager: Multi-turn conversation tracking
    - ContextWindowManager: Dynamic context optimization
    - ConversationState: Persistent session state

Long-term Memory (Phase 3.2):
    - VectorDatabase: Semantic search with ChromaDB/FAISS
    - KnowledgeGraph: Entity-relationship storage
    - EpisodicMemory: Long-term conversation storage
"""

import importlib as _importlib


# All imports are lazy to avoid pulling in numpy/chromadb/faiss
# when only the API server is needed.
def __getattr__(name: str):
    _lazy_map = {
        # Short-term memory (Phase 3.1)
        "ConversationManager": "versaai.memory.conversation",
        "ConversationTurn": "versaai.memory.conversation",
        "ContextWindowManager": "versaai.memory.context_window",
        "MessagePriority": "versaai.memory.context_window",
        "ConversationState": "versaai.memory.state",
        "SessionInfo": "versaai.memory.state",
        "UserPreferences": "versaai.memory.state",
        # Long-term memory (Phase 3.2)
        "VectorDatabase": "versaai.memory.vector_db",
        "KnowledgeGraph": "versaai.memory.knowledge_graph",
        "Entity": "versaai.memory.knowledge_graph",
        "Relation": "versaai.memory.knowledge_graph",
        "EntityType": "versaai.memory.knowledge_graph",
        "EpisodicMemory": "versaai.memory.episodic",
        "Episode": "versaai.memory.episodic",
    }
    if name in _lazy_map:
        module = _importlib.import_module(_lazy_map[name])
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    # Short-term memory
    "ConversationManager",
    "ConversationTurn",
    "ContextWindowManager",
    "MessagePriority",
    "ConversationState",
    "SessionInfo",
    "UserPreferences",

    # Long-term memory
    "VectorDatabase",
    "KnowledgeGraph",
    "Entity",
    "Relation",
    "EntityType",
    "EpisodicMemory",
    "Episode",
]

__version__ = "0.2.0"  # Phase 3.2 complete
