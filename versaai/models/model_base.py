"""
ModelBase: Abstract base class for all VersaAI models.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class ModelMetadata:
    """Metadata for a loaded model."""

    name: str
    format: str  # huggingface, gguf, onnx, pytorch
    architecture: Optional[str] = None  # llama, gpt, mistral, etc.
    parameter_count: Optional[int] = None
    context_length: Optional[int] = None
    quantization: Optional[str] = None  # Q4_0, Q5_K_M, etc.
    file_size_mb: Optional[float] = None
    memory_usage_mb: Optional[float] = None


class ModelBase(ABC):
    """
    Abstract base class for all VersaAI models.

    This class defines the interface that all models must implement,
    whether loaded via HuggingFace, llama-cpp-python, or custom loaders.

    The design mirrors the C++ ModelBase but leverages Python's ML ecosystem
    for actual model loading and inference.
    """

    def __init__(self, metadata: ModelMetadata):
        """
        Initialize model with metadata.

        Args:
            metadata: Model metadata
        """
        self.metadata = metadata
        self._loaded = False

    @abstractmethod
    def load(self) -> None:
        """
        Load the model into memory.

        This method should initialize the underlying ML framework
        (transformers, llama-cpp, etc.) and prepare the model for inference.

        Raises:
            RuntimeError: If model loading fails
        """
        pass

    @abstractmethod
    def unload(self) -> None:
        """
        Unload the model from memory.

        This method should release all resources held by the model,
        including GPU memory and cached tensors.
        """
        pass

    @abstractmethod
    def generate(
        self,
        prompt: str,
        max_tokens: int = 100,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop_sequences: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """
        Generate text from a prompt.

        Args:
            prompt: Input text prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 2.0)
            top_p: Nucleus sampling threshold
            stop_sequences: Sequences that stop generation
            **kwargs: Model-specific generation parameters

        Returns:
            Generated text

        Raises:
            RuntimeError: If model not loaded or generation fails
        """
        pass

    @abstractmethod
    def get_embeddings(self, text: str) -> List[float]:
        """
        Get embeddings for input text.

        Args:
            text: Input text

        Returns:
            List of embedding values

        Raises:
            NotImplementedError: If model doesn't support embeddings
        """
        pass

    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._loaded

    def get_metadata(self) -> ModelMetadata:
        """Get model metadata."""
        return self.metadata

    def __enter__(self):
        """Context manager entry - load model."""
        if not self._loaded:
            self.load()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - unload model."""
        if self._loaded:
            self.unload()

    def __repr__(self) -> str:
        status = "loaded" if self._loaded else "unloaded"
        return f"<{self.__class__.__name__} {self.metadata.name} ({status})>"
