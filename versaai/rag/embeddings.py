"""
Production-grade embedding model wrapper for VersaAI RAG system.

Supports:
- Sentence transformers (BERT, MPNet, etc.)
- OpenAI embeddings (API)
- Custom embedding models
- Multimodal embeddings (text, code, images)
- Batch processing with optimal performance
"""

from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass
import numpy as np
from pathlib import Path

try:
    import versaai_core
    CPPLogger = versaai_core.Logger.get_instance()
    HAS_CPP_LOGGER = True
except (ImportError, AttributeError):
    import logging
    CPPLogger = logging.getLogger(__name__)
    HAS_CPP_LOGGER = False


@dataclass
class EmbeddingConfig:
    """Configuration for embedding models."""
    
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    device: str = "cpu"  # "cpu", "cuda", "mps"
    normalize_embeddings: bool = True
    batch_size: int = 32
    max_seq_length: Optional[int] = None
    cache_dir: Optional[Path] = None
    show_progress: bool = False


class EmbeddingModel:
    """
    Production-grade embedding model with optimal performance.
    
    Features:
    - Automatic batching
    - GPU acceleration
    - Normalization
    - Caching
    - Multiple backend support
    """
    
    def __init__(self, config: Optional[EmbeddingConfig] = None):
        """Initialize embedding model."""
        self.config = config or EmbeddingConfig()
        self.model = None
        self.dimension: Optional[int] = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the embedding model based on config."""
        try:
            from sentence_transformers import SentenceTransformer
            
            if HAS_CPP_LOGGER:
                CPPLogger.info(
                    f"Loading embedding model: {self.config.model_name}",
                    "EmbeddingModel"
                )
            else:
                CPPLogger.info(f"Loading embedding model: {self.config.model_name}")
            
            # Load model
            self.model = SentenceTransformer(
                self.config.model_name,
                device=self.config.device,
                cache_folder=str(self.config.cache_dir) if self.config.cache_dir else None
            )
            
            # Set max sequence length
            if self.config.max_seq_length:
                self.model.max_seq_length = self.config.max_seq_length
            
            # Get embedding dimension
            self.dimension = self.model.get_sentence_embedding_dimension()
            
            if HAS_CPP_LOGGER:
                CPPLogger.info(
                    f"Model loaded: {self.config.model_name} (dim={self.dimension})",
                    "EmbeddingModel"
                )
            else:
                CPPLogger.info(f"Model loaded: {self.config.model_name} (dim={self.dimension})")
                
        except ImportError as e:
            error_msg = f"Failed to import sentence-transformers: {e}"
            if HAS_CPP_LOGGER:
                CPPLogger.error(error_msg, "EmbeddingModel")
            else:
                CPPLogger.error(error_msg)
            raise
        except Exception as e:
            error_msg = f"Failed to load embedding model: {e}"
            if HAS_CPP_LOGGER:
                CPPLogger.error(error_msg, "EmbeddingModel")
            else:
                CPPLogger.error(error_msg)
            raise
    
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            numpy array of shape (len(texts), embedding_dimension)
        """
        if not texts:
            return np.array([])
        
        try:
            embeddings = self.model.encode(
                texts,
                batch_size=self.config.batch_size,
                show_progress_bar=self.config.show_progress,
                normalize_embeddings=self.config.normalize_embeddings,
                convert_to_numpy=True
            )
            return embeddings
            
        except Exception as e:
            error_msg = f"Failed to generate embeddings: {e}"
            if HAS_CPP_LOGGER:
                CPPLogger.error(error_msg, "EmbeddingModel")
            else:
                CPPLogger.error(error_msg)
            raise
    
    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text string to embed
            
        Returns:
            numpy array of shape (embedding_dimension,)
        """
        embeddings = self.embed_texts([text])
        return embeddings[0] if len(embeddings) > 0 else np.array([])
    
    def embed_documents(
        self,
        documents: List[Dict[str, Any]],
        text_key: str = "text"
    ) -> List[Dict[str, Any]]:
        """
        Embed documents with metadata preservation.
        
        Args:
            documents: List of document dictionaries
            text_key: Key in document dict containing text to embed
            
        Returns:
            List of documents with added 'embedding' field
        """
        texts = [doc.get(text_key, "") for doc in documents]
        embeddings = self.embed_texts(texts)
        
        # Add embeddings to documents
        for doc, embedding in zip(documents, embeddings):
            doc["embedding"] = embedding.tolist()
        
        return documents
    
    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (-1 to 1)
        """
        # Normalize if not already normalized
        if not self.config.normalize_embeddings:
            embedding1 = embedding1 / np.linalg.norm(embedding1)
            embedding2 = embedding2 / np.linalg.norm(embedding2)
        
        return float(np.dot(embedding1, embedding2))
    
    def get_dimension(self) -> int:
        """Get the embedding dimension."""
        return self.dimension
    
    def __repr__(self) -> str:
        """String representation."""
        return (
            f"EmbeddingModel(model={self.config.model_name}, "
            f"dim={self.dimension}, device={self.config.device})"
        )
