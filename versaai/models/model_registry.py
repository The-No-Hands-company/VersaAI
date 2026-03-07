"""
ModelRegistry: Central registry for loading and managing models.

This Python implementation replaces the C++ model infrastructure,
providing direct access to the Python ML ecosystem while maintaining
integration with the C++ core via pybind11.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum

from versaai.models.model_base import ModelBase, ModelMetadata

# Import C++ bindings for high-performance logging
try:
    from versaai import versaai_core
    CPP_LOGGER_AVAILABLE = True
except ImportError:
    versaai_core = None
    CPP_LOGGER_AVAILABLE = False

# Setup logger
if CPP_LOGGER_AVAILABLE:
    _cpp_logger = versaai_core.Logger.get_instance()

    class _LoggerAdapter:
        """Adapter for C++ logger to match Python logging interface."""
        def info(self, msg): _cpp_logger.info(str(msg), "ModelRegistry")
        def warning(self, msg): _cpp_logger.warning(str(msg), "ModelRegistry")
        def error(self, msg): _cpp_logger.error(str(msg), "ModelRegistry")
        def debug(self, msg): _cpp_logger.debug(str(msg), "ModelRegistry")

    logger = _LoggerAdapter()
else:
    logger = logging.getLogger(__name__)


class ModelFormat(Enum):
    """Supported model formats."""

    HUGGINGFACE = "huggingface"
    GGUF = "gguf"
    ONNX = "onnx"
    PYTORCH = "pytorch"
    SAFETENSORS = "safetensors"
    AUTO = "auto"


class ModelRegistry:
    """
    Central registry for model loading and management.

    This class provides a unified interface for loading models from
    various sources (HuggingFace, local files, etc.) and manages
    their lifecycle.

    Features:
    - Automatic format detection
    - Model caching
    - Memory management
    - Integration with C++ logger (when available)

    Example:
        >>> registry = ModelRegistry()
        >>> model = registry.load("meta-llama/Llama-3-8B")
        >>> response = model.generate("Hello, world!")
    """

    _instance: Optional['ModelRegistry'] = None

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize model registry.

        Args:
            cache_dir: Directory for caching models
        """
        self.cache_dir = cache_dir or Path.home() / ".versaai" / "models"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.models: Dict[str, ModelBase] = {}

        logger.info(f"ModelRegistry initialized (cache: {self.cache_dir})")

    @classmethod
    def get_instance(cls, cache_dir: Optional[Path] = None) -> 'ModelRegistry':
        """Get singleton instance of ModelRegistry."""
        if cls._instance is None:
            cls._instance = cls(cache_dir)
        return cls._instance

    @staticmethod
    def load(
        model_id: str,
        format: ModelFormat = ModelFormat.AUTO,
        **kwargs
    ) -> ModelBase:
        """
        Load a model by ID.

        Args:
            model_id: Model identifier (HuggingFace ID or local path)
            format: Model format (auto-detected if not specified)
            **kwargs: Format-specific loading arguments

        Returns:
            Loaded model instance

        Example:
            >>> model = ModelRegistry.load("meta-llama/Llama-3-8B")
            >>> model = ModelRegistry.load("models/llama.gguf", format=ModelFormat.GGUF)
        """
        logger.info(f"Loading model: {model_id} (format: {format.value})")

        # Auto-detect format if needed
        if format == ModelFormat.AUTO:
            format = ModelRegistry._detect_format(model_id)
            logger.debug(f"Auto-detected format: {format.value}")

        # Delegate to format-specific loader
        if format == ModelFormat.HUGGINGFACE:
            return ModelRegistry.load_huggingface(model_id, **kwargs)
        elif format == ModelFormat.GGUF:
            return ModelRegistry.load_gguf(model_id, **kwargs)
        elif format == ModelFormat.ONNX:
            return ModelRegistry.load_onnx(model_id, **kwargs)
        elif format == ModelFormat.PYTORCH:
            return ModelRegistry.load_pytorch(model_id, **kwargs)
        else:
            raise ValueError(f"Unsupported model format: {format}")

    @staticmethod
    def load_huggingface(model_id: str, **kwargs) -> ModelBase:
        """
        Load a HuggingFace model.

        Args:
            model_id: HuggingFace model ID (e.g., "meta-llama/Llama-3-8B")
            **kwargs: Arguments passed to transformers.AutoModelForCausalLM

        Returns:
            HuggingFace model wrapper
        """
        from versaai.models.huggingface_model import HuggingFaceModel

        model = HuggingFaceModel(model_id, **kwargs)
        model.load()
        return model

    @staticmethod
    def load_gguf(path: str, **kwargs) -> ModelBase:
        """
        Load a GGUF model via llama-cpp-python.

        Args:
            path: Path to GGUF file
            **kwargs: Arguments passed to llama_cpp.Llama

        Returns:
            GGUF model wrapper
        """
        from versaai.models.code_llm import LlamaCppCodeLLM

        model = LlamaCppCodeLLM(path, **kwargs)
        # LlamaCppCodeLLM loads in __init__
        return model

    @staticmethod
    def load_onnx(path: str, **kwargs) -> ModelBase:
        """Load an ONNX model."""
        raise NotImplementedError("ONNX support coming in Phase 2.2")

    @staticmethod
    def load_pytorch(path: str, **kwargs) -> ModelBase:
        """Load a PyTorch checkpoint."""
        raise NotImplementedError("PyTorch checkpoint support coming in Phase 2.2")

    @staticmethod
    def _detect_format(model_id: str) -> ModelFormat:
        """
        Auto-detect model format from ID or path.

        Args:
            model_id: Model identifier

        Returns:
            Detected format
        """
        path = Path(model_id)

        # Check file extension for local files
        if path.exists():
            suffix = path.suffix.lower()
            if suffix == ".gguf":
                return ModelFormat.GGUF
            elif suffix == ".onnx":
                return ModelFormat.ONNX
            elif suffix in [".pt", ".pth", ".bin"]:
                return ModelFormat.PYTORCH
            elif suffix == ".safetensors":
                return ModelFormat.SAFETENSORS

        # If not a local file, assume HuggingFace
        if "/" in model_id or not path.exists():
            return ModelFormat.HUGGINGFACE

        raise ValueError(f"Cannot detect format for: {model_id}")

    def register_model(self, name: str, model: ModelBase) -> None:
        """
        Register a loaded model in the registry.

        Args:
            name: Model name/identifier
            model: Model instance
        """
        self.models[name] = model
        logger.info(f"Registered model: {name}")

    def get_model(self, name: str) -> Optional[ModelBase]:
        """Get a registered model by name."""
        return self.models.get(name)

    def list_models(self) -> List[str]:
        """List all registered models."""
        return list(self.models.keys())

    def unload_model(self, name: str) -> None:
        """Unload a model from the registry."""
        if name in self.models:
            self.models[name].unload()
            del self.models[name]
            logger.info(f"Unloaded model: {name}")
