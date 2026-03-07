"""
Production-grade Vector Store system with ChromaDB and FAISS support.

Features:
- Multiple backend support (ChromaDB, FAISS)
- Efficient similarity search
- Metadata filtering
- Batch operations
- Persistence
"""

from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import numpy as np

try:
    import versaai_core
    CPPLogger = versaai_core.Logger.get_instance()
    HAS_CPP_LOGGER = True
except (ImportError, AttributeError):
    import logging
    CPPLogger = logging.getLogger(__name__)
    HAS_CPP_LOGGER = False


class VectorStoreType(Enum):
    """Supported vector store backends."""
    CHROMADB = "chromadb"
    FAISS = "faiss"
    MEMORY = "memory"  # In-memory for testing


@dataclass
class VectorStoreConfig:
    """Configuration for vector store."""
    
    store_type: VectorStoreType = VectorStoreType.CHROMADB
    persist_directory: Optional[Path] = None
    collection_name: str = "versaai_documents"
    embedding_dimension: int = 384
    distance_metric: str = "cosine"  # "cosine", "l2", "ip"
    
    # ChromaDB specific
    chroma_host: Optional[str] = None
    chroma_port: Optional[int] = None
    
    # FAISS specific
    faiss_index_type: str = "Flat"  # "Flat", "IVF", "HNSW"
    faiss_nprobe: int = 10


class VectorStore:
    """
    Unified vector store interface supporting multiple backends.
    
    Features:
    - Add/delete/update documents with embeddings
    - Similarity search with metadata filtering
    - Batch operations
    - Persistence and recovery
    """
    
    def __init__(self, config: VectorStoreConfig, embedding_model=None):
        """
        Initialize vector store.
        
        Args:
            config: Vector store configuration
            embedding_model: Optional embedding model for auto-embedding
        """
        self.config = config
        self.embedding_model = embedding_model
        self.store = None
        self._document_count = 0
        
        self._initialize_store()
    
    def _initialize_store(self):
        """Initialize the underlying vector store backend."""
        if self.config.store_type == VectorStoreType.CHROMADB:
            self._init_chromadb()
        elif self.config.store_type == VectorStoreType.FAISS:
            self._init_faiss()
        elif self.config.store_type == VectorStoreType.MEMORY:
            self._init_memory()
        else:
            raise ValueError(f"Unsupported store type: {self.config.store_type}")
    
    def _init_chromadb(self):
        """Initialize ChromaDB backend."""
        try:
            import chromadb
            from chromadb.config import Settings
            
            if HAS_CPP_LOGGER:
                CPPLogger.info("Initializing ChromaDB vector store", "VectorStore")
            else:
                CPPLogger.info("Initializing ChromaDB vector store")
            
            if self.config.chroma_host and self.config.chroma_port:
                # Remote ChromaDB client
                self.client = chromadb.HttpClient(
                    host=self.config.chroma_host,
                    port=self.config.chroma_port
                )
            elif self.config.persist_directory:
                # Persistent local client
                self.client = chromadb.PersistentClient(
                    path=str(self.config.persist_directory)
                )
            else:
                # Ephemeral in-memory client
                self.client = chromadb.Client()
            
            # Get or create collection
            self.store = self.client.get_or_create_collection(
                name=self.config.collection_name,
                metadata={"hnsw:space": self.config.distance_metric}
            )
            
            self._document_count = self.store.count()
            
            if HAS_CPP_LOGGER:
                CPPLogger.info(
                    f"ChromaDB initialized with {self._document_count} documents",
                    "VectorStore"
                )
            else:
                CPPLogger.info(f"ChromaDB initialized with {self._document_count} documents")
                
        except ImportError:
            raise ImportError("ChromaDB not installed. Install with: pip install chromadb")
        except Exception as e:
            if HAS_CPP_LOGGER:
                CPPLogger.error(f"Failed to initialize ChromaDB: {e}", "VectorStore")
            else:
                CPPLogger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    def _init_faiss(self):
        """Initialize FAISS backend."""
        try:
            import faiss
            
            if HAS_CPP_LOGGER:
                CPPLogger.info("Initializing FAISS vector store", "VectorStore")
            else:
                CPPLogger.info("Initializing FAISS vector store")
            
            # Create FAISS index based on type
            if self.config.faiss_index_type == "Flat":
                if self.config.distance_metric == "cosine":
                    self.index = faiss.IndexFlatIP(self.config.embedding_dimension)
                elif self.config.distance_metric == "l2":
                    self.index = faiss.IndexFlatL2(self.config.embedding_dimension)
                else:
                    raise ValueError(f"Unsupported distance metric: {self.config.distance_metric}")
            elif self.config.faiss_index_type == "IVF":
                # IndexIVFFlat for large-scale approximate search
                quantizer = faiss.IndexFlatL2(self.config.embedding_dimension)
                self.index = faiss.IndexIVFFlat(
                    quantizer,
                    self.config.embedding_dimension,
                    100  # nlist (number of cells)
                )
                self.index.nprobe = self.config.faiss_nprobe
            else:
                raise ValueError(f"Unsupported FAISS index type: {self.config.faiss_index_type}")
            
            # Metadata storage (FAISS doesn't store metadata)
            self.metadata_store = {}
            self.id_to_idx = {}
            
            # Load existing index if available
            if self.config.persist_directory:
                index_path = self.config.persist_directory / "faiss.index"
                metadata_path = self.config.persist_directory / "metadata.npy"
                
                if index_path.exists():
                    self.index = faiss.read_index(str(index_path))
                    if metadata_path.exists():
                        self.metadata_store = np.load(str(metadata_path), allow_pickle=True).item()
                    
                    self._document_count = self.index.ntotal
                    
                    if HAS_CPP_LOGGER:
                        CPPLogger.info(
                            f"Loaded FAISS index with {self._document_count} vectors",
                            "VectorStore"
                        )
                    else:
                        CPPLogger.info(f"Loaded FAISS index with {self._document_count} vectors")
            
            self.store = self.index
            
        except ImportError:
            raise ImportError("FAISS not installed. Install with: pip install faiss-cpu or faiss-gpu")
        except Exception as e:
            if HAS_CPP_LOGGER:
                CPPLogger.error(f"Failed to initialize FAISS: {e}", "VectorStore")
            else:
                CPPLogger.error(f"Failed to initialize FAISS: {e}")
            raise
    
    def _init_memory(self):
        """Initialize simple in-memory backend (for testing)."""
        if HAS_CPP_LOGGER:
            CPPLogger.info("Initializing in-memory vector store", "VectorStore")
        else:
            CPPLogger.info("Initializing in-memory vector store")
        
        self.store = {
            "embeddings": [],
            "documents": [],
            "metadata": [],
            "ids": []
        }
    
    def add_documents(
        self,
        documents: List[str],
        embeddings: Optional[List[np.ndarray]] = None,
        metadata: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Add documents to vector store.
        
        Args:
            documents: List of text documents
            embeddings: Optional pre-computed embeddings
            metadata: Optional metadata for each document
            ids: Optional IDs for documents (auto-generated if None)
            
        Returns:
            List of document IDs
        """
        if not documents:
            return []
        
        # Generate embeddings if not provided
        if embeddings is None:
            if self.embedding_model is None:
                raise ValueError("Either provide embeddings or set embedding_model")
            embeddings = self.embedding_model.embed_texts(documents)
        
        # Generate IDs if not provided
        if ids is None:
            ids = [f"doc_{self._document_count + i}" for i in range(len(documents))]
        
        # Default metadata
        if metadata is None:
            metadata = [{} for _ in documents]
        
        # Add to appropriate backend
        if self.config.store_type == VectorStoreType.CHROMADB:
            self.store.add(
                documents=documents,
                embeddings=[emb.tolist() for emb in embeddings],
                metadatas=metadata,
                ids=ids
            )
        elif self.config.store_type == VectorStoreType.FAISS:
            # Add to FAISS index
            embeddings_array = np.array(embeddings).astype('float32')
            self.index.add(embeddings_array)
            
            # Store metadata separately
            for i, (doc_id, doc, meta) in enumerate(zip(ids, documents, metadata)):
                idx = self._document_count + i
                self.metadata_store[doc_id] = {
                    "document": doc,
                    "metadata": meta,
                    "index": idx
                }
                self.id_to_idx[doc_id] = idx
        else:  # MEMORY
            self.store["embeddings"].extend(embeddings)
            self.store["documents"].extend(documents)
            self.store["metadata"].extend(metadata)
            self.store["ids"].extend(ids)
        
        self._document_count += len(documents)
        
        if HAS_CPP_LOGGER:
            CPPLogger.debug(
                f"Added {len(documents)} documents (total: {self._document_count})",
                "VectorStore"
            )
        else:
            CPPLogger.debug(f"Added {len(documents)} documents (total: {self._document_count})")
        
        return ids
    
    def search(
        self,
        query: Union[str, np.ndarray],
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents.
        
        Args:
            query: Query text or embedding vector
            k: Number of results to return
            filter_metadata: Optional metadata filters
            
        Returns:
            List of results with documents, scores, and metadata
        """
        # Get query embedding
        if isinstance(query, str):
            if self.embedding_model is None:
                raise ValueError("embedding_model required for text queries")
            query_embedding = self.embedding_model.embed_text(query)
        else:
            query_embedding = query
        
        # Search in appropriate backend
        if self.config.store_type == VectorStoreType.CHROMADB:
            results = self.store.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=k,
                where=filter_metadata
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results["ids"][0])):
                formatted_results.append({
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "score": 1 - results["distances"][0][i],  # Convert distance to similarity
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {}
                })
            
            return formatted_results
            
        elif self.config.store_type == VectorStoreType.FAISS:
            # Search FAISS index
            query_vec = query_embedding.reshape(1, -1).astype('float32')
            distances, indices = self.index.search(query_vec, k)
            
            # Format results with metadata
            formatted_results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx == -1:  # FAISS returns -1 for missing results
                    continue
                
                # Find document by index
                doc_id = None
                for did, meta in self.metadata_store.items():
                    if meta["index"] == idx:
                        doc_id = did
                        break
                
                if doc_id:
                    meta_info = self.metadata_store[doc_id]
                    
                    # Apply metadata filter if specified
                    if filter_metadata:
                        if not all(
                            meta_info["metadata"].get(k) == v
                            for k, v in filter_metadata.items()
                        ):
                            continue
                    
                    formatted_results.append({
                        "id": doc_id,
                        "document": meta_info["document"],
                        "score": float(dist),
                        "metadata": meta_info["metadata"]
                    })
            
            return formatted_results
            
        else:  # MEMORY
            # Simple brute-force search
            embeddings = np.array(self.store["embeddings"])
            if len(embeddings) == 0:
                return []
            
            # Compute similarities
            similarities = np.dot(embeddings, query_embedding)
            top_k_indices = np.argsort(similarities)[-k:][::-1]
            
            formatted_results = []
            for idx in top_k_indices:
                # Apply metadata filter if specified
                if filter_metadata:
                    if not all(
                        self.store["metadata"][idx].get(k) == v
                        for k, v in filter_metadata.items()
                    ):
                        continue
                
                formatted_results.append({
                    "id": self.store["ids"][idx],
                    "document": self.store["documents"][idx],
                    "score": float(similarities[idx]),
                    "metadata": self.store["metadata"][idx]
                })
            
            return formatted_results
    
    def delete(self, ids: List[str]) -> None:
        """Delete documents by ID."""
        if self.config.store_type == VectorStoreType.CHROMADB:
            self.store.delete(ids=ids)
        elif self.config.store_type == VectorStoreType.FAISS:
            # FAISS doesn't support deletion, remove from metadata
            for doc_id in ids:
                if doc_id in self.metadata_store:
                    del self.metadata_store[doc_id]
                if doc_id in self.id_to_idx:
                    del self.id_to_idx[doc_id]
        else:  # MEMORY
            for doc_id in ids:
                if doc_id in self.store["ids"]:
                    idx = self.store["ids"].index(doc_id)
                    del self.store["ids"][idx]
                    del self.store["documents"][idx]
                    del self.store["metadata"][idx]
                    del self.store["embeddings"][idx]
        
        self._document_count = max(0, self._document_count - len(ids))
    
    def persist(self) -> None:
        """Persist vector store to disk."""
        if not self.config.persist_directory:
            if HAS_CPP_LOGGER:
                CPPLogger.warning("No persist_directory configured", "VectorStore")
            else:
                CPPLogger.warning("No persist_directory configured")
            return
        
        self.config.persist_directory.mkdir(parents=True, exist_ok=True)
        
        if self.config.store_type == VectorStoreType.FAISS:
            import faiss
            
            index_path = self.config.persist_directory / "faiss.index"
            metadata_path = self.config.persist_directory / "metadata.npy"
            
            faiss.write_index(self.index, str(index_path))
            np.save(str(metadata_path), self.metadata_store)
            
            if HAS_CPP_LOGGER:
                CPPLogger.info(f"Persisted FAISS index to {index_path}", "VectorStore")
            else:
                CPPLogger.info(f"Persisted FAISS index to {index_path}")
        
        # ChromaDB auto-persists if using PersistentClient
    
    def count(self) -> int:
        """Get total number of documents."""
        return self._document_count
    
    def __repr__(self) -> str:
        """String representation."""
        return (
            f"VectorStore(type={self.config.store_type.value}, "
            f"collection={self.config.collection_name}, docs={self._document_count})"
        )
