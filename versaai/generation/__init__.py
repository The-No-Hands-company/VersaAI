"""
VersaAI Generation — production-grade generative AI pipelines.

Provides image, video, and 3D model generation through a unified
provider abstraction. Each modality supports multiple backends
(local inference, API-based services) with automatic fallback.

Architecture:
    GenerationProvider (ABC)
    ├── ImageProvider → StableDiffusionProvider, ComfyUIImageProvider, DallEProvider
    ├── VideoProvider → StableVideoProvider, ComfyUIVideoProvider
    └── Model3DProvider → TripoSRProvider, MeshyProvider

    GenerationManager (singleton facade)
    └── Selects provider by config, dispatches requests, handles results

Usage:
    >>> from versaai.generation import GenerationManager
    >>> manager = GenerationManager()
    >>> result = await manager.generate_image(
    ...     prompt="A futuristic cityscape at sunset",
    ...     width=1024, height=1024,
    ... )
    >>> result.save("output.png")
"""

from versaai.generation.base import (
    GenerationProvider,
    GenerationRequest,
    GenerationResult,
    GenerationError,
    GenerationType,
    ProviderStatus,
)
from versaai.generation.image_gen import (
    ImageProvider,
    StableDiffusionProvider,
    ComfyUIImageProvider,
    DallEProvider,
)
from versaai.generation.video_gen import (
    VideoProvider,
    StableVideoProvider,
)
from versaai.generation.model_3d_gen import (
    Model3DProvider,
    TripoSRProvider,
    MeshyProvider,
)
from versaai.generation.manager import GenerationManager

__all__ = [
    # Base
    "GenerationProvider",
    "GenerationRequest",
    "GenerationResult",
    "GenerationError",
    "GenerationType",
    "ProviderStatus",
    # Image
    "ImageProvider",
    "StableDiffusionProvider",
    "ComfyUIImageProvider",
    "DallEProvider",
    # Video
    "VideoProvider",
    "StableVideoProvider",
    # 3D
    "Model3DProvider",
    "TripoSRProvider",
    "MeshyProvider",
    # Manager
    "GenerationManager",
]
