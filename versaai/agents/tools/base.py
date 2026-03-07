"""
Tool Framework Base — abstract tool interface and registry.

Every tool the agent can use inherits from Tool and implements execute().
Tools are registered in a ToolRegistry which provides:
- Lookup by name
- Automatic schema generation for LLM function-calling
- Execution dispatch

Design principles:
- Tools are stateless pure functions (input → output)
- Tools declare their parameters as JSON Schema (for LLM function calling)
- Tools return ToolResult (success/failure + output + metadata)
- Tools have safety levels (read-only, write, destructive)
- The registry sandboxes execution with timeouts and working directory constraints
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SafetyLevel(str, Enum):
    """How dangerous a tool is. Agents can be restricted to certain levels."""
    READ_ONLY = "read_only"    # File reads, searches — no side effects
    WRITE = "write"            # File writes, git operations — reversible side effects
    EXECUTE = "execute"        # Shell commands — potentially irreversible
    DESTRUCTIVE = "destructive"  # File deletes, system commands — data loss risk


@dataclass
class ToolResult:
    """
    Result of a tool execution.

    Agents parse the output field. The metadata field carries
    structured data (file paths, line numbers, etc.) for programmatic use.
    """
    success: bool
    output: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0

    def __str__(self) -> str:
        if self.success:
            return self.output
        return f"Error: {self.error}"


class Tool(ABC):
    """
    Abstract base class for all agent tools.

    Subclasses must implement:
    - name: str property — unique tool identifier (e.g., "file_read")
    - description: str property — human-readable description for LLM
    - parameters_schema: dict property — JSON Schema for parameters
    - execute(**kwargs) → ToolResult — the actual tool logic

    Example:
        class MyTool(Tool):
            @property
            def name(self) -> str:
                return "my_tool"

            @property
            def description(self) -> str:
                return "Does something useful"

            @property
            def parameters_schema(self) -> Dict[str, Any]:
                return {
                    "type": "object",
                    "properties": {
                        "input": {"type": "string", "description": "The input"},
                    },
                    "required": ["input"],
                }

            @property
            def safety_level(self) -> SafetyLevel:
                return SafetyLevel.READ_ONLY

            def execute(self, **kwargs) -> ToolResult:
                return ToolResult(success=True, output=f"Got: {kwargs['input']}")
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name. Used as the function name in LLM tool calls."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """One-line description shown to the LLM."""
        ...

    @property
    @abstractmethod
    def parameters_schema(self) -> Dict[str, Any]:
        """JSON Schema describing the tool's parameters."""
        ...

    @property
    def safety_level(self) -> SafetyLevel:
        """Safety level of this tool. Default: READ_ONLY."""
        return SafetyLevel.READ_ONLY

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with the given parameters. Must return ToolResult."""
        ...

    def to_function_schema(self) -> Dict[str, Any]:
        """
        Convert to OpenAI function-calling format.

        Returns a dict suitable for the `tools` parameter in chat completions:
        {
            "type": "function",
            "function": {
                "name": "file_read",
                "description": "Read contents of a file",
                "parameters": { ... JSON Schema ... }
            }
        }
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema,
            },
        }

    def __repr__(self) -> str:
        return f"<Tool:{self.name} [{self.safety_level.value}]>"


class ToolRegistry:
    """
    Registry of available tools.

    Provides:
    - Registration and lookup by name
    - Schema generation for LLM function-calling
    - Execution dispatch with safety checks and timeouts
    - Working directory sandboxing
    """

    def __init__(
        self,
        max_safety_level: SafetyLevel = SafetyLevel.EXECUTE,
        working_dir: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self._tools: Dict[str, Tool] = {}
        self._max_safety_level = max_safety_level
        self._working_dir = working_dir
        self._timeout = timeout
        self._execution_log: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, tool: Tool) -> None:
        """Register a tool. Raises ValueError if name conflicts."""
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' already registered")
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name} [{tool.safety_level.value}]")

    def register_defaults(self) -> None:
        """Register the standard built-in tools."""
        from versaai.agents.tools.file_ops import (
            FileReadTool,
            FileWriteTool,
            FileSearchTool,
        )
        from versaai.agents.tools.shell import ShellTool

        defaults = [
            FileReadTool(working_dir=self._working_dir),
            FileWriteTool(working_dir=self._working_dir),
            FileSearchTool(working_dir=self._working_dir),
            ShellTool(working_dir=self._working_dir, timeout=self._timeout),
        ]

        for tool in defaults:
            if tool.name not in self._tools:
                self.register(tool)

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[Tool]:
        """List all registered tools."""
        return list(self._tools.values())

    def list_names(self) -> List[str]:
        """List all tool names."""
        return list(self._tools.keys())

    # ------------------------------------------------------------------
    # Schema generation (for LLM function calling)
    # ------------------------------------------------------------------

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Get OpenAI function-calling schemas for all registered tools.

        Only includes tools at or below the max safety level.
        """
        safety_order = list(SafetyLevel)
        max_idx = safety_order.index(self._max_safety_level)

        schemas = []
        for tool in self._tools.values():
            tool_idx = safety_order.index(tool.safety_level)
            if tool_idx <= max_idx:
                schemas.append(tool.to_function_schema())
        return schemas

    def get_tool_descriptions(self) -> str:
        """
        Get a formatted text description of all tools.

        For insertion into system prompts when function-calling isn't available.
        """
        lines = ["Available tools:"]
        for tool in self._tools.values():
            params = tool.parameters_schema.get("properties", {})
            param_list = ", ".join(
                f"{k}: {v.get('type', 'any')}" for k, v in params.items()
            )
            lines.append(f"  - {tool.name}({param_list}): {tool.description}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """
        Execute a tool by name with the given arguments.

        Performs safety checks and logs execution.
        """
        tool = self._tools.get(tool_name)
        if tool is None:
            return ToolResult(
                success=False,
                output="",
                error=f"Unknown tool: {tool_name}",
            )

        # Safety check
        safety_order = list(SafetyLevel)
        tool_idx = safety_order.index(tool.safety_level)
        max_idx = safety_order.index(self._max_safety_level)
        if tool_idx > max_idx:
            return ToolResult(
                success=False,
                output="",
                error=(
                    f"Tool '{tool_name}' requires safety level "
                    f"'{tool.safety_level.value}' but max allowed is "
                    f"'{self._max_safety_level.value}'"
                ),
            )

        # Execute with timing
        start = time.monotonic()
        try:
            result = tool.execute(**kwargs)
            result.execution_time = time.monotonic() - start
        except Exception as e:
            logger.error(f"Tool '{tool_name}' failed: {e}", exc_info=True)
            result = ToolResult(
                success=False,
                output="",
                error=f"Tool execution failed: {type(e).__name__}: {e}",
                execution_time=time.monotonic() - start,
            )

        # Log execution
        self._execution_log.append({
            "tool": tool_name,
            "args": kwargs,
            "success": result.success,
            "time": result.execution_time,
            "error": result.error,
        })

        return result

    @property
    def execution_log(self) -> List[Dict[str, Any]]:
        """Get the execution log for debugging/audit."""
        return self._execution_log

    def __repr__(self) -> str:
        names = ", ".join(self._tools.keys())
        return f"ToolRegistry(tools=[{names}], max_safety={self._max_safety_level.value})"
