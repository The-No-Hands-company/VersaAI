"""
VersaAI RAG (Retrieval-Augmented Generation) Infrastructure.

Production-grade RAG components:
- Vector stores (ChromaDB, FAISS)
- Query decomposition
- Retrieval strategies
- Planner & Critic agents
- Complete RAG pipeline
"""

from versaai.rag.embeddings import EmbeddingModel, EmbeddingConfig
from versaai.rag.vector_store import VectorStore, VectorStoreConfig, VectorStoreType
from versaai.rag.query_decomposer import (
    QueryDecomposer,
    DecompositionResult,
    SubQuery,
    QueryType
)
from versaai.rag.planner import (
    PlannerAgent,
    Plan,
    PlanStep,
    StepType,
    StepStatus
)
from versaai.rag.critic import (
    CriticAgent,
    Critique,
    CriticConfig,
    CriticDimension,
    CriticSeverity,
    CriticIssue,
    DimensionScore
)
from versaai.rag.retriever import (
    AdaptiveRetriever,
    RetrieverConfig,
    RetrievalStrategy,
    RerankMethod,
    RetrievalResult
)
from versaai.rag.pipeline import (
    RAGPipeline,
    RAGConfig,
    RAGResult,
    PipelineStage
)

__all__ = [
    # Embeddings
    "EmbeddingModel",
    "EmbeddingConfig",
    
    # Vector Store
    "VectorStore",
    "VectorStoreConfig",
    "VectorStoreType",
    
    # Query Decomposer
    "QueryDecomposer",
    "DecompositionResult",
    "SubQuery",
    "QueryType",
    
    # Planner
    "PlannerAgent",
    "Plan",
    "PlanStep",
    "StepType",
    "StepStatus",
    
    # Critic
    "CriticAgent",
    "Critique",
    "CriticConfig",
    "CriticDimension",
    "CriticSeverity",
    "CriticIssue",
    "DimensionScore",
    
    # Retriever
    "AdaptiveRetriever",
    "RetrieverConfig",
    "RetrievalStrategy",
    "RerankMethod",
    "RetrievalResult",
    
    # Pipeline
    "RAGPipeline",
    "RAGConfig",
    "RAGResult",
    "PipelineStage",
]
