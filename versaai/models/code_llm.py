"""
Real Code LLM Integration - Production-grade code model implementations

This module provides actual LLM integrations for the CodeModel:
1. Local models via llama.cpp (GGUF format)
2. HuggingFace transformers
3. OpenAI API
4. Anthropic Claude API

Usage:
    # Local model
    model = LlamaCppCodeLLM("./models/deepseek-coder-6.7b.gguf")

    # HuggingFace model
    model = HuggingFaceCodeLLM("bigcode/starcoder2-7b")

    # OpenAI API
    model = OpenAICodeLLM("gpt-4-turbo")

    # Anthropic API
    model = AnthropicCodeLLM("claude-3-sonnet")
"""

import os
import logging
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
from dataclasses import dataclass

try:
    from versaai import versaai_core
    CPP_LOGGER = versaai_core.Logger.get_instance()
except ImportError:
    CPP_LOGGER = None


@dataclass
class GenerationConfig:
    """Configuration for code generation"""
    max_tokens: int = 1024
    temperature: float = 0.7
    top_p: float = 0.95
    top_k: int = 50
    stop_sequences: List[str] = None

    def __post_init__(self):
        if self.stop_sequences is None:
            self.stop_sequences = ["```\n", "\n\n\n", "<|EOT|>", "</s>", "<|endoftext|>"]


class CodeLLMBase(ABC):
    """Base class for code LLM implementations"""

    def __init__(self, model_id: str):
        self.model_id = model_id
        self.logger = logging.getLogger(__name__)

    @abstractmethod
    def generate(self, prompt: str, config: GenerationConfig, stream: bool = False) -> Any:
        """
        Generate code from prompt.

        Args:
            prompt: Input prompt
            config: Generation configuration
            stream: If True, returns a generator yielding tokens/text chunks.
                   If False, returns variable string.
        """
        pass

    @abstractmethod
    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        pass

    def _log(self, message: str, level: str = "INFO"):
        """Log with C++ logger if available"""
        if CPP_LOGGER:
            getattr(CPP_LOGGER, level.lower())(message, "CodeLLM")
        else:
            getattr(self.logger, level.lower())(message)


# ============================================================================
# LOCAL MODELS (llama.cpp/GGUF)
# ============================================================================

class LlamaCppCodeLLM(CodeLLMBase):
    """
    Local code LLM using llama.cpp (GGUF format)

    Supports models like:
    - DeepSeek-Coder (6.7B, 33B)
    - StarCoder2 (7B, 15B)
    - CodeLlama (7B, 13B, 34B)

    Example:
        >>> llm = LlamaCppCodeLLM("./models/deepseek-coder-6.7b.Q4_K_M.gguf")
        >>> code = llm.generate("def fibonacci(n):", GenerationConfig())
    """

    def __init__(
        self,
        model_path: str,
        n_ctx: int = 4096,
        n_gpu_layers: int = -1,  # -1 = all layers to GPU
        n_threads: Optional[int] = None,
        verbose: bool = False
    ):
        super().__init__(model_path)
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self.n_threads = n_threads
        self.verbose = verbose
        self._model = None

        self._load_model()

    def _load_model(self):
        """Load llama.cpp model"""
        try:
            from llama_cpp import Llama

            self._log(f"Loading GGUF model from {self.model_path}", "INFO")

            self._model = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_gpu_layers=self.n_gpu_layers,
                n_threads=self.n_threads,
                verbose=self.verbose
            )

            self._log(f"Model loaded successfully", "INFO")

        except ImportError:
            raise ImportError(
                "llama-cpp-python not installed. "
                "Install with: pip install llama-cpp-python"
            )
        except Exception as e:
            self._log(f"Failed to load model: {e}", "ERROR")
            raise

    def generate(self, prompt: str, config: GenerationConfig, stream: bool = False) -> Any:
        """Generate code using llama.cpp"""
        if not self.is_loaded():
            raise RuntimeError("Model not loaded")

        try:
            output = self._model(
                prompt,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                top_p=config.top_p,
                top_k=config.top_k,
                stop=config.stop_sequences,
                echo=False,
                stream=stream
            )

            if stream:
                return output # Generator of tokens
            else:
                return output["choices"][0]["text"]

        except Exception as e:
            self._log(f"Generation failed: {e}", "ERROR")
            raise

    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self._model is not None


# ============================================================================
# HUGGINGFACE MODELS
# ============================================================================

class HuggingFaceCodeLLM(CodeLLMBase):
    """
    HuggingFace transformers code LLM

    Supports models like:
    - bigcode/starcoder2-7b
    - bigcode/starcoder2-15b
    - Salesforce/codegen-350M-mono
    - microsoft/phi-2
    - WizardLM/WizardCoder-15B-V1.0

    Example:
        >>> llm = HuggingFaceCodeLLM("bigcode/starcoder2-7b")
        >>> code = llm.generate("Create a binary search function", GenerationConfig())
    """

    def __init__(
        self,
        model_id: str,
        device: str = "auto",
        torch_dtype: str = "float16",
        load_in_8bit: bool = False,
        load_in_4bit: bool = False,
        trust_remote_code: bool = True
    ):
        super().__init__(model_id)
        self.device = device
        self.torch_dtype_str = torch_dtype
        self.load_in_8bit = load_in_8bit
        self.load_in_4bit = load_in_4bit
        self.trust_remote_code = trust_remote_code

        self._tokenizer = None
        self._model = None

        self._load_model()

    def _load_model(self):
        """Load HuggingFace model"""
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch

            # Convert dtype string to torch dtype
            dtype_map = {
                "float16": torch.float16,
                "float32": torch.float32,
                "bfloat16": torch.bfloat16
            }
            torch_dtype = dtype_map.get(self.torch_dtype_str, torch.float16)

            self._log(f"Loading HuggingFace model: {self.model_id}", "INFO")

            # Load tokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_id,
                trust_remote_code=self.trust_remote_code
            )

            # Load model
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                torch_dtype=torch_dtype,
                device_map=self.device,
                load_in_8bit=self.load_in_8bit,
                load_in_4bit=self.load_in_4bit,
                trust_remote_code=self.trust_remote_code
            )

            self._log("Model loaded successfully", "INFO")

        except ImportError:
            raise ImportError(
                "transformers not installed. "
                "Install with: pip install transformers torch accelerate"
            )
        except Exception as e:
            self._log(f"Failed to load model: {e}", "ERROR")
            raise

    def generate(self, prompt: str, config: GenerationConfig) -> str:
        """Generate code using HuggingFace model"""
        if not self.is_loaded():
            raise RuntimeError("Model not loaded")

        try:
            import torch

            # Tokenize
            inputs = self._tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=self._model.config.max_position_embeddings - config.max_tokens
            ).to(self._model.device)

            # Generate
            with torch.no_grad():
                outputs = self._model.generate(
                    **inputs,
                    max_new_tokens=config.max_tokens,
                    temperature=config.temperature,
                    top_p=config.top_p,
                    top_k=config.top_k,
                    do_sample=True,
                    pad_token_id=self._tokenizer.eos_token_id
                )

            # Decode
            generated_text = self._tokenizer.decode(
                outputs[0][inputs.input_ids.shape[1]:],
                skip_special_tokens=True
            )

            # Stop at stop sequences
            for stop_seq in (config.stop_sequences or []):
                if stop_seq in generated_text:
                    generated_text = generated_text.split(stop_seq)[0]

            return generated_text

        except Exception as e:
            self._log(f"Generation failed: {e}", "ERROR")
            raise

    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self._model is not None and self._tokenizer is not None


# ============================================================================
# OPENAI API
# ============================================================================

class OpenAICodeLLM(CodeLLMBase):
    """
    OpenAI API code LLM

    Supports:
    - gpt-4-turbo
    - gpt-4
    - gpt-3.5-turbo

    Requires OPENAI_API_KEY environment variable.

    Example:
        >>> llm = OpenAICodeLLM("gpt-4-turbo")
        >>> code = llm.generate("Create a REST API with FastAPI", GenerationConfig())
    """

    def __init__(
        self,
        model: str = "gpt-4-turbo",
        api_key: Optional[str] = None
    ):
        super().__init__(f"openai-{model}")
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            raise ValueError(
                "OpenAI API key not found. "
                "Set OPENAI_API_KEY environment variable or pass api_key parameter."
            )

        self._client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize OpenAI client"""
        try:
            from openai import OpenAI

            self._client = OpenAI(api_key=self.api_key)
            self._log(f"OpenAI client initialized (model: {self.model})", "INFO")

        except ImportError:
            raise ImportError(
                "openai not installed. "
                "Install with: pip install openai"
            )
        except Exception as e:
            self._log(f"Failed to initialize OpenAI client: {e}", "ERROR")
            raise

    def generate(self, prompt: str, config: GenerationConfig, stream: bool = False) -> Any:
        """Generate code using OpenAI API"""
        if not self.is_loaded():
            raise RuntimeError("Client not initialized")

        try:
            # Build messages
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert programmer. Generate clean, efficient, well-documented code."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            # Call API
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                top_p=config.top_p,
                stop=config.stop_sequences,
                stream=stream
            )

            if stream:
                return response
            else:
                return response.choices[0].message.content

        except Exception as e:
            self._log(f"OpenAI API call failed: {e}", "ERROR")
            raise

    def is_loaded(self) -> bool:
        """Check if client is initialized"""
        return self._client is not None


# ============================================================================
# ANTHROPIC CLAUDE API
# ============================================================================

class AnthropicCodeLLM(CodeLLMBase):
    """
    Anthropic Claude API code LLM

    Supports:
    - claude-3-opus
    - claude-3-sonnet
    - claude-3-haiku

    Requires ANTHROPIC_API_KEY environment variable.

    Example:
        >>> llm = AnthropicCodeLLM("claude-3-sonnet")
        >>> code = llm.generate("Implement a LRU cache in Python", GenerationConfig())
    """

    def __init__(
        self,
        model: str = "claude-3-sonnet-20240229",
        api_key: Optional[str] = None
    ):
        super().__init__(f"anthropic-{model}")
        self.model = model
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

        if not self.api_key:
            raise ValueError(
                "Anthropic API key not found. "
                "Set ANTHROPIC_API_KEY environment variable or pass api_key parameter."
            )

        self._client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Anthropic client"""
        try:
            from anthropic import Anthropic

            self._client = Anthropic(api_key=self.api_key)
            self._log(f"Anthropic client initialized (model: {self.model})", "INFO")

        except ImportError:
            raise ImportError(
                "anthropic not installed. "
                "Install with: pip install anthropic"
            )
        except Exception as e:
            self._log(f"Failed to initialize Anthropic client: {e}", "ERROR")
            raise

    def generate(self, prompt: str, config: GenerationConfig, stream: bool = False) -> Any:
        """Generate code using Anthropic API"""
        if not self.is_loaded():
            raise RuntimeError("Client not initialized")

        try:
            if stream:
                return self._generate_stream(prompt, config)
            else:
                # Call API
                message = self._client.messages.create(
                    model=self.model,
                    max_tokens=config.max_tokens,
                    temperature=config.temperature,
                    top_p=config.top_p,
                    system="You are an expert programmer. Generate clean, efficient, well-documented code.",
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    stop_sequences=config.stop_sequences
                )

                return message.content[0].text

        except Exception as e:
            self._log(f"Anthropic API call failed: {e}", "ERROR")
            raise

    def _generate_stream(self, prompt: str, config: GenerationConfig):
        """Internal streaming generator for Anthropic API."""
        with self._client.messages.stream(
            model=self.model,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            top_p=config.top_p,
            system="You are an expert programmer. Generate clean, efficient, well-documented code.",
            messages=[{"role": "user", "content": prompt}],
            stop_sequences=config.stop_sequences
        ) as stream_manager:
            yield from stream_manager.text_stream

    def is_loaded(self) -> bool:
        """Check if client is initialized"""
        return self._client is not None


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_code_llm(
    provider: str,
    model_id: str,
    **kwargs
) -> CodeLLMBase:
    """
    Factory function to create code LLM instances

    Args:
        provider: "llama-cpp", "huggingface", "openai", or "anthropic"
        model_id: Model identifier (path for llama-cpp, model name for others)
        **kwargs: Additional arguments for the specific provider

    Returns:
        CodeLLMBase instance

    Example:
        >>> # Local GGUF model
        >>> llm = create_code_llm("llama-cpp", "~/.versaai/models/deepseek-coder.gguf")

        >>> # HuggingFace
        >>> llm = create_code_llm("huggingface", "bigcode/starcoder2-7b")

        >>> # OpenAI
        >>> llm = create_code_llm("openai", "gpt-4-turbo")

        >>> # Anthropic
        >>> llm = create_code_llm("anthropic", "claude-3-sonnet-20240229")
    """
    provider = provider.lower()

    if provider in ("llama-cpp", "local", "llamacpp"):
        return LlamaCppCodeLLM(model_id, **kwargs)

    elif provider in ("huggingface", "hf"):
        return HuggingFaceCodeLLM(model_id, **kwargs)

    elif provider == "openai":
        return OpenAICodeLLM(model_id, **kwargs)

    elif provider in ("anthropic", "claude"):
        return AnthropicCodeLLM(model_id, **kwargs)

    else:
        raise ValueError(
            f"Unknown provider: {provider}. "
            f"Use 'llama-cpp', 'huggingface', 'openai', or 'anthropic'"
        )


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def build_code_prompt(
    task: str,
    language: str,
    framework: Optional[str] = None,
    requirements: Optional[List[str]] = None,
    existing_code: Optional[str] = None,
    examples: Optional[List[str]] = None
) -> str:
    """
    Build a well-structured prompt for code generation

    Args:
        task: Description of the coding task
        language: Programming language
        framework: Optional framework (e.g., "FastAPI", "React")
        requirements: List of requirements
        existing_code: Optional existing code context
        examples: Optional similar code examples

    Returns:
        Formatted prompt string
    """
    prompt_parts = [f"# Task: {task}"]

    # Add language and framework
    prompt_parts.append(f"# Language: {language}")
    if framework:
        prompt_parts.append(f"# Framework: {framework}")

    # Add requirements
    if requirements:
        prompt_parts.append("\n# Requirements:")
        for req in requirements:
            prompt_parts.append(f"- {req}")

    # Add existing code context
    if existing_code:
        prompt_parts.append(f"\n# Existing Code:\n```{language}\n{existing_code}\n```")

    # Add examples
    if examples:
        prompt_parts.append("\n# Similar Examples:")
        for i, example in enumerate(examples, 1):
            prompt_parts.append(f"\n## Example {i}:\n```{language}\n{example}\n```")

    # Add generation instruction
    prompt_parts.append(f"\n# Generate the code:\n```{language}")

    return "\n".join(prompt_parts)


def extract_code_from_response(response: str, language: str = None) -> str:
    """
    Extract code from LLM response (handles markdown code blocks)

    Args:
        response: LLM response text
        language: Optional expected language for validation

    Returns:
        Extracted code
    """
    # Try to find code block
    if "```" in response:
        # Split by code blocks
        blocks = response.split("```")

        # Find first code block (skip language identifier)
        for block in blocks[1::2]:  # Every second block is code
            # Remove language identifier if present
            lines = block.strip().split("\n")
            if lines and not lines[0].strip().isalpha():
                # First line is language identifier
                code = "\n".join(lines[1:])
            else:
                code = block.strip()

            if code:
                return code

    # No code block found, return as-is
    return response.strip()


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    import sys

    print("VersaAI Code LLM - Quick Test\n")

    # Example 1: Local model (if available)
    print("=" * 70)
    print("Example 1: Local Model (llama.cpp)")
    print("=" * 70)
    model_path = "./models/deepseek-coder-6.7b.Q4_K_M.gguf"

    if os.path.exists(model_path):
        try:
            llm = LlamaCppCodeLLM(model_path, n_gpu_layers=32)

            prompt = build_code_prompt(
                task="Create a function to calculate factorial",
                language="python",
                requirements=["Handle edge cases", "Add docstring"]
            )

            config = GenerationConfig(max_tokens=256)
            code = llm.generate(prompt, config)

            print(f"\nGenerated Code:\n{code}\n")
        except Exception as e:
            print(f"Local model test failed: {e}\n")
    else:
        print(f"Model not found at {model_path}\n")

    # Example 2: OpenAI (if API key available)
    print("=" * 70)
    print("Example 2: OpenAI API")
    print("=" * 70)

    if os.getenv("OPENAI_API_KEY"):
        try:
            llm = OpenAICodeLLM("gpt-3.5-turbo")

            prompt = "Create a Python function to reverse a string"
            config = GenerationConfig(max_tokens=256)

            code = llm.generate(prompt, config)
            extracted = extract_code_from_response(code, "python")

            print(f"\nGenerated Code:\n{extracted}\n")
        except Exception as e:
            print(f"OpenAI test failed: {e}\n")
    else:
        print("OPENAI_API_KEY not set, skipping\n")

    print("=" * 70)
    print("Test complete!")
    print("=" * 70)
