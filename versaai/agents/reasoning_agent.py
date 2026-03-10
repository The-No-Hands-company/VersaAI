"""
ReasoningAgent — AgentBase-compliant wrapper around ReasoningEngine.

Exposes Chain-of-Thought, ReAct, Tree-of-Thoughts, and Self-Consistency
reasoning strategies through the standard agent ``initialize()`` /
``execute()`` / ``reset()`` contract.

Example:
    >>> from versaai.agents.reasoning_agent import ReasoningAgent
    >>> agent = ReasoningAgent()
    >>> agent.initialize({"model": "ollama/qwen2.5-coder:7b", "strategy": "react"})
    >>> result = agent.execute("What files are in the src/ directory?")
    >>> print(result["result"])
"""

import logging
import os
from typing import Any, Dict, List, Optional

from versaai.agents.agent_base import AgentBase, AgentMetadata

logger = logging.getLogger(__name__)


class ReasoningAgent(AgentBase):
    """
    Agent wrapping ReasoningEngine for structured multi-step reasoning.

    Capabilities:
    - Chain-of-Thought (CoT) reasoning
    - ReAct (Reason + Act) with tool execution
    - Tree-of-Thoughts (parallel path exploration)
    - Self-Consistency (majority vote)
    - LLM-powered step verification
    """

    def __init__(self):
        metadata = AgentMetadata(
            name="ReasoningAgent",
            description="Advanced multi-strategy reasoning with CoT, ReAct, ToT, and Self-Consistency",
            version="2.0.0",
            capabilities=[
                "chain_of_thought",
                "react",
                "tree_of_thoughts",
                "self_consistency",
                "zero_shot",
            ],
        )
        super().__init__(metadata)

        self.engine = None
        self.tool_registry = None
        self.memory: Dict[str, Any] = {}
        self.config: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the reasoning agent.

        Args:
            config: Configuration dict:
                - model: Model ID (default: from settings)
                - strategy: Default strategy — cot|react|tot|self_consistency|zero_shot
                - max_steps: Maximum reasoning steps (default: 10)
                - temperature: Sampling temperature (default: 0.7)
                - enable_verification: Verify final answer via LLM (default: True)
                - work_dir: Working directory for tool access (default: cwd)
        """
        if self._initialized:
            return

        self.config = config or {}
        strategy = self.config.get("strategy", "cot")
        work_dir = self.config.get("work_dir", os.getcwd())

        self.logger.info(
            f"Initializing ReasoningAgent (strategy={strategy}, "
            f"model={self.config.get('model', 'default')})"
        )

        # 1. LLM
        llm = self._create_llm()

        # 2. Tools (for ReAct strategy)
        self._init_tools(work_dir)

        # 3. Engine
        from versaai.agents.reasoning import ReasoningEngine

        self.engine = ReasoningEngine(
            strategy=strategy,
            llm_function=llm,
            tool_registry=self.tool_registry,
            max_steps=self.config.get("max_steps", 10),
            enable_verification=self.config.get("enable_verification", True),
            temperature=self.config.get("temperature", 0.7),
        )

        # 4. Memory
        self.memory = {"messages": [], "context": {}}

        self._initialized = True
        self.logger.info("ReasoningAgent initialized successfully")

    def _create_llm(self):
        """Create LLMClient for the reasoning engine."""
        from versaai.agents.llm_client import LLMClient

        return LLMClient(
            model=self.config.get("model"),
            system_prompt=(
                "You are a systematic reasoning assistant. "
                "Think step by step, verify your reasoning, and provide clear answers."
            ),
            temperature=self.config.get("temperature", 0.7),
            max_tokens=self.config.get("max_tokens", 2048),
        )

    def _init_tools(self, work_dir: str) -> None:
        """Register tools for ReAct strategy."""
        try:
            from versaai.agents.tools import (
                FileReadTool,
                FileSearchTool,
                ShellTool,
                ToolRegistry,
            )

            self.tool_registry = ToolRegistry()
            self.tool_registry.register(FileReadTool(work_dir))
            self.tool_registry.register(FileSearchTool(work_dir))
            self.tool_registry.register(ShellTool(
                working_dir=work_dir,
                allowed_commands=self.config.get("allowed_commands"),
            ))
            self.logger.info(
                f"Tools registered: {list(self.tool_registry._tools.keys())}"
            )
        except Exception as exc:
            self.logger.warning(f"Tool initialization failed ({exc}), ReAct disabled")
            self.tool_registry = None

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(
        self, task: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a reasoning task.

        Args:
            task: Problem or question to reason about.
            context: Optional context dict. May include:
                - strategy: Override default strategy for this call
                - num_paths: For ToT, number of parallel paths (default 3)
                - num_samples: For self-consistency, sample count (default 5)
                - status_callback: Callable for progress updates

        Returns:
            {
                "result": str (final answer),
                "steps": List[Dict] (reasoning trace),
                "confidence": float,
                "verified": bool,
                "strategy_used": str,
                "execution_time": float,
                "metadata": Dict,
                "status": "success" | "error",
            }
        """
        if not self._initialized:
            raise RuntimeError("ReasoningAgent not initialized. Call initialize() first.")

        self.logger.info(f"Reasoning on: {task[:120]}...")
        ctx = context or {}
        status_cb = ctx.get("status_callback")

        strategy_override = ctx.get("strategy")

        try:
            if status_cb:
                status_cb({"type": "reasoning_start", "task": task[:120]})

            result = self.engine.reason(
                task=task,
                context=ctx,
                strategy=strategy_override,
            )

            if status_cb:
                status_cb({"type": "reasoning_complete", "confidence": result.confidence})

            # Store in memory
            self.memory["messages"].append({
                "role": "user",
                "content": task,
            })
            self.memory["messages"].append({
                "role": "assistant",
                "content": result.answer,
            })

            return {
                "result": result.answer,
                "steps": [s.to_dict() for s in result.steps],
                "confidence": result.confidence,
                "verified": result.verified,
                "strategy_used": result.strategy_used,
                "execution_time": result.execution_time,
                "metadata": result.metadata,
                "status": "success",
            }

        except Exception as exc:
            self.logger.error(f"Reasoning failed: {exc}", exc_info=True)
            return {
                "result": f"Reasoning error: {exc}",
                "steps": [],
                "confidence": 0.0,
                "verified": False,
                "strategy_used": strategy_override or self.config.get("strategy", "cot"),
                "execution_time": 0.0,
                "metadata": {"error": str(exc)},
                "status": "error",
            }

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        self.memory = {"messages": [], "context": {}}
        self.logger.info("ReasoningAgent state reset")
