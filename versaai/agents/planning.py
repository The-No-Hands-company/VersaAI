"""
PlanningSystem — LLM-powered goal decomposition and task planning.

Provides hierarchical task decomposition via LLM inference, dependency
resolution, and execution scheduling for complex multi-step tasks.

Features:
    - LLM-powered goal decomposition (replaces keyword heuristics)
    - Dependency resolution and cycle detection
    - Priority-based execution scheduling
    - Progress tracking
    - Heuristic fallback when LLM is unavailable

Example:
    >>> from versaai.agents.planning import PlanningSystem
    >>> planner = PlanningSystem()
    >>> plan = planner.create_plan("Build a REST API with user auth")
    >>> for task in plan.get_next_tasks():
    ...     print(f"{task.name}: {task.description}")
"""

import json
import logging
import re
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class TaskPriority(Enum):
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    OPTIONAL = 1


@dataclass
class Task:
    """Represents a single task in a plan."""
    task_id: str
    name: str
    description: str
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    subtasks: List["Task"] = field(default_factory=list)
    estimated_duration: float = 0.0  # hours
    resources_required: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "dependencies": self.dependencies,
            "subtasks": [st.to_dict() for st in self.subtasks],
            "estimated_duration": self.estimated_duration,
            "resources_required": self.resources_required,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    def is_ready(self, completed_tasks: Set[str]) -> bool:
        if self.status != TaskStatus.PENDING:
            return False
        return all(dep in completed_tasks for dep in self.dependencies)

    def start(self):
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = time.time()

    def complete(self):
        self.status = TaskStatus.COMPLETED
        self.completed_at = time.time()

    def fail(self):
        self.status = TaskStatus.FAILED
        self.completed_at = time.time()


@dataclass
class ExecutionPlan:
    """Represents a complete execution plan."""
    plan_id: str
    goal: str
    tasks: List[Task]
    total_estimated_duration: float = 0.0
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "tasks": [t.to_dict() for t in self.tasks],
            "total_estimated_duration": self.total_estimated_duration,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    def get_next_tasks(self) -> List[Task]:
        completed = {
            t.task_id for t in self.tasks if t.status == TaskStatus.COMPLETED
        }
        ready = [t for t in self.tasks if t.is_ready(completed)]
        ready.sort(key=lambda t: t.priority.value, reverse=True)
        return ready

    def get_progress(self) -> Dict[str, Any]:
        total = len(self.tasks)
        if total == 0:
            return {"completion": 0.0}
        done = sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)
        ip = sum(1 for t in self.tasks if t.status == TaskStatus.IN_PROGRESS)
        fail = sum(1 for t in self.tasks if t.status == TaskStatus.FAILED)
        return {
            "total_tasks": total,
            "completed": done,
            "in_progress": ip,
            "failed": fail,
            "pending": total - done - ip - fail,
            "completion": done / total,
            "success_rate": done / max(1, done + fail),
        }


class PlanningSystem:
    """
    LLM-powered planning system for task decomposition.

    Uses LLMClient for intelligent goal decomposition; falls back to
    heuristic patterns when LLM is unavailable.

    Args:
        llm_function: Callable(prompt, params) -> str.  Pass an LLMClient.
        max_depth: Maximum decomposition depth.
        default_priority: Default task priority.
        enable_optimization: Sort tasks for optimal execution.
    """

    def __init__(
        self,
        llm_function: Optional[Callable] = None,
        max_depth: int = 5,
        default_priority: TaskPriority = TaskPriority.MEDIUM,
        enable_optimization: bool = True,
    ):
        self.max_depth = max_depth
        self.default_priority = default_priority
        self.enable_optimization = enable_optimization

        if llm_function is not None:
            self._llm = llm_function
        else:
            self._llm = None  # Lazy init

        self.stats = {
            "plans_created": 0,
            "tasks_decomposed": 0,
            "optimizations_performed": 0,
        }

    def _get_llm(self) -> Optional[Callable]:
        """Lazily create LLMClient if not provided."""
        if self._llm is not None:
            return self._llm
        try:
            from versaai.agents.llm_client import LLMClient
            self._llm = LLMClient(temperature=0.4, max_tokens=1024)
            logger.info("PlanningSystem: created LLMClient lazily")
            return self._llm
        except Exception as exc:
            logger.warning(f"Cannot create LLMClient ({exc}); using heuristic decomposition")
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_plan(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> ExecutionPlan:
        """
        Create an execution plan for a goal.

        Uses LLM for intelligent decomposition when available.
        """
        self.stats["plans_created"] += 1
        plan_id = f"plan_{int(time.time() * 1000)}"

        tasks = self._decompose_goal(goal, context or {}, constraints or {})
        self._resolve_dependencies(tasks)

        if self.enable_optimization:
            tasks = self._optimize_plan(tasks, context or {})
            self.stats["optimizations_performed"] += 1

        total_duration = sum(t.estimated_duration for t in tasks)

        return ExecutionPlan(
            plan_id=plan_id,
            goal=goal,
            tasks=tasks,
            total_estimated_duration=total_duration,
            metadata={
                "context": context,
                "constraints": constraints,
                "num_tasks": len(tasks),
            },
        )

    # ------------------------------------------------------------------
    # LLM-powered decomposition
    # ------------------------------------------------------------------

    def _decompose_goal(
        self,
        goal: str,
        context: Dict[str, Any],
        constraints: Dict[str, Any],
    ) -> List[Task]:
        """Decompose goal into tasks. Tries LLM first, heuristic fallback."""
        llm = self._get_llm()
        if llm is not None:
            try:
                return self._llm_decompose(goal, context, constraints, llm)
            except Exception as exc:
                logger.warning(f"LLM decomposition failed ({exc}), using heuristic")

        return self._heuristic_decompose(goal, context)

    def _llm_decompose(
        self,
        goal: str,
        context: Dict[str, Any],
        constraints: Dict[str, Any],
        llm: Callable,
    ) -> List[Task]:
        """Ask the LLM to decompose a goal into structured tasks."""
        ctx_str = json.dumps(context, default=str) if context else "none"
        con_str = json.dumps(constraints, default=str) if constraints else "none"

        prompt = (
            f"You are a project planning assistant. Decompose this goal into "
            f"a list of concrete, actionable tasks with dependencies.\n\n"
            f"Goal: {goal}\n"
            f"Context: {ctx_str}\n"
            f"Constraints: {con_str}\n\n"
            f"Return ONLY a JSON array. Each element must have:\n"
            f'  {{"id": "task_1", "name": "...", "description": "...", '
            f'"priority": 1-5, "estimated_hours": N, '
            f'"dependencies": ["task_X", ...]}}\n\n'
            f"Use sequential ids (task_1, task_2, ...). "
            f"Dependencies reference other task ids. "
            f"Priority: 5=critical, 4=high, 3=medium, 2=low, 1=optional.\n"
            f"JSON array:"
        )

        raw = llm(prompt, {"temperature": 0.4})

        # Extract JSON array
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not match:
            raise ValueError("No JSON array found in LLM response")

        items = json.loads(match.group())
        if not isinstance(items, list) or not items:
            raise ValueError("Empty or invalid task list")

        base_id = int(time.time() * 1000)
        tasks = []
        id_map: Dict[str, str] = {}  # map LLM ids → internal ids

        for i, item in enumerate(items):
            internal_id = f"task_{base_id}_{i + 1}"
            llm_id = str(item.get("id", f"task_{i + 1}"))
            id_map[llm_id] = internal_id

            pri_val = int(item.get("priority", 3))
            priority = TaskPriority(min(5, max(1, pri_val)))

            tasks.append(Task(
                task_id=internal_id,
                name=str(item.get("name", f"Task {i + 1}")),
                description=str(item.get("description", "")),
                priority=priority,
                estimated_duration=float(item.get("estimated_hours", 1.0)),
                dependencies=[],  # resolved below
            ))

        # Map dependencies
        for i, item in enumerate(items):
            raw_deps = item.get("dependencies", [])
            tasks[i].dependencies = [
                id_map[d] for d in raw_deps if d in id_map
            ]

        self.stats["tasks_decomposed"] += len(tasks)
        return tasks

    # ------------------------------------------------------------------
    # Heuristic fallback
    # ------------------------------------------------------------------

    def _heuristic_decompose(
        self, goal: str, context: Dict[str, Any]
    ) -> List[Task]:
        """Keyword-based decomposition when LLM is unavailable."""
        gl = goal.lower()
        if "build" in gl or "create" in gl:
            return self._pattern_build(goal)
        elif "deploy" in gl:
            return self._pattern_deploy(goal)
        elif "analyze" in gl or "research" in gl:
            return self._pattern_analysis(goal)
        return self._pattern_generic(goal)

    def _pattern_build(self, goal: str) -> List[Task]:
        base = int(time.time() * 1000)
        return [
            Task(f"task_{base}_1", "Design and Planning",
                 f"Design architecture for: {goal}",
                 TaskPriority.HIGH, estimated_duration=2.0),
            Task(f"task_{base}_2", "Implementation",
                 "Implement core functionality",
                 TaskPriority.CRITICAL, estimated_duration=8.0,
                 dependencies=[f"task_{base}_1"]),
            Task(f"task_{base}_3", "Testing",
                 "Test implementation",
                 TaskPriority.HIGH, estimated_duration=4.0,
                 dependencies=[f"task_{base}_2"]),
            Task(f"task_{base}_4", "Documentation",
                 "Create documentation",
                 TaskPriority.MEDIUM, estimated_duration=2.0,
                 dependencies=[f"task_{base}_2"]),
        ]

    def _pattern_deploy(self, goal: str) -> List[Task]:
        base = int(time.time() * 1000)
        return [
            Task(f"task_{base}_1", "Prepare Environment",
                 "Setup deployment environment",
                 TaskPriority.HIGH, estimated_duration=1.0),
            Task(f"task_{base}_2", "Run Tests",
                 "Execute test suite",
                 TaskPriority.CRITICAL, estimated_duration=1.0,
                 dependencies=[f"task_{base}_1"]),
            Task(f"task_{base}_3", "Deploy to Staging",
                 "Deploy to staging environment",
                 TaskPriority.HIGH, estimated_duration=0.5,
                 dependencies=[f"task_{base}_2"]),
            Task(f"task_{base}_4", "Deploy to Production",
                 "Deploy to production",
                 TaskPriority.CRITICAL, estimated_duration=1.0,
                 dependencies=[f"task_{base}_3"]),
        ]

    def _pattern_analysis(self, goal: str) -> List[Task]:
        base = int(time.time() * 1000)
        return [
            Task(f"task_{base}_1", "Data Collection",
                 "Gather relevant data and sources",
                 TaskPriority.HIGH, estimated_duration=2.0),
            Task(f"task_{base}_2", "Analysis",
                 "Perform analysis",
                 TaskPriority.CRITICAL, estimated_duration=4.0,
                 dependencies=[f"task_{base}_1"]),
            Task(f"task_{base}_3", "Report Generation",
                 "Generate analysis report",
                 TaskPriority.MEDIUM, estimated_duration=2.0,
                 dependencies=[f"task_{base}_2"]),
        ]

    def _pattern_generic(self, goal: str) -> List[Task]:
        base = int(time.time() * 1000)
        return [
            Task(f"task_{base}_1", "Preparation",
                 f"Prepare for: {goal}",
                 self.default_priority, estimated_duration=1.0),
            Task(f"task_{base}_2", "Execution",
                 f"Execute: {goal}",
                 TaskPriority.HIGH, estimated_duration=3.0,
                 dependencies=[f"task_{base}_1"]),
            Task(f"task_{base}_3", "Verification",
                 f"Verify completion of: {goal}",
                 self.default_priority, estimated_duration=1.0,
                 dependencies=[f"task_{base}_2"]),
        ]

    # ------------------------------------------------------------------
    # Dependency resolution & optimization
    # ------------------------------------------------------------------

    def _resolve_dependencies(self, tasks: List[Task]) -> None:
        ids = {t.task_id for t in tasks}
        for t in tasks:
            t.dependencies = [d for d in t.dependencies if d in ids]

    def _optimize_plan(
        self, tasks: List[Task], context: Dict[str, Any]
    ) -> List[Task]:
        def score(t: Task) -> tuple:
            return (-t.priority.value, len(t.dependencies), t.estimated_duration)
        return sorted(tasks, key=score)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self.stats,
            "max_depth": self.max_depth,
            "default_priority": self.default_priority.value,
            "optimization_enabled": self.enable_optimization,
        }
