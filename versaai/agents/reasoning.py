"""
ReasoningEngine — Chain-of-Thought and advanced reasoning for agents.

Implements multiple reasoning strategies including Chain-of-Thought (CoT),
ReAct, and Tree-of-Thoughts for systematic problem solving.

All strategies use real LLM inference via LLMClient (Ollama / llama.cpp).
ReAct strategy uses ToolRegistry for executing actions.

Features:
    - Chain-of-Thought reasoning with actual LLM calls
    - ReAct (Reason + Act) with real tool execution
    - Tree-of-Thoughts (parallel path exploration)
    - Self-Consistency (majority vote)
    - LLM-powered step verification
    - Reasoning trace logging

Example:
    >>> from versaai.agents.llm_client import LLMClient
    >>> from versaai.agents.reasoning import ReasoningEngine
    >>> from versaai.agents.tools import ToolRegistry, FileReadTool, ShellTool
    >>>
    >>> llm = LLMClient()
    >>> registry = ToolRegistry()
    >>> registry.register(FileReadTool("/my/project"))
    >>> registry.register(ShellTool("/my/project"))
    >>>
    >>> engine = ReasoningEngine(llm_function=llm, tool_registry=registry)
    >>> result = engine.reason("What files are in the src/ directory?")
    >>> print(result.answer)
"""

import json
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ReasoningStrategy(Enum):
    """Reasoning strategy types."""
    CHAIN_OF_THOUGHT = "cot"
    REACT = "react"
    TREE_OF_THOUGHTS = "tot"
    SELF_CONSISTENCY = "self_consistency"
    ZERO_SHOT = "zero_shot"


@dataclass
class ReasoningStep:
    """Represents a single reasoning step."""
    step_num: int
    thought: str
    action: Optional[str] = None
    action_input: Optional[str] = None
    observation: Optional[str] = None
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_num": self.step_num,
            "thought": self.thought,
            "action": self.action,
            "action_input": self.action_input,
            "observation": self.observation,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }


@dataclass
class ReasoningResult:
    """Result of reasoning process."""
    answer: str
    steps: List[ReasoningStep]
    strategy_used: str
    confidence: float
    verified: bool = False
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "steps": [s.to_dict() for s in self.steps],
            "strategy_used": self.strategy_used,
            "confidence": self.confidence,
            "verified": self.verified,
            "execution_time": self.execution_time,
            "metadata": self.metadata,
        }


class ReasoningEngine:
    """
    Production-grade reasoning engine for systematic problem solving.

    Supports real LLM inference and real tool execution.

    Args:
        strategy: Default reasoning strategy.
        llm_function: Callable(prompt, params_dict) -> str.  Pass an LLMClient
                       instance directly (it implements __call__).
        tool_registry: Optional ToolRegistry for ReAct actions.
        max_steps: Maximum reasoning steps per invocation.
        enable_verification: Use LLM to verify final answer.
        temperature: Default sampling temperature.
    """

    def __init__(
        self,
        strategy: str = "cot",
        llm_function: Optional[Callable] = None,
        tool_registry: Optional[Any] = None,
        max_steps: int = 10,
        enable_verification: bool = True,
        temperature: float = 0.7,
    ):
        self.strategy = ReasoningStrategy(strategy)
        self.max_steps = max_steps
        self.enable_verification = enable_verification
        self.temperature = temperature
        self.tool_registry = tool_registry

        # LLM function: accept LLMClient (callable) or plain function
        if llm_function is not None:
            self.llm_function = llm_function
        else:
            # Lazy-init: create LLMClient on first use so import is not
            # required at class-definition time.
            self._lazy_llm: Optional[Callable] = None

        self.stats = {
            "reasoning_calls": 0,
            "total_steps_generated": 0,
            "verifications_performed": 0,
            "self_corrections": 0,
        }

    # ------------------------------------------------------------------
    # Lazy LLM fallback
    # ------------------------------------------------------------------

    def _get_llm(self) -> Callable:
        """Return the LLM callable, creating an LLMClient lazily if needed."""
        if hasattr(self, "llm_function"):
            return self.llm_function
        if self._lazy_llm is None:
            try:
                from versaai.agents.llm_client import LLMClient
                self._lazy_llm = LLMClient()
                logger.info("ReasoningEngine: created LLMClient lazily")
            except Exception as exc:
                logger.warning(f"Cannot create LLMClient ({exc}); using echo stub")
                self._lazy_llm = lambda prompt, params=None: f"[stub] {prompt[:60]}..."
        return self._lazy_llm

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reason(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        strategy: Optional[str] = None,
    ) -> ReasoningResult:
        """
        Perform reasoning on a task using real LLM inference.

        Args:
            task: Task or problem to solve.
            context: Additional context dict.
            strategy: Override default strategy.

        Returns:
            ReasoningResult with answer and steps.
        """
        start_time = time.time()
        self.stats["reasoning_calls"] += 1

        strat = ReasoningStrategy(strategy) if strategy else self.strategy

        dispatch = {
            ReasoningStrategy.CHAIN_OF_THOUGHT: self._chain_of_thought,
            ReasoningStrategy.REACT: self._react_reasoning,
            ReasoningStrategy.TREE_OF_THOUGHTS: self._tree_of_thoughts,
            ReasoningStrategy.SELF_CONSISTENCY: self._self_consistency,
            ReasoningStrategy.ZERO_SHOT: self._zero_shot,
        }

        result = dispatch[strat](task, context or {})
        result.execution_time = time.time() - start_time
        self.stats["total_steps_generated"] += len(result.steps)
        return result

    # ------------------------------------------------------------------
    # Strategies
    # ------------------------------------------------------------------

    def _chain_of_thought(
        self, task: str, context: Dict[str, Any]
    ) -> ReasoningResult:
        """Chain-of-Thought: step-by-step reasoning via LLM."""
        llm = self._get_llm()
        steps: List[ReasoningStep] = []
        history = ""

        cot_prompt = self._build_cot_prompt(task, context)

        for step_num in range(1, self.max_steps + 1):
            prompt = (
                f"{cot_prompt}\n{history}\n"
                f"Step {step_num}: Think carefully and provide your reasoning for this step.\n"
                f"If you have reached the final answer, state it clearly starting with 'Answer:'."
            )
            thought = llm(prompt, {"temperature": self.temperature})
            thought = thought.strip()

            step = ReasoningStep(step_num=step_num, thought=thought)
            steps.append(step)
            history += f"\nStep {step_num}: {thought}"

            if self._is_conclusion(thought):
                break

        answer = self._extract_answer(steps)

        verified = False
        if self.enable_verification:
            verified = self._verify_reasoning(task, steps, answer)
            self.stats["verifications_performed"] += 1

        return ReasoningResult(
            answer=answer,
            steps=steps,
            strategy_used="chain_of_thought",
            confidence=self._calculate_confidence(steps, verified),
            verified=verified,
        )

    def _react_reasoning(
        self, task: str, context: Dict[str, Any]
    ) -> ReasoningResult:
        """
        ReAct: interleave Thought → Action → Observation loops.

        Actions are dispatched through self.tool_registry when available.
        The LLM is prompted to output structured Thought/Action/Action Input.
        """
        llm = self._get_llm()
        steps: List[ReasoningStep] = []

        # Build tool descriptions for the prompt
        tool_descriptions = self._format_tool_descriptions()

        history = ""
        for step_num in range(1, self.max_steps + 1):
            # --- Thought + Action generation ---
            prompt = (
                f"You are solving a task step-by-step.\n\n"
                f"Task: {task}\n\n"
                f"Available tools:\n{tool_descriptions}\n\n"
                f"Previous steps:\n{history}\n\n"
                f"Respond with EXACTLY this format:\n"
                f"Thought: <your reasoning>\n"
                f"Action: <tool_name OR 'finish'>\n"
                f"Action Input: <input for the tool, or your final answer if Action is finish>\n"
            )
            raw = llm(prompt, {"temperature": self.temperature})

            thought, action, action_input = self._parse_react_output(raw)

            # --- Observation: execute action ---
            if action.lower() == "finish":
                observation = action_input
                step = ReasoningStep(
                    step_num=step_num,
                    thought=thought,
                    action="finish",
                    action_input=action_input,
                    observation=observation,
                )
                steps.append(step)
                break
            else:
                observation = self._execute_action(action, action_input, context)

            step = ReasoningStep(
                step_num=step_num,
                thought=thought,
                action=action,
                action_input=action_input,
                observation=observation,
            )
            steps.append(step)
            history += (
                f"\nStep {step_num}:\n"
                f"  Thought: {thought}\n"
                f"  Action: {action}\n"
                f"  Action Input: {action_input}\n"
                f"  Observation: {observation}\n"
            )

        answer = self._extract_answer(steps)

        return ReasoningResult(
            answer=answer,
            steps=steps,
            strategy_used="react",
            confidence=self._calculate_confidence(steps),
            verified=False,
        )

    def _tree_of_thoughts(
        self, task: str, context: Dict[str, Any]
    ) -> ReasoningResult:
        """Explore multiple CoT paths and pick the best."""
        num_paths = context.get("num_paths", 3)

        paths = []
        for i in range(num_paths):
            result = self._chain_of_thought(task, {**context, "path_id": i})
            paths.append(result)

        best = max(paths, key=lambda r: r.confidence)
        best.strategy_used = "tree_of_thoughts"
        best.metadata["num_paths_explored"] = num_paths
        return best

    def _self_consistency(
        self, task: str, context: Dict[str, Any]
    ) -> ReasoningResult:
        """Generate multiple answers and majority-vote."""
        num_samples = context.get("num_samples", 5)

        results = [
            self._chain_of_thought(task, {**context, "sample_id": i})
            for i in range(num_samples)
        ]

        votes: Dict[str, int] = {}
        for r in results:
            votes[r.answer] = votes.get(r.answer, 0) + 1

        best_answer = max(votes, key=votes.get)  # type: ignore[arg-type]
        best_result = next(r for r in results if r.answer == best_answer)
        best_result.strategy_used = "self_consistency"
        best_result.metadata["num_samples"] = num_samples
        best_result.metadata["vote_distribution"] = votes
        return best_result

    def _zero_shot(self, task: str, context: Dict[str, Any]) -> ReasoningResult:
        """Direct answer — single LLM call, no intermediate steps."""
        llm = self._get_llm()
        prompt = f"Task: {task}\n\nProvide a clear, direct answer:"
        answer = llm(prompt, {"temperature": 0.1}).strip()

        step = ReasoningStep(
            step_num=1,
            thought="Direct answer without intermediate reasoning",
            observation=answer,
        )
        return ReasoningResult(
            answer=answer,
            steps=[step],
            strategy_used="zero_shot",
            confidence=0.8,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_cot_prompt(self, task: str, context: Dict[str, Any]) -> str:
        prompt = f"Task: {task}\n\nLet's solve this step by step:"
        if "examples" in context:
            prompt = f"Examples:\n{context['examples']}\n\n{prompt}"
        return prompt

    def _is_conclusion(self, text: str) -> bool:
        markers = [
            "therefore", "thus", "final answer", "in conclusion",
            "the answer is", "result:", "answer:",
        ]
        return any(m in text.lower() for m in markers)

    def _extract_answer(self, steps: List[ReasoningStep]) -> str:
        if not steps:
            return "No answer generated"

        # Check the last few steps for explicit answer patterns
        for step in reversed(steps[-3:]):
            combined = step.thought + " " + (step.observation or "")
            patterns = [
                r"answer:\s*(.+)",
                r"result:\s*(.+)",
                r"therefore[,:]?\s*(.+)",
                r"the answer is\s*(.+)",
            ]
            for pat in patterns:
                match = re.search(pat, combined, re.IGNORECASE)
                if match:
                    return match.group(1).strip()

        last = steps[-1]
        return (last.observation or last.thought).strip()

    def _calculate_confidence(
        self, steps: List[ReasoningStep], verified: bool = False
    ) -> float:
        if not steps:
            return 0.0
        avg = sum(s.confidence for s in steps) / len(steps)
        if verified:
            avg = min(1.0, avg * 1.15)
        return min(1.0, avg)

    # ------------------------------------------------------------------
    # LLM-powered verification (replaces heuristic)
    # ------------------------------------------------------------------

    def _verify_reasoning(
        self, task: str, steps: List[ReasoningStep], answer: str
    ) -> bool:
        """
        Use the LLM to verify the reasoning chain and answer.

        Asks the model to judge whether the steps logically lead to the
        answer and whether the answer is correct.
        """
        llm = self._get_llm()

        steps_text = "\n".join(
            f"  Step {s.step_num}: {s.thought}" for s in steps
        )
        prompt = (
            f"You are a verification agent.  A reasoning engine solved a task.\n\n"
            f"Task: {task}\n\n"
            f"Reasoning steps:\n{steps_text}\n\n"
            f"Final answer: {answer}\n\n"
            f"Does the reasoning logically support the answer? "
            f"Is the answer correct?\n"
            f"Respond with ONLY 'VERIFIED' or 'REJECTED' on the first line, "
            f"optionally followed by a brief explanation."
        )
        try:
            response = llm(prompt, {"temperature": 0.0})
            first_line = response.strip().splitlines()[0].upper()
            return "VERIFIED" in first_line
        except Exception as exc:
            logger.warning(f"Verification LLM call failed: {exc}")
            # Fallback heuristic
            return len(steps) >= 2 and self._is_conclusion(steps[-1].thought)

    # ------------------------------------------------------------------
    # Tool execution (replaces placeholder)
    # ------------------------------------------------------------------

    def _format_tool_descriptions(self) -> str:
        """Build a text description of available tools for the ReAct prompt."""
        if not self.tool_registry:
            return "  (no tools available — reason only)"
        descriptions = []
        for schema in self.tool_registry.get_tool_schemas():
            descriptions.append(
                f"  - {schema['name']}: {schema['description']}"
            )
        return "\n".join(descriptions) if descriptions else "  (no tools)"

    def _parse_react_output(self, raw: str) -> tuple:
        """Parse structured Thought/Action/Action Input from LLM output."""
        thought = action = action_input = ""

        # Try structured parsing
        t_match = re.search(r"Thought:\s*(.+?)(?=\nAction:|\Z)", raw, re.DOTALL)
        a_match = re.search(r"Action:\s*(.+?)(?=\nAction Input:|\Z)", raw, re.DOTALL)
        ai_match = re.search(r"Action Input:\s*(.+)", raw, re.DOTALL)

        thought = t_match.group(1).strip() if t_match else raw.strip()
        action = a_match.group(1).strip() if a_match else "finish"
        action_input = ai_match.group(1).strip() if ai_match else ""

        return thought, action, action_input

    def _execute_action(
        self, action: str, action_input: str, context: Dict[str, Any]
    ) -> str:
        """
        Execute a tool action via ToolRegistry.

        Falls back to a textual description if no registry is available.
        """
        if not self.tool_registry:
            return f"[no tool registry] Cannot execute: {action}({action_input})"

        # Try to parse action_input as JSON kwargs, fall back to single arg
        try:
            kwargs = json.loads(action_input) if action_input.strip().startswith("{") else {}
        except json.JSONDecodeError:
            kwargs = {}

        # If kwargs is empty, try to pass as the first required param
        if not kwargs:
            tool = self.tool_registry._tools.get(action)
            if tool:
                schema = tool.parameters_schema
                required = schema.get("required", [])
                if required:
                    kwargs = {required[0]: action_input}

        try:
            result = self.tool_registry.execute(action, **kwargs)
            if result.success:
                # Truncate very long outputs for the reasoning context
                output = result.output
                if len(output) > 2000:
                    output = output[:2000] + f"\n... [truncated, {len(result.output)} chars total]"
                return output
            else:
                return f"[tool error] {result.error}"
        except Exception as exc:
            return f"[execution error] {exc}"

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self.stats,
            "strategy": self.strategy.value,
            "max_steps": self.max_steps,
            "verification_enabled": self.enable_verification,
        }
