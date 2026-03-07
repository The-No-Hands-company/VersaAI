#!/usr/bin/env python3
"""
Example usage of VersaAI RAG System.

Demonstrates:
- Basic pipeline setup
- Document ingestion
- Query processing
- Quality monitoring
- Advanced configuration
"""

from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from versaai.rag import (
    RAGPipeline,
    RAGConfig,
    EmbeddingConfig,
    VectorStoreConfig,
    VectorStoreType,
    RetrieverConfig,
    RetrievalStrategy,
    RerankMethod,
    CriticConfig,
    CriticDimension,
    PipelineStage
)


def basic_example():
    """Basic RAG pipeline usage."""
    print("\n" + "="*70)
    print("BASIC RAG PIPELINE EXAMPLE")
    print("="*70)
    
    # Initialize pipeline with default config
    pipeline = RAGPipeline()
    
    # Add knowledge base documents
    documents = [
        "Python is a high-level, interpreted programming language created by Guido van Rossum in 1991.",
        "Machine learning is a method of data analysis that automates analytical model building.",
        "Deep learning is part of a broader family of machine learning methods based on artificial neural networks.",
        "Natural language processing (NLP) is a subfield of AI that helps computers understand human language.",
        "TensorFlow is an open-source library for machine learning and deep learning developed by Google.",
        "PyTorch is another popular deep learning framework developed by Facebook's AI Research lab.",
        "Neural networks are computing systems inspired by biological neural networks in animal brains.",
        "Computer vision is a field of AI that trains computers to interpret and understand visual information.",
    ]
    
    print(f"\nAdding {len(documents)} documents to knowledge base...")
    pipeline.add_documents(documents)
    print(f"✓ Documents added successfully")
    
    # Query the system
    queries = [
        "What is Python?",
        "Explain machine learning and deep learning.",
        "What are popular deep learning frameworks?"
    ]
    
    print("\nProcessing queries...")
    print("-" * 70)
    
    for query in queries:
        result = pipeline.query(query)
        
        print(f"\nQuery: {query}")
        print(f"Answer: {result.answer}")
        print(f"Confidence: {result.confidence_score:.2f}")
        print(f"Execution time: {result.execution_time:.2f}s")
        print(f"Documents used: {len(result.retrieved_documents)}")
    
    # Show statistics
    stats = pipeline.get_stats()
    print("\n" + "-" * 70)
    print("PIPELINE STATISTICS")
    print("-" * 70)
    print(f"Total queries: {stats['total_queries']}")
    print(f"Successful: {stats['successful_queries']}")
    print(f"Average time: {stats['average_time']:.2f}s")
    print(f"Average score: {stats['average_score']:.2f}")


def advanced_example():
    """Advanced RAG pipeline with custom configuration."""
    print("\n" + "="*70)
    print("ADVANCED RAG PIPELINE EXAMPLE")
    print("="*70)
    
    # Custom configuration
    config = RAGConfig(
        # Embedding config
        embedding_config=EmbeddingConfig(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            device="cpu",
            batch_size=32
        ),
        
        # Vector store config
        vector_store_config=VectorStoreConfig(
            store_type=VectorStoreType.MEMORY,  # Use in-memory for example
            collection_name="advanced_demo"
        ),
        
        # Retriever config
        retriever_config=RetrieverConfig(
            strategy=RetrievalStrategy.HYBRID,
            top_k=10,
            rerank_top_k=5,
            rerank_method=RerankMethod.CROSS_ENCODER,
            use_mmr=True,
            mmr_lambda=0.7,  # Favor relevance over diversity
            use_compression=True
        ),
        
        # Critic config
        critic_config=CriticConfig(
            use_llm=False,
            enabled_dimensions=[
                CriticDimension.FACTUALITY,
                CriticDimension.RELEVANCE,
                CriticDimension.COMPLETENESS,
                CriticDimension.COHERENCE,
                CriticDimension.HALLUCINATION
            ],
            min_acceptable_score=0.75,
            check_citations=True
        ),
        
        # Pipeline behavior
        enable_decomposition=True,
        enable_planning=True,
        enable_critique=True,
        enable_refinement=False,  # Would need LLM for refinement
        
        # Quality & performance
        min_acceptable_score=0.7,
        cache_results=True
    )
    
    pipeline = RAGPipeline(config)
    
    # Add documents with metadata
    documents = [
        "Artificial Intelligence (AI) is the simulation of human intelligence by machines.",
        "Machine learning is a subset of AI that enables systems to learn from data.",
        "Deep learning uses neural networks with multiple layers to process complex patterns.",
        "Supervised learning requires labeled training data.",
        "Unsupervised learning finds patterns in unlabeled data.",
        "Reinforcement learning learns through trial and error with rewards.",
    ]
    
    metadata = [
        {"source": "AI Overview", "category": "fundamental"},
        {"source": "ML Basics", "category": "fundamental"},
        {"source": "Deep Learning Guide", "category": "advanced"},
        {"source": "ML Methods", "category": "techniques"},
        {"source": "ML Methods", "category": "techniques"},
        {"source": "ML Methods", "category": "techniques"},
    ]
    
    print(f"\nAdding {len(documents)} documents with metadata...")
    pipeline.add_documents(documents, metadata=metadata)
    print("✓ Documents indexed")
    
    # Define callbacks for monitoring
    def on_retrieval(result):
        print(f"  → Retrieved {len(result.documents)} docs using {result.strategy_used.value}")
    
    def on_critique(critique):
        print(f"  → Quality score: {critique.overall_score:.2f}")
        if critique.issues:
            print(f"  → Issues found: {len(critique.issues)}")
    
    callbacks = {
        PipelineStage.RETRIEVAL: on_retrieval,
        PipelineStage.CRITIQUE: on_critique
    }
    
    # Complex query
    query = "What is machine learning and what are its main types?"
    
    print(f"\nProcessing complex query with monitoring...")
    print(f"Query: {query}")
    print()
    
    result = pipeline.query(query, callbacks=callbacks)
    
    print("\n" + "-" * 70)
    print("RESULT")
    print("-" * 70)
    print(f"Answer: {result.answer}")
    print(f"\nConfidence: {result.confidence_score:.2f}")
    print(f"Execution time: {result.execution_time:.2f}s")
    
    # Show stage timing breakdown
    print("\nStage Timing:")
    for stage, time_taken in result.stage_times.items():
        print(f"  {stage}: {time_taken:.3f}s")
    
    # Show critique details
    if result.critique:
        print("\nQuality Assessment:")
        for dim_score in result.critique.dimension_scores:
            print(f"  {dim_score.dimension.value}: {dim_score.score:.2f}")
        
        if result.critique.issues:
            print(f"\nIssues ({len(result.critique.issues)}):")
            for issue in result.critique.issues[:3]:  # Show first 3
                print(f"  - [{issue.severity.value}] {issue.description}")


def component_example():
    """Example using individual RAG components."""
    print("\n" + "="*70)
    print("INDIVIDUAL COMPONENT EXAMPLES")
    print("="*70)
    
    from versaai.rag import (
        QueryDecomposer,
        PlannerAgent,
        CriticAgent
    )
    
    # Query Decomposer
    print("\n1. Query Decomposer")
    print("-" * 70)
    
    decomposer = QueryDecomposer(use_llm=False)
    
    queries_to_decompose = [
        "What is Python?",  # Simple
        "Compare Python and JavaScript for web development.",  # Comparative
        "What happened in AI research in 2023?"  # Temporal
    ]
    
    for query in queries_to_decompose:
        result = decomposer.decompose(query)
        print(f"\nQuery: {query}")
        print(f"Type: {result.query_type.value}")
        print(f"Complexity: {result.complexity_score:.2f}")
        print(f"Sub-queries: {len(result.sub_queries)}")
    
    # Planner Agent
    print("\n\n2. Planner Agent")
    print("-" * 70)
    
    planner = PlannerAgent(use_llm=False)
    plan = planner.create_plan("Explain neural networks and their applications")
    
    print(planner.visualize_plan(plan))
    
    # Critic Agent
    print("\n\n3. Critic Agent")
    print("-" * 70)
    
    critic = CriticAgent(CriticConfig(
        enabled_dimensions=list(CriticDimension)
    ))
    
    test_query = "What is machine learning?"
    test_answer = "Machine learning is a method that allows computers to learn from data without being explicitly programmed."
    test_docs = [
        {"document": "Machine learning is a subset of artificial intelligence."}
    ]
    
    critique = critic.critique(test_query, test_answer, test_docs)
    
    print(f"Query: {test_query}")
    print(f"Overall Score: {critique.overall_score:.2f}")
    print(f"\nDimension Scores:")
    for ds in critique.dimension_scores:
        print(f"  {ds.dimension.value}: {ds.score:.2f}")
    
    print(f"\nRecommendations:")
    for rec in critique.recommendations:
        print(f"  • {rec}")


def main():
    """Run all examples."""
    print("\n" + "="*70)
    print("VersaAI RAG SYSTEM - USAGE EXAMPLES")
    print("="*70)
    
    # Run examples
    basic_example()
    advanced_example()
    component_example()
    
    print("\n" + "="*70)
    print("EXAMPLES COMPLETE")
    print("="*70)
    print("\nFor more information, see versaai/rag/README.md")


if __name__ == "__main__":
    main()
