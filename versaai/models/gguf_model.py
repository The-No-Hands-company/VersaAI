"""
GGUF Model Wrapper: Integration with llama-cpp-python.

This module provides a VersaAI ModelBase wrapper around llama-cpp-python,
enabling efficient loading and usage of GGUF quantized models.

Example:
    >>> from versaai.models.gguf_model import GGUFModel
    >>>
    >>> # Load GGUF model
    >>> model = GGUFModel("models/llama-3-8b-q4_0.gguf")
    >>> model.load()
    >>>
    >>> # Generate text
    >>> response = model.generate("What is AI?", max_tokens=100)
"""

import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

from versaai.models.model_base import ModelBase, ModelMetadata


logger = logging.getLogger(__name__)


class GGUFModel(ModelBase):
    """
    GGUF model wrapper for VersaAI via llama-cpp-python.

    This class wraps GGUF models (llama.cpp format) for efficient inference,
    particularly useful for quantized models running on CPU or Metal/CUDA.

    Features:
    - Memory-efficient quantized inference
    - CPU, CUDA, and Metal backend support
    - Low memory footprint
    - Fast inference on consumer hardware

    Example:
        >>> model = GGUFModel("models/llama-3-8b-q4_0.gguf", n_ctx=4096, n_gpu_layers=32)
        >>> model.load()
        >>> text = model.generate("Once upon a time", max_tokens=50)
    """

    def __init__(
        self,
        model_path: str,
        n_ctx: int = 2048,
        n_gpu_layers: int = 0,
        n_threads: Optional[int] = None,
        use_mmap: bool = True,
        use_mlock: bool = False,
        **kwargs
    ):
        """
        Initialize GGUF model wrapper.

        Args:
            model_path: Path to GGUF model file
            n_ctx: Context window size
            n_gpu_layers: Number of layers to offload to GPU (0 for CPU-only)
            n_threads: Number of threads for CPU inference (None for auto)
            use_mmap: Use memory mapping for faster loading
            use_mlock: Lock model in RAM to prevent swapping
            **kwargs: Additional arguments passed to llama_cpp.Llama
        """
        # Validate path
        path = Path(model_path)
        if not path.exists():
            raise FileNotFoundError(f"GGUF model not found: {model_path}")

        # Create metadata
        metadata = ModelMetadata(
            name=path.stem,
            format="gguf",
            architecture=self._detect_architecture(path.name),
            context_length=n_ctx,
            file_size_mb=path.stat().st_size / (1024 * 1024)
        )
        super().__init__(metadata)

        self.model_path = str(path)
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self.n_threads = n_threads
        self.use_mmap = use_mmap
        self.use_mlock = use_mlock
        self.load_kwargs = kwargs

        # Model instance (initialized in load())
        self.model = None

        logger.info(f"GGUFModel initialized: {self.model_path} (GPU layers: {n_gpu_layers})")

    def load(self) -> None:
        """Load GGUF model via llama-cpp-python."""
        if self._loaded:
            logger.warning(f"Model {self.metadata.name} already loaded")
            return

        try:
            from llama_cpp import Llama

            logger.info(f"Loading GGUF model: {self.model_path}")

            # Load model
            self.model = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_gpu_layers=self.n_gpu_layers,
                n_threads=self.n_threads,
                use_mmap=self.use_mmap,
                use_mlock=self.use_mlock,
                verbose=False,
                **self.load_kwargs
            )

            # Detect quantization from filename
            self.metadata.quantization = self._detect_quantization(Path(self.model_path).name)

            # Get model metadata from llama.cpp
            if hasattr(self.model, "metadata"):
                metadata_dict = self.model.metadata
                if "llama.context_length" in metadata_dict:
                    self.metadata.context_length = int(metadata_dict["llama.context_length"])

            self._loaded = True
            logger.info(f"GGUF model loaded: {self.metadata.name}")

        except ImportError:
            logger.error("llama-cpp-python not installed. Install with: uv pip install llama-cpp-python")
            raise RuntimeError(
                "llama-cpp-python required for GGUF support. "
                "Install with: uv pip install llama-cpp-python"
            )
        except Exception as e:
            logger.error(f"Failed to load GGUF model: {e}")
            raise RuntimeError(f"GGUF model loading failed: {e}") from e

    def unload(self) -> None:
        """Unload GGUF model from memory."""
        if not self._loaded:
            return

        logger.info(f"Unloading GGUF model: {self.metadata.name}")

        # Delete model
        del self.model
        self.model = None

        self._loaded = False
        logger.info(f"GGUF model unloaded: {self.metadata.name}")

    def generate(
        self,
        prompt: str,
        max_tokens: int = 100,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40,
        stop_sequences: Optional[List[str]] = None,
        stream: bool = False,
        **kwargs
    ) -> str:
        """
        Generate text from a prompt.

        Args:
            prompt: Input text prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 2.0)
            top_p: Nucleus sampling threshold
            top_k: Top-k sampling parameter
            stop_sequences: Sequences that stop generation
            stream: Whether to stream output (not yet supported)
            **kwargs: Additional generation parameters

        Returns:
            Generated text

        Raises:
            RuntimeError: If model not loaded
        """
        if not self._loaded:
            raise RuntimeError(f"Model {self.metadata.name} not loaded. Call load() first.")

        # Prepare generation kwargs
        gen_kwargs = {
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "stop": stop_sequences or [],
            "echo": False,  # Don't echo the prompt
            **kwargs
        }

        # Generate
        output = self.model(
            prompt,
            **gen_kwargs
        )

        # Extract generated text
        generated_text = output["choices"][0]["text"]

        return generated_text

    def get_embeddings(self, text: str) -> List[float]:
        """
        Get embeddings for input text.

        Args:
            text: Input text

        Returns:
            List of embedding values

        Raises:
            RuntimeError: If model not loaded
        """
        if not self._loaded:
            raise RuntimeError(f"Model {self.metadata.name} not loaded. Call load() first.")

        # Create embedding
        embedding = self.model.embed(text)

        return embedding

    @staticmethod
    def _detect_architecture(filename: str) -> Optional[str]:
        """
        Detect model architecture from filename.

        Args:
            filename: Model filename

        Returns:
            Detected architecture or None
        """
        filename_lower = filename.lower()

        if "llama" in filename_lower:
            return "llama"
        elif "mistral" in filename_lower:
            return "mistral"
        elif "mixtral" in filename_lower:
            return "mixtral"
        elif "gemma" in filename_lower:
            return "gemma"
        elif "phi" in filename_lower:
            return "phi"
        elif "gpt" in filename_lower:
            return "gpt"

        return None

    @staticmethod
    def _detect_quantization(filename: str) -> Optional[str]:
        """
        Detect quantization type from filename.

        Args:
            filename: Model filename

        Returns:
            Detected quantization type or None
        """
        filename_lower = filename.lower()

        # Common GGUF quantization schemes
        quant_types = [
            "q2_k", "q3_k_s", "q3_k_m", "q3_k_l",
            "q4_0", "q4_1", "q4_k_s", "q4_k_m",
            "q5_0", "q5_1", "q5_k_s", "q5_k_m",
            "q6_k", "q8_0"
        ]

        for quant in quant_types:
            if quant in filename_lower:
                return quant.upper()

        return None

    def __repr__(self) -> str:
        status = "loaded" if self._loaded else "unloaded"
        quant_str = f", quant={self.metadata.quantization}" if self.metadata.quantization else ""
        return f"<GGUFModel {self.metadata.name} ({status}{quant_str})>"
