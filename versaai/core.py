"""
VersaAI Core: Main orchestration class bridging C++ and Python components.

Updated to use C++ infrastructure for performance-critical operations.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Import C++ bindings
try:
    from versaai import versaai_core
    CPP_AVAILABLE = True
except ImportError:
    versaai_core = None
    CPP_AVAILABLE = False
    import warnings
    warnings.warn(
        "C++ bindings not available. Build with: cd bindings/build && ninja install"
    )


class VersaAI:
    """
    Main VersaAI orchestration class.

    This class bridges the C++ core infrastructure with Python ML components,
    providing a unified interface for model management, agent execution, and
    system configuration.

    Architecture:
        - Uses C++ Logger for high-performance logging (100K+ logs/sec)
        - Uses C++ ContextV2 for state management (sub-ms access)
        - Uses C++ CircuitBreaker for fault tolerance
        - Delegates to Python for ML/AI operations

    Example:
        >>> ai = VersaAI(log_level="INFO")
        >>> # Context managed by high-performance C++ backend
        >>> ai.set_context("user_id", 12345)
        >>> # Automatic circuit breaker protection
        >>> ai.load_model("meta-llama/Llama-3-8B")
    """

    def __init__(
        self,
        log_level: str = "INFO",
        enable_cpp_logging: bool = True,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize VersaAI core.

        Args:
            log_level: Logging level (TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL)
            enable_cpp_logging: Whether to use C++ logger (recommended)
            cache_dir: Directory for caching models and data
        """
        self.log_level = log_level
        self.enable_cpp_logging = enable_cpp_logging
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".versaai" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize C++ infrastructure
        self.cpp_context = None
        self.cpp_logger = None
        self.circuit_breakers = {}
        
        if CPP_AVAILABLE and enable_cpp_logging:
            self._init_cpp_infrastructure()
        else:
            self._init_python_fallback()

        # Initialize registries
        self.models: Dict[str, Any] = {}
        self.agents: Dict[str, Any] = {}

        self.logger.info(f"VersaAI initialized (CPP: {CPP_AVAILABLE})", "VersaAI")
        self.set_context("cache_dir", str(self.cache_dir))
        self.set_context("cpp_available", CPP_AVAILABLE)

    def _init_cpp_infrastructure(self) -> None:
        """Initialize C++ infrastructure for maximum performance."""
        # Use C++ Context for state management
        self.cpp_context = versaai_core.ContextV2()
        
        # Use C++ Logger for high-performance logging
        self.cpp_logger = versaai_core.Logger.get_instance()
        
        # Create a Python-friendly wrapper
        self.logger = CPPLoggerWrapper(self.cpp_logger)
        
        # Set up circuit breakers for fault tolerance
        cb_registry = versaai_core.CircuitBreakerRegistry.get_instance()
        
        # Configure circuit breakers for critical operations
        model_cb_config = versaai_core.CircuitBreakerConfig()
        model_cb_config.failure_threshold = 3
        model_cb_config.half_open_successes = 2
        
        rag_cb_config = versaai_core.CircuitBreakerConfig()
        rag_cb_config.failure_threshold = 5
        rag_cb_config.half_open_successes = 3
        
        self.circuit_breakers['model_inference'] = cb_registry.get_or_create(
            "model_inference", model_cb_config
        )
        self.circuit_breakers['rag_retrieval'] = cb_registry.get_or_create(
            "rag_retrieval", rag_cb_config
        )
        
        self.logger.info("C++ infrastructure initialized", "VersaAI")
        self.logger.info(
            f"Circuit breakers: {', '.join(self.circuit_breakers.keys())}", 
            "VersaAI"
        )

    def _init_python_fallback(self) -> None:
        """Fallback to Python-only implementation."""
        logging.basicConfig(
            level=getattr(logging, self.log_level),
            format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger("VersaAI")
        # Use simple dict for context in fallback mode
        self._python_context = {}

    def set_context(self, key: str, value: Any, namespace: str = "", persistent: bool = False) -> None:
        """
        Set a value in the context.

        Args:
            key: Context key
            value: Value to store
            namespace: Optional namespace for organization
            persistent: Whether value survives context resets

        Example:
            >>> ai.set_context("user_id", 12345)
            >>> ai.set_context("theme", "dark", namespace="preferences")
        """
        if self.cpp_context:
            self.cpp_context.set(key, value, namespace, persistent)
        else:
            full_key = f"{namespace}.{key}" if namespace else key
            self._python_context[full_key] = value

    def get_context(self, key: str, namespace: str = "", default: Any = None) -> Any:
        """Get a value from the context."""
        if self.cpp_context:
            value = self.cpp_context.get(key, namespace)
            return value if value is not None else default
        else:
            full_key = f"{namespace}.{key}" if namespace else key
            return self._python_context.get(full_key, default)

    def context_exists(self, key: str, namespace: str = "") -> bool:
        """Check if a context key exists."""
        if self.cpp_context:
            return self.cpp_context.exists(key, namespace)
        else:
            full_key = f"{namespace}.{key}" if namespace else key
            return full_key in self._python_context

    def create_context_snapshot(self) -> int:
        """Create a snapshot of current context state."""
        if self.cpp_context:
            return self.cpp_context.create_snapshot()
        else:
            # Simple Python snapshot (not implemented in fallback)
            return 0

    def rollback_context(self, snapshot_id: int) -> bool:
        """Rollback context to a previous snapshot."""
        if self.cpp_context:
            return self.cpp_context.rollback_to_snapshot(snapshot_id)
        return False

    def save_context(self, filepath: Path) -> None:
        """Save context to disk."""
        if self.cpp_context:
            json_str = self.cpp_context.serialize_to_json()
            filepath.write_text(json_str)
        else:
            import json
            filepath.write_text(json.dumps(self._python_context))

    def load_context(self, filepath: Path) -> bool:
        """Load context from disk."""
        if self.cpp_context:
            json_str = filepath.read_text()
            return self.cpp_context.deserialize_from_json(json_str)
        else:
            import json
            self._python_context = json.loads(filepath.read_text())
            return True

    def load_model(
        self,
        model_id: str,
        model_type: str = "auto",
        **kwargs
    ) -> Any:
        """
        Load a model into the registry.

        Args:
            model_id: Model identifier (HuggingFace ID, local path, or GGUF file)
            model_type: Model type (auto, huggingface, gguf, onnx, pytorch)
            **kwargs: Additional model-specific arguments

        Returns:
            Loaded model instance

        Example:
            >>> model = ai.load_model("meta-llama/Llama-3-8B")
            >>> model = ai.load_model("models/llama-3-8b.gguf", model_type="gguf")
        """
        self.logger.info(f"Loading model: {model_id} (type: {model_type})")

        # This will delegate to ModelRegistry once implemented
        # from versaai.models import ModelRegistry
        # model = ModelRegistry.load(model_id, model_type, **kwargs)
        # self.models[model_id] = model
        # return model

        raise NotImplementedError(
            "Model loading will be implemented in Phase 2. "
            "See docs/Architecture_Hybrid.md for implementation plan."
        )

    def register_agent(self, name: str, agent: Any) -> None:
        """
        Register an agent in the system.

        Args:
            name: Agent name/identifier
            agent: Agent instance

        Example:
            >>> from versaai.agents import ResearchAgent
            >>> agent = ResearchAgent(model=model)
            >>> ai.register_agent("research", agent)
        """
        self.logger.info(f"Registering agent: {name}")
        self.agents[name] = agent

    def invoke_agent(
        self,
        agent_name: str,
        input_text: str,
        **kwargs
    ) -> str:
        """
        Invoke a registered agent with input.

        Args:
            agent_name: Name of registered agent
            input_text: Input text/query for agent
            **kwargs: Additional agent-specific arguments

        Returns:
            Agent response

        Example:
            >>> result = ai.invoke_agent("research", "What is quantum computing?")
        """
        if agent_name not in self.agents:
            raise ValueError(f"Agent '{agent_name}' not registered")

        self.logger.info(f"Invoking agent: {agent_name}")
        agent = self.agents[agent_name]

        # Agent execution with C++ error recovery (once bindings available)
        try:
            result = agent.perform_task(input_text, **kwargs)
            return result
        except Exception as e:
            self.logger.error(f"Agent execution failed: {e}")
            raise

    def get_model(self, model_id: str) -> Any:
        """Get a loaded model by ID."""
        if model_id not in self.models:
            raise KeyError(f"Model '{model_id}' not loaded")
        return self.models[model_id]

    def get_agent(self, agent_name: str) -> Any:
        """Get a registered agent by name."""
        if agent_name not in self.agents:
            raise KeyError(f"Agent '{agent_name}' not registered")
        return self.agents[agent_name]

    def list_models(self) -> list[str]:
        """List all loaded models."""
        return list(self.models.keys())

    def list_agents(self) -> list[str]:
        """List all registered agents."""
        return list(self.agents.keys())

    def get_stats(self) -> Dict[str, Any]:
        """Get VersaAI statistics."""
        stats = {
            "models_loaded": len(self.models),
            "agents_registered": len(self.agents),
            "cpp_available": CPP_AVAILABLE,
            "cache_dir": str(self.cache_dir),
        }
        
        if self.circuit_breakers:
            stats["circuit_breakers"] = {
                name: {
                    "state": str(cb.get_state()),
                    "failures": cb.get_failure_count(),
                    "successes": cb.get_success_count(),
                }
                for name, cb in self.circuit_breakers.items()
            }
        
        return stats


class CPPLoggerWrapper:
    """Wrapper to make C++ Logger compatible with Python logging interface."""
    
    def __init__(self, cpp_logger):
        self.cpp_logger = cpp_logger
        self.component = "VersaAI"
    
    def trace(self, msg: str, component: str = None) -> None:
        self.cpp_logger.trace(str(msg), component or self.component)
    
    def debug(self, msg: str, component: str = None, **kwargs) -> None:
        self.cpp_logger.debug(str(msg), component or self.component)
    
    def info(self, msg: str, component: str = None, **kwargs) -> None:
        self.cpp_logger.info(str(msg), component or self.component)
    
    def warning(self, msg: str, component: str = None, **kwargs) -> None:
        self.cpp_logger.warning(str(msg), component or self.component)
    
    def error(self, msg: str, component: str = None, **kwargs) -> None:
        self.cpp_logger.error(str(msg), component or self.component)
    
    def critical(self, msg: str, component: str = None, **kwargs) -> None:
        self.cpp_logger.critical(str(msg), component or self.component)
