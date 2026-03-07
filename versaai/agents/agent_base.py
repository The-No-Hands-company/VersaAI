"""
AgentBase: Abstract base class for all VersaAI agents.

This mirrors the C++ AgentBase design but leverages Python's ML ecosystem
for actual agent implementation using LangChain.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# Import C++ bindings for high-performance logging
try:
    from versaai import versaai_core
    CPP_LOGGER_AVAILABLE = True
except ImportError:
    versaai_core = None
    CPP_LOGGER_AVAILABLE = False


@dataclass
class AgentMetadata:
    """Metadata for an agent."""

    name: str
    description: str
    version: str = "1.0.0"
    capabilities: List[str] = None

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []


class AgentBase(ABC):
    """
    Abstract base class for all VersaAI agents.

    Agents are specialized AI systems that can:
    - Execute multi-step tasks (planning, execution, verification)
    - Use external tools (search, calculator, code execution)
    - Maintain conversation memory and context
    - Leverage RAG for knowledge-grounded responses

    Design Pattern:
        - Python implementation uses LangChain for agent orchestration
        - C++ logger for performance-critical logging
        - Integration with VersaAI ModelRegistry for model access
    """

    def __init__(self, metadata: AgentMetadata):
        """
        Initialize agent with metadata.

        Args:
            metadata: Agent metadata
        """
        self.metadata = metadata
        self._initialized = False

        # Setup logger — always use Python logging so output goes to stderr.
        # If C++ bindings are available, also forward to the C++ logger.
        import logging
        py_logger = logging.getLogger(f"versaai.agents.{metadata.name}")

        if CPP_LOGGER_AVAILABLE:
            self._cpp_logger = versaai_core.Logger.get_instance()
            self.logger = self._create_dual_logger(py_logger)
        else:
            self.logger = py_logger

    def _create_dual_logger(self, py_logger):
        """Create adapter that logs to both C++ logger and Python logger."""
        component = f"Agent.{self.metadata.name}"
        cpp_logger = self._cpp_logger

        class DualLoggerAdapter:
            def __init__(self):
                pass

            def debug(self, msg):
                py_logger.debug(msg)
                try:
                    cpp_logger.debug(str(msg), component)
                except Exception:
                    pass

            def info(self, msg):
                py_logger.info(msg)
                try:
                    cpp_logger.info(str(msg), component)
                except Exception:
                    pass

            def warning(self, msg):
                py_logger.warning(msg)
                try:
                    cpp_logger.warning(str(msg), component)
                except Exception:
                    pass

            def error(self, msg):
                py_logger.error(msg)
                try:
                    cpp_logger.error(str(msg), component)
                except Exception:
                    pass

            def critical(self, msg):
                py_logger.critical(msg)
                try:
                    cpp_logger.critical(str(msg), component)
                except Exception:
                    pass

        return DualLoggerAdapter()

    @abstractmethod
    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize agent with configuration.

        This should set up:
        - LangChain components (LLM, tools, memory)
        - RAG pipeline (vector DB, retrievers)
        - Any external service connections

        Args:
            config: Agent configuration dictionary
        """
        pass

    @abstractmethod
    def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a task.

        Args:
            task: Task description or query
            context: Additional context for task execution

        Returns:
            Dictionary with execution results:
                {
                    "result": "...",  # Primary result
                    "sources": [...],  # Source citations (if RAG used)
                    "steps": [...],    # Execution steps taken
                    "metadata": {...}  # Additional metadata
                }
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """
        Reset agent state (clear memory, reset tools).
        """
        pass

    def get_capabilities(self) -> List[str]:
        """Get list of agent capabilities."""
        return self.metadata.capabilities

    def is_initialized(self) -> bool:
        """Check if agent is initialized."""
        return self._initialized
