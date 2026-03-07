"""
KnowledgeGraph - Entity-relationship storage for structured knowledge

Provides graph-based storage and query capabilities for entities and their
relationships with temporal reasoning and conflict resolution.

Features:
    - Entity nodes with types and properties
    - Directed relationships (edges)
    - Multi-hop traversal (BFS/DFS)
    - Temporal tracking
    - Conflict resolution
    - JSON serialization

Example:
    >>> from versaai.memory import KnowledgeGraph
    >>> 
    >>> kg = KnowledgeGraph(persist_dir="./knowledge")
    >>> 
    >>> # Add entities
    >>> kg.add_entity("Python", "programming_language", {
    ...     "created": 1991,
    ...     "creator": "Guido van Rossum"
    ... })
    >>> 
    >>> # Add relationships
    >>> kg.add_relation("Python", "used_for", "machine_learning")
    >>> kg.add_relation("Python", "has_framework", "Django")
    >>> 
    >>> # Query
    >>> related = kg.query_related("Python", max_hops=2)
    >>> path = kg.find_path("Python", "Django")
"""

import json
import time
from typing import List, Dict, Any, Optional, Set, Tuple
from pathlib import Path
from collections import deque, defaultdict
from dataclasses import dataclass, asdict, field
from enum import Enum


class EntityType(Enum):
    """Common entity types."""
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    CONCEPT = "concept"
    TECHNOLOGY = "technology"
    DOCUMENT = "document"
    EVENT = "event"
    CUSTOM = "custom"


@dataclass
class Entity:
    """Represents an entity node in the knowledge graph."""
    name: str
    entity_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    confidence: float = 1.0  # 0-1 confidence score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Entity':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class Relation:
    """Represents a relationship edge in the knowledge graph."""
    subject: str  # Entity name
    predicate: str  # Relationship type
    object: str  # Entity name
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    confidence: float = 1.0
    temporal_valid_from: Optional[float] = None
    temporal_valid_to: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Relation':
        """Create from dictionary."""
        return cls(**data)
    
    def is_valid_at(self, timestamp: Optional[float] = None) -> bool:
        """Check if relationship is valid at given timestamp."""
        if timestamp is None:
            timestamp = time.time()
        
        if self.temporal_valid_from and timestamp < self.temporal_valid_from:
            return False
        if self.temporal_valid_to and timestamp > self.temporal_valid_to:
            return False
        
        return True


class KnowledgeGraph:
    """
    Production-grade knowledge graph for entity-relationship storage.
    
    Provides graph operations including traversal, path finding, and
    querying with temporal reasoning and conflict resolution.
    
    Attributes:
        entities: Dictionary of entity_name -> Entity
        relations: List of Relation objects
        adjacency: Adjacency list for efficient traversal
        persist_dir: Directory for persistence
    """
    
    def __init__(
        self,
        persist_dir: Optional[Path] = None,
        auto_save: bool = True
    ):
        """
        Initialize KnowledgeGraph.
        
        Args:
            persist_dir: Directory for persistence (None = in-memory only)
            auto_save: Automatically save after modifications
        """
        self.entities: Dict[str, Entity] = {}
        self.relations: List[Relation] = []
        self.adjacency: Dict[str, List[Tuple[str, str, int]]] = defaultdict(list)  # entity -> [(relation, target, relation_idx)]
        self.reverse_adjacency: Dict[str, List[Tuple[str, str, int]]] = defaultdict(list)  # For inverse queries
        
        self.persist_dir = Path(persist_dir) if persist_dir else None
        self.auto_save = auto_save
        
        # Statistics
        self.stats = {
            'num_entities': 0,
            'num_relations': 0,
            'num_entity_types': 0,
            'num_relation_types': 0,
            'queries_performed': 0
        }
        
        # Load from disk if exists
        if self.persist_dir:
            self.persist_dir.mkdir(parents=True, exist_ok=True)
            self.load()
    
    def add_entity(
        self,
        name: str,
        entity_type: str,
        properties: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0
    ) -> Entity:
        """
        Add or update an entity.
        
        Args:
            name: Unique entity name
            entity_type: Type of entity
            properties: Entity properties
            confidence: Confidence score (0-1)
        
        Returns:
            Created or updated Entity
        
        Example:
            >>> entity = kg.add_entity("Python", "language", {
            ...     "paradigm": "multi-paradigm",
            ...     "typing": "dynamic"
            ... })
        """
        if name in self.entities:
            # Update existing entity
            entity = self.entities[name]
            entity.entity_type = entity_type
            entity.properties.update(properties or {})
            entity.updated_at = time.time()
            entity.confidence = max(entity.confidence, confidence)  # Keep highest confidence
        else:
            # Create new entity
            entity = Entity(
                name=name,
                entity_type=entity_type,
                properties=properties or {},
                confidence=confidence
            )
            self.entities[name] = entity
            self.stats['num_entities'] += 1
        
        self._update_stats()
        
        if self.auto_save and self.persist_dir:
            self.save()
        
        return entity
    
    def add_relation(
        self,
        subject: str,
        predicate: str,
        object: str,
        properties: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0,
        temporal_valid_from: Optional[float] = None,
        temporal_valid_to: Optional[float] = None
    ) -> Relation:
        """
        Add a relationship between entities.
        
        Args:
            subject: Source entity name
            predicate: Relationship type
            object: Target entity name
            properties: Relationship properties
            confidence: Confidence score
            temporal_valid_from: Valid from timestamp
            temporal_valid_to: Valid to timestamp
        
        Returns:
            Created Relation
        
        Example:
            >>> rel = kg.add_relation("Python", "created_by", "Guido van Rossum")
            >>> rel = kg.add_relation("Python", "version", "3.12", 
            ...     temporal_valid_from=time.time())
        """
        # Create entities if they don't exist
        if subject not in self.entities:
            self.add_entity(subject, "unknown", confidence=confidence)
        if object not in self.entities:
            self.add_entity(object, "unknown", confidence=confidence)
        
        # Create relation
        relation = Relation(
            subject=subject,
            predicate=predicate,
            object=object,
            properties=properties or {},
            confidence=confidence,
            temporal_valid_from=temporal_valid_from,
            temporal_valid_to=temporal_valid_to
        )
        
        relation_idx = len(self.relations)
        self.relations.append(relation)
        
        # Update adjacency lists
        self.adjacency[subject].append((predicate, object, relation_idx))
        self.reverse_adjacency[object].append((predicate, subject, relation_idx))
        
        self.stats['num_relations'] += 1
        self._update_stats()
        
        if self.auto_save and self.persist_dir:
            self.save()
        
        return relation
    
    def get_entity(self, name: str) -> Optional[Entity]:
        """Get entity by name."""
        return self.entities.get(name)
    
    def get_relations(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        object: Optional[str] = None,
        include_temporal_invalid: bool = False
    ) -> List[Relation]:
        """
        Query relations with optional filtering.
        
        Args:
            subject: Filter by subject entity
            predicate: Filter by predicate type
            object: Filter by object entity
            include_temporal_invalid: Include temporally invalid relations
        
        Returns:
            List of matching relations
        """
        results = []
        
        for relation in self.relations:
            # Apply filters
            if subject and relation.subject != subject:
                continue
            if predicate and relation.predicate != predicate:
                continue
            if object and relation.object != object:
                continue
            if not include_temporal_invalid and not relation.is_valid_at():
                continue
            
            results.append(relation)
        
        return results
    
    def query_related(
        self,
        entity_name: str,
        max_hops: int = 2,
        predicate_filter: Optional[List[str]] = None,
        include_reverse: bool = True
    ) -> Dict[str, Any]:
        """
        Find entities related to the given entity within max_hops.
        
        Args:
            entity_name: Starting entity
            max_hops: Maximum number of hops
            predicate_filter: Only follow these predicates
            include_reverse: Include reverse relations
        
        Returns:
            Dictionary with related entities by hop distance
        
        Example:
            >>> related = kg.query_related("Python", max_hops=2)
            >>> print(related['hop_1'])  # Direct relations
            >>> print(related['hop_2'])  # 2-hop relations
        """
        self.stats['queries_performed'] += 1
        
        if entity_name not in self.entities:
            return {}
        
        visited = {entity_name}
        results = defaultdict(list)
        queue = deque([(entity_name, 0)])  # (entity, hop_count)
        
        while queue:
            current, hops = queue.popleft()
            
            if hops >= max_hops:
                continue
            
            # Forward relations
            for predicate, target, rel_idx in self.adjacency[current]:
                relation = self.relations[rel_idx]
                
                # Apply filters
                if predicate_filter and predicate not in predicate_filter:
                    continue
                if not relation.is_valid_at():
                    continue
                
                if target not in visited:
                    visited.add(target)
                    results[f'hop_{hops + 1}'].append({
                        'entity': target,
                        'predicate': predicate,
                        'from': current,
                        'confidence': relation.confidence
                    })
                    queue.append((target, hops + 1))
            
            # Reverse relations
            if include_reverse:
                for predicate, source, rel_idx in self.reverse_adjacency[current]:
                    relation = self.relations[rel_idx]
                    
                    if predicate_filter and predicate not in predicate_filter:
                        continue
                    if not relation.is_valid_at():
                        continue
                    
                    if source not in visited:
                        visited.add(source)
                        results[f'hop_{hops + 1}'].append({
                            'entity': source,
                            'predicate': f'inverse_{predicate}',
                            'from': current,
                            'confidence': relation.confidence
                        })
                        queue.append((source, hops + 1))
        
        return dict(results)
    
    def find_path(
        self,
        start: str,
        end: str,
        max_depth: int = 5
    ) -> Optional[List[Tuple[str, str, str]]]:
        """
        Find shortest path between two entities.
        
        Args:
            start: Start entity name
            end: End entity name
            max_depth: Maximum path length
        
        Returns:
            List of (subject, predicate, object) tuples or None
        
        Example:
            >>> path = kg.find_path("Python", "Django")
            >>> # [("Python", "has_framework", "Django")]
        """
        if start not in self.entities or end not in self.entities:
            return None
        
        queue = deque([(start, [])])
        visited = {start}
        
        while queue:
            current, path = queue.popleft()
            
            if len(path) >= max_depth:
                continue
            
            if current == end:
                return path
            
            # Explore neighbors
            for predicate, target, rel_idx in self.adjacency[current]:
                relation = self.relations[rel_idx]
                
                if not relation.is_valid_at():
                    continue
                
                if target not in visited:
                    visited.add(target)
                    new_path = path + [(current, predicate, target)]
                    queue.append((target, new_path))
        
        return None  # No path found
    
    def get_entity_types(self) -> List[str]:
        """Get all entity types in the graph."""
        return list(set(e.entity_type for e in self.entities.values()))
    
    def get_predicate_types(self) -> List[str]:
        """Get all predicate types in the graph."""
        return list(set(r.predicate for r in self.relations))
    
    def save(self, filepath: Optional[Path] = None) -> None:
        """
        Save knowledge graph to disk.
        
        Args:
            filepath: Custom filepath (uses persist_dir if None)
        """
        if filepath is None:
            if not self.persist_dir:
                return
            filepath = self.persist_dir / "knowledge_graph.json"
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'entities': {name: entity.to_dict() for name, entity in self.entities.items()},
            'relations': [relation.to_dict() for relation in self.relations],
            'stats': self.stats,
            'version': '1.0.0',
            'saved_at': time.time()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load(self, filepath: Optional[Path] = None) -> bool:
        """
        Load knowledge graph from disk.
        
        Args:
            filepath: Custom filepath (uses persist_dir if None)
        
        Returns:
            True if loaded successfully
        """
        if filepath is None:
            if not self.persist_dir:
                return False
            filepath = self.persist_dir / "knowledge_graph.json"
        
        filepath = Path(filepath)
        if not filepath.exists():
            return False
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Load entities
        self.entities = {
            name: Entity.from_dict(entity_data)
            for name, entity_data in data.get('entities', {}).items()
        }
        
        # Load relations
        self.relations = [
            Relation.from_dict(rel_data)
            for rel_data in data.get('relations', [])
        ]
        
        # Rebuild adjacency lists
        self.adjacency.clear()
        self.reverse_adjacency.clear()
        
        for idx, relation in enumerate(self.relations):
            self.adjacency[relation.subject].append((relation.predicate, relation.object, idx))
            self.reverse_adjacency[relation.object].append((relation.predicate, relation.subject, idx))
        
        # Update stats
        if 'stats' in data:
            self.stats.update(data['stats'])
        
        self._update_stats()
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge graph statistics."""
        return {
            **self.stats,
            'entity_types': self.get_entity_types(),
            'predicate_types': self.get_predicate_types()
        }
    
    def _update_stats(self):
        """Update internal statistics."""
        self.stats['num_entities'] = len(self.entities)
        self.stats['num_relations'] = len(self.relations)
        self.stats['num_entity_types'] = len(self.get_entity_types())
        self.stats['num_relation_types'] = len(self.get_predicate_types())
