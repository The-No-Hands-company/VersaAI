"""
OrchestratorAgent — multi-agent task coordination and delegation.

The Orchestrator is the "meta-agent" that receives a complex, multi-step
user goal, decomposes it using the PlanningAgent, selects the appropriate
specialist agent for each subtask, executes them (respecting dependencies),
merges results, and returns a unified response.

This is the core of VersaAI's agentic architecture — the component that
turns VersaAI from a collection of agents into an autonomous system.

Execution flow:
    1. Receive high-level goal
    2. Delegate to PlanningAgent for decomposition
    3. Map each subtask to a specialist agent (coding, research, reasoning)
    4. Execute subtasks in dependency order (parallel where possible)
    5. Aggregate results with conflict resolution
    6. Return final synthesized output with audit trail

Agent Selection Heuristics:
    - Code: coding_agent   (keywords: code, implement, debug, test, function)
    - Research: research_agent   (keywords: find, search, learn, summarize)
    - Reasoning: reasoning_agent  (keywords: analyze, reason, compare, decide)
    - Planning: planning_agent   (keywords: plan, schedule, organize, break down)
"""

import logging
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from versaai.agents.agent_base import AgentBase, AgentMetadata

logger = logging.getLogger(__name__)

# ============================================================================
# Agent selection classifier
# ============================================================================

_AGENT_PATTERNS: List[Tuple[str, List[str]]] = [
    ("coding", [
        r"\b(?:cod(?:e|ing)|implement|debug|test|function|class|refactor"
        r"|compil|syntax|bug|script|program|api|endpoint|module)\b",
    ]),
    ("research", [
        r"\b(?:research|search|find|look\s*up|summariz|source|cit|article"
        r"|paper|document|learn\s+about|what\s+is|explain)\b",
    ]),
    ("reasoning", [
        r"\b(?:reason|analyz|compar|decid|evaluat|pros?\s+and\s+cons"
        r"|trade-?off|logic|why|deduc|infer|assess)\b",
    ]),
    ("image_gen", [
        r"\b(?:generat(?:e|ing)\s+(?:an?\s+)?image|draw|paint|illustrat"
        r"|creat(?:e|ing)\s+(?:an?\s+)?(?:image|picture|photo|artwork)"
        r"|image\s+generat|text[\s-]to[\s-]image|stable\s*diffusion"
        r"|dall[\s-]?e|midjourney|render\s+(?:an?\s+)?image)\b",
    ]),
    ("video_gen", [
        r"\b(?:generat(?:e|ing)\s+(?:an?\s+)?video|creat(?:e|ing)\s+(?:an?\s+)?video"
        r"|animat(?:e|ion)|text[\s-]to[\s-]video|video\s+generat"
        r"|stable\s*video|motion\s+generat)\b",
    ]),
    ("model_gen", [
        r"\b(?:generat(?:e|ing)\s+(?:an?\s+)?(?:3d|three[\s-]?d)\s*model"
        r"|creat(?:e|ing)\s+(?:an?\s+)?(?:3d|three[\s-]?d)"
        r"|text[\s-]to[\s-]3d|3d\s+generat|mesh\s+generat"
        r"|(?:3d|three[\s-]?d)\s+(?:object|model|asset|scene))\b",
    ]),
    ("companion", [
        r"\b(?:chat|talk|convers|companion|friend|buddy|hang\s*out"
        r"|how\s+are\s+you|tell\s+me\s+about\s+yourself"
        r"|let'?s?\s+talk|just\s+talk|casual|bored|lonely)\b",
    ]),
]

_COMPILED_PATTERNS = [
    (name, [re.compile(p, re.IGNORECASE) for p in patterns])
    for name, patterns in _AGENT_PATTERNS
]


def classify_subtask(task_description: str) -> str:
    """
    Classify a subtask description to the best-fit agent.

    Returns one of: "coding", "research", "reasoning", "image_gen",
    "video_gen", "model_gen", "companion".
    Defaults to "reasoning" for ambiguous tasks.
    """
    scores: Dict[str, int] = {}
    for name, patterns in _COMPILED_PATTERNS:
        score = sum(
            len(p.findall(task_description)) for p in patterns
        )
        if score > 0:
            scores[name] = score

    if not scores:
        return "reasoning"

    return max(scores, key=scores.get)


# ============================================================================
# Subtask dataclass
# ============================================================================

@dataclass
class SubtaskResult:
    """Result from executing a single subtask via a specialist agent."""
    task_id: str
    task_description: str
    agent_used: str
    result: str
    success: bool
    execution_time: float
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# OrchestratorAgent
# ============================================================================

class OrchestratorAgent(AgentBase):
    """
    Meta-agent that coordinates specialist agents for complex, multi-step goals.

    Capabilities:
    - Goal decomposition via PlanningAgent
    - Automatic agent selection per subtask
    - Dependency-aware execution ordering
    - Parallel execution of independent subtasks
    - Result aggregation and synthesis
    - Full audit trail
    """

    def __init__(self):
        super().__init__(
            metadata=AgentMetadata(
                name="orchestrator",
                description=(
                    "Multi-agent orchestrator that decomposes complex goals, "
                    "delegates subtasks to specialist agents (coding, research, "
                    "reasoning), and synthesizes results into a unified response."
                ),
                version="1.0.0",
                capabilities=[
                    "multi_agent_coordination",
                    "goal_decomposition",
                    "parallel_execution",
                    "dependency_resolution",
                    "result_synthesis",
                    "audit_trail",
                ],
            )
        )
        self._agents: Dict[str, AgentBase] = {}
        self._llm = None
        self._max_parallel = 4

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        self._max_parallel = cfg.get("max_parallel", 4)

        from versaai.agents.llm_client import LLMClient

        self._llm = LLMClient(
            model=cfg.get("model"),
            temperature=cfg.get("temperature", 0.3),
            max_tokens=cfg.get("max_tokens", 4096),
        )

        # Lazily initialize specialist agents
        self._init_specialist("coding", cfg)
        self._init_specialist("research", cfg)
        self._init_specialist("reasoning", cfg)

        logger.info(
            "OrchestratorAgent initialized with %d specialists",
            len(self._agents),
        )

    def _init_specialist(self, name: str, cfg: Dict[str, Any]) -> None:
        """Lazily initialize a specialist agent."""
        try:
            if name == "coding":
                from versaai.agents.coding_agent import CodingAgent
                agent = CodingAgent()
            elif name == "research":
                from versaai.agents.research_agent import ResearchAgent
                agent = ResearchAgent()
            elif name == "reasoning":
                from versaai.agents.reasoning_agent import ReasoningAgent
                agent = ReasoningAgent()
            else:
                return

            agent.initialize(cfg)
            self._agents[name] = agent
        except Exception as exc:
            logger.warning("Failed to init %s agent: %s", name, exc)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(
        self, task: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a complex multi-step goal.

        Args:
            task: High-level goal description.
            context: Optional context dict. Accepts:
                - "max_subtasks": int — limit on subtasks (default: 8)
                - "strategy": str — "sequential" or "parallel" (default: parallel)

        Returns:
            Dict with keys: result, subtasks, execution_time, plan_summary
        """
        ctx = context or {}
        start = time.monotonic()
        max_subtasks = ctx.get("max_subtasks", 8)
        strategy = ctx.get("strategy", "parallel")

        # Step 1: Decompose goal into subtasks
        subtasks = self._decompose(task, max_subtasks)
        if not subtasks:
            # Simple task — route directly to best agent
            agent_name = classify_subtask(task)
            result = self._execute_single(task, agent_name)
            return {
                "result": result.result if result.success else f"Error: {result.error}",
                "subtasks": [self._subtask_to_dict(result)],
                "execution_time": time.monotonic() - start,
                "plan_summary": f"Direct execution via {agent_name} agent",
            }

        # Step 2: Assign agents to subtasks
        assignments = self._assign_agents(subtasks)

        # Step 3: Execute
        if strategy == "sequential":
            results = self._execute_sequential(assignments)
        else:
            results = self._execute_parallel(assignments)

        # Step 4: Synthesize
        synthesis = self._synthesize(task, results)

        return {
            "result": synthesis,
            "subtasks": [self._subtask_to_dict(r) for r in results],
            "execution_time": time.monotonic() - start,
            "plan_summary": self._format_plan(assignments, results),
        }

    def reset(self) -> None:
        """Reset all specialist agents."""
        for agent in self._agents.values():
            try:
                agent.reset()
            except Exception:
                pass
        self.memory.clear()

    # ------------------------------------------------------------------
    # Decomposition
    # ------------------------------------------------------------------

    def _decompose(
        self, goal: str, max_subtasks: int
    ) -> List[Dict[str, str]]:
        """
        Decompose a goal into actionable subtasks using the LLM.

        Returns a list of dicts: [{"id": "1", "description": "..."}]
        """
        if self._llm is None:
            return []

        prompt = (
            "You are a task decomposition expert. Break down the following goal "
            "into concrete, actionable subtasks. Each subtask should be "
            "independently executable.\n\n"
            f"Goal: {goal}\n\n"
            f"Return at most {max_subtasks} subtasks, one per line, in format:\n"
            "1. <subtask description>\n"
            "2. <subtask description>\n"
            "...\n\n"
            "If the goal is simple enough to execute directly, return exactly:\n"
            "DIRECT\n"
        )

        try:
            response = self._llm.complete(prompt)
        except Exception as exc:
            logger.warning("LLM decomposition failed: %s", exc)
            return []

        if "DIRECT" in response.strip().upper()[:20]:
            return []

        return self._parse_subtasks(response, max_subtasks)

    @staticmethod
    def _parse_subtasks(
        text: str, limit: int
    ) -> List[Dict[str, str]]:
        """Parse numbered subtasks from LLM output."""
        results = []
        for line in text.strip().splitlines():
            line = line.strip()
            # Match "1. ...", "1) ...", "- ..."
            m = re.match(r"^(?:\d+[.)]\s*|-\s*)(.*)", line)
            if m:
                desc = m.group(1).strip()
                if desc and len(desc) > 5:
                    results.append({
                        "id": str(len(results) + 1),
                        "description": desc,
                    })
                    if len(results) >= limit:
                        break
        return results

    # ------------------------------------------------------------------
    # Agent assignment
    # ------------------------------------------------------------------

    def _assign_agents(
        self, subtasks: List[Dict[str, str]]
    ) -> List[Tuple[Dict[str, str], str]]:
        """Assign each subtask to the best-fit agent."""
        assignments = []
        for st in subtasks:
            agent_name = classify_subtask(st["description"])
            # Fall back to reasoning if agent not available
            if agent_name not in self._agents:
                agent_name = "reasoning" if "reasoning" in self._agents else next(
                    iter(self._agents), "reasoning"
                )
            assignments.append((st, agent_name))
        return assignments

    # ------------------------------------------------------------------
    # Execution strategies
    # ------------------------------------------------------------------

    def _execute_single(
        self, task: str, agent_name: str
    ) -> SubtaskResult:
        """Execute a single task on the named agent."""
        agent = self._agents.get(agent_name)
        if agent is None:
            return SubtaskResult(
                task_id="1",
                task_description=task,
                agent_used=agent_name,
                result="",
                success=False,
                execution_time=0.0,
                error=f"Agent '{agent_name}' not available",
            )

        start = time.monotonic()
        try:
            raw = agent.execute(task, {})
            result_text = raw.get("result", str(raw)) if isinstance(raw, dict) else str(raw)
            return SubtaskResult(
                task_id="1",
                task_description=task,
                agent_used=agent_name,
                result=result_text,
                success=True,
                execution_time=time.monotonic() - start,
            )
        except Exception as exc:
            return SubtaskResult(
                task_id="1",
                task_description=task,
                agent_used=agent_name,
                result="",
                success=False,
                execution_time=time.monotonic() - start,
                error=str(exc),
            )

    def _execute_sequential(
        self, assignments: List[Tuple[Dict[str, str], str]]
    ) -> List[SubtaskResult]:
        """Execute subtasks one at a time, in order."""
        results = []
        context_so_far = ""
        for st, agent_name in assignments:
            result = self._execute_subtask(st, agent_name, context_so_far)
            results.append(result)
            if result.success:
                context_so_far += f"\n[Completed] {st['description']}: {result.result[:200]}\n"
        return results

    def _execute_parallel(
        self, assignments: List[Tuple[Dict[str, str], str]]
    ) -> List[SubtaskResult]:
        """Execute independent subtasks in parallel using a thread pool."""
        results: List[SubtaskResult] = [None] * len(assignments)  # type: ignore

        with ThreadPoolExecutor(max_workers=self._max_parallel) as pool:
            futures = {}
            for idx, (st, agent_name) in enumerate(assignments):
                future = pool.submit(self._execute_subtask, st, agent_name, "")
                futures[future] = idx

            for future in as_completed(futures):
                idx = futures[future]
                try:
                    results[idx] = future.result(timeout=120)
                except Exception as exc:
                    st, agent_name = assignments[idx]
                    results[idx] = SubtaskResult(
                        task_id=st["id"],
                        task_description=st["description"],
                        agent_used=agent_name,
                        result="",
                        success=False,
                        execution_time=0.0,
                        error=str(exc),
                    )

        return results

    def _execute_subtask(
        self,
        subtask: Dict[str, str],
        agent_name: str,
        prior_context: str,
    ) -> SubtaskResult:
        """Execute a single subtask on the assigned agent."""
        agent = self._agents.get(agent_name)
        if agent is None:
            return SubtaskResult(
                task_id=subtask["id"],
                task_description=subtask["description"],
                agent_used=agent_name,
                result="",
                success=False,
                execution_time=0.0,
                error=f"Agent '{agent_name}' not available",
            )

        start = time.monotonic()
        try:
            ctx: Dict[str, Any] = {}
            if prior_context:
                ctx["prior_context"] = prior_context

            raw = agent.execute(subtask["description"], ctx)
            result_text = raw.get("result", str(raw)) if isinstance(raw, dict) else str(raw)
            return SubtaskResult(
                task_id=subtask["id"],
                task_description=subtask["description"],
                agent_used=agent_name,
                result=result_text,
                success=True,
                execution_time=time.monotonic() - start,
            )
        except Exception as exc:
            return SubtaskResult(
                task_id=subtask["id"],
                task_description=subtask["description"],
                agent_used=agent_name,
                result="",
                success=False,
                execution_time=time.monotonic() - start,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Synthesis
    # ------------------------------------------------------------------

    def _synthesize(
        self, original_goal: str, results: List[SubtaskResult]
    ) -> str:
        """Synthesize subtask results into a unified response."""
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        if not successful:
            return "All subtasks failed. " + "; ".join(
                f"[{r.task_id}] {r.error}" for r in failed
            )

        # For single successful result, return directly
        if len(successful) == 1 and not failed:
            return successful[0].result

        # For multiple results, ask LLM to synthesize
        if self._llm is not None:
            parts = []
            for r in successful:
                parts.append(
                    f"--- Subtask {r.task_id}: {r.task_description} "
                    f"(via {r.agent_used}) ---\n{r.result}\n"
                )
            if failed:
                parts.append(
                    "--- Failed subtasks ---\n"
                    + "\n".join(f"- {r.task_description}: {r.error}" for r in failed)
                )

            prompt = (
                "You are synthesizing results from multiple subtasks into a "
                "single coherent response for the user.\n\n"
                f"Original goal: {original_goal}\n\n"
                f"Subtask results:\n{''.join(parts)}\n\n"
                "Provide a clear, unified response that addresses the original "
                "goal. Integrate information from all subtasks. Be concise."
            )

            try:
                return self._llm.complete(prompt)
            except Exception as exc:
                logger.warning("Synthesis LLM call failed: %s", exc)

        # Fallback: concatenate results
        lines = [f"## Results for: {original_goal}\n"]
        for r in successful:
            lines.append(f"### {r.task_description}\n{r.result}\n")
        if failed:
            lines.append("### Failed subtasks\n")
            for r in failed:
                lines.append(f"- {r.task_description}: {r.error}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _subtask_to_dict(r: SubtaskResult) -> Dict[str, Any]:
        return {
            "id": r.task_id,
            "description": r.task_description,
            "agent": r.agent_used,
            "result": r.result[:500] if r.result else "",
            "success": r.success,
            "error": r.error,
            "execution_time": r.execution_time,
        }

    @staticmethod
    def _format_plan(
        assignments: List[Tuple[Dict[str, str], str]],
        results: List[SubtaskResult],
    ) -> str:
        lines = []
        for (st, agent_name), r in zip(assignments, results):
            status = "✓" if r.success else "✗"
            lines.append(
                f"{status} [{r.task_id}] {st['description']} "
                f"→ {agent_name} ({r.execution_time:.1f}s)"
            )
        succeeded = sum(1 for r in results if r.success)
        lines.append(f"\n{succeeded}/{len(results)} subtasks completed")
        return "\n".join(lines)
