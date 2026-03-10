"""
Generation API routes — image, video, and 3D model generation endpoints.

Endpoints:
    POST /v1/generate/image     — Generate an image from text/image
    POST /v1/generate/video     — Generate a video from text/image
    POST /v1/generate/3d        — Generate a 3D model from text/image
    GET  /v1/generate/providers — List available generation providers
"""

import asyncio
import base64
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field

from versaai.api.errors import InvalidRequestError, InferenceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/generate")


# ============================================================================
# Schemas
# ============================================================================


class ImageGenerateRequest(BaseModel):
    """Request to generate an image."""
    prompt: str = Field(description="Text prompt for image generation")
    negative_prompt: Optional[str] = Field(default=None, description="Negative prompt")
    width: int = Field(default=512, ge=64, le=2048, description="Image width in pixels")
    height: int = Field(default=512, ge=64, le=2048, description="Image height in pixels")
    num_inference_steps: int = Field(default=30, ge=1, le=150, description="Number of denoising steps")
    guidance_scale: float = Field(default=7.5, ge=1.0, le=30.0, description="Classifier-free guidance scale")
    num_images: int = Field(default=1, ge=1, le=4, description="Number of images to generate")
    seed: Optional[int] = Field(default=None, description="Random seed for reproducibility")
    provider: Optional[str] = Field(default=None, description="Provider override (stable_diffusion, comfyui, dalle)")
    model: Optional[str] = Field(default=None, description="Model override")
    source_image_base64: Optional[str] = Field(default=None, description="Source image for img2img (base64)")


class VideoGenerateRequest(BaseModel):
    """Request to generate a video."""
    prompt: str = Field(description="Text prompt for video generation")
    negative_prompt: Optional[str] = Field(default=None, description="Negative prompt")
    width: int = Field(default=512, ge=64, le=1024, description="Video width")
    height: int = Field(default=512, ge=64, le=1024, description="Video height")
    duration: float = Field(default=4.0, ge=1.0, le=30.0, description="Duration in seconds")
    fps: int = Field(default=8, ge=4, le=30, description="Frames per second")
    motion_strength: float = Field(default=0.7, ge=0.0, le=1.0, description="Motion strength")
    seed: Optional[int] = Field(default=None, description="Random seed")
    provider: Optional[str] = Field(default=None, description="Provider override")
    source_image_base64: Optional[str] = Field(default=None, description="Source image for img2vid (base64)")


class Model3DGenerateRequest(BaseModel):
    """Request to generate a 3D model."""
    prompt: str = Field(description="Text prompt for 3D generation")
    format: str = Field(default="glb", description="Output format (glb, obj, stl, fbx, usdz)")
    texture_resolution: int = Field(default=1024, ge=256, le=4096, description="Texture resolution")
    mesh_quality: str = Field(default="medium", description="Mesh quality (low, medium, high)")
    seed: Optional[int] = Field(default=None, description="Random seed")
    provider: Optional[str] = Field(default=None, description="Provider override (triposr, meshy)")
    source_image_base64: Optional[str] = Field(default=None, description="Source image for img-to-3D (base64)")


class GenerationResult(BaseModel):
    """Response for generation endpoints."""
    id: str
    type: str  # "image", "video", "3d"
    data_base64: str
    mime_type: str
    provider: str
    model: Optional[str] = None
    generation_time: float
    seed_used: Optional[int] = None
    metadata: Dict[str, Any] = {}
    additional_results: List[Dict[str, Any]] = []


class ProviderInfo(BaseModel):
    """Information about a generation provider."""
    name: str
    type: str  # "image", "video", "3d"
    status: str
    supported_models: List[str] = []


class ProvidersListResponse(BaseModel):
    """List of available generation providers."""
    providers: List[ProviderInfo]


# ============================================================================
# Lazy manager singleton
# ============================================================================

_manager = None


def _get_manager():
    """Get or create the GenerationManager singleton."""
    global _manager
    if _manager is None:
        from versaai.config import settings
        from versaai.generation.manager import GenerationManager

        # Build config dict from settings
        gen = settings.generation
        config = {
            "image": {
                "provider": gen.image_provider,
                "stable_diffusion": {
                    "base_url": gen.stable_diffusion.base_url,
                    "timeout": gen.stable_diffusion.timeout,
                },
                "comfyui": {
                    "base_url": gen.comfyui.base_url,
                    "timeout": gen.comfyui.timeout,
                },
                "dalle": {
                    "api_key": gen.dalle.api_key,
                    "timeout": gen.dalle.timeout,
                },
            },
            "video": {
                "provider": gen.video_provider,
                "stable_video": {
                    "base_url": gen.stable_video.base_url,
                    "timeout": gen.stable_video.timeout,
                },
            },
            "3d": {
                "provider": gen.model_3d_provider,
                "triposr": {
                    "base_url": gen.triposr.base_url,
                    "api_key": gen.triposr.api_key,
                    "timeout": gen.triposr.timeout,
                },
                "meshy": {
                    "api_key": gen.meshy.api_key,
                    "timeout": gen.meshy.timeout,
                },
            },
        }
        _manager = GenerationManager(config)
    return _manager


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/image", response_model=GenerationResult)
async def generate_image(request: ImageGenerateRequest):
    """Generate an image from a text prompt (and optionally a source image)."""
    request_id = f"gen-img-{uuid.uuid4().hex[:12]}"
    logger.info(f"[{request_id}] Image generation: prompt='{request.prompt[:80]}...'")

    manager = _get_manager()

    source_image = None
    if request.source_image_base64:
        source_image = base64.b64decode(request.source_image_base64)

    try:
        result = await manager.generate_image(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            width=request.width,
            height=request.height,
            num_inference_steps=request.num_inference_steps,
            guidance_scale=request.guidance_scale,
            num_images=request.num_images,
            seed=request.seed,
            source_image=source_image,
            provider=request.provider,
            model=request.model,
        )
    except Exception as exc:
        logger.error(f"[{request_id}] Image generation failed: {exc}", exc_info=True)
        raise InferenceError(f"Image generation failed: {exc}")

    additional = []
    for extra in result.additional_results:
        additional.append({
            "data_base64": extra.to_base64(),
            "mime_type": extra.mime_type,
            "seed_used": extra.seed_used,
        })

    return GenerationResult(
        id=request_id,
        type="image",
        data_base64=result.to_base64(),
        mime_type=result.mime_type,
        provider=result.provider_name,
        model=result.model_name,
        generation_time=result.generation_time,
        seed_used=result.seed_used,
        metadata=result.metadata,
        additional_results=additional,
    )


@router.post("/video", response_model=GenerationResult)
async def generate_video(request: VideoGenerateRequest):
    """Generate a video from a text prompt (and optionally a source image)."""
    request_id = f"gen-vid-{uuid.uuid4().hex[:12]}"
    logger.info(f"[{request_id}] Video generation: prompt='{request.prompt[:80]}...'")

    manager = _get_manager()

    source_image = None
    if request.source_image_base64:
        source_image = base64.b64decode(request.source_image_base64)

    try:
        result = await manager.generate_video(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            width=request.width,
            height=request.height,
            duration=request.duration,
            fps=request.fps,
            motion_strength=request.motion_strength,
            seed=request.seed,
            source_image=source_image,
            provider=request.provider,
        )
    except Exception as exc:
        logger.error(f"[{request_id}] Video generation failed: {exc}", exc_info=True)
        raise InferenceError(f"Video generation failed: {exc}")

    return GenerationResult(
        id=request_id,
        type="video",
        data_base64=result.to_base64(),
        mime_type=result.mime_type,
        provider=result.provider_name,
        model=result.model_name,
        generation_time=result.generation_time,
        seed_used=result.seed_used,
        metadata=result.metadata,
    )


@router.post("/3d", response_model=GenerationResult)
async def generate_3d(request: Model3DGenerateRequest):
    """Generate a 3D model from a text prompt (and optionally a source image)."""
    request_id = f"gen-3d-{uuid.uuid4().hex[:12]}"
    logger.info(f"[{request_id}] 3D generation: prompt='{request.prompt[:80]}...'")

    manager = _get_manager()

    source_image = None
    if request.source_image_base64:
        source_image = base64.b64decode(request.source_image_base64)

    try:
        result = await manager.generate_3d(
            prompt=request.prompt,
            format=request.format,
            texture_resolution=request.texture_resolution,
            mesh_quality=request.mesh_quality,
            seed=request.seed,
            source_image=source_image,
            provider=request.provider,
        )
    except Exception as exc:
        logger.error(f"[{request_id}] 3D generation failed: {exc}", exc_info=True)
        raise InferenceError(f"3D generation failed: {exc}")

    return GenerationResult(
        id=request_id,
        type="3d",
        data_base64=result.to_base64(),
        mime_type=result.mime_type,
        provider=result.provider_name,
        model=result.model_name,
        generation_time=result.generation_time,
        seed_used=result.seed_used,
        metadata=result.metadata,
    )


@router.get("/providers", response_model=ProvidersListResponse)
async def list_providers():
    """List all registered generation providers and their status."""
    manager = _get_manager()

    providers_data = manager.list_providers()
    providers = []
    for gen_type, provider_list in providers_data.items():
        for p in provider_list:
            providers.append(ProviderInfo(
                name=p["name"],
                type=gen_type,
                status=p["status"],
                supported_models=p.get("models", []),
            ))

    return ProvidersListResponse(providers=providers)


@router.post("/providers/health")
async def check_provider_health():
    """Run health checks on all generation providers."""
    manager = _get_manager()

    results = await manager.check_all_providers()
    return {
        "providers": {
            name: status.value for name, status in results.items()
        },
        "timestamp": time.time(),
    }
