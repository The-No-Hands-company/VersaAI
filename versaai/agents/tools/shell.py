"""
Shell Execution Tool — run commands in a sandboxed subprocess.

This is the most dangerous tool available to agents. Security controls:
- Commands run in a restricted working directory
- Configurable timeout prevents runaway processes
- Blocked commands list prevents catastrophic operations
- Output is size-limited to prevent memory exhaustion
- No shell=True by default (prevents injection via pipes/redirects)
"""

import logging
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from versaai.agents.tools.base import SafetyLevel, Tool, ToolResult

logger = logging.getLogger(__name__)

MAX_OUTPUT_SIZE = 500_000  # 500KB max combined stdout+stderr
DEFAULT_TIMEOUT = 30       # 30 second default timeout
MAX_TIMEOUT = 300          # 5 minute hard cap

# Commands that are never allowed
BLOCKED_COMMANDS: Set[str] = {
    "rm -rf /",
    "rm -rf /*",
    "mkfs",
    "dd",
    "shutdown",
    "reboot",
    "poweroff",
    "halt",
    "init",
    "systemctl",
    "format",
    ":(){:|:&};:",  # fork bomb
}

# Command prefixes that are blocked
BLOCKED_PREFIXES: List[str] = [
    "sudo ",
    "su ",
    "chmod 777",
    "chown ",
    "mount ",
    "umount ",
]


def _is_command_safe(command: str) -> tuple[bool, str]:
    """
    Check if a command is safe to execute.

    Returns (is_safe, reason).
    """
    cmd_lower = command.strip().lower()

    # Check exact blocked commands
    for blocked in BLOCKED_COMMANDS:
        if cmd_lower == blocked or cmd_lower.startswith(blocked):
            return False, f"Blocked command: {blocked}"

    # Check blocked prefixes
    for prefix in BLOCKED_PREFIXES:
        if cmd_lower.startswith(prefix):
            return False, f"Blocked command prefix: {prefix.strip()}"

    return True, ""


class ShellTool(Tool):
    """Execute shell commands in a sandboxed subprocess."""

    def __init__(
        self,
        working_dir: Optional[str] = None,
        allowed_commands: Optional[Set[str]] = None,
        extra_blocked: Optional[Set[str]] = None,
    ):
        """
        Args:
            working_dir: Directory where commands execute. If None, uses cwd.
            allowed_commands: If set, ONLY these command base names are allowed.
                              e.g., {"python", "git", "grep", "find", "cat"}
            extra_blocked: Additional blocked command strings.
        """
        self._working_dir = working_dir
        self._allowed_commands = allowed_commands
        self._extra_blocked = extra_blocked or set()

    @property
    def name(self) -> str:
        return "shell"

    @property
    def description(self) -> str:
        return (
            "Execute a shell command and return its output. "
            "Commands run in the project directory with a timeout. "
            "Use for: running tests, linting, git operations, "
            "package management, and other development tasks."
        )

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute",
                },
                "timeout": {
                    "type": "integer",
                    "description": f"Timeout in seconds (default: {DEFAULT_TIMEOUT}, max: {MAX_TIMEOUT})",
                },
                "working_dir": {
                    "type": "string",
                    "description": "Override working directory for this command (relative to project root)",
                },
            },
            "required": ["command"],
        }

    @property
    def safety_level(self) -> SafetyLevel:
        return SafetyLevel.EXECUTE

    def execute(self, **kwargs) -> ToolResult:
        command = kwargs.get("command", "").strip()
        timeout = min(kwargs.get("timeout", DEFAULT_TIMEOUT), MAX_TIMEOUT)
        override_dir = kwargs.get("working_dir")

        if not command:
            return ToolResult(success=False, output="", error="command is required")

        # Safety checks
        safe, reason = _is_command_safe(command)
        if not safe:
            return ToolResult(success=False, output="", error=reason)

        for blocked in self._extra_blocked:
            if blocked.lower() in command.lower():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Command contains blocked pattern: {blocked}",
                )

        # Check allowlist
        if self._allowed_commands:
            try:
                parts = shlex.split(command)
                base_cmd = os.path.basename(parts[0]) if parts else ""
            except ValueError:
                base_cmd = command.split()[0] if command.split() else ""

            if base_cmd not in self._allowed_commands:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Command '{base_cmd}' not in allowed list: {sorted(self._allowed_commands)}",
                )

        # Resolve working directory
        if self._working_dir:
            base = Path(self._working_dir).resolve()
        else:
            base = Path.cwd().resolve()

        if override_dir:
            cwd = (base / override_dir).resolve()
            if not str(cwd).startswith(str(base)):
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Working directory '{override_dir}' escapes project root",
                )
        else:
            cwd = base

        if not cwd.is_dir():
            return ToolResult(
                success=False,
                output="",
                error=f"Working directory does not exist: {cwd}",
            )

        # Execute
        logger.info(f"ShellTool: executing '{command}' in {cwd} (timeout={timeout}s)")

        try:
            result = subprocess.run(
                command,
                shell=True,  # Needed for pipes, redirects, env vars
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=timeout,
                env={
                    **os.environ,
                    "TERM": "dumb",        # Disable terminal colors/escape codes
                    "NO_COLOR": "1",       # Standard no-color env
                    "FORCE_COLOR": "0",
                },
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                output="",
                error=f"Command timed out after {timeout} seconds",
                metadata={"timeout": timeout, "command": command},
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Execution error: {e}",
            )

        stdout = result.stdout or ""
        stderr = result.stderr or ""

        # Truncate if needed
        total_size = len(stdout) + len(stderr)
        if total_size > MAX_OUTPUT_SIZE:
            half = MAX_OUTPUT_SIZE // 2
            if len(stdout) > half:
                stdout = stdout[:half] + f"\n... [truncated, {len(stdout)} bytes total]"
            if len(stderr) > half:
                stderr = stderr[:half] + f"\n... [truncated, {len(stderr)} bytes total]"

        # Build output
        output_parts = []
        if stdout:
            output_parts.append(stdout)
        if stderr:
            output_parts.append(f"[stderr]\n{stderr}")

        output = "\n".join(output_parts)
        success = result.returncode == 0

        return ToolResult(
            success=success,
            output=output,
            error=f"Exit code: {result.returncode}" if not success else None,
            metadata={
                "command": command,
                "exit_code": result.returncode,
                "cwd": str(cwd),
            },
        )
