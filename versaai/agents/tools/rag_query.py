"""
RAGQueryTool — allows agents to autonomously query the RAG knowledge base.

The tool wraps RAGSystem.query() behind the standard Tool interface so that
ReAct-style agents can retrieve relevant documents during their reasoning loop.

Results are returned as numbered excerpts with metadata (source, relevance score)
so the agent can cite and reason over them.
"""

import logging
from typing import Any, Dict, Optional

from versaai.agents.tools.base import SafetyLevel, Tool, ToolResult

logger = logging.getLogger(__name__)


class RAGQueryTool(Tool):
    """
    Agent tool that queries the VersaAI RAG knowledge base.

    Usage in a ReAct loop::

        Action: rag_query
        Action Input: {"query": "How does the event loop work?", "top_k": 5}

    The tool returns the top-k most relevant document chunks with
    their relevance scores, allowing the agent to ground its answers
    in ingested documentation.
    """

    def __init__(self, rag_system: Optional[Any] = None):
        """
        Args:
            rag_system: A pre-initialized RAGSystem instance. If None, the tool
                        will attempt lazy initialization on first use.
        """
        self._rag = rag_system

    # ------------------------------------------------------------------
    # Tool interface
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "rag_query"

    @property
    def description(self) -> str:
        return (
            "Search the knowledge base for documents relevant to a query. "
            "Returns ranked excerpts with source metadata and relevance scores."
        )

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to find relevant documents.",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return (default: 5, max: 20).",
                },
            },
            "required": ["query"],
        }

    @property
    def safety_level(self) -> SafetyLevel:
        return SafetyLevel.READ_ONLY

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        top_k = min(int(kwargs.get("top_k", 5)), 20)

        if not query.strip():
            return ToolResult(
                success=False,
                output="",
                error="Query must be a non-empty string.",
            )

        rag = self._get_rag()
        if rag is None:
            return ToolResult(
                success=False,
                output="",
                error="RAG system is not available. Ingest documents first.",
            )

        try:
            results = rag.query(query, top_k=top_k)
        except Exception as exc:
            logger.error("RAG query failed: %s", exc, exc_info=True)
            return ToolResult(
                success=False,
                output="",
                error=f"RAG query error: {exc}",
            )

        if not results:
            return ToolResult(
                success=True,
                output="No relevant documents found.",
                metadata={"result_count": 0},
            )

        lines = [f"Found {len(results)} relevant document(s):\n"]
        for i, r in enumerate(results, 1):
            doc = r.get("document", r.get("content", ""))
            score = r.get("score", 0.0)
            source = r.get("metadata", {}).get("source", "unknown")
            # Truncate long chunks to keep the observation manageable
            if len(doc) > 600:
                doc = doc[:600] + "…"
            lines.append(f"[{i}] (score={score:.3f}, source={source})")
            lines.append(f"    {doc}\n")

        output = "\n".join(lines)
        return ToolResult(
            success=True,
            output=output,
            metadata={"result_count": len(results)},
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_rag(self) -> Optional[Any]:
        """Return the RAG system, attempting lazy init if needed."""
        if self._rag is not None:
            return self._rag

        try:
            from versaai.rag.rag_system import RAGSystem
            self._rag = RAGSystem()
            logger.info("RAGQueryTool: lazily initialized RAGSystem")
            return self._rag
        except Exception as exc:
            logger.warning("RAGQueryTool: failed to initialize RAGSystem: %s", exc)
            return None
