"""
Video generation providers — Stable Video Diffusion via ComfyUI, Replicate API.

Supports text-to-video and image-to-video pipelines.

Stable Video Diffusion (ComfyUI):
    - Local pipeline via ComfyUI workflow
    - SVD or SVD-XT for image-to-video
    - AnimateDiff for text-to-video
    - Full control over motion, FPS, duration

Replicate:
    - Cloud API at https://api.replicate.com/v1
    - Supports various video models (Stable Video Diffusion, ModelScope, etc.)
    - Simple REST interface with polling
"""

import base64
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import httpx

from versaai.generation.base import (
    GenerationError,
    GenerationProvider,
    GenerationRequest,
    GenerationResult,
    GenerationTimeoutError,
    GenerationType,
    ProviderStatus,
    ProviderUnavailableError,
    VideoFormat,
)

logger = logging.getLogger(__name__)

_CONNECT_TIMEOUT = 10.0
_GENERATE_TIMEOUT = 600.0  # Video gen is slower


class VideoProvider(GenerationProvider, ABC):
    """Base class for video generation providers."""

    def __init__(self, name: str):
        super().__init__(name, GenerationType.VIDEO)


# ============================================================================
# Stable Video Diffusion via ComfyUI
# ============================================================================


class StableVideoProvider(VideoProvider):
    """
    Video generation via ComfyUI with AnimateDiff (txt2vid)
    or Stable Video Diffusion (img2vid).

    Requires ComfyUI with:
    - AnimateDiff extension (for text-to-video)
    - SVD models (for image-to-video)
    - ComfyUI-VideoHelperSuite (for video encoding)

    Two generation modes:
    1. Text-to-video: Uses AnimateDiff with a text prompt
    2. Image-to-video: Uses SVD/SVD-XT to animate a source image
    """

    # AnimateDiff txt2vid workflow
    _TXT2VID_WORKFLOW = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"},
        },
        "2": {
            "class_type": "ADE_AnimateDiffLoaderGen1",
            "inputs": {
                "model_name": "mm_sd_v15_v2.ckpt",
                "beta_schedule": "autoselect",
                "model": ["1", 0],
            },
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "", "clip": ["1", 1]},
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "", "clip": ["1", 1]},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 512, "height": 512, "batch_size": 16},
        },
        "6": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 0,
                "steps": 25,
                "cfg": 7.5,
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
                "denoise": 1.0,
                "model": ["2", 0],
                "positive": ["3", 0],
                "negative": ["4", 0],
                "latent_image": ["5", 0],
            },
        },
        "7": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["6", 0], "vae": ["1", 2]},
        },
        "8": {
            "class_type": "VHS_VideoCombine",
            "inputs": {
                "frame_rate": 8,
                "loop_count": 0,
                "filename_prefix": "VersaAI_video",
                "format": "video/h264-mp4",
                "pingpong": False,
                "save_output": True,
                "images": ["7", 0],
            },
        },
    }

    # SVD img2vid workflow
    _IMG2VID_WORKFLOW = {
        "1": {
            "class_type": "ImageOnlyCheckpointLoader",
            "inputs": {"ckpt_name": "svd_xt_1_1.safetensors"},
        },
        "2": {
            "class_type": "LoadImage",
            "inputs": {"image": "", "upload": "image"},
        },
        "3": {
            "class_type": "SVD_img2vid_Conditioning",
            "inputs": {
                "width": 1024,
                "height": 576,
                "video_frames": 25,
                "motion_bucket_id": 127,
                "fps": 6,
                "augmentation_level": 0.0,
                "clip_vision": ["1", 1],
                "init_image": ["2", 0],
                "vae": ["1", 2],
            },
        },
        "4": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 0,
                "steps": 25,
                "cfg": 2.5,
                "sampler_name": "euler",
                "scheduler": "karras",
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["3", 0],
                "negative": ["3", 1],
                "latent_image": ["3", 2],
            },
        },
        "5": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["4", 0], "vae": ["1", 2]},
        },
        "6": {
            "class_type": "VHS_VideoCombine",
            "inputs": {
                "frame_rate": 6,
                "loop_count": 0,
                "filename_prefix": "VersaAI_svd",
                "format": "video/h264-mp4",
                "pingpong": False,
                "save_output": True,
                "images": ["5", 0],
            },
        },
    }

    def __init__(
        self,
        base_url: str = "http://localhost:8188",
        timeout: float = _GENERATE_TIMEOUT,
        animatediff_model: str = "mm_sd_v15_v2.ckpt",
        svd_model: str = "svd_xt_1_1.safetensors",
        base_checkpoint: str = "v1-5-pruned-emaonly.safetensors",
    ):
        super().__init__("stable_video")
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._animatediff_model = animatediff_model
        self._svd_model = svd_model
        self._base_checkpoint = base_checkpoint
        self._client_id = uuid.uuid4().hex[:8]
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(connect=_CONNECT_TIMEOUT, read=timeout, write=60.0, pool=10.0),
        )

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate video via ComfyUI workflow."""
        if request.source_image:
            return await self._img2vid(request)
        return await self._txt2vid(request)

    async def _txt2vid(self, request: GenerationRequest) -> GenerationResult:
        """Text-to-video via AnimateDiff."""
        import copy

        workflow = copy.deepcopy(self._TXT2VID_WORKFLOW)

        # Calculate frame count from duration and FPS
        frame_count = max(8, int(request.duration_seconds * request.fps))
        # AnimateDiff typically works best with 16-32 frames
        frame_count = min(frame_count, 64)

        workflow["1"]["inputs"]["ckpt_name"] = request.model or self._base_checkpoint
        workflow["2"]["inputs"]["model_name"] = self._animatediff_model
        workflow["3"]["inputs"]["text"] = request.prompt
        workflow["4"]["inputs"]["text"] = request.negative_prompt or (
            "blurry, low quality, distorted, watermark, text"
        )
        workflow["5"]["inputs"]["width"] = min(request.width, 768)
        workflow["5"]["inputs"]["height"] = min(request.height, 768)
        workflow["5"]["inputs"]["batch_size"] = frame_count
        workflow["6"]["inputs"]["seed"] = request.seed if request.seed is not None else int(time.time())
        workflow["6"]["inputs"]["steps"] = request.steps
        workflow["6"]["inputs"]["cfg"] = request.guidance_scale
        workflow["8"]["inputs"]["frame_rate"] = request.fps

        self._logger.info(
            f"AnimateDiff txt2vid: {request.width}x{request.height}, "
            f"frames={frame_count}, fps={request.fps}"
        )

        video_bytes = await self._submit_and_poll(workflow)

        return GenerationResult(
            data=video_bytes,
            mime_type=f"video/{request.video_format.value}",
            generation_type=GenerationType.VIDEO,
            provider_name=self._name,
            model_name=self._animatediff_model,
            seed_used=workflow["6"]["inputs"]["seed"],
            metadata={
                "prompt": request.prompt,
                "mode": "txt2vid",
                "frames": frame_count,
                "fps": request.fps,
                "steps": request.steps,
            },
        )

    async def _img2vid(self, request: GenerationRequest) -> GenerationResult:
        """Image-to-video via SVD."""
        import copy

        workflow = copy.deepcopy(self._IMG2VID_WORKFLOW)

        frame_count = max(14, int(request.duration_seconds * 6))
        frame_count = min(frame_count, 50)
        motion_bucket = int(request.motion_strength * 254)  # 0-254 range

        # Upload source image first
        image_name = await self._upload_image(request.source_image)

        workflow["1"]["inputs"]["ckpt_name"] = request.model or self._svd_model
        workflow["2"]["inputs"]["image"] = image_name
        workflow["3"]["inputs"]["width"] = min(request.width, 1024)
        workflow["3"]["inputs"]["height"] = min(request.height, 576)
        workflow["3"]["inputs"]["video_frames"] = frame_count
        workflow["3"]["inputs"]["motion_bucket_id"] = motion_bucket
        workflow["3"]["inputs"]["fps"] = 6
        workflow["4"]["inputs"]["seed"] = request.seed if request.seed is not None else int(time.time())
        workflow["4"]["inputs"]["steps"] = request.steps
        workflow["6"]["inputs"]["frame_rate"] = 6

        self._logger.info(
            f"SVD img2vid: frames={frame_count}, motion={motion_bucket}"
        )

        video_bytes = await self._submit_and_poll(workflow)

        return GenerationResult(
            data=video_bytes,
            mime_type=f"video/{request.video_format.value}",
            generation_type=GenerationType.VIDEO,
            provider_name=self._name,
            model_name=self._svd_model,
            seed_used=workflow["4"]["inputs"]["seed"],
            metadata={
                "prompt": request.prompt,
                "mode": "img2vid",
                "frames": frame_count,
                "motion_bucket": motion_bucket,
            },
        )

    async def _upload_image(self, image_data: bytes) -> str:
        """Upload an image to ComfyUI's input directory."""
        import io
        filename = f"versaai_input_{uuid.uuid4().hex[:8]}.png"
        files = {"image": (filename, io.BytesIO(image_data), "image/png")}
        try:
            resp = await self._client.post(
                "/upload/image",
                files=files,
                data={"overwrite": "true"},
            )
            if resp.status_code == 200:
                return resp.json().get("name", filename)
            raise GenerationError(
                f"Image upload failed: {resp.status_code}",
                provider=self._name,
            )
        except httpx.ConnectError as exc:
            raise ProviderUnavailableError(self._name, str(exc)) from exc

    async def _submit_and_poll(self, workflow: Dict) -> bytes:
        """Submit workflow and poll for video output."""
        prompt_payload = {"prompt": workflow, "client_id": self._client_id}

        try:
            resp = await self._client.post("/prompt", json=prompt_payload)
        except httpx.ConnectError as exc:
            raise ProviderUnavailableError(
                self._name, f"Cannot connect to ComfyUI: {exc}"
            ) from exc

        if resp.status_code != 200:
            raise GenerationError(
                f"ComfyUI queue error: {resp.text[:500]}",
                provider=self._name,
                status_code=resp.status_code,
            )

        prompt_id = resp.json().get("prompt_id")
        if not prompt_id:
            raise GenerationError("No prompt_id from ComfyUI", provider=self._name)

        return await self._poll_video_result(prompt_id)

    async def _poll_video_result(self, prompt_id: str, poll_interval: float = 2.0) -> bytes:
        """Poll ComfyUI for video generation completion."""
        import asyncio

        deadline = time.monotonic() + self._timeout

        while time.monotonic() < deadline:
            try:
                resp = await self._client.get(f"/history/{prompt_id}", timeout=_CONNECT_TIMEOUT)
            except Exception:
                await asyncio.sleep(poll_interval)
                continue

            if resp.status_code != 200:
                await asyncio.sleep(poll_interval)
                continue

            history = resp.json()
            entry = history.get(prompt_id)
            if not entry:
                await asyncio.sleep(poll_interval)
                continue

            outputs = entry.get("outputs", {})
            for node_id, node_out in outputs.items():
                # VHS_VideoCombine outputs gifs or videos
                gifs = node_out.get("gifs", [])
                if gifs:
                    filename = gifs[0].get("filename")
                    subfolder = gifs[0].get("subfolder", "")
                    file_type = gifs[0].get("type", "output")
                    return await self._fetch_file(filename, subfolder, file_type)

                # Some nodes output as "videos"
                videos = node_out.get("videos", [])
                if videos:
                    filename = videos[0].get("filename")
                    subfolder = videos[0].get("subfolder", "")
                    file_type = videos[0].get("type", "output")
                    return await self._fetch_file(filename, subfolder, file_type)

            await asyncio.sleep(poll_interval)

        raise GenerationTimeoutError(self._name, self._timeout)

    async def _fetch_file(self, filename: str, subfolder: str, file_type: str) -> bytes:
        """Download a generated file from ComfyUI."""
        params = {"filename": filename, "subfolder": subfolder, "type": file_type}
        resp = await self._client.get("/view", params=params)
        if resp.status_code != 200:
            raise GenerationError(
                f"Failed to fetch '{filename}' from ComfyUI",
                provider=self._name,
            )
        return resp.content

    async def check_health(self) -> ProviderStatus:
        try:
            resp = await self._client.get("/system_stats", timeout=_CONNECT_TIMEOUT)
            if resp.status_code == 200:
                self._status = ProviderStatus.AVAILABLE
            else:
                self._status = ProviderStatus.DEGRADED
        except Exception:
            self._status = ProviderStatus.UNAVAILABLE
        return self._status

    def supported_models(self) -> List[str]:
        return [
            "mm_sd_v15_v2.ckpt",           # AnimateDiff v2
            "mm_sdxl_v10_beta.ckpt",       # AnimateDiff XL
            "svd_xt_1_1.safetensors",      # SVD-XT
            "svd.safetensors",             # SVD base
        ]
