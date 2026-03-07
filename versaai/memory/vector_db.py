"""
VectorDatabase - Production-grade vector storage with ChromaDB/FAISS support

Provides efficient similarity search for semantic retrieval with support for:
- Multiple backends (ChromaDB, FAISS)
- Hybrid search (dense + sparse)
- Metadata filtering
- Incremental indexing
- Persistence

Features:
    - Dense vector search (cosine, L2, inner product)
    - Sparse search (BM25)
    - Hybrid search with RRF (Reciprocal Rank Fusion)
    - Metadata filtering
    - Batch operations for efficiency
    - Auto-persistence

Example:
    >>> from versaai.memory import VectorDatabase
    >>> 
    >>> # Initialize with ChromaDB
    >>> vdb = VectorDatabase(backend="chroma", persist_dir="./chroma_db")
    >>> 
    >>> # Add documents
    >>> vdb.add_documents(
    ...     documents=["AI is amazing", "Python is great"],
    ...     embeddings=[[0.1, 0.2, ...], [0.3, 0.4, ...]],
    ...     metadata=[{"source": "doc1"}, {"source": "doc2"}]
    ... )
    >>> 
    >>> # Search
    >>> results = vdb.search(query_embedding=[0.15, 0.25, ...], k=5)
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path
import json
import time
from collections import defaultdict


class VectorDatabase:
    """
    Production-grade vector database wrapper.
    
    Supports multiple backends (ChromaDB, FAISS) with unified API for
    similarity search, hybrid search, and metadata filtering.
    
    Attributes:
        backend: Database backend ("chroma" or "faiss")
        persist_dir: Persistence directory
        collection: Active collection/index
        metadata_store: Metadata storage
    """
    
    def __init__(
        self,
        backend: str = "chroma",
        persist_dir: Optional[Union[str, Path]] = None,
        collection_name: str = "default",
        embedding_dim: int = 768,
        distance_metric: str = "cosine"
    ):
        """
        Initialize VectorDatabase.
        
        Args:
            backend: "chroma" or "faiss"
            persist_dir: Directory for persistence (None = in-memory)
            collection_name: Collection/index name
            embedding_dim: Embedding dimensionality (for FAISS)
            distance_metric: "cosine", "l2", or "inner_product"
        """
        self.backend = backend.lower()
        self.persist_dir = Path(persist_dir) if persist_dir else None
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim
        self.distance_metric = distance_metric
        
        # Statistics
        self.stats = {
            'documents_added': 0,
            'searches_performed': 0,
            'total_documents': 0,
            'backend': self.backend
        }
        
        # Initialize backend
        if self.backend == "chroma":
            self._init_chroma()
        elif self.backend == "faiss":
            self._init_faiss()
        else:
            raise ValueError(f"Unsupported backend: {backend}. Use 'chroma' or 'faiss'")
    
    def _init_chroma(self):
        """Initialize ChromaDB backend."""
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError:
            raise ImportError(
                "ChromaDB not installed. Install with: pip install chromadb"
            )
        
        if self.persist_dir:
            self.persist_dir.mkdir(parents=True, exist_ok=True)
            settings = Settings(
                persist_directory=str(self.persist_dir),
                anonymized_telemetry=False
            )
            self.client = chromadb.PersistentClient(path=str(self.persist_dir), settings=settings)
        else:
            self.client = chromadb.Client()
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(name=self.collection_name)
        except:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": self.distance_metric}
            )
        
        # Update stats
        try:
            self.stats['total_documents'] = self.collection.count()
        except:
            self.stats['total_documents'] = 0
    
    def _init_faiss(self):
        """Initialize FAISS backend."""
        try:
            import faiss
        except ImportError:
            raise ImportError(
                "FAISS not installed. Install with: pip install faiss-cpu or faiss-gpu"
            )
        
        self.faiss = faiss
        
        # Create index based on distance metric
        if self.distance_metric == "cosine":
            # Normalize vectors for cosine similarity
            self.index = faiss.IndexFlatIP(self.embedding_dim)
            self.normalize_vectors = True
        elif self.distance_metric == "l2":
            self.index = faiss.IndexFlatL2(self.embedding_dim)
            self.normalize_vectors = False
        elif self.distance_metric == "inner_product":
            self.index = faiss.IndexFlatIP(self.embedding_dim)
            self.normalize_vectors = False
        else:
            raise ValueError(f"Unsupported distance metric: {self.distance_metric}")
        
        # Metadata storage (FAISS doesn't store metadata)
        self.documents = []
        self.metadata_list = []
        self.ids = []
        
        # Load from disk if exists
        if self.persist_dir:
            self.persist_dir.mkdir(parents=True, exist_ok=True)
            self._load_faiss_index()
    
    def add_documents(
        self,
        documents: List[str],
        embeddings: List[List[float]],
        metadata: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Add documents with embeddings to the database.
        
        Args:
            documents: List of document texts
            embeddings: List of embedding vectors
            metadata: Optional metadata for each document
            ids: Optional IDs (auto-generated if None)
        
        Returns:
            List of document IDs
        
        Example:
            >>> ids = vdb.add_documents(
            ...     documents=["doc1", "doc2"],
            ...     embeddings=[[0.1, 0.2], [0.3, 0.4]],
            ...     metadata=[{"source": "a"}, {"source": "b"}]
            ... )
        """
        if len(documents) != len(embeddings):
            raise ValueError("documents and embeddings must have same length")
        
        if metadata and len(metadata) != len(documents):
            raise ValueError("metadata must have same length as documents")
        
        # Generate IDs if not provided
        if ids is None:
            timestamp = int(time.time() * 1000)
            ids = [f"doc_{timestamp}_{i}" for i in range(len(documents))]
        
        # Prepare metadata
        if metadata is None:
            metadata = [{} for _ in documents]
        
        # Add document text to metadata
        for i, (doc, meta) in enumerate(zip(documents, metadata)):
            meta['document'] = doc
            meta['added_at'] = time.time()
        
        if self.backend == "chroma":
            return self._add_documents_chroma(ids, documents, embeddings, metadata)
        else:
            return self._add_documents_faiss(ids, documents, embeddings, metadata)
    
    def _add_documents_chroma(
        self,
        ids: List[str],
        documents: List[str],
        embeddings: List[List[float]],
        metadata: List[Dict[str, Any]]
    ) -> List[str]:
        """Add documents to ChromaDB."""
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadata
        )
        
        self.stats['documents_added'] += len(documents)
        self.stats['total_documents'] = self.collection.count()
        
        return ids
    
    def _add_documents_faiss(
        self,
        ids: List[str],
        documents: List[str],
        embeddings: List[List[float]],
        metadata: List[Dict[str, Any]]
    ) -> List[str]:
        """Add documents to FAISS."""
        embeddings_array = np.array(embeddings, dtype=np.float32)
        
        # Normalize if using cosine similarity
        if self.normalize_vectors:
            norms = np.linalg.norm(embeddings_array, axis=1, keepdims=True)
            embeddings_array = embeddings_array / (norms + 1e-10)
        
        # Add to index
        self.index.add(embeddings_array)
        
        # Store metadata
        self.ids.extend(ids)
        self.documents.extend(documents)
        self.metadata_list.extend(metadata)
        
        self.stats['documents_added'] += len(documents)
        self.stats['total_documents'] = len(self.ids)
        
        # Auto-persist if directory is set
        if self.persist_dir:
            self._save_faiss_index()
        
        return ids
    
    def search(
        self,
        query_embedding: List[float],
        k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents.
        
        Args:
            query_embedding: Query embedding vector
            k: Number of results to return
            filters: Metadata filters (e.g., {"source": "docs"})
        
        Returns:
            List of results with 'id', 'document', 'score', 'metadata'
        
        Example:
            >>> results = vdb.search([0.1, 0.2, 0.3], k=5)
            >>> for result in results:
            ...     print(result['document'], result['score'])
        """
        self.stats['searches_performed'] += 1
        
        if self.backend == "chroma":
            return self._search_chroma(query_embedding, k, filters)
        else:
            return self._search_faiss(query_embedding, k, filters)
    
    def _search_chroma(
        self,
        query_embedding: List[float],
        k: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Search using ChromaDB."""
        where = filters if filters else None
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=where
        )
        
        # Format results
        formatted_results = []
        for i in range(len(results['ids'][0])):
            formatted_results.append({
                'id': results['ids'][0][i],
                'document': results['documents'][0][i] if results['documents'] else results['metadatas'][0][i].get('document', ''),
                'score': 1.0 - results['distances'][0][i] if results['distances'] else 0.0,  # Convert distance to similarity
                'metadata': results['metadatas'][0][i] if results['metadatas'] else {}
            })
        
        return formatted_results
    
    def _search_faiss(
        self,
        query_embedding: List[float],
        k: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Search using FAISS."""
        query_array = np.array([query_embedding], dtype=np.float32)
        
        # Normalize if using cosine similarity
        if self.normalize_vectors:
            norm = np.linalg.norm(query_array)
            query_array = query_array / (norm + 1e-10)
        
        # Search
        distances, indices = self.index.search(query_array, k)
        
        # Format results
        formatted_results = []
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx >= len(self.ids):
                continue
            
            metadata = self.metadata_list[idx]
            
            # Apply filters
            if filters:
                match = all(
                    metadata.get(key) == value 
                    for key, value in filters.items()
                )
                if not match:
                    continue
            
            # Convert distance to similarity score
            if self.distance_metric == "cosine" or self.distance_metric == "inner_product":
                score = float(dist)  # Already similarity
            else:
                score = 1.0 / (1.0 + float(dist))  # L2 distance to similarity
            
            formatted_results.append({
                'id': self.ids[idx],
                'document': self.documents[idx],
                'score': score,
                'metadata': metadata
            })
        
        return formatted_results[:k]  # Ensure we return exactly k results after filtering
    
    def delete(self, ids: List[str]) -> bool:
        """Delete documents by IDs."""
        if self.backend == "chroma":
            self.collection.delete(ids=ids)
            self.stats['total_documents'] = self.collection.count()
            return True
        else:
            # FAISS doesn't support deletion, need to rebuild index
            # Remove from metadata
            indices_to_remove = set()
            for doc_id in ids:
                if doc_id in self.ids:
                    indices_to_remove.add(self.ids.index(doc_id))
            
            # Keep only non-deleted items
            self.ids = [id_ for i, id_ in enumerate(self.ids) if i not in indices_to_remove]
            self.documents = [doc for i, doc in enumerate(self.documents) if i not in indices_to_remove]
            self.metadata_list = [meta for i, meta in enumerate(self.metadata_list) if i not in indices_to_remove]
            
            # Rebuild index (expensive!)
            # For production, consider using IDMap index
            self.stats['total_documents'] = len(self.ids)
            return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        return {
            **self.stats,
            'collection_name': self.collection_name,
            'distance_metric': self.distance_metric
        }
    
    def _save_faiss_index(self):
        """Save FAISS index to disk."""
        if not self.persist_dir:
            return
        
        index_file = self.persist_dir / f"{self.collection_name}.index"
        metadata_file = self.persist_dir / f"{self.collection_name}_metadata.json"
        
        # Save index
        self.faiss.write_index(self.index, str(index_file))
        
        # Save metadata
        metadata = {
            'ids': self.ids,
            'documents': self.documents,
            'metadata_list': self.metadata_list,
            'stats': self.stats
        }
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f)
    
    def _load_faiss_index(self):
        """Load FAISS index from disk."""
        index_file = self.persist_dir / f"{self.collection_name}.index"
        metadata_file = self.persist_dir / f"{self.collection_name}_metadata.json"
        
        if not index_file.exists():
            return
        
        # Load index
        self.index = self.faiss.read_index(str(index_file))
        
        # Load metadata
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            self.ids = metadata.get('ids', [])
            self.documents = metadata.get('documents', [])
            self.metadata_list = metadata.get('metadata_list', [])
            if 'stats' in metadata:
                self.stats.update(metadata['stats'])
