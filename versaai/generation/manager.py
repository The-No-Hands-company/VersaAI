"""
GenerationManager — unified facade for all generative AI pipelines.

Provides a single entry point for image, video, and 3D model generation
with automatic provider selection, health checking, and fallback.

Usage:
    >>> from versaai.generation import GenerationManager
    >>> manager = GenerationManager()
    >>> result = await manager.generate_image("A sunset over mountains")
    >>> result.save("sunset.png")
    >>>
    >>> result = await manager.generate_video("Ocean waves on a beach")
    >>> result.save("waves.mp4")
    >>>
    >>> result = await manager.generate_3d("A medieval sword")
    >>> result.save("sword.glb")
"""

import logging
from typing import Any, Dict, List, Optional

from versaai.generation.base import (
    GenerationError,
    GenerationProvider,
    GenerationRequest,
    GenerationResult,
    GenerationType,
    ImageFormat,
    Model3DFormat,
    ProviderStatus,
    ProviderUnavailableError,
    VideoFormat,
)

logger = logging.getLogger(__name__)


class GenerationManager:
    """
    Centralized manager for all generation providers.

    Handles:
    - Provider registration and lazy initialization
    - Health checking and status monitoring
    - Automatic provider selection with fallback
    - Generation request dispatch

    Providers are initialized lazily from config the first time
    a generation type is requested.
    """

    def __init__(self):
        # provider_name → provider instance
        self._image_providers: Dict[str, GenerationProvider] = {}
        self._video_providers: Dict[str, GenerationProvider] = {}
        self._3d_providers: Dict[str, GenerationProvider] = {}

        # Preferred order (first available wins)
        self._image_preference: List[str] = []
        self._video_preference: List[str] = []
        self._3d_preference: List[str] = []

        self._initialized = False

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize providers from config.

        Config structure:
            {
                "image": {
                    "provider": "stable_diffusion",  # default provider
                    "stable_diffusion": {"base_url": "http://localhost:7860"},
                    "comfyui": {"base_url": "http://localhost:8188"},
                    "dalle": {"api_key": "sk-..."},
                },
                "video": {
                    "provider": "stable_video",
                    "stable_video": {"base_url": "http://localhost:8188"},
                },
                "3d": {
                    "provider": "triposr",
                    "triposr": {"base_url": "http://localhost:8090"},
                    "meshy": {"api_key": "..."},
                },
            }
        """
        cfg = config or {}

        self._init_image_providers(cfg.get("image", {}))
        self._init_video_providers(cfg.get("video", {}))
        self._init_3d_providers(cfg.get("3d", {}))

        self._initialized = True
        logger.info(
            f"GenerationManager initialized: "
            f"image={list(self._image_providers.keys())}, "
            f"video={list(self._video_providers.keys())}, "
            f"3d={list(self._3d_providers.keys())}"
        )

    def _init_image_providers(self, cfg: Dict[str, Any]) -> None:
        """Register image generation providers."""
        from versaai.generation.image_gen import (
            ComfyUIImageProvider,
            DallEProvider,
            StableDiffusionProvider,
        )

        default = cfg.get("provider", "stable_diffusion")

        # Stable Diffusion WebUI
        sd_cfg = cfg.get("stable_diffusion", {})
        sd = StableDiffusionProvider(
            base_url=sd_cfg.get("base_url", "http://localhost:7860"),
            timeout=sd_cfg.get("timeout", 300.0),
            default_sampler=sd_cfg.get("sampler", "DPM++ 2M Karras"),
        )
        self._image_providers["stable_diffusion"] = sd

        # ComfyUI
        comfy_cfg = cfg.get("comfyui", {})
        comfy = ComfyUIImageProvider(
            base_url=comfy_cfg.get("base_url", "http://localhost:8188"),
            timeout=comfy_cfg.get("timeout", 300.0),
            checkpoint=comfy_cfg.get("checkpoint", "v1-5-pruned-emaonly.safetensors"),
        )
        self._image_providers["comfyui"] = comfy

        # DALL-E
        dalle_cfg = cfg.get("dalle", {})
        dalle = DallEProvider(
            api_key=dalle_cfg.get("api_key"),
            default_model=dalle_cfg.get("model", "dall-e-3"),
            timeout=dalle_cfg.get("timeout", 120.0),
        )
        self._image_providers["dalle"] = dalle

        # Set preference order with default first
        order = [default]
        for name in ("stable_diffusion", "comfyui", "dalle"):
            if name not in order:
                order.append(name)
        self._image_preference = order

    def _init_video_providers(self, cfg: Dict[str, Any]) -> None:
        """Register video generation providers."""
        from versaai.generation.video_gen import StableVideoProvider

        sv_cfg = cfg.get("stable_video", {})
        sv = StableVideoProvider(
            base_url=sv_cfg.get("base_url", "http://localhost:8188"),
            timeout=sv_cfg.get("timeout", 600.0),
        )
        self._video_providers["stable_video"] = sv
        self._video_preference = ["stable_video"]

    def _init_3d_providers(self, cfg: Dict[str, Any]) -> None:
        """Register 3D model generation providers."""
        from versaai.generation.model_3d_gen import MeshyProvider, TripoSRProvider

        default = cfg.get("provider", "triposr")

        tripo_cfg = cfg.get("triposr", {})
        tripo = TripoSRProvider(
            base_url=tripo_cfg.get("base_url", "http://localhost:8090"),
            timeout=tripo_cfg.get("timeout", 600.0),
            use_tripo_cloud=tripo_cfg.get("use_cloud", False),
            tripo_api_key=tripo_cfg.get("api_key"),
        )
        self._3d_providers["triposr"] = tripo

        meshy_cfg = cfg.get("meshy", {})
        meshy = MeshyProvider(
            api_key=meshy_cfg.get("api_key"),
            timeout=meshy_cfg.get("timeout", 600.0),
            auto_refine=meshy_cfg.get("auto_refine", True),
        )
        self._3d_providers["meshy"] = meshy

        order = [default]
        for name in ("triposr", "meshy"):
            if name not in order:
                order.append(name)
        self._3d_preference = order

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.initialize()

    # ------------------------------------------------------------------
    # Provider selection
    # ------------------------------------------------------------------

    def _get_providers_for_type(
        self, gen_type: GenerationType
    ) -> tuple:
        """Return (providers_dict, preference_list) for a generation type."""
        if gen_type == GenerationType.IMAGE:
            return self._image_providers, self._image_preference
        elif gen_type == GenerationType.VIDEO:
            return self._video_providers, self._video_preference
        elif gen_type == GenerationType.THREE_D:
            return self._3d_providers, self._3d_preference
        raise GenerationError(f"Unknown generation type: {gen_type}")

    async def _select_provider(
        self, gen_type: GenerationType, preferred: Optional[str] = None
    ) -> GenerationProvider:
        """
        Select the best available provider for the given generation type.

        Priority:
        1. Explicitly requested provider (if specified and available)
        2. First available provider in preference order
        """
        providers, preference = self._get_providers_for_type(gen_type)

        if not providers:
            raise GenerationError(
                f"No {gen_type.value} generation providers registered",
                provider="manager",
            )

        # Explicit provider override
        if preferred and preferred in providers:
            return providers[preferred]

        # Try preference order
        for name in preference:
            provider = providers.get(name)
            if provider:
                return provider

        # Fallback to first registered
        return next(iter(providers.values()))

    # ------------------------------------------------------------------
    # Generation methods
    # ------------------------------------------------------------------

    async def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        steps: int = 30,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None,
        num_images: int = 1,
        image_format: ImageFormat = ImageFormat.PNG,
        source_image: Optional[bytes] = None,
        source_image_strength: float = 0.75,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        **extra,
    ) -> GenerationResult:
        """
        Generate an image from a text prompt or source image.

        Args:
            prompt: Text description of the desired image.
            negative_prompt: What to avoid in the image.
            width: Output width in pixels.
            height: Output height in pixels.
            steps: Number of diffusion steps (more = higher quality, slower).
            guidance_scale: Classifier-free guidance scale (higher = more prompt-adherent).
            seed: Random seed for reproducibility.
            num_images: Number of images to generate.
            image_format: Output format (PNG, JPEG, WEBP).
            source_image: Source image bytes for img2img.
            source_image_strength: Denoising strength for img2img (0.0-1.0).
            provider: Force a specific provider name.
            model: Force a specific model within the provider.
            **extra: Additional provider-specific parameters.

        Returns:
            GenerationResult with the generated image data.
        """
        self._ensure_initialized()

        request = GenerationRequest(
            prompt=prompt,
            generation_type=GenerationType.IMAGE,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            steps=steps,
            guidance_scale=guidance_scale,
            seed=seed,
            num_images=num_images,
            image_format=image_format,
            source_image=source_image,
            source_image_strength=source_image_strength,
            provider=provider,
            model=model,
            extra=extra,
        )

        selected = await self._select_provider(GenerationType.IMAGE, provider)
        logger.info(f"Image generation via {selected.name}: '{prompt[:80]}...'")
        return await selected._timed_generate(request)

    async def generate_video(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 512,
        height: int = 512,
        steps: int = 25,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None,
        duration_seconds: float = 4.0,
        fps: int = 8,
        video_format: VideoFormat = VideoFormat.MP4,
        motion_strength: float = 0.5,
        source_image: Optional[bytes] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        **extra,
    ) -> GenerationResult:
        """
        Generate a video from a text prompt or source image.

        Args:
            prompt: Text description for text-to-video.
            width: Output width.
            height: Output height.
            steps: Diffusion steps.
            guidance_scale: CFG scale.
            seed: Random seed.
            duration_seconds: Video duration in seconds.
            fps: Frames per second.
            video_format: Output format (MP4, WEBM, GIF).
            motion_strength: Motion intensity (0.0-1.0).
            source_image: Source image for image-to-video (SVD).
            provider: Force a specific provider.
            model: Force a specific model.
            **extra: Provider-specific parameters.

        Returns:
            GenerationResult with the generated video data.
        """
        self._ensure_initialized()

        request = GenerationRequest(
            prompt=prompt,
            generation_type=GenerationType.VIDEO,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            steps=steps,
            guidance_scale=guidance_scale,
            seed=seed,
            duration_seconds=duration_seconds,
            fps=fps,
            video_format=video_format,
            motion_strength=motion_strength,
            source_image=source_image,
            provider=provider,
            model=model,
            extra=extra,
        )

        selected = await self._select_provider(GenerationType.VIDEO, provider)
        logger.info(f"Video generation via {selected.name}: '{prompt[:80]}...'")
        return await selected._timed_generate(request)

    async def generate_3d(
        self,
        prompt: str = "",
        negative_prompt: str = "",
        seed: Optional[int] = None,
        model_3d_format: Model3DFormat = Model3DFormat.GLB,
        texture_resolution: int = 1024,
        generate_textures: bool = True,
        mesh_quality: str = "high",
        source_image: Optional[bytes] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        **extra,
    ) -> GenerationResult:
        """
        Generate a 3D model from text or a reference image.

        Args:
            prompt: Text description (for text-to-3D).
            source_image: Reference image bytes (for image-to-3D).
            model_3d_format: Output format (GLB, OBJ, STL, etc.).
            texture_resolution: Texture map resolution.
            generate_textures: Whether to generate PBR textures.
            mesh_quality: Mesh quality level (low, medium, high).
            provider: Force a specific provider.
            model: Force a specific model.
            **extra: Provider-specific parameters.

        Returns:
            GenerationResult with the generated 3D model data.
        """
        self._ensure_initialized()

        if not prompt and not source_image:
            raise GenerationError(
                "Either prompt or source_image must be provided for 3D generation",
                provider="manager",
            )

        request = GenerationRequest(
            prompt=prompt,
            generation_type=GenerationType.THREE_D,
            negative_prompt=negative_prompt,
            seed=seed,
            model_3d_format=model_3d_format,
            texture_resolution=texture_resolution,
            generate_textures=generate_textures,
            mesh_quality=mesh_quality,
            source_image=source_image,
            provider=provider,
            model=model,
            extra=extra,
        )

        selected = await self._select_provider(GenerationType.THREE_D, provider)
        logger.info(f"3D generation via {selected.name}: '{prompt[:80]}...'")
        return await selected._timed_generate(request)

    # ------------------------------------------------------------------
    # Health & introspection
    # ------------------------------------------------------------------

    async def check_all_providers(self) -> Dict[str, Dict[str, str]]:
        """
        Check health of all registered providers.

        Returns:
            {
                "image": {"stable_diffusion": "available", "dalle": "unavailable"},
                "video": {"stable_video": "unavailable"},
                "3d": {"triposr": "available", "meshy": "available"},
            }
        """
        self._ensure_initialized()
        result: Dict[str, Dict[str, str]] = {}

        for gen_type, providers in [
            ("image", self._image_providers),
            ("video", self._video_providers),
            ("3d", self._3d_providers),
        ]:
            result[gen_type] = {}
            for name, provider in providers.items():
                try:
                    status = await provider.check_health()
                    result[gen_type][name] = status.value
                except Exception as exc:
                    result[gen_type][name] = f"error: {exc}"

        return result

    def list_providers(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        List all registered providers and their capabilities.

        Returns:
            {
                "image": [
                    {"name": "stable_diffusion", "status": "unknown", "models": [...]},
                    ...
                ],
            }
        """
        self._ensure_initialized()
        result: Dict[str, List[Dict[str, Any]]] = {}

        for gen_type, providers in [
            ("image", self._image_providers),
            ("video", self._video_providers),
            ("3d", self._3d_providers),
        ]:
            result[gen_type] = []
            for name, provider in providers.items():
                result[gen_type].append({
                    "name": name,
                    "status": provider.status.value,
                    "models": provider.supported_models(),
                    "generation_type": provider.generation_type.value,
                })

        return result
