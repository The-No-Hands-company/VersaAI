"""
Comprehensive test suite for RAG system components.

Tests:
- Unit tests for each component
- Integration tests for pipeline
- Benchmark tests for performance
- Quality evaluation tests
"""

import unittest
import time
import numpy as np
from pathlib import Path
from typing import List, Dict, Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from versaai.rag.embeddings import EmbeddingModel, EmbeddingConfig
from versaai.rag.vector_store import VectorStore, VectorStoreConfig, VectorStoreType
from versaai.rag.query_decomposer import QueryDecomposer, QueryType
from versaai.rag.planner import PlannerAgent, StepType
from versaai.rag.critic import CriticAgent, CriticConfig, CriticDimension, CriticSeverity
from versaai.rag.retriever import AdaptiveRetriever, RetrieverConfig, RetrievalStrategy, RerankMethod
from versaai.rag.pipeline import RAGPipeline, RAGConfig


class TestEmbeddings(unittest.TestCase):
    """Test embedding model."""

    @classmethod
    def setUpClass(cls):
        """Initialize embedding model once for all tests."""
        cls.embedding_model = EmbeddingModel(EmbeddingConfig(
            backend="hash",
            device="cpu"
        ))

    def test_embed_single_text(self):
        """Test single text embedding."""
        text = "This is a test sentence."
        embedding = self.embedding_model.embed_text(text)

        self.assertIsInstance(embedding, np.ndarray)
        self.assertEqual(len(embedding.shape), 1)
        self.assertEqual(embedding.shape[0], self.embedding_model.dimension)

    def test_embed_multiple_texts(self):
        """Test batch text embedding."""
        texts = [
            "First sentence.",
            "Second sentence.",
            "Third sentence."
        ]
        embeddings = self.embedding_model.embed_texts(texts)

        self.assertIsInstance(embeddings, np.ndarray)
        self.assertEqual(embeddings.shape[0], len(texts))
        self.assertEqual(embeddings.shape[1], self.embedding_model.dimension)

    def test_similarity(self):
        """Test similarity calculation with hash backend (non-semantic)."""
        text1 = "Machine learning is fascinating."
        text2 = "Artificial intelligence is interesting."
        text3 = "I like pizza."

        emb1 = self.embedding_model.embed_text(text1)
        emb2 = self.embedding_model.embed_text(text2)
        emb3 = self.embedding_model.embed_text(text3)

        sim_12 = self.embedding_model.similarity(emb1, emb2)
        sim_13 = self.embedding_model.similarity(emb1, emb3)

        # Hash backend: verify similarity returns valid float in [-1, 1]
        self.assertIsInstance(sim_12, float)
        self.assertGreaterEqual(sim_12, -1.0)
        self.assertLessEqual(sim_12, 1.0)
        self.assertIsInstance(sim_13, float)
        # Same text should have perfect similarity
        sim_11 = self.embedding_model.similarity(emb1, emb1)
        self.assertAlmostEqual(sim_11, 1.0, places=5)


class TestVectorStore(unittest.TestCase):
    """Test vector store."""

    def setUp(self):
        """Set up vector store for each test."""
        self.embedding_model = EmbeddingModel(EmbeddingConfig(backend="hash"))
        self.vector_store = VectorStore(
            VectorStoreConfig(store_type=VectorStoreType.MEMORY),
            self.embedding_model
        )

    def test_add_documents(self):
        """Test adding documents."""
        documents = [
            "Python is a programming language.",
            "Machine learning is a subset of AI.",
            "Deep learning uses neural networks."
        ]

        ids = self.vector_store.add_documents(documents)

        self.assertEqual(len(ids), len(documents))
        self.assertEqual(self.vector_store.count(), len(documents))

    def test_search(self):
        """Test similarity search."""
        documents = [
            "Python is great for data science.",
            "JavaScript is used for web development.",
            "Machine learning requires Python or R."
        ]

        self.vector_store.add_documents(documents)

        results = self.vector_store.search("Python programming", k=2)

        self.assertEqual(len(results), 2)
        self.assertTrue(all("score" in r for r in results))
        self.assertTrue(all("document" in r for r in results))
        self.assertTrue(all("id" in r for r in results))

    def test_metadata_filtering(self):
        """Test metadata-based filtering."""
        documents = ["Doc 1", "Doc 2", "Doc 3"]
        metadata = [
            {"category": "A"},
            {"category": "B"},
            {"category": "A"}
        ]

        self.vector_store.add_documents(documents, metadata=metadata)

        results = self.vector_store.search(
            "Doc",
            k=10,
            filter_metadata={"category": "A"}
        )

        # Should only return documents with category A
        self.assertEqual(len([r for r in results if r["metadata"].get("category") == "A"]), 2)


class TestQueryDecomposer(unittest.TestCase):
    """Test query decomposer."""

    def setUp(self):
        """Set up decomposer for each test."""
        self.decomposer = QueryDecomposer(use_llm=False)

    def test_simple_query(self):
        """Test simple query detection."""
        query = "What is Python?"
        result = self.decomposer.decompose(query)

        self.assertEqual(result.query_type, QueryType.SIMPLE)
        self.assertEqual(len(result.sub_queries), 1)

    def test_complex_query(self):
        """Test complex query decomposition."""
        query = "What is machine learning, and how is it different from deep learning?"
        result = self.decomposer.decompose(query)

        self.assertEqual(result.query_type, QueryType.COMPLEX)
        self.assertGreater(len(result.sub_queries), 1)

    def test_temporal_query(self):
        """Test temporal query detection."""
        query = "What happened in AI research in 2023?"
        result = self.decomposer.decompose(query)

        self.assertEqual(result.query_type, QueryType.TEMPORAL)
        self.assertIsNotNone(result.sub_queries[0].temporal_constraint)

    def test_comparative_query(self):
        """Test comparative query detection."""
        query = "Compare Python and JavaScript for web development."
        result = self.decomposer.decompose(query)

        self.assertEqual(result.query_type, QueryType.COMPARATIVE)


class TestPlanner(unittest.TestCase):
    """Test planner agent."""

    def setUp(self):
        """Set up planner for each test."""
        self.planner = PlannerAgent(use_llm=False)

    def test_plan_creation(self):
        """Test basic plan creation."""
        query = "What is machine learning?"
        plan = self.planner.create_plan(query)

        self.assertIsNotNone(plan)
        self.assertEqual(plan.query, query)
        self.assertGreater(len(plan.steps), 0)

    def test_plan_dependencies(self):
        """Test plan step dependencies."""
        query = "Explain neural networks."
        plan = self.planner.create_plan(query)

        # Check that dependencies are valid
        for step in plan.steps:
            for dep_id in step.dependencies:
                self.assertLess(dep_id, step.step_id)

    def test_execution_plan(self):
        """Test execution plan generation."""
        query = "What is AI?"
        plan = self.planner.create_plan(query)

        # First executable steps should have no blocking dependencies
        executable = plan.get_next_executable_steps()
        self.assertGreater(len(executable), 0)
        for step in executable:
            self.assertEqual(len(step.dependencies), 0)


class TestCritic(unittest.TestCase):
    """Test critic agent."""

    def setUp(self):
        """Set up critic for each test."""
        config = CriticConfig(
            use_llm=False,
            enabled_dimensions=list(CriticDimension)
        )
        self.critic = CriticAgent(config)

    def test_relevance_evaluation(self):
        """Test relevance scoring."""
        query = "What is Python?"
        answer = "Python is a high-level programming language known for its simplicity."
        docs = [{"document": "Python is a programming language."}]

        critique = self.critic.critique(query, answer, docs)

        # Should have high relevance
        relevance_score = next(
            (ds.score for ds in critique.dimension_scores
             if ds.dimension == CriticDimension.RELEVANCE),
            None
        )
        self.assertIsNotNone(relevance_score)
        self.assertGreater(relevance_score, 0.5)

    def test_factuality_evaluation(self):
        """Test factuality checking."""
        query = "What is the capital of France?"
        answer = "The capital of France is Paris."
        docs = [{"document": "Paris is the capital city of France."}]

        critique = self.critic.critique(query, answer, docs)

        # Should have high factuality
        factuality_score = next(
            (ds.score for ds in critique.dimension_scores
             if ds.dimension == CriticDimension.FACTUALITY),
            None
        )
        self.assertIsNotNone(factuality_score)
        self.assertGreater(factuality_score, 0.5)

    def test_hallucination_detection(self):
        """Test hallucination detection."""
        query = "What is AI?"
        answer = "AI was invented in 1492 by Christopher Columbus."  # Clearly false
        docs = [{"document": "AI emerged in the 1950s."}]

        critique = self.critic.critique(query, answer, docs)

        # Should detect hallucination
        hallucination_score = next(
            (ds.score for ds in critique.dimension_scores
             if ds.dimension == CriticDimension.HALLUCINATION),
            None
        )
        if hallucination_score is not None:
            # Should have issues with unsupported date
            self.assertLess(hallucination_score, 0.9)


class TestRetriever(unittest.TestCase):
    """Test adaptive retriever."""

    def setUp(self):
        """Set up retriever for each test."""
        self.embedding_model = EmbeddingModel(EmbeddingConfig(backend="hash"))
        self.vector_store = VectorStore(
            VectorStoreConfig(store_type=VectorStoreType.MEMORY),
            self.embedding_model
        )

        # Add test documents
        self.documents = [
            "Python is a versatile programming language.",
            "Machine learning is a branch of artificial intelligence.",
            "Deep learning uses neural networks with multiple layers.",
            "Natural language processing deals with text and language.",
            "Computer vision focuses on image understanding."
        ]
        self.vector_store.add_documents(self.documents)

        self.retriever = AdaptiveRetriever(
            self.vector_store,
            self.embedding_model,
            RetrieverConfig(
                strategy=RetrievalStrategy.DENSE,
                rerank_method=RerankMethod.NONE,
                use_mmr=False,
                use_query_expansion=False,
                use_compression=False,
            )
        )

    def test_dense_retrieval(self):
        """Test dense retrieval."""
        query = "What is machine learning?"
        result = self.retriever.retrieve(query, top_k=3)

        self.assertEqual(len(result.documents), 3)
        self.assertEqual(len(result.scores), 3)
        # Verify result structure
        for doc in result.documents:
            self.assertIn("document", doc)
            self.assertIn("id", doc)

    def test_retrieval_ranking(self):
        """Test that results are properly ranked."""
        query = "neural networks"
        result = self.retriever.retrieve(query, top_k=3)

        # Scores should be in descending order
        for i in range(len(result.scores) - 1):
            self.assertGreaterEqual(result.scores[i], result.scores[i + 1])


class TestRAGPipeline(unittest.TestCase):
    """Test complete RAG pipeline."""

    def setUp(self):
        """Set up pipeline for each test."""
        config = RAGConfig(
            embedding_config=EmbeddingConfig(backend="hash"),
            vector_store_config=VectorStoreConfig(store_type=VectorStoreType.MEMORY),
            enable_decomposition=True,
            enable_planning=True,
            enable_critique=True,
            enable_refinement=False  # Disable for testing without LLM
        )
        self.pipeline = RAGPipeline(config)

        # Add test documents
        documents = [
            "Python is a high-level programming language created by Guido van Rossum.",
            "Machine learning is a method of data analysis that automates analytical model building.",
            "Deep learning is part of machine learning based on artificial neural networks.",
            "Natural language processing (NLP) is a branch of AI that helps computers understand human language.",
            "TensorFlow is an open-source library for machine learning developed by Google."
        ]
        self.pipeline.add_documents(documents)

    def test_basic_query(self):
        """Test basic query processing."""
        query = "What is Python?"
        result = self.pipeline.query(query)

        self.assertIsNotNone(result)
        self.assertEqual(result.query, query)
        self.assertIsNotNone(result.answer)
        self.assertGreater(len(result.retrieved_documents), 0)

    def test_pipeline_stages(self):
        """Test that all stages are executed."""
        query = "What is machine learning?"
        result = self.pipeline.query(query)

        # Check stage times
        self.assertIn("retrieval", result.stage_times)
        self.assertIn("synthesis", result.stage_times)

    def test_caching(self):
        """Test result caching."""
        query = "What is deep learning?"

        # First query
        start1 = time.time()
        result1 = self.pipeline.query(query)
        time1 = time.time() - start1

        # Second query (should be cached)
        start2 = time.time()
        result2 = self.pipeline.query(query)
        time2 = time.time() - start2

        self.assertEqual(result1.answer, result2.answer)
        # Cached query should be faster
        self.assertLess(time2, time1)


class TestBenchmarks(unittest.TestCase):
    """Benchmark tests for performance evaluation."""

    @classmethod
    def setUpClass(cls):
        """Set up pipeline once for all benchmarks."""
        cls.pipeline = RAGPipeline(RAGConfig(
            embedding_config=EmbeddingConfig(backend="hash"),
            vector_store_config=VectorStoreConfig(store_type=VectorStoreType.MEMORY),
            enable_decomposition=False,  # Faster for benchmarks
            enable_planning=False,
            enable_critique=False
        ))

        # Add larger document set
        cls.num_docs = 100
        documents = [
            f"Document {i}: This is test document number {i} containing information about topic {i % 10}."
            for i in range(cls.num_docs)
        ]
        cls.pipeline.add_documents(documents)

    def test_embedding_performance(self):
        """Benchmark embedding generation."""
        texts = [f"Test sentence number {i}." for i in range(100)]

        start = time.time()
        embeddings = self.pipeline.embedding_model.embed_texts(texts)
        duration = time.time() - start

        throughput = len(texts) / duration
        print(f"\nEmbedding throughput: {throughput:.2f} texts/second")

        self.assertGreater(throughput, 10)  # At least 10 texts/second

    def test_retrieval_performance(self):
        """Benchmark retrieval speed."""
        queries = [f"Query about topic {i}" for i in range(20)]

        start = time.time()
        for query in queries:
            self.pipeline.retriever.retrieve(query, top_k=5)
        duration = time.time() - start

        avg_latency = duration / len(queries)
        print(f"\nAverage retrieval latency: {avg_latency*1000:.2f} ms")

        self.assertLess(avg_latency, 1.0)  # Less than 1 second per query

    def test_end_to_end_performance(self):
        """Benchmark complete pipeline."""
        queries = [
            "What is the information?",
            "Tell me about the topics.",
            "Explain the documents."
        ]

        results = []
        start = time.time()
        for query in queries:
            result = self.pipeline.query(query)
            results.append(result)
        duration = time.time() - start

        avg_time = duration / len(queries)
        print(f"\nAverage end-to-end time: {avg_time:.2f} seconds")

        # All queries should complete
        self.assertEqual(len(results), len(queries))
        self.assertLess(avg_time, 5.0)  # Less than 5 seconds per query


class TestQualityMetrics(unittest.TestCase):
    """Test quality evaluation metrics."""

    def setUp(self):
        """Set up for quality tests."""
        self.critic = CriticAgent(CriticConfig(
            enabled_dimensions=list(CriticDimension)
        ))

    def test_quality_scoring(self):
        """Test quality scoring."""
        # High quality answer
        good_query = "What is Python?"
        good_answer = "Python is a high-level, interpreted programming language known for its simplicity and readability."
        good_docs = [{"document": "Python is a programming language created by Guido van Rossum."}]

        good_critique = self.critic.critique(good_query, good_answer, good_docs)

        # Low quality answer
        bad_query = "What is Python?"
        bad_answer = "Something."
        bad_docs = good_docs

        bad_critique = self.critic.critique(bad_query, bad_answer, bad_docs)

        # Good answer should score higher
        self.assertGreater(good_critique.overall_score, bad_critique.overall_score)

    def test_issue_detection(self):
        """Test issue detection."""
        query = "What is machine learning?"
        answer = "Machine learning."  # Too brief
        docs = [{"document": "Machine learning is a field of study."}]

        critique = self.critic.critique(query, answer, docs)

        # Should detect completeness issue
        self.assertGreater(len(critique.issues), 0)

        # Should have recommendations
        self.assertGreater(len(critique.recommendations), 0)


def run_tests(verbosity=2):
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestEmbeddings))
    suite.addTests(loader.loadTestsFromTestCase(TestVectorStore))
    suite.addTests(loader.loadTestsFromTestCase(TestQueryDecomposer))
    suite.addTests(loader.loadTestsFromTestCase(TestPlanner))
    suite.addTests(loader.loadTestsFromTestCase(TestCritic))
    suite.addTests(loader.loadTestsFromTestCase(TestRetriever))
    suite.addTests(loader.loadTestsFromTestCase(TestRAGPipeline))
    suite.addTests(loader.loadTestsFromTestCase(TestBenchmarks))
    suite.addTests(loader.loadTestsFromTestCase(TestQualityMetrics))

    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)

    return result


if __name__ == "__main__":
    result = run_tests()

    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*70)
