"""
VersaAI Configuration System

Centralized configuration using Pydantic Settings with support for:
- YAML config files (config/default.yaml)
- Environment variables (VERSAAI_ prefix)
- .env file
- Runtime overrides

Priority (highest to lowest):
1. Runtime overrides (passed directly)
2. Environment variables
3. .env file
4. YAML config file
5. Defaults defined here
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

# ============================================================================
# Sub-configuration models
# ============================================================================

class ModelProviderConfig(BaseModel):
    """Configuration for a single model provider."""
    enabled: bool = True
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    default_model: Optional[str] = None
    timeout: int = 120
    max_retries: int = 3


class OllamaConfig(ModelProviderConfig):
    """Ollama-specific configuration."""
    base_url: str = "http://localhost:11434"
    default_model: str = "qwen2.5-coder:7b"


class LlamaCppConfig(ModelProviderConfig):
    """llama.cpp-specific configuration."""
    base_url: str = "http://localhost:8080"
    model_dir: str = "~/.versaai/models"
    n_gpu_layers: int = -1  # -1 = auto (all layers to GPU if available)
    n_ctx: int = 4096
    n_batch: int = 512
    n_threads: int = 0  # 0 = auto-detect


class OpenAIConfig(ModelProviderConfig):
    """OpenAI-specific configuration."""
    base_url: str = "https://api.openai.com/v1"
    default_model: str = "gpt-4o"


class AnthropicConfig(ModelProviderConfig):
    """Anthropic-specific configuration."""
    default_model: str = "claude-sonnet-4-20250514"


class HuggingFaceConfig(ModelProviderConfig):
    """HuggingFace-specific configuration."""
    cache_dir: str = "~/.cache/huggingface"
    default_model: str = "Qwen/Qwen2.5-Coder-7B-Instruct"
    quantization: Optional[Literal["4bit", "8bit"]] = "4bit"
    device: str = "auto"


class ModelsConfig(BaseModel):
    """Model layer configuration."""
    ollama: OllamaConfig = OllamaConfig()
    llamacpp: LlamaCppConfig = LlamaCppConfig()
    openai: OpenAIConfig = OpenAIConfig()
    anthropic: AnthropicConfig = AnthropicConfig()
    huggingface: HuggingFaceConfig = HuggingFaceConfig()

    # Routing
    default_provider: str = "ollama"
    code_provider: str = "ollama"
    chat_provider: str = "ollama"
    embedding_model: str = "all-MiniLM-L6-v2"


class ServerConfig(BaseModel):
    """API server configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = ["*"]
    log_level: str = "info"
    workers: int = 1
    reload: bool = False


class RAGConfig(BaseModel):
    """RAG pipeline configuration."""
    enabled: bool = True
    vector_store_backend: Literal["chromadb", "faiss", "memory"] = "memory"
    vector_store_dir: str = "~/.versaai/data/vectorstore"
    chunk_size: int = 512
    chunk_overlap: int = 64
    top_k: int = 5
    similarity_threshold: float = 0.7


class MemoryConfig(BaseModel):
    """Memory system configuration."""
    conversation_max_turns: int = 50
    context_window_tokens: int = 4096
    persistence_dir: str = "~/.versaai/data/memory"
    auto_save: bool = True


# ============================================================================
# Main Settings
# ============================================================================

class Settings(BaseSettings):
    """
    VersaAI application settings.

    Loads from (in priority order):
    1. Environment variables with VERSAAI_ prefix
    2. .env file
    3. config/default.yaml
    4. Defaults below

    Usage:
        from versaai.config import settings

        # Access nested settings
        settings.models.ollama.base_url
        settings.server.port
        settings.rag.enabled
    """

    # Application
    app_name: str = "VersaAI"
    version: str = "0.2.0"
    debug: bool = False
    data_dir: str = "~/.versaai"
    log_level: str = "INFO"

    # Sub-configs
    models: ModelsConfig = ModelsConfig()
    server: ServerConfig = ServerConfig()
    rag: RAGConfig = RAGConfig()
    memory: MemoryConfig = MemoryConfig()

    model_config = {
        "env_prefix": "VERSAAI_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "env_nested_delimiter": "__",
        "extra": "ignore",
    }

    def resolve_path(self, path: str) -> Path:
        """Resolve ~ and relative paths to absolute."""
        return Path(os.path.expanduser(path)).resolve()

    @property
    def data_path(self) -> Path:
        """Resolved data directory path."""
        p = self.resolve_path(self.data_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def models_path(self) -> Path:
        """Resolved model storage directory."""
        p = self.resolve_path(self.models.llamacpp.model_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


def _load_yaml_config() -> Dict[str, Any]:
    """Load YAML config file if it exists."""
    config_paths = [
        Path("config/default.yaml"),
        Path(os.path.expanduser("~/.versaai/config.yaml")),
        Path("/etc/versaai/config.yaml"),
    ]

    for config_path in config_paths:
        if config_path.exists():
            try:
                import yaml
                with open(config_path) as f:
                    data = yaml.safe_load(f) or {}
                logger.info(f"Loaded config from {config_path}")
                return data
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")

    return {}


def _create_settings() -> Settings:
    """Create settings instance with YAML defaults merged in."""
    yaml_config = _load_yaml_config()

    # Environment variables and .env take priority over YAML
    # Pydantic Settings handles env var priority automatically
    try:
        return Settings(**yaml_config)
    except Exception as e:
        logger.warning(f"Config validation failed, using defaults: {e}")
        return Settings()


# Singleton settings instance
settings = _create_settings()
