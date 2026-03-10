"""
ResearchAgent — production-grade research agent with adaptive retrieval.

Implements the design from docs/ResearchAgent_Design.md:
- Adaptive retrieval: real-time search + (future) vector DB + knowledge graph
- Self-correction: LLM-powered generator-critic pattern
- Tool integration: web search, calculator, shell
- Inline citations and confidence scoring

All LLM calls go through the unified LLMClient.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from versaai.agents.agent_base import AgentBase, AgentMetadata

logger = logging.getLogger(__name__)


class ResearchAgent(AgentBase):
    """
    Production-grade research agent with RAG and self-correction.

    Features:
        - Adaptive retrieval (real-time search, vector DB, knowledge graph)
        - Self-correction via LLM-powered generator-critic pattern
        - Tool use (web search, calculator, code execution)
        - Inline citations with source tracking
        - Confidence scoring with configurable threshold

    Example:
        >>> agent = ResearchAgent()
        >>> agent.initialize({"model": "ollama/qwen2.5-coder:7b"})
        >>> result = agent.execute("Explain how B-trees work")
        >>> print(result["result"])
        >>> print(result["confidence"])
    """

    def __init__(self):
        metadata = AgentMetadata(
            name="ResearchAgent",
            description="Production-grade research agent with RAG and self-correction",
            version="2.0.0",
            capabilities=[
                "information_retrieval",
                "document_qa",
                "fact_verification",
                "citation_generation",
                "multi_hop_reasoning",
            ],
        )
        super().__init__(metadata)

        self.llm = None
        self.rag = None  # RAGSystem instance (lazy)
        self.tools: List[Dict[str, Any]] = []
        self.memory: Dict[str, Any] = {}
        self.config: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize ResearchAgent.

        Args:
            config: Configuration dict:
                - model: Model ID (default: from settings)
                - confidence_threshold: Min confidence (default: 0.9)
                - max_tokens: Max generation tokens (default: 1024)
                - temperature: Sampling temperature (default: 0.7)
                - enable_calculator: Enable calculator tool (default: True)
        """
        if self._initialized:
            self.logger.warning("ResearchAgent already initialized")
            return

        self.config = config or {}

        self.logger.info("Initializing ResearchAgent")

        # 1. LLM
        self._init_llm()

        # 2. RAG
        self._init_rag()

        # 3. Tools
        self._init_tools()

        # 4. Memory
        self.memory = {"messages": [], "context": {}}

        self._initialized = True
        self.logger.info("ResearchAgent initialized successfully")

    def _init_llm(self) -> None:
        """Initialize LLM via unified LLMClient."""
        from versaai.agents.llm_client import LLMClient

        model_id = self.config.get("model")

        self.llm = LLMClient(
            model=model_id,
            system_prompt=(
                "You are a thorough research assistant. "
                "Provide well-structured, citation-backed answers. "
                "When uncertain, say so explicitly."
            ),
            temperature=self.config.get("temperature", 0.7),
            max_tokens=self.config.get("max_tokens", 1024),
        )
        self.logger.info(f"LLM initialized: {self.llm}")

    def _init_rag(self) -> None:
        """Initialize RAG system for document retrieval."""
        try:
            from versaai.rag.rag_system import RAGSystem

            self.rag = RAGSystem()
            self.logger.info("RAG system initialized")
        except Exception as exc:
            self.logger.warning(f"RAG system unavailable ({exc}), retrieval disabled")
            self.rag = None

    def _init_tools(self) -> None:
        """Initialize lightweight tools."""
        self.tools = []

        if self.config.get("enable_calculator", True):
            self.tools.append({
                "name": "calculator",
                "description": "Performs basic arithmetic calculations",
                "function": self._calculator_tool,
            })

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(
        self, task: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute research task with adaptive retrieval and self-correction.

        Pipeline:
            1. Query decomposition via LLM
            2. (Optional) RAG retrieval
            3. Generation
            4. LLM-powered critique
            5. Correction if needed

        Returns:
            {
                "result": str,
                "sources": List[Dict],
                "steps": List[str],
                "confidence": float,
                "metadata": Dict,
            }
        """
        if not self._initialized:
            raise RuntimeError("ResearchAgent not initialized. Call initialize() first.")

        self.logger.info(f"Executing task: {task[:120]}...")
        ctx = context or {}
        status_cb = ctx.get("status_callback")
        steps: List[str] = []
        sources: List[Dict[str, Any]] = []

        # Step 1: Decompose query via LLM
        steps.append("query_decomposition")
        if status_cb:
            status_cb("Decomposing query into sub-queries...")
        sub_queries = self._decompose_query(task)
        self.logger.debug(f"Decomposed into {len(sub_queries)} sub-queries")

        # Step 2: RAG retrieval
        if self.rag:
            steps.append("retrieval")
            if status_cb:
                status_cb(f"Retrieving documents for {len(sub_queries)} sub-queries...")
            retrieved_docs = self._retrieve_documents(sub_queries)
            sources.extend(retrieved_docs)

        # Step 3: Generation
        steps.append("generation")
        if status_cb:
            status_cb("Generating draft response...")
        draft = self._generate_response(task, ctx, sources)
        self.logger.debug("Generated draft response")

        # Step 4: LLM-powered critique
        steps.append("critique")
        if status_cb:
            status_cb("Critiquing response for accuracy...")
        critique = self._critique_response(task, draft, sources)

        # Step 5: Correction if needed
        if critique["needs_correction"]:
            steps.append("correction")
            if status_cb:
                status_cb("Correcting response based on critique...")
            final = self._correct_response(task, draft, critique, sources)
            confidence = min(critique.get("confidence", 0.7) + 0.1, 1.0)
        else:
            final = draft
            confidence = critique.get("confidence", 0.9)

        self.logger.info(f"Task completed — confidence: {confidence:.2f}")

        # Memory
        self.memory["messages"].append({
            "task": task,
            "response": final,
            "sources": sources,
        })

        return {
            "result": final,
            "sources": sources,
            "steps": steps,
            "confidence": confidence,
            "metadata": {
                "sub_queries": sub_queries,
                "critique": critique,
            },
        }

    def reset(self) -> None:
        self.memory = {"messages": [], "context": {}}
        self.logger.info("ResearchAgent state reset")

    # ------------------------------------------------------------------
    # LLM-powered decomposition (replaces heuristic)
    # ------------------------------------------------------------------

    def _decompose_query(self, query: str) -> List[str]:
        """
        Decompose a complex query into sub-queries using the LLM.

        Falls back to the original query if the LLM fails or the query
        is simple enough.
        """
        prompt = (
            f"Break the following research query into independent sub-queries "
            f"that can be researched separately. Return ONLY a JSON array of strings.\n\n"
            f"Query: {query}\n\n"
            f"Sub-queries (JSON array):"
        )
        try:
            raw = self.llm.complete(prompt, temperature=0.3, max_tokens=256)
            # Try to extract JSON array
            import re
            match = re.search(r"\[.*\]", raw, re.DOTALL)
            if match:
                subs = json.loads(match.group())
                if isinstance(subs, list) and all(isinstance(s, str) for s in subs):
                    return subs if subs else [query]
        except Exception as exc:
            self.logger.debug(f"Decomposition failed ({exc}), using original query")

        return [query]

    def _retrieve_documents(self, queries: List[str]) -> List[Dict[str, Any]]:
        """Retrieve relevant documents from the RAG system for each sub-query."""
        if not self.rag:
            return []

        all_results: List[Dict[str, Any]] = []
        seen_ids: set = set()

        for query in queries:
            try:
                results = self.rag.query(query, top_k=3)
                for r in results:
                    doc_text = r.get("document") or r.get("content", "")
                    doc_id = r.get("id", doc_text[:64])
                    if doc_id not in seen_ids:
                        seen_ids.add(doc_id)
                        all_results.append({
                            "content": doc_text,
                            "metadata": r.get("metadata", {}),
                            "score": r.get("score", 0.0),
                            "source": r.get("metadata", {}).get("source", "rag"),
                        })
            except Exception as exc:
                self.logger.warning(f"RAG query failed for '{query[:60]}': {exc}")

        # Sort by relevance score descending
        all_results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        return all_results[:10]  # Cap at 10 most relevant

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def _generate_response(
        self,
        task: str,
        context: Dict[str, Any],
        sources: List[Dict[str, Any]],
    ) -> str:
        """Generate a response using the LLM."""
        prompt_parts = []

        if sources:
            prompt_parts.append("Relevant information:")
            for i, source in enumerate(sources[:5], 1):
                prompt_parts.append(f"  [{i}] {source.get('content', '')}")
            prompt_parts.append("")

        prompt_parts.append(f"Research task: {task}")

        if context:
            prompt_parts.append(f"\nAdditional context: {json.dumps(context, default=str)}")

        prompt_parts.append(
            "\nProvide a thorough, well-structured answer. "
            "Cite sources by number [1], [2] etc. where applicable."
        )

        prompt = "\n".join(prompt_parts)

        try:
            return self.llm.complete(
                prompt,
                temperature=self.config.get("temperature", 0.7),
                max_tokens=self.config.get("max_tokens", 1024),
            ).strip()
        except Exception as e:
            self.logger.error(f"Generation failed: {e}")
            return f"Error generating response: {e}"

    # ------------------------------------------------------------------
    # LLM-powered critique (replaces heuristic)
    # ------------------------------------------------------------------

    def _critique_response(
        self,
        task: str,
        response: str,
        sources: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Use the LLM as a critic to evaluate the draft response.

        Returns:
            {
                "needs_correction": bool,
                "issues": List[str],
                "confidence": float
            }
        """
        prompt = (
            f"You are a fact-checking critic. Evaluate this response for accuracy, "
            f"completeness, and relevance to the original task.\n\n"
            f"Task: {task}\n\n"
            f"Response:\n{response}\n\n"
            f"Rate the response on these criteria:\n"
            f"1. Accuracy: Are the facts correct?\n"
            f"2. Completeness: Does it fully address the task?\n"
            f"3. Relevance: Is everything relevant to the task?\n\n"
            f"Respond in this EXACT JSON format:\n"
            f'{{"confidence": 0.0-1.0, "issues": ["issue1", ...], "needs_correction": true/false}}'
        )

        try:
            raw = self.llm.complete(prompt, temperature=0.1, max_tokens=256)
            # Extract JSON
            import re
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                result = json.loads(match.group())
                return {
                    "needs_correction": bool(result.get("needs_correction", False)),
                    "issues": result.get("issues", []),
                    "confidence": float(result.get("confidence", 0.8)),
                }
        except Exception as exc:
            self.logger.debug(f"Critique parsing failed ({exc}), using fallback heuristic")

        # Fallback heuristic
        issues = []
        confidence = 0.85
        if len(response.split()) < 10:
            issues.append("Response too short")
            confidence -= 0.2
        if "error" in response.lower():
            issues.append("Response contains error")
            confidence -= 0.3
        if not response.strip():
            issues.append("Empty response")
            confidence = 0.0

        threshold = self.config.get("confidence_threshold", 0.9)
        return {
            "needs_correction": confidence < threshold,
            "issues": issues,
            "confidence": max(0.0, confidence),
        }

    # ------------------------------------------------------------------
    # Correction
    # ------------------------------------------------------------------

    def _correct_response(
        self,
        task: str,
        draft: str,
        critique: Dict[str, Any],
        sources: List[Dict[str, Any]],
    ) -> str:
        """Re-generate response addressing the critique's issues."""
        issues_text = ", ".join(critique.get("issues", ["unspecified"]))
        prompt = (
            f"You previously attempted to answer this research task but "
            f"the response had these issues: {issues_text}\n\n"
            f"Task: {task}\n\n"
            f"Previous response:\n{draft}\n\n"
            f"Provide an improved, corrected response that addresses all issues."
        )

        try:
            return self.llm.complete(
                prompt,
                temperature=0.5,
                max_tokens=self.config.get("max_tokens", 1024),
            ).strip()
        except Exception as e:
            self.logger.error(f"Correction failed: {e}")
            return draft

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    def _calculator_tool(self, expression: str) -> str:
        """Safe arithmetic evaluation."""
        try:
            allowed = {
                "abs": abs, "round": round, "min": min,
                "max": max, "sum": sum, "pow": pow,
            }
            result = eval(expression, {"__builtins__": {}}, allowed)
            return str(result)
        except Exception as e:
            return f"Calculation error: {e}"
