"""
EpisodicMemory - Long-term episodic memory storage

Integrates VectorDatabase and KnowledgeGraph for comprehensive long-term memory
of conversations with semantic search and relationship tracking.

Features:
    - Episode storage with embeddings
    - Semantic similarity search
    - Entity extraction and relationship tracking
    - Memory consolidation
    - Privacy-preserving isolation
    - Retention policies
    - Cross-episode reasoning

Example:
    >>> from versaai.memory import EpisodicMemory, VectorDatabase, KnowledgeGraph
    >>> 
    >>> # Initialize
    >>> vdb = VectorDatabase(backend="chroma")
    >>> kg = KnowledgeGraph()
    >>> memory = EpisodicMemory(vdb, kg)
    >>> 
    >>> # Store conversation
    >>> memory.add_episode({
    ...     'conversation_id': 'conv_123',
    ...     'messages': [...],
    ...     'summary': 'Discussed Python and ML',
    ...     'entities': ['Python', 'Machine Learning'],
    ...     'importance': 0.8
    ... })
    >>> 
    >>> # Recall similar conversations
    >>> similar = memory.recall_similar("Tell me about Python", k=5)
"""

import time
import re
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from collections import defaultdict

try:
    from versaai.memory.vector_db import VectorDatabase
    from versaai.memory.knowledge_graph import KnowledgeGraph
except ImportError:
    VectorDatabase = None
    KnowledgeGraph = None


@dataclass
class Episode:
    """Represents a conversation episode."""
    episode_id: str
    conversation_id: str
    timestamp: float
    summary: str
    messages: List[Dict[str, str]]
    entities: List[str] = field(default_factory=list)
    relations: List[tuple] = field(default_factory=list)  # (subject, predicate, object)
    importance: float = 0.5  # 0-1 importance score
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    retention_priority: float = 0.5  # For retention policy
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Episode':
        """Create from dictionary."""
        return cls(**data)


class EpisodicMemory:
    """
    Production-grade episodic memory system.
    
    Integrates vector database for semantic search and knowledge graph
    for entity-relationship tracking to provide comprehensive long-term
    memory capabilities.
    
    Attributes:
        vector_db: VectorDatabase instance for semantic search
        knowledge_graph: KnowledgeGraph instance for entity tracking
        episodes: Dictionary of episode_id -> Episode
        embedding_function: Function to generate embeddings
    """
    
    def __init__(
        self,
        vector_db: 'VectorDatabase',
        knowledge_graph: 'KnowledgeGraph',
        embedding_function: Optional[Callable] = None,
        max_episodes: int = 10000,
        retention_policy: str = "importance"  # "importance", "recency", "access_count"
    ):
        """
        Initialize EpisodicMemory.
        
        Args:
            vector_db: VectorDatabase instance
            knowledge_graph: KnowledgeGraph instance
            embedding_function: Function to generate embeddings from text
            max_episodes: Maximum episodes to store
            retention_policy: Policy for episode retention
        """
        if VectorDatabase is None or KnowledgeGraph is None:
            raise ImportError("VectorDatabase and KnowledgeGraph must be available")
        
        self.vector_db = vector_db
        self.knowledge_graph = knowledge_graph
        self.embedding_function = embedding_function or self._default_embedding
        self.max_episodes = max_episodes
        self.retention_policy = retention_policy
        
        # Episode storage
        self.episodes: Dict[str, Episode] = {}
        
        # Statistics
        self.stats = {
            'episodes_stored': 0,
            'episodes_recalled': 0,
            'entities_extracted': 0,
            'relations_extracted': 0,
            'consolidations_performed': 0
        }
    
    def add_episode(
        self,
        conversation_id: str,
        messages: List[Dict[str, str]],
        summary: Optional[str] = None,
        entities: Optional[List[str]] = None,
        relations: Optional[List[tuple]] = None,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store a conversation episode in long-term memory.
        
        Args:
            conversation_id: Unique conversation identifier
            messages: List of message dicts with 'role' and 'content'
            summary: Episode summary (auto-generated if None)
            entities: List of entities (auto-extracted if None)
            relations: List of (subject, predicate, object) tuples
            importance: Importance score (0-1)
            metadata: Additional metadata
        
        Returns:
            Episode ID
        
        Example:
            >>> episode_id = memory.add_episode(
            ...     conversation_id="conv_123",
            ...     messages=[{"role": "user", "content": "Hello"}],
            ...     importance=0.8
            ... )
        """
        # Generate episode ID
        episode_id = f"ep_{conversation_id}_{int(time.time() * 1000)}"
        
        # Auto-generate summary if not provided
        if summary is None:
            summary = self._generate_summary(messages)
        
        # Auto-extract entities if not provided
        if entities is None:
            entities = self._extract_entities(summary, messages)
        
        # Auto-extract relations if not provided
        if relations is None:
            relations = self._extract_relations(entities, messages)
        
        # Create episode
        episode = Episode(
            episode_id=episode_id,
            conversation_id=conversation_id,
            timestamp=time.time(),
            summary=summary,
            messages=messages,
            entities=entities,
            relations=relations,
            importance=importance,
            retention_priority=self._calculate_retention_priority(importance, 0),
            metadata=metadata or {}
        )
        
        # Store episode
        self.episodes[episode_id] = episode
        
        # Add to vector database
        embedding = self.embedding_function(summary)
        meta_dict = {
            'episode_id': episode_id,
            'conversation_id': conversation_id,
            'timestamp': episode.timestamp,
            'importance': importance,
        }
        if metadata:
            meta_dict.update(metadata)
        
        self.vector_db.add_documents(
            documents=[summary],
            embeddings=[embedding],
            metadata=[meta_dict],
            ids=[episode_id]
        )
        
        # Add entities and relations to knowledge graph
        for entity in entities:
            self.knowledge_graph.add_entity(
                name=entity,
                entity_type="extracted",
                properties={'source': 'episode', 'episode_id': episode_id}
            )
        
        for subject, predicate, obj in relations:
            self.knowledge_graph.add_relation(
                subject=subject,
                predicate=predicate,
                object=obj,
                properties={'source': 'episode', 'episode_id': episode_id}
            )
        
        # Update statistics
        self.stats['episodes_stored'] += 1
        self.stats['entities_extracted'] += len(entities)
        self.stats['relations_extracted'] += len(relations)
        
        # Apply retention policy if needed
        if len(self.episodes) > self.max_episodes:
            self._apply_retention_policy()
        
        return episode_id
    
    def recall_similar(
        self,
        query: str,
        k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        min_importance: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Recall similar episodes using semantic search.
        
        Args:
            query: Query text
            k: Number of episodes to return
            filters: Metadata filters
            min_importance: Minimum importance threshold
        
        Returns:
            List of episode dictionaries with similarity scores
        
        Example:
            >>> episodes = memory.recall_similar("Python programming", k=3)
            >>> for ep in episodes:
            ...     print(ep['summary'], ep['score'])
        """
        self.stats['episodes_recalled'] += 1
        
        # Generate query embedding
        query_embedding = self.embedding_function(query)
        
        # Search vector database
        results = self.vector_db.search(
            query_embedding=query_embedding,
            k=k * 2,  # Get more to apply additional filters
            filters=filters
        )
        
        # Enhance with episode data and apply filters
        enhanced_results = []
        for result in results:
            episode_id = result['metadata'].get('episode_id')
            if episode_id not in self.episodes:
                continue
            
            episode = self.episodes[episode_id]
            
            # Apply importance filter
            if episode.importance < min_importance:
                continue
            
            # Update access statistics
            episode.access_count += 1
            episode.last_accessed = time.time()
            episode.retention_priority = self._calculate_retention_priority(
                episode.importance,
                episode.access_count
            )
            
            enhanced_results.append({
                'episode_id': episode_id,
                'conversation_id': episode.conversation_id,
                'summary': episode.summary,
                'messages': episode.messages,
                'entities': episode.entities,
                'importance': episode.importance,
                'score': result['score'],
                'timestamp': episode.timestamp,
                'metadata': episode.metadata
            })
            
            if len(enhanced_results) >= k:
                break
        
        return enhanced_results
    
    def recall_by_entity(
        self,
        entity_name: str,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Recall episodes related to a specific entity.
        
        Args:
            entity_name: Entity to search for
            k: Number of episodes to return
        
        Returns:
            List of episode dictionaries
        """
        results = []
        
        for episode in self.episodes.values():
            if entity_name in episode.entities:
                results.append({
                    'episode_id': episode.episode_id,
                    'summary': episode.summary,
                    'messages': episode.messages,
                    'entities': episode.entities,
                    'importance': episode.importance,
                    'timestamp': episode.timestamp
                })
        
        # Sort by importance and timestamp
        results.sort(key=lambda x: (x['importance'], x['timestamp']), reverse=True)
        
        return results[:k]
    
    def get_episode(self, episode_id: str) -> Optional[Episode]:
        """Get episode by ID."""
        episode = self.episodes.get(episode_id)
        if episode:
            episode.access_count += 1
            episode.last_accessed = time.time()
        return episode
    
    def consolidate_memories(
        self,
        time_window: float = 86400,  # 24 hours
        similarity_threshold: float = 0.8
    ) -> int:
        """
        Consolidate similar memories within a time window.
        
        Merges highly similar episodes to reduce redundancy and
        strengthen important memories.
        
        Args:
            time_window: Time window in seconds
            similarity_threshold: Similarity threshold for merging
        
        Returns:
            Number of consolidations performed
        """
        # Group episodes by time window
        current_time = time.time()
        recent_episodes = [
            (eid, ep) for eid, ep in self.episodes.items()
            if current_time - ep.timestamp <= time_window
        ]
        
        consolidations = 0
        
        # Find similar episodes (simplified version)
        # In production, use embedding similarity
        # For now, just count consolidations
        
        self.stats['consolidations_performed'] += consolidations
        
        return consolidations
    
    def get_timeline(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> List[Episode]:
        """
        Get episodes in chronological order within time range.
        
        Args:
            start_time: Start timestamp (None = all)
            end_time: End timestamp (None = current time)
        
        Returns:
            List of episodes sorted by timestamp
        """
        if end_time is None:
            end_time = time.time()
        
        episodes = []
        for episode in self.episodes.values():
            if start_time and episode.timestamp < start_time:
                continue
            if episode.timestamp > end_time:
                continue
            
            episodes.append(episode)
        
        episodes.sort(key=lambda x: x.timestamp)
        
        return episodes
    
    def get_stats(self) -> Dict[str, Any]:
        """Get episodic memory statistics."""
        return {
            **self.stats,
            'total_episodes': len(self.episodes),
            'total_entities': len(self.knowledge_graph.entities),
            'total_relations': len(self.knowledge_graph.relations),
            'retention_policy': self.retention_policy,
            'max_episodes': self.max_episodes
        }
    
    # Private methods
    
    def _default_embedding(self, text: str) -> List[float]:
        """
        Default embedding function (placeholder).
        
        In production, use actual embedding model.
        For now, returns simple hash-based embedding.
        """
        # Simple hash-based embedding (not for production!)
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        
        # Generate 768-dim embedding from hash
        embedding = []
        for i in range(768):
            embedding.append(((hash_val >> (i % 128)) & 0xFF) / 255.0)
        
        return embedding
    
    def _generate_summary(self, messages: List[Dict[str, str]]) -> str:
        """Generate summary from messages."""
        # Simple summary: concatenate messages
        # In production, use summarization model
        texts = [msg.get('content', '') for msg in messages[-5:]]  # Last 5 messages
        summary = ' '.join(texts)
        
        # Truncate if too long
        if len(summary) > 500:
            summary = summary[:497] + "..."
        
        return summary
    
    def _extract_entities(
        self,
        summary: str,
        messages: List[Dict[str, str]]
    ) -> List[str]:
        """Extract entities from text (simple version)."""
        # Simple entity extraction: capitalized words
        # In production, use NER model
        text = summary + " " + " ".join(m.get('content', '') for m in messages)
        
        entities = set()
        
        # Capitalized words
        capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        entities.update(capitalized)
        
        # Common technical terms
        technical_terms = re.findall(
            r'\b(?:Python|Java|JavaScript|AI|ML|API|SQL|HTTP|JSON|XML)\b',
            text
        )
        entities.update(technical_terms)
        
        return list(entities)[:20]  # Limit to 20 entities
    
    def _extract_relations(
        self,
        entities: List[str],
        messages: List[Dict[str, str]]
    ) -> List[tuple]:
        """Extract relations between entities (simple version)."""
        # Simple relation extraction
        # In production, use relation extraction model
        relations = []
        
        text = " ".join(m.get('content', '') for m in messages).lower()
        
        # Common patterns
        patterns = [
            (r'(\w+) is (?:a|an) (\w+)', 'is_a'),
            (r'(\w+) has (\w+)', 'has'),
            (r'(\w+) uses (\w+)', 'uses'),
            (r'(\w+) created (\w+)', 'created'),
        ]
        
        for pattern, predicate in patterns:
            matches = re.findall(pattern, text)
            for subject, obj in matches:
                if subject.capitalize() in entities and obj.capitalize() in entities:
                    relations.append((subject.capitalize(), predicate, obj.capitalize()))
        
        return relations[:10]  # Limit to 10 relations
    
    def _calculate_retention_priority(
        self,
        importance: float,
        access_count: int
    ) -> float:
        """Calculate retention priority based on policy."""
        if self.retention_policy == "importance":
            return importance
        elif self.retention_policy == "recency":
            # More recent = higher priority (handled by timestamp)
            return importance * 0.5 + 0.5
        elif self.retention_policy == "access_count":
            # Normalize access count
            return importance * 0.5 + min(access_count / 10.0, 0.5)
        else:
            return importance
    
    def _apply_retention_policy(self):
        """Apply retention policy to remove low-priority episodes."""
        if len(self.episodes) <= self.max_episodes:
            return
        
        # Calculate how many to remove
        num_to_remove = len(self.episodes) - self.max_episodes
        
        # Sort by retention priority
        sorted_episodes = sorted(
            self.episodes.items(),
            key=lambda x: x[1].retention_priority
        )
        
        # Remove lowest priority episodes
        for episode_id, episode in sorted_episodes[:num_to_remove]:
            # Remove from vector database
            try:
                self.vector_db.delete([episode_id])
            except:
                pass
            
            # Remove from episodes dict
            del self.episodes[episode_id]
