"""
HuggingFace Model Wrapper: Integration with transformers library.

This module provides a VersaAI ModelBase wrapper around HuggingFace's
transformers library, enabling seamless loading and usage of any model
from the HuggingFace Hub.

Example:
    >>> from versaai.models.huggingface_model import HuggingFaceModel
    >>>
    >>> # Load model
    >>> model = HuggingFaceModel("meta-llama/Llama-3-8B")
    >>> model.load()
    >>>
    >>> # Generate text
    >>> response = model.generate("What is AI?", max_tokens=100)
    >>>
    >>> # Get embeddings (if supported)
    >>> embeddings = model.get_embeddings("Hello world")
"""

import logging
from typing import Optional, List, Dict, Any
import torch

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
        def info(self, msg): _cpp_logger.info(str(msg), "HuggingFaceModel")
        def warning(self, msg): _cpp_logger.warning(str(msg), "HuggingFaceModel")
        def error(self, msg): _cpp_logger.error(str(msg), "HuggingFaceModel")
        def debug(self, msg): _cpp_logger.debug(str(msg), "HuggingFaceModel")

    logger = _LoggerAdapter()
else:
    logger = logging.getLogger(__name__)


class HuggingFaceModel(ModelBase):
    """
    HuggingFace model wrapper for VersaAI.

    This class wraps models from the HuggingFace transformers library,
    providing a unified interface consistent with VersaAI's ModelBase.

    Features:
    - Automatic model and tokenizer loading
    - GPU acceleration (if available)
    - Streaming generation support
    - Embeddings extraction (for encoder models)

    Example:
        >>> model = HuggingFaceModel("gpt2")
        >>> model.load()
        >>> text = model.generate("Once upon a time", max_tokens=50)
    """

    def __init__(
        self,
        model_id: str,
        device: Optional[str] = None,
        torch_dtype: Optional[torch.dtype] = None,
        load_in_8bit: bool = False,
        load_in_4bit: bool = False,
        **kwargs
    ):
        """
        Initialize HuggingFace model wrapper.

        Args:
            model_id: HuggingFace model identifier (e.g., "gpt2", "meta-llama/Llama-3-8B")
            device: Device to load model on ("cuda", "cpu", or None for auto)
            torch_dtype: Torch dtype for model weights (float16, bfloat16, etc.)
            load_in_8bit: Load model with 8-bit quantization (requires bitsandbytes)
            load_in_4bit: Load model with 4-bit quantization (requires bitsandbytes)
            **kwargs: Additional arguments passed to AutoModelForCausalLM.from_pretrained
        """
        # Create metadata
        metadata = ModelMetadata(
            name=model_id,
            format="huggingface",
            architecture=None,  # Will be set after loading
        )
        super().__init__(metadata)

        self.model_id = model_id
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.torch_dtype = torch_dtype or torch.float16
        self.load_in_8bit = load_in_8bit
        self.load_in_4bit = load_in_4bit
        self.load_kwargs = kwargs

        # Model components (initialized in load())
        self.model = None
        self.tokenizer = None

        logger.info(f"HuggingFaceModel initialized: {model_id} (device: {self.device})")

    def load(self) -> None:
        """Load model and tokenizer from HuggingFace Hub."""
        if self._loaded:
            logger.warning(f"Model {self.model_id} already loaded")
            return

        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer

            logger.info(f"Loading HuggingFace model: {self.model_id}")

            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_id,
                trust_remote_code=True
            )

            # Ensure padding token is set
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            # Prepare model loading kwargs
            model_kwargs = {
                "trust_remote_code": True,
                **self.load_kwargs
            }

            # Add quantization if requested
            if self.load_in_8bit:
                model_kwargs["load_in_8bit"] = True
                self.metadata.quantization = "int8"
            elif self.load_in_4bit:
                model_kwargs["load_in_4bit"] = True
                self.metadata.quantization = "int4"
            else:
                model_kwargs["dtype"] = self.torch_dtype

            # Load model
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                **model_kwargs
            )

            # Move to device if not quantized (quantized models handle device internally)
            if not (self.load_in_8bit or self.load_in_4bit):
                self.model = self.model.to(self.device)

            # Update metadata
            self.metadata.architecture = self.model.config.model_type
            if hasattr(self.model.config, "num_parameters"):
                self.metadata.parameter_count = self.model.config.num_parameters
            if hasattr(self.model.config, "max_position_embeddings"):
                self.metadata.context_length = self.model.config.max_position_embeddings

            # Calculate memory usage
            self.metadata.memory_usage_mb = self._estimate_memory_usage()

            self._loaded = True
            logger.info(f"Model loaded: {self.model_id} ({self.metadata.parameter_count} params)")

        except Exception as e:
            logger.error(f"Failed to load model {self.model_id}: {e}")
            raise RuntimeError(f"Model loading failed: {e}") from e

    def unload(self) -> None:
        """Unload model from memory."""
        if not self._loaded:
            return

        logger.info(f"Unloading model: {self.model_id}")

        # Delete model and tokenizer
        del self.model
        del self.tokenizer
        self.model = None
        self.tokenizer = None

        # Clear CUDA cache if using GPU
        if self.device == "cuda":
            torch.cuda.empty_cache()

        self._loaded = False
        logger.info(f"Model unloaded: {self.model_id}")

    def generate(
        self,
        prompt: str,
        max_tokens: int = 100,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50,
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
            stop_sequences: Sequences that stop generation (not yet supported)
            stream: Whether to stream output (not yet supported)
            **kwargs: Additional generation parameters

        Returns:
            Generated text

        Raises:
            RuntimeError: If model not loaded
        """
        if not self._loaded:
            raise RuntimeError(f"Model {self.model_id} not loaded. Call load() first.")

        # Tokenize input
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            padding=True
        ).to(self.device)

        # Prepare generation kwargs
        gen_kwargs = {
            "max_new_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "do_sample": temperature > 0,
            "pad_token_id": self.tokenizer.pad_token_id,
            **kwargs
        }

        # Generate
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                **gen_kwargs
            )

        # Decode output (skip the input tokens)
        generated_text = self.tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True
        )

        return generated_text

    def get_embeddings(self, text: str) -> List[float]:
        """
        Get embeddings for input text.

        For causal LMs, this returns the last hidden state.
        For encoder models, use HuggingFaceEmbeddingModel instead.

        Args:
            text: Input text

        Returns:
            List of embedding values

        Raises:
            RuntimeError: If model not loaded
        """
        if not self._loaded:
            raise RuntimeError(f"Model {self.model_id} not loaded. Call load() first.")

        # Tokenize
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            padding=True
        ).to(self.device)

        # Get hidden states
        with torch.no_grad():
            outputs = self.model(**inputs, output_hidden_states=True)
            # Get last layer's last token embedding
            last_hidden_state = outputs.hidden_states[-1]
            embeddings = last_hidden_state[0, -1, :].cpu().numpy()

        return embeddings

    def _estimate_memory_usage(self) -> float:
        """
        Estimate memory usage in MB.

        Returns:
            Estimated memory usage in megabytes
        """
        if self.model is None:
            return 0.0

        # Count parameters
        param_count = sum(p.numel() for p in self.model.parameters())

        # Estimate bytes per parameter based on dtype
        if self.load_in_8bit:
            bytes_per_param = 1
        elif self.load_in_4bit:
            bytes_per_param = 0.5
        elif self.torch_dtype == torch.float16 or self.torch_dtype == torch.bfloat16:
            bytes_per_param = 2
        else:
            bytes_per_param = 4

        # Calculate MB
        memory_mb = (param_count * bytes_per_param) / (1024 * 1024)
        return memory_mb

    def __repr__(self) -> str:
        status = "loaded" if self._loaded else "unloaded"
        device_str = f", device={self.device}" if self._loaded else ""
        return f"<HuggingFaceModel {self.model_id} ({status}{device_str})>"
