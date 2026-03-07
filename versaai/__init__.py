"""
VersaAI: Hybrid C++/Python AI System for VersaVerse

This package provides Python interfaces to VersaAI's AI capabilities,
built on a high-performance C++ core with seamless integration to the
Python ML ecosystem.

Architecture:
- C++ Core: Performance-critical infrastructure (logging, error handling, inference)
- Python Layer: Model management, agents, RAG, tool integration
- pybind11 Bridge: Seamless C++/Python interop

Example:
    >>> from versaai import VersaAI
    >>> from versaai.models import ModelRegistry
    >>> from versaai.agents import ResearchAgent
    >>>
    >>> # Initialize core (uses C++ infrastructure)
    >>> core = VersaAI()
    >>>
    >>> # Load model (Python + HuggingFace)
    >>> model = ModelRegistry.load("meta-llama/Llama-3-8B")
    >>>
    >>> # Create agent (Python orchestration)
    >>> agent = ResearchAgent(model=model)
    >>>
    >>> # Process query (hybrid execution)
    >>> result = agent.process("What is quantum computing?")
"""

__version__ = "0.1.0"
__author__ = "The No-hands Company"

from typing import Optional

# Import C++ core bindings (Logger)
try:
    from versaai import versaai_core
    _cpp_available = True
except ImportError:
    _cpp_available = False
    import warnings
    warnings.warn(
        "C++ bindings not available. Build with: cd bindings/build && ninja\n"
        "Python-only mode will be used (slower logging)."
    )

# Python components
from versaai.core import VersaAI

__all__ = [
    "VersaAI",
    "versaai_core",  # Expose C++ bindings
    "__version__",
]


def get_version() -> str:
    """Get VersaAI version string."""
    return __version__


def init(
    log_level: str = "INFO",
    enable_cpp_logging: bool = True,
    cache_dir: Optional[str] = None
) -> VersaAI:
    """
    Initialize VersaAI with optional configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        enable_cpp_logging: Whether to enable C++ logger integration
        cache_dir: Directory for caching models and data

    Returns:
        Initialized VersaAI instance

    Example:
        >>> ai = init(log_level="DEBUG", cache_dir="~/.versaai/cache")
        >>> ai.load_model("gpt2")
    """
    return VersaAI(
        log_level=log_level,
        enable_cpp_logging=enable_cpp_logging,
        cache_dir=cache_dir
    )
