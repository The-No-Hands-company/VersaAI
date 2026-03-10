"""
PlanningAgent — AgentBase-compliant wrapper around PlanningSystem.

Provides LLM-powered goal decomposition, task dependency resolution, and
execution scheduling through the standard agent ``initialize()`` /
``execute()`` / ``reset()`` contract.

Example:
    >>> from versaai.agents.planning_agent import PlanningAgent
    >>> agent = PlanningAgent()
    >>> agent.initialize({"model": "ollama/qwen2.5-coder:7b"})
    >>> result = agent.execute("Build a REST API with user authentication")
    >>> print(result["result"])
    >>> for task in result["metadata"]["tasks"]:
    ...     print(f"  {task['name']}: {task['description']}")
"""

import logging
import os
from typing import Any, Dict, List, Optional

from versaai.agents.agent_base import AgentBase, AgentMetadata

logger = logging.getLogger(__name__)


class PlanningAgent(AgentBase):
    """
    Agent wrapping PlanningSystem for intelligent task decomposition.

    Capabilities:
    - LLM-powered goal decomposition with heuristic fallback
    - Dependency resolution and cycle detection
    - Priority-based execution scheduling
    - Plan execution tracking with progress reporting
    """

    def __init__(self):
        metadata = AgentMetadata(
            name="PlanningAgent",
            description="LLM-powered goal decomposition, dependency resolution, and task scheduling",
            version="2.0.0",
            capabilities=[
                "goal_decomposition",
                "dependency_resolution",
                "execution_scheduling",
                "progress_tracking",
            ],
        )
        super().__init__(metadata)

        self.planner = None
        self.active_plans: Dict[str, Any] = {}  # plan_id → ExecutionPlan
        self.memory: Dict[str, Any] = {}
        self.config: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the planning agent.

        Args:
            config: Configuration dict:
                - model: Model ID (default: from settings)
                - max_depth: Maximum decomposition depth (default: 5)
                - temperature: Sampling temperature (default: 0.4)
                - enable_optimization: Optimize task ordering (default: True)
        """
        if self._initialized:
            return

        self.config = config or {}

        self.logger.info(
            f"Initializing PlanningAgent "
            f"(model={self.config.get('model', 'default')})"
        )

        # 1. LLM
        llm = self._create_llm()

        # 2. Planner
        from versaai.agents.planning import PlanningSystem

        self.planner = PlanningSystem(
            llm_function=llm,
            max_depth=self.config.get("max_depth", 5),
            enable_optimization=self.config.get("enable_optimization", True),
        )

        # 3. Memory
        self.memory = {"messages": [], "context": {}}

        self._initialized = True
        self.logger.info("PlanningAgent initialized successfully")

    def _create_llm(self):
        """Create LLMClient for the planning system."""
        from versaai.agents.llm_client import LLMClient

        return LLMClient(
            model=self.config.get("model"),
            system_prompt=(
                "You are a project planning assistant. "
                "Decompose goals into concrete, actionable tasks with clear dependencies."
            ),
            temperature=self.config.get("temperature", 0.4),
            max_tokens=self.config.get("max_tokens", 1024),
        )

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(
        self, task: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a planning task: decompose a goal into a structured plan.

        Args:
            task: Goal description to decompose.
            context: Optional context dict. May include:
                - constraints: Dict of planning constraints
                - action: "plan" (default) | "status" | "next_tasks"
                - plan_id: Reference an existing plan (for status/next_tasks)
                - status_callback: Callable for progress updates

        Returns:
            {
                "result": str (formatted plan summary),
                "steps": List[str] (pipeline stages executed),
                "confidence": float,
                "metadata": {
                    "plan_id": str,
                    "tasks": List[Dict],
                    "progress": Dict,
                    "total_estimated_duration": float,
                },
                "status": "success" | "error",
            }
        """
        if not self._initialized:
            raise RuntimeError("PlanningAgent not initialized. Call initialize() first.")

        ctx = context or {}
        action = ctx.get("action", "plan")
        status_cb = ctx.get("status_callback")

        try:
            if action == "status":
                return self._get_plan_status(ctx.get("plan_id"))
            elif action == "next_tasks":
                return self._get_next_tasks(ctx.get("plan_id"))
            else:
                return self._create_plan(task, ctx, status_cb)

        except Exception as exc:
            self.logger.error(f"Planning failed: {exc}", exc_info=True)
            return {
                "result": f"Planning error: {exc}",
                "steps": [],
                "confidence": 0.0,
                "metadata": {"error": str(exc)},
                "status": "error",
            }

    def _create_plan(
        self,
        goal: str,
        ctx: Dict[str, Any],
        status_cb=None,
    ) -> Dict[str, Any]:
        """Create a new execution plan for the given goal."""
        self.logger.info(f"Planning: {goal[:120]}...")

        if status_cb:
            status_cb({"type": "planning_start", "goal": goal[:120]})

        constraints = ctx.get("constraints", {})
        plan = self.planner.create_plan(
            goal=goal,
            context=ctx,
            constraints=constraints,
        )

        # Cache the plan for later status queries
        self.active_plans[plan.plan_id] = plan

        if status_cb:
            status_cb({
                "type": "planning_complete",
                "plan_id": plan.plan_id,
                "num_tasks": len(plan.tasks),
            })

        # Format plan as readable summary
        summary_lines = [f"## Plan: {goal}\n"]
        summary_lines.append(
            f"**{len(plan.tasks)} tasks** | "
            f"Est. {plan.total_estimated_duration:.1f}h total\n"
        )
        for i, t in enumerate(plan.tasks, 1):
            deps = f" (after: {', '.join(t.dependencies)})" if t.dependencies else ""
            summary_lines.append(
                f"{i}. **{t.name}** [{t.priority.name}]{deps}\n"
                f"   {t.description}"
            )

        summary = "\n".join(summary_lines)

        # Store in memory
        self.memory["messages"].append({"role": "user", "content": goal})
        self.memory["messages"].append({"role": "assistant", "content": summary})

        return {
            "result": summary,
            "steps": ["goal_decomposition", "dependency_resolution", "optimization"],
            "confidence": 0.85,
            "metadata": {
                "plan_id": plan.plan_id,
                "tasks": [t.to_dict() for t in plan.tasks],
                "progress": plan.get_progress(),
                "total_estimated_duration": plan.total_estimated_duration,
            },
            "status": "success",
        }

    def _get_plan_status(self, plan_id: Optional[str]) -> Dict[str, Any]:
        """Get status of an existing plan."""
        if not plan_id or plan_id not in self.active_plans:
            return {
                "result": f"Plan '{plan_id}' not found. Available: {list(self.active_plans.keys())}",
                "steps": [],
                "confidence": 1.0,
                "metadata": {},
                "status": "error",
            }

        plan = self.active_plans[plan_id]
        progress = plan.get_progress()

        return {
            "result": (
                f"Plan '{plan_id}': {progress['completed']}/{progress['total_tasks']} "
                f"completed ({progress['completion']:.0%}), "
                f"{progress['in_progress']} in progress, "
                f"{progress['failed']} failed"
            ),
            "steps": ["status_check"],
            "confidence": 1.0,
            "metadata": {
                "plan_id": plan_id,
                "progress": progress,
                "tasks": [t.to_dict() for t in plan.tasks],
            },
            "status": "success",
        }

    def _get_next_tasks(self, plan_id: Optional[str]) -> Dict[str, Any]:
        """Get the next executable tasks from a plan."""
        if not plan_id or plan_id not in self.active_plans:
            return {
                "result": f"Plan '{plan_id}' not found.",
                "steps": [],
                "confidence": 1.0,
                "metadata": {},
                "status": "error",
            }

        plan = self.active_plans[plan_id]
        ready = plan.get_next_tasks()

        if not ready:
            return {
                "result": "No tasks are ready to execute (all completed or blocked).",
                "steps": ["next_tasks_check"],
                "confidence": 1.0,
                "metadata": {"plan_id": plan_id},
                "status": "success",
            }

        lines = ["**Next executable tasks:**\n"]
        for t in ready:
            lines.append(f"- **{t.name}** [{t.priority.name}]: {t.description}")

        return {
            "result": "\n".join(lines),
            "steps": ["next_tasks_check"],
            "confidence": 1.0,
            "metadata": {
                "plan_id": plan_id,
                "next_tasks": [t.to_dict() for t in ready],
            },
            "status": "success",
        }

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        self.memory = {"messages": [], "context": {}}
        self.active_plans.clear()
        self.logger.info("PlanningAgent state reset")
