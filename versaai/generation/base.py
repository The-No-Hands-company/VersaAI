"""
Generation base classes — abstract provider interface and data types.

All generation providers (image, video, 3D) share these common types
and the GenerationProvider ABC.
"""

import hashlib
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


# ============================================================================
# Enums
# ============================================================================


class GenerationType(str, Enum):
    """Supported generation modalities."""
    IMAGE = "image"
    VIDEO = "video"
    THREE_D = "3d"


class ProviderStatus(str, Enum):
    """Health status of a generation provider."""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class ImageFormat(str, Enum):
    """Supported image output formats."""
    PNG = "png"
    JPEG = "jpeg"
    WEBP = "webp"


class VideoFormat(str, Enum):
    """Supported video output formats."""
    MP4 = "mp4"
    WEBM = "webm"
    GIF = "gif"


class Model3DFormat(str, Enum):
    """Supported 3D model output formats."""
    GLB = "glb"
    GLTF = "gltf"
    OBJ = "obj"
    STL = "stl"
    FBX = "fbx"
    USDZ = "usdz"


# ============================================================================
# Request / Result data classes
# ============================================================================


@dataclass
class GenerationRequest:
    """
    Unified generation request.

    Works for image, video, and 3D generation — each provider
    ignores fields that don't apply to its modality.
    """
    # Core
    prompt: str
    generation_type: GenerationType
    negative_prompt: str = ""
    seed: Optional[int] = None

    # Image parameters
    width: int = 1024
    height: int = 1024
    steps: int = 30
    guidance_scale: float = 7.5
    image_format: ImageFormat = ImageFormat.PNG
    num_images: int = 1

    # Video parameters
    duration_seconds: float = 4.0
    fps: int = 24
    video_format: VideoFormat = VideoFormat.MP4
    motion_strength: float = 0.5  # 0.0 (still) to 1.0 (max motion)

    # 3D parameters
    model_3d_format: Model3DFormat = Model3DFormat.GLB
    texture_resolution: int = 1024
    generate_textures: bool = True
    mesh_quality: str = "high"  # low, medium, high

    # Source image for img2img, video from image, image-to-3D
    source_image: Optional[bytes] = None
    source_image_strength: float = 0.75  # denoising strength for img2img

    # Provider override
    provider: Optional[str] = None  # Force a specific provider
    model: Optional[str] = None  # Force a specific model within the provider

    # Extra parameters passed through to provider
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def request_id(self) -> str:
        """Deterministic ID for caching/dedup based on prompt + params."""
        h = hashlib.sha256()
        h.update(self.prompt.encode())
        h.update(self.generation_type.value.encode())
        h.update(str(self.seed or "none").encode())
        h.update(f"{self.width}x{self.height}".encode())
        return h.hexdigest()[:16]


@dataclass
class GenerationResult:
    """
    Result from a generation operation.

    Contains the raw binary data, metadata, and convenience methods
    for saving / encoding the output.
    """
    data: bytes
    mime_type: str
    generation_type: GenerationType
    provider_name: str
    model_name: str = ""
    generation_time: float = 0.0
    seed_used: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    result_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    # For multi-image generation
    additional_results: List["GenerationResult"] = field(default_factory=list)

    @property
    def size_bytes(self) -> int:
        return len(self.data)

    def save(self, path: Union[str, Path]) -> Path:
        """Save result to disk."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(self.data)
        logger.info(f"Saved {self.generation_type.value} to {p} ({self.size_bytes} bytes)")
        return p

    def to_base64(self) -> str:
        """Encode result as base64 string."""
        import base64
        return base64.b64encode(self.data).decode("ascii")

    def to_data_uri(self) -> str:
        """Encode as a data: URI for embedding in HTML/JSON."""
        return f"data:{self.mime_type};base64,{self.to_base64()}"


# ============================================================================
# Errors
# ============================================================================


class GenerationError(Exception):
    """Base error for generation operations."""

    def __init__(
        self,
        message: str,
        provider: str = "",
        retriable: bool = False,
        status_code: Optional[int] = None,
    ):
        super().__init__(message)
        self.provider = provider
        self.retriable = retriable
        self.status_code = status_code


class ProviderUnavailableError(GenerationError):
    """Provider is not reachable or not configured."""

    def __init__(self, provider: str, detail: str = ""):
        super().__init__(
            f"Generation provider '{provider}' is unavailable: {detail}",
            provider=provider,
            retriable=True,
        )


class GenerationTimeoutError(GenerationError):
    """Generation exceeded the allowed time."""

    def __init__(self, provider: str, timeout: float):
        super().__init__(
            f"Generation via '{provider}' timed out after {timeout:.1f}s",
            provider=provider,
            retriable=True,
        )


class ContentPolicyError(GenerationError):
    """Content was rejected by safety filters."""

    def __init__(self, provider: str, detail: str = ""):
        super().__init__(
            f"Content rejected by '{provider}' safety filter: {detail}",
            provider=provider,
            retriable=False,
        )


# ============================================================================
# Abstract Provider
# ============================================================================


class GenerationProvider(ABC):
    """
    Abstract base class for all generation providers.

    Each provider:
    - Targets one GenerationType (image, video, 3D)
    - Connects to a local or remote inference backend
    - Implements health checks and graceful degradation
    """

    def __init__(self, name: str, generation_type: GenerationType):
        self._name = name
        self._generation_type = generation_type
        self._status = ProviderStatus.UNKNOWN
        self._logger = logging.getLogger(f"versaai.generation.{name}")

    @property
    def name(self) -> str:
        return self._name

    @property
    def generation_type(self) -> GenerationType:
        return self._generation_type

    @property
    def status(self) -> ProviderStatus:
        return self._status

    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """
        Execute a generation request.

        Args:
            request: The generation parameters.

        Returns:
            GenerationResult with the output data.

        Raises:
            GenerationError: On any generation failure.
        """
        ...

    @abstractmethod
    async def check_health(self) -> ProviderStatus:
        """
        Check if this provider is available and ready.

        Returns:
            ProviderStatus indicating availability.
        """
        ...

    @abstractmethod
    def supported_models(self) -> List[str]:
        """List model names/identifiers this provider supports."""
        ...

    async def _timed_generate(self, request: GenerationRequest) -> GenerationResult:
        """Wrapper that measures generation time and updates status."""
        start = time.monotonic()
        try:
            result = await self.generate(request)
            result.generation_time = time.monotonic() - start
            self._status = ProviderStatus.AVAILABLE
            return result
        except GenerationError:
            raise
        except Exception as exc:
            self._status = ProviderStatus.DEGRADED
            raise GenerationError(
                f"Unexpected error in {self._name}: {exc}",
                provider=self._name,
                retriable=True,
            ) from exc
