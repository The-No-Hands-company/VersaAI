"""
CodingAgent — specialized agent for code generation, analysis, and debugging.

Uses LLMClient for inference and ToolRegistry for file/shell operations.
Implements a ReAct-style execution loop:
    1. Think about the task
    2. Choose and execute a tool (file_read, file_write, file_search, shell)
    3. Observe the result
    4. Repeat until the task is complete

Example:
    >>> from versaai.agents.coding_agent import CodingAgent
    >>> agent = CodingAgent()
    >>> agent.initialize({"model": "ollama/qwen2.5-coder:7b", "work_dir": "/my/project"})
    >>> result = agent.execute("Read main.py and add type hints to all functions")
    >>> print(result["result"])
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from versaai.agents.agent_base import AgentBase, AgentMetadata

logger = logging.getLogger(__name__)

# Maximum ReAct iterations before forcing a final answer
MAX_REACT_STEPS = 8


class CodingAgent(AgentBase):
    """
    Agent specialized for coding tasks.

    Capabilities:
    - Code generation from natural language
    - File system operations (read / write / search)
    - Shell command execution (tests, linting, builds)
    - Code analysis and debugging via ReAct loop
    """

    def __init__(self):
        metadata = AgentMetadata(
            name="CodingAgent",
            description="Specialized agent for code generation, analysis, and debugging",
            version="2.0.0",
            capabilities=[
                "code_generation",
                "code_analysis",
                "debugging",
                "file_system_access",
                "shell_execution",
            ],
        )
        super().__init__(metadata)

        self.llm = None
        self.tool_registry = None
        self.rag = None  # RAGSystem instance (lazy)
        self.memory: Dict[str, Any] = {}
        self.config: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize CodingAgent.

        Args:
            config: Configuration dict:
                - model: Model ID, e.g. "ollama/qwen2.5-coder:7b" (default from settings)
                - work_dir: Working directory for tools (default: cwd)
                - max_tokens: Max tokens per generation (default: 4096)
                - temperature: Sampling temperature (default: 0.2)
                - allowed_commands: Set of allowed shell commands (default: all safe)
        """
        if self._initialized:
            return

        self.config = config or {}
        work_dir = self.config.get("work_dir", os.getcwd())

        self.logger.info(
            f"Initializing CodingAgent (model={self.config.get('model', 'default')}, "
            f"work_dir={work_dir})"
        )

        # 1. LLM
        self._init_llm()

        # 2. RAG
        self._init_rag()

        # 3. Tools
        self._init_tools(work_dir)

        # 3. Memory
        self.memory = {"messages": [], "context": {}}

        self._initialized = True
        self.logger.info("CodingAgent initialized successfully")

    def _init_llm(self) -> None:
        """Initialize LLM via the unified LLMClient."""
        from versaai.agents.llm_client import LLMClient

        model_id = self.config.get("model")  # None → LLMClient picks default
        system_prompt = (
            "You are an expert AI coding assistant. "
            "You solve tasks step-by-step using the available tools. "
            "Always read relevant files before editing them. "
            "Write production-quality, well-documented code."
        )
        self.llm = LLMClient(
            model=model_id,
            system_prompt=system_prompt,
            temperature=self.config.get("temperature", 0.2),
            max_tokens=self.config.get("max_tokens", 4096),
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

    def _init_tools(self, work_dir: str) -> None:
        """Register file and shell tools."""
        from versaai.agents.tools import (
            FileReadTool,
            FileSearchTool,
            FileWriteTool,
            RAGQueryTool,
            ShellTool,
            ToolRegistry,
        )

        self.tool_registry = ToolRegistry()
        self.tool_registry.register(FileReadTool(work_dir))
        self.tool_registry.register(FileWriteTool(work_dir))
        self.tool_registry.register(FileSearchTool(work_dir))
        self.tool_registry.register(ShellTool(
            working_dir=work_dir,
            allowed_commands=self.config.get("allowed_commands"),
        ))
        self.tool_registry.register(RAGQueryTool(rag_system=self.rag))
        self.logger.info(
            f"Tools registered: {list(self.tool_registry._tools.keys())}"
        )

    # ------------------------------------------------------------------
    # Execution — ReAct loop
    # ------------------------------------------------------------------

    def execute(
        self, task: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a coding task via a ReAct loop.

        The agent iterates:
            Thought → Action → Observation
        until it decides to finish OR hits MAX_REACT_STEPS.

        Args:
            task: Human-language description of the coding task.
            context: Optional context dict (file_content, status_callback, etc.)

        Returns:
            {
                "result": str (final answer / generated code),
                "steps": List[Dict] (reasoning trace),
                "files_modified": List[str],
                "status": "success" | "error",
            }
        """
        if not self._initialized:
            raise RuntimeError("CodingAgent not initialized. Call initialize() first.")

        self.logger.info(f"Executing coding task: {task[:120]}...")
        ctx = context or {}
        status_cb = ctx.get("status_callback")

        # Build tool descriptions for the prompt
        tool_desc = self.tool_registry.get_tool_descriptions()

        steps: List[Dict[str, Any]] = []
        files_modified: List[str] = []
        history = ""

        # Optional: inject existing file content into context
        extra_context = ""
        if ctx.get("file_content"):
            extra_context = f"\nProvided file content:\n```\n{ctx['file_content']}\n```\n"

        # RAG: retrieve relevant docs to seed the agent with domain knowledge
        rag_context = ""
        if self.rag:
            try:
                rag_results = self.rag.query(task, top_k=3)
                if rag_results:
                    snippets = []
                    for i, r in enumerate(rag_results, 1):
                        doc = r.get("document", r.get("content", ""))
                        if len(doc) > 500:
                            doc = doc[:500] + "…"
                        source = r.get("metadata", {}).get("source", "knowledge base")
                        snippets.append(f"  [{i}] ({source}) {doc}")
                    rag_context = (
                        "\nRelevant knowledge base excerpts:\n"
                        + "\n".join(snippets)
                        + "\n"
                    )
                    self.logger.info(f"Injected {len(rag_results)} RAG docs into prompt")
            except Exception as exc:
                self.logger.warning(f"RAG retrieval failed: {exc}")

        for step_num in range(1, MAX_REACT_STEPS + 1):
            self.logger.info(f"[ReAct] Step {step_num}/{MAX_REACT_STEPS}")
            if status_cb:
                status_cb(f"Step {step_num}: thinking...")

            prompt = (
                f"You are solving a coding task step-by-step.\n\n"
                f"Task: {task}\n"
                f"{extra_context}\n"
                f"{rag_context}\n"
                f"Available tools:\n{tool_desc}\n\n"
                f"Previous steps:\n{history}\n\n"
                f"Respond in EXACTLY this format:\n"
                f"Thought: <your reasoning about what to do next>\n"
                f"Action: <tool_name OR 'finish'>\n"
                f"Action Input: <JSON object with tool parameters, OR your final answer if Action is finish>\n"
            )

            try:
                self.logger.info(f"[ReAct] Step {step_num}: prompt_len={len(prompt)} chars, calling LLM...")
                raw = self.llm.chat(
                    prompt,
                    temperature=0.2,
                    max_tokens=512,
                    stop=["\nObservation:", "\nStep "],
                )
            except Exception as exc:
                self.logger.error(f"LLM call failed: {exc}")
                return {
                    "result": f"LLM error: {exc}",
                    "steps": steps,
                    "files_modified": files_modified,
                    "status": "error",
                }

            thought, action, action_input = self._parse_react(raw)
            self.logger.info(f"[ReAct] Step {step_num}: action={action!r} thought={thought[:80]!r}")

            if status_cb:
                status_cb(f"Thought: {thought[:200]}")

            # --- Finish ---
            if action.lower() == "finish":
                steps.append({
                    "step": step_num,
                    "thought": thought,
                    "action": "finish",
                    "result": action_input,
                })
                self.logger.info(f"Agent finished after {step_num} steps")
                return {
                    "result": action_input or thought,
                    "steps": steps,
                    "files_modified": files_modified,
                    "status": "success",
                }

            # --- Execute tool ---
            kwargs = self._parse_action_input(action, action_input)
            if status_cb:
                status_cb(f"Action: {action}({json.dumps(kwargs, default=str)[:200]})")

            try:
                tool_result = self.tool_registry.execute(action, **kwargs)
                observation = tool_result.output if tool_result.success else f"ERROR: {tool_result.error}"
                self.logger.info(f"[ReAct] Step {step_num}: tool={action} success={tool_result.success} output_len={len(observation)}")

                # Track file writes
                if action == "file_write" and tool_result.success:
                    files_modified.append(kwargs.get("path", "unknown"))
            except Exception as exc:
                observation = f"Tool execution error: {exc}"

            # Truncate long observations to control prompt growth
            MAX_OBS_CHARS = 1500
            if len(observation) > MAX_OBS_CHARS:
                observation = observation[:MAX_OBS_CHARS] + "\n... [truncated]"

            steps.append({
                "step": step_num,
                "thought": thought,
                "action": action,
                "action_input": kwargs,
                "observation": observation,
            })

            # Keep history compact — only retain last 3 steps in full,
            # summarize older steps to prevent prompt explosion.
            step_entry = (
                f"\nStep {step_num}:\n"
                f"  Thought: {thought[:200]}\n"
                f"  Action: {action}\n"
                f"  Observation: {observation[:800]}\n"
            )
            history += step_entry

            # Hard-cap history to avoid multi-minute LLM calls
            MAX_HISTORY_CHARS = 4000
            if len(history) > MAX_HISTORY_CHARS:
                history = "... [earlier steps truncated]\n" + history[-MAX_HISTORY_CHARS:]

        # Exhausted steps — ask LLM for a summary
        summary_prompt = (
            f"You were solving this task: {task}\n\n"
            f"Here are all the steps you took:\n{history}\n\n"
            f"Provide a final summary of what was accomplished."
        )
        try:
            summary = self.llm.complete(summary_prompt, temperature=0.1)
        except Exception:
            summary = "Max steps reached. See steps for details."

        return {
            "result": summary,
            "steps": steps,
            "files_modified": files_modified,
            "status": "success",
        }

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    def _parse_react(self, raw: str) -> tuple:
        """Parse Thought / Action / Action Input from LLM output."""
        thought = action = action_input = ""

        t = re.search(r"Thought:\s*(.+?)(?=\nAction:|\Z)", raw, re.DOTALL)
        a = re.search(r"Action:\s*(.+?)(?=\nAction Input:|\Z)", raw, re.DOTALL)
        ai = re.search(r"Action Input:\s*(.+)", raw, re.DOTALL)

        thought = t.group(1).strip() if t else raw.strip()
        action = a.group(1).strip().strip("`") if a else "finish"
        action_input = ai.group(1).strip() if ai else ""

        # Small models often wrap the Action Input in backticks too – unwrap
        if action_input.startswith("`") and action_input.endswith("`"):
            action_input = action_input[1:-1].strip()

        # Handle function-call style: "file_read('pyproject.toml', 0, 5)"
        # Extract tool name and merge positional args into action_input.
        func_match = re.match(r"^(\w+)\s*\((.+)\)\s*$", action, re.DOTALL)
        if func_match:
            action = func_match.group(1)
            positional_args = func_match.group(2).strip()
            # If no Action Input was provided, use the positional args
            if not action_input:
                action_input = positional_args

        return thought, action, action_input

    def _parse_action_input(self, action: str, raw_input: str) -> Dict[str, Any]:
        """Parse action input as JSON kwargs. Falls back to positional or first-required-param."""
        # Strip wrapping backticks (small models often produce `{...}`)
        stripped = raw_input.strip().strip("`").strip()

        # Truncate at the first closing brace to discard hallucinated continuations
        if stripped.startswith("{"):
            depth = 0
            for i, ch in enumerate(stripped):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        stripped = stripped[: i + 1]
                        break
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                pass

        # Try to parse as positional args: 'pyproject.toml', 0, 5
        tool = self.tool_registry._tools.get(action)
        if tool:
            props = list(tool.parameters_schema.get("properties", {}).keys())
            # Split on comma, strip quotes/spaces
            parts = [p.strip().strip("'\"") for p in stripped.split(",")]
            if len(parts) > 1 and len(parts) <= len(props):
                result = {}
                for i, part in enumerate(parts):
                    key = props[i]
                    # Attempt numeric conversion
                    try:
                        val = int(part)
                    except (ValueError, TypeError):
                        try:
                            val = float(part)
                        except (ValueError, TypeError):
                            val = part
                    result[key] = val
                return result

            # Single value — assign to first required param
            required = tool.parameters_schema.get("required", [])
            if required:
                return {required[0]: stripped}

        return {"input": raw_input}

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def reset(self) -> None:
        self.memory = {"messages": [], "context": {}}
