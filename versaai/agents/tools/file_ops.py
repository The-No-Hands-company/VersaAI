"""
File Operations Tools — read, write, and search files.

These are the most fundamental tools agents use. Every coding task
requires reading existing code and writing modified code.

Security:
- All paths are resolved relative to working_dir (no escaping)
- Symlinks are resolved and checked against working_dir
- Binary files are detected and rejected
- File size limits prevent memory exhaustion
"""

import fnmatch
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from versaai.agents.tools.base import SafetyLevel, Tool, ToolResult

logger = logging.getLogger(__name__)

MAX_READ_SIZE = 1_000_000     # 1MB max read
MAX_WRITE_SIZE = 1_000_000    # 1MB max write
MAX_SEARCH_RESULTS = 100      # Max files returned by search


def _resolve_safe_path(file_path: str, working_dir: Optional[str]) -> Path:
    """
    Resolve a file path securely.

    - Relative paths are resolved against working_dir
    - Absolute paths are checked to be under working_dir (if set)
    - Symlinks are resolved and re-checked
    - Raises ValueError if path escapes working_dir
    """
    if working_dir:
        base = Path(working_dir).resolve()
        candidate = (base / file_path).resolve()
        if not str(candidate).startswith(str(base)):
            raise ValueError(
                f"Path '{file_path}' resolves to '{candidate}' which is "
                f"outside working directory '{base}'"
            )
        return candidate
    else:
        return Path(file_path).resolve()


def _is_binary(path: Path, check_bytes: int = 8192) -> bool:
    """Heuristic binary file detection."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(check_bytes)
        # Check for null bytes (strong binary indicator)
        if b"\x00" in chunk:
            return True
        # Check ratio of non-text bytes
        text_chars = set(range(32, 127)) | {9, 10, 13}  # printable + tab/newline/cr
        non_text = sum(1 for b in chunk if b not in text_chars)
        return non_text / max(len(chunk), 1) > 0.3
    except Exception:
        return True


# ============================================================================
# FileReadTool
# ============================================================================

class FileReadTool(Tool):
    """Read contents of a file, optionally with line range."""

    def __init__(self, working_dir: Optional[str] = None):
        self._working_dir = working_dir

    @property
    def name(self) -> str:
        return "file_read"

    @property
    def description(self) -> str:
        return (
            "Read the contents of a file. Returns the text content. "
            "Optionally specify start_line and end_line for a range."
        )

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path (relative to project root or absolute)",
                },
                "start_line": {
                    "type": "integer",
                    "description": "First line to read (1-based, inclusive). Default: 1",
                },
                "end_line": {
                    "type": "integer",
                    "description": "Last line to read (1-based, inclusive). Default: end of file",
                },
            },
            "required": ["path"],
        }

    @property
    def safety_level(self) -> SafetyLevel:
        return SafetyLevel.READ_ONLY

    def execute(self, **kwargs) -> ToolResult:
        path_str = kwargs.get("path", "")
        start_line = kwargs.get("start_line")
        end_line = kwargs.get("end_line")

        if not path_str:
            return ToolResult(success=False, output="", error="path is required")

        try:
            path = _resolve_safe_path(path_str, self._working_dir)
        except ValueError as e:
            return ToolResult(success=False, output="", error=str(e))

        if not path.exists():
            return ToolResult(
                success=False, output="", error=f"File not found: {path_str}"
            )

        if not path.is_file():
            return ToolResult(
                success=False, output="", error=f"Not a file: {path_str}"
            )

        if path.stat().st_size > MAX_READ_SIZE:
            return ToolResult(
                success=False,
                output="",
                error=f"File too large ({path.stat().st_size} bytes, max {MAX_READ_SIZE})",
            )

        if _is_binary(path):
            return ToolResult(
                success=False, output="", error=f"Binary file: {path_str}"
            )

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Read error: {e}")

        # Apply line range if specified
        lines = content.splitlines(keepends=True)
        total_lines = len(lines)

        if start_line is not None or end_line is not None:
            start = max(1, start_line or 1) - 1  # Convert to 0-based
            end = min(total_lines, end_line or total_lines)
            lines = lines[start:end]
            content = "".join(lines)
            range_info = f" (lines {start + 1}-{end} of {total_lines})"
        else:
            range_info = f" ({total_lines} lines)"

        return ToolResult(
            success=True,
            output=content,
            metadata={
                "path": str(path),
                "total_lines": total_lines,
                "range": range_info.strip(),
            },
        )


# ============================================================================
# FileWriteTool
# ============================================================================

class FileWriteTool(Tool):
    """Write content to a file. Creates parent directories if needed."""

    def __init__(self, working_dir: Optional[str] = None):
        self._working_dir = working_dir

    @property
    def name(self) -> str:
        return "file_write"

    @property
    def description(self) -> str:
        return (
            "Write content to a file. Creates the file if it doesn't exist. "
            "Creates parent directories automatically. "
            "Use mode='append' to append instead of overwrite."
        )

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path to write to",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write",
                },
                "mode": {
                    "type": "string",
                    "enum": ["overwrite", "append"],
                    "description": "Write mode. Default: overwrite",
                },
            },
            "required": ["path", "content"],
        }

    @property
    def safety_level(self) -> SafetyLevel:
        return SafetyLevel.WRITE

    def execute(self, **kwargs) -> ToolResult:
        path_str = kwargs.get("path", "")
        content = kwargs.get("content", "")
        mode = kwargs.get("mode", "overwrite")

        if not path_str:
            return ToolResult(success=False, output="", error="path is required")

        if len(content) > MAX_WRITE_SIZE:
            return ToolResult(
                success=False,
                output="",
                error=f"Content too large ({len(content)} bytes, max {MAX_WRITE_SIZE})",
            )

        try:
            path = _resolve_safe_path(path_str, self._working_dir)
        except ValueError as e:
            return ToolResult(success=False, output="", error=str(e))

        try:
            path.parent.mkdir(parents=True, exist_ok=True)

            if mode == "append":
                with open(path, "a", encoding="utf-8") as f:
                    f.write(content)
            else:
                path.write_text(content, encoding="utf-8")

            return ToolResult(
                success=True,
                output=f"Wrote {len(content)} bytes to {path_str}",
                metadata={"path": str(path), "bytes_written": len(content)},
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Write error: {e}")


# ============================================================================
# FileSearchTool
# ============================================================================

class FileSearchTool(Tool):
    """Search for files by name pattern or content grep."""

    def __init__(self, working_dir: Optional[str] = None):
        self._working_dir = working_dir

    @property
    def name(self) -> str:
        return "file_search"

    @property
    def description(self) -> str:
        return (
            "Search for files in the project. "
            "Use 'pattern' for filename glob matching (e.g., '*.py'). "
            "Use 'content' for text search within files (grep). "
            "Both can be combined."
        )

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern for filenames (e.g., '*.py', 'src/**/*.ts')",
                },
                "content": {
                    "type": "string",
                    "description": "Text to search for within files (case-insensitive)",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results. Default: 20",
                },
            },
        }

    @property
    def safety_level(self) -> SafetyLevel:
        return SafetyLevel.READ_ONLY

    def execute(self, **kwargs) -> ToolResult:
        pattern = kwargs.get("pattern")
        content_query = kwargs.get("content")
        max_results = min(kwargs.get("max_results", 20), MAX_SEARCH_RESULTS)

        if not pattern and not content_query:
            return ToolResult(
                success=False,
                output="",
                error="At least one of 'pattern' or 'content' is required",
            )

        base_dir = Path(self._working_dir) if self._working_dir else Path.cwd()
        base_dir = base_dir.resolve()

        # Directories to skip
        skip_dirs = {
            ".git", "__pycache__", "node_modules", ".venv", "venv",
            "build", "dist", ".tox", ".mypy_cache", ".ruff_cache",
            ".eggs", "*.egg-info",
        }

        results: List[Dict[str, Any]] = []

        try:
            for root, dirs, files in os.walk(base_dir):
                # Prune skip directories
                dirs[:] = [
                    d for d in dirs
                    if d not in skip_dirs and not d.endswith(".egg-info")
                ]

                for fname in files:
                    if len(results) >= max_results:
                        break

                    full_path = Path(root) / fname
                    rel_path = full_path.relative_to(base_dir)

                    # Pattern filter
                    if pattern and not fnmatch.fnmatch(str(rel_path), pattern):
                        if not fnmatch.fnmatch(fname, pattern):
                            continue

                    # Content filter
                    if content_query:
                        if _is_binary(full_path):
                            continue
                        if full_path.stat().st_size > MAX_READ_SIZE:
                            continue
                        try:
                            text = full_path.read_text(
                                encoding="utf-8", errors="replace"
                            )
                            if content_query.lower() not in text.lower():
                                continue
                            # Find matching lines
                            matching_lines = [
                                (i + 1, line.rstrip())
                                for i, line in enumerate(text.splitlines())
                                if content_query.lower() in line.lower()
                            ]
                            results.append({
                                "path": str(rel_path),
                                "matches": matching_lines[:5],  # First 5 matches
                            })
                        except Exception:
                            continue
                    else:
                        results.append({"path": str(rel_path)})

                if len(results) >= max_results:
                    break

        except Exception as e:
            return ToolResult(success=False, output="", error=f"Search error: {e}")

        if not results:
            return ToolResult(
                success=True,
                output="No files found matching the criteria.",
                metadata={"count": 0},
            )

        # Format output
        lines = []
        for r in results:
            lines.append(r["path"])
            for match in r.get("matches", []):
                lines.append(f"  L{match[0]}: {match[1][:120]}")

        return ToolResult(
            success=True,
            output="\n".join(lines),
            metadata={"count": len(results), "files": [r["path"] for r in results]},
        )
