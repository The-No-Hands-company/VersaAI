"""VersaAI Models: Base classes and implementations for AI models.

Imports are lazy to avoid pulling in heavy ML dependencies (numpy, torch, etc.)
when only the lightweight providers (Ollama, llama.cpp) are needed.
"""

import importlib as _importlib

# Lightweight — always available
from versaai.models.ollama_provider import OllamaProvider
from versaai.models.llamacpp_provider import LlamaCppServerProvider


# Heavy imports — loaded on demand
def __getattr__(name: str):
    _lazy_map = {
        "ModelBase": "versaai.models.model_base",
        "ModelRegistry": "versaai.models.model_registry",
        "CodeModel": "versaai.models.code_model",
        "CodeContext": "versaai.models.code_model",
        "CodeTaskType": "versaai.models.code_model",
        "CodeLLMBase": "versaai.models.code_llm",
        "LlamaCppCodeLLM": "versaai.models.code_llm",
        "HuggingFaceCodeLLM": "versaai.models.code_llm",
        "OpenAICodeLLM": "versaai.models.code_llm",
        "AnthropicCodeLLM": "versaai.models.code_llm",
        "create_code_llm": "versaai.models.code_llm",
        "GenerationConfig": "versaai.models.code_llm",
        "build_code_prompt": "versaai.models.code_llm",
        "extract_code_from_response": "versaai.models.code_llm",
    }
    if name in _lazy_map:
        module = _importlib.import_module(_lazy_map[name])
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "OllamaProvider",
    "LlamaCppServerProvider",
    "ModelBase",
    "ModelRegistry",
    "CodeModel",
    "CodeContext",
    "CodeTaskType",
    "CodeLLMBase",
    "LlamaCppCodeLLM",
    "HuggingFaceCodeLLM",
    "OpenAICodeLLM",
    "AnthropicCodeLLM",
    "create_code_llm",
    "GenerationConfig",
    "build_code_prompt",
    "extract_code_from_response",
]
