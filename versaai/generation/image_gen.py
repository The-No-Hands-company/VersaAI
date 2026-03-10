"""
Image generation providers — Stable Diffusion WebUI, ComfyUI, DALL-E.

Each provider implements the GenerationProvider ABC and connects to
a real inference backend via HTTP.

Stable Diffusion WebUI (AUTOMATIC1111):
    - Local API at http://localhost:7860
    - Supports txt2img, img2img, upscale, inpaint
    - Full Stable Diffusion parameter control

ComfyUI:
    - Local API at http://localhost:8188
    - Node-graph based — uses workflow templates
    - Supports any model/pipeline ComfyUI can run

DALL-E (OpenAI):
    - Cloud API at https://api.openai.com/v1/images/generations
    - DALL-E 3 for highest quality
    - DALL-E 2 for speed/cost optimization
"""

import base64
import io
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import httpx

from versaai.generation.base import (
    ContentPolicyError,
    GenerationError,
    GenerationProvider,
    GenerationRequest,
    GenerationResult,
    GenerationTimeoutError,
    GenerationType,
    ImageFormat,
    ProviderStatus,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)

# Default connection timeout (seconds)
_CONNECT_TIMEOUT = 10.0
# Default generation timeout (seconds) — image gen can be slow
_GENERATE_TIMEOUT = 300.0


class ImageProvider(GenerationProvider, ABC):
    """Base class for image generation providers."""

    def __init__(self, name: str):
        super().__init__(name, GenerationType.IMAGE)


# ============================================================================
# Stable Diffusion WebUI (AUTOMATIC1111)
# ============================================================================


class StableDiffusionProvider(ImageProvider):
    """
    Connects to AUTOMATIC1111's Stable Diffusion WebUI API.

    Requires the WebUI running with --api flag:
        python launch.py --api

    API docs: http://localhost:7860/docs

    Supports:
    - txt2img: Text-to-image generation
    - img2img: Image-to-image with denoising
    - Upscale, inpainting (via img2img mask)
    - All samplers (Euler, DPM++, DDIM, etc.)
    - ControlNet (when extension installed)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:7860",
        timeout: float = _GENERATE_TIMEOUT,
        default_sampler: str = "DPM++ 2M Karras",
    ):
        super().__init__("stable_diffusion")
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._default_sampler = default_sampler
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(connect=_CONNECT_TIMEOUT, read=timeout, write=30.0, pool=10.0),
        )

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate image via Stable Diffusion WebUI txt2img or img2img API."""
        if request.source_image:
            return await self._img2img(request)
        return await self._txt2img(request)

    async def _txt2img(self, request: GenerationRequest) -> GenerationResult:
        """Text-to-image generation."""
        payload = {
            "prompt": request.prompt,
            "negative_prompt": request.negative_prompt or (
                "blurry, low quality, distorted, deformed, ugly, bad anatomy, "
                "watermark, text, signature, jpeg artifacts"
            ),
            "width": request.width,
            "height": request.height,
            "steps": request.steps,
            "cfg_scale": request.guidance_scale,
            "sampler_name": self._default_sampler,
            "batch_size": min(request.num_images, 4),
            "seed": request.seed if request.seed is not None else -1,
            "send_images": True,
            "save_images": False,
        }
        payload.update(request.extra)

        self._logger.info(
            f"txt2img: {request.width}x{request.height}, "
            f"steps={request.steps}, cfg={request.guidance_scale}"
        )

        try:
            response = await self._client.post("/sdapi/v1/txt2img", json=payload)
        except httpx.ConnectError as exc:
            raise ProviderUnavailableError(
                self._name,
                f"Cannot connect to Stable Diffusion WebUI at {self._base_url}: {exc}",
            ) from exc
        except httpx.ReadTimeout as exc:
            raise GenerationTimeoutError(self._name, self._timeout) from exc

        if response.status_code != 200:
            raise GenerationError(
                f"Stable Diffusion API error {response.status_code}: {response.text[:500]}",
                provider=self._name,
                status_code=response.status_code,
            )

        data = response.json()
        images = data.get("images", [])
        if not images:
            raise GenerationError("No images returned from Stable Diffusion", provider=self._name)

        # Decode first image
        img_bytes = base64.b64decode(images[0])
        info = json.loads(data.get("info", "{}")) if isinstance(data.get("info"), str) else data.get("info", {})

        result = GenerationResult(
            data=img_bytes,
            mime_type=f"image/{request.image_format.value}",
            generation_type=GenerationType.IMAGE,
            provider_name=self._name,
            model_name=info.get("sd_model_name", "unknown"),
            seed_used=info.get("seed"),
            metadata={
                "prompt": request.prompt,
                "negative_prompt": request.negative_prompt,
                "steps": request.steps,
                "cfg_scale": request.guidance_scale,
                "sampler": info.get("sampler_name", self._default_sampler),
                "width": request.width,
                "height": request.height,
            },
        )

        # Additional images
        for extra_b64 in images[1:]:
            result.additional_results.append(GenerationResult(
                data=base64.b64decode(extra_b64),
                mime_type=f"image/{request.image_format.value}",
                generation_type=GenerationType.IMAGE,
                provider_name=self._name,
                model_name=result.model_name,
                seed_used=info.get("all_seeds", [None])[0],
            ))

        return result

    async def _img2img(self, request: GenerationRequest) -> GenerationResult:
        """Image-to-image generation."""
        source_b64 = base64.b64encode(request.source_image).decode("ascii")

        payload = {
            "init_images": [source_b64],
            "prompt": request.prompt,
            "negative_prompt": request.negative_prompt or "",
            "width": request.width,
            "height": request.height,
            "steps": request.steps,
            "cfg_scale": request.guidance_scale,
            "sampler_name": self._default_sampler,
            "denoising_strength": request.source_image_strength,
            "seed": request.seed if request.seed is not None else -1,
            "send_images": True,
            "save_images": False,
        }
        payload.update(request.extra)

        self._logger.info(
            f"img2img: {request.width}x{request.height}, "
            f"denoise={request.source_image_strength}"
        )

        try:
            response = await self._client.post("/sdapi/v1/img2img", json=payload)
        except httpx.ConnectError as exc:
            raise ProviderUnavailableError(
                self._name,
                f"Cannot connect to Stable Diffusion WebUI at {self._base_url}: {exc}",
            ) from exc
        except httpx.ReadTimeout as exc:
            raise GenerationTimeoutError(self._name, self._timeout) from exc

        if response.status_code != 200:
            raise GenerationError(
                f"Stable Diffusion img2img error {response.status_code}: {response.text[:500]}",
                provider=self._name,
                status_code=response.status_code,
            )

        data = response.json()
        images = data.get("images", [])
        if not images:
            raise GenerationError("No images returned from img2img", provider=self._name)

        img_bytes = base64.b64decode(images[0])
        info = json.loads(data.get("info", "{}")) if isinstance(data.get("info"), str) else data.get("info", {})

        return GenerationResult(
            data=img_bytes,
            mime_type=f"image/{request.image_format.value}",
            generation_type=GenerationType.IMAGE,
            provider_name=self._name,
            model_name=info.get("sd_model_name", "unknown"),
            seed_used=info.get("seed"),
            metadata={
                "prompt": request.prompt,
                "mode": "img2img",
                "denoising_strength": request.source_image_strength,
            },
        )

    async def check_health(self) -> ProviderStatus:
        """Ping the Stable Diffusion WebUI API."""
        try:
            resp = await self._client.get("/sdapi/v1/sd-models", timeout=_CONNECT_TIMEOUT)
            if resp.status_code == 200:
                self._status = ProviderStatus.AVAILABLE
            else:
                self._status = ProviderStatus.DEGRADED
        except Exception:
            self._status = ProviderStatus.UNAVAILABLE
        return self._status

    def supported_models(self) -> List[str]:
        return [
            "stable-diffusion-v1-5",
            "stable-diffusion-xl-base-1.0",
            "stable-diffusion-xl-refiner-1.0",
            "stable-diffusion-3-medium",
            "flux-1-schnell",
            "flux-1-dev",
        ]

    async def list_remote_models(self) -> List[Dict[str, Any]]:
        """Fetch actually loaded models from the WebUI."""
        try:
            resp = await self._client.get("/sdapi/v1/sd-models", timeout=_CONNECT_TIMEOUT)
            if resp.status_code == 200:
                return resp.json()
        except Exception as exc:
            self._logger.warning(f"Failed to list SD models: {exc}")
        return []

    async def list_samplers(self) -> List[str]:
        """Fetch available samplers from the WebUI."""
        try:
            resp = await self._client.get("/sdapi/v1/samplers", timeout=_CONNECT_TIMEOUT)
            if resp.status_code == 200:
                return [s["name"] for s in resp.json()]
        except Exception as exc:
            self._logger.warning(f"Failed to list samplers: {exc}")
        return []


# ============================================================================
# ComfyUI
# ============================================================================


class ComfyUIImageProvider(ImageProvider):
    """
    Connects to ComfyUI's API for image generation.

    ComfyUI uses a node-graph workflow system. This provider submits
    a pre-built workflow JSON and polls for the result.

    API: http://localhost:8188
    - POST /prompt → queue a workflow
    - GET /history/{prompt_id} → poll for results
    - GET /view?filename=... → fetch output image

    Workflow templates are stored in the provider and parameterized
    at runtime based on the GenerationRequest.
    """

    # Minimal txt2img workflow template
    _TXT2IMG_WORKFLOW = {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 0,
                "steps": 30,
                "cfg": 7.5,
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
        },
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 1024, "height": 1024, "batch_size": 1},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "", "clip": ["4", 1]},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "", "clip": ["4", 1]},
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "VersaAI", "images": ["8", 0]},
        },
    }

    def __init__(
        self,
        base_url: str = "http://localhost:8188",
        timeout: float = _GENERATE_TIMEOUT,
        checkpoint: str = "v1-5-pruned-emaonly.safetensors",
    ):
        super().__init__("comfyui")
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._checkpoint = checkpoint
        self._client_id = uuid.uuid4().hex[:8]
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(connect=_CONNECT_TIMEOUT, read=timeout, write=30.0, pool=10.0),
        )

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate image by submitting a ComfyUI workflow."""
        import copy

        workflow = copy.deepcopy(self._TXT2IMG_WORKFLOW)

        # Parameterize the workflow
        workflow["3"]["inputs"]["seed"] = request.seed if request.seed is not None else int(time.time())
        workflow["3"]["inputs"]["steps"] = request.steps
        workflow["3"]["inputs"]["cfg"] = request.guidance_scale
        workflow["4"]["inputs"]["ckpt_name"] = request.model or self._checkpoint
        workflow["5"]["inputs"]["width"] = request.width
        workflow["5"]["inputs"]["height"] = request.height
        workflow["5"]["inputs"]["batch_size"] = min(request.num_images, 4)
        workflow["6"]["inputs"]["text"] = request.prompt
        workflow["7"]["inputs"]["text"] = request.negative_prompt or ""

        prompt_payload = {
            "prompt": workflow,
            "client_id": self._client_id,
        }

        self._logger.info(f"ComfyUI txt2img: {request.width}x{request.height}, steps={request.steps}")

        # Queue the workflow
        try:
            resp = await self._client.post("/prompt", json=prompt_payload)
        except httpx.ConnectError as exc:
            raise ProviderUnavailableError(
                self._name,
                f"Cannot connect to ComfyUI at {self._base_url}: {exc}",
            ) from exc

        if resp.status_code != 200:
            raise GenerationError(
                f"ComfyUI queue error {resp.status_code}: {resp.text[:500]}",
                provider=self._name,
                status_code=resp.status_code,
            )

        prompt_id = resp.json().get("prompt_id")
        if not prompt_id:
            raise GenerationError("ComfyUI did not return a prompt_id", provider=self._name)

        # Poll for completion
        img_bytes = await self._poll_result(prompt_id)

        return GenerationResult(
            data=img_bytes,
            mime_type=f"image/{request.image_format.value}",
            generation_type=GenerationType.IMAGE,
            provider_name=self._name,
            model_name=request.model or self._checkpoint,
            seed_used=workflow["3"]["inputs"]["seed"],
            metadata={
                "prompt": request.prompt,
                "prompt_id": prompt_id,
                "steps": request.steps,
                "cfg_scale": request.guidance_scale,
            },
        )

    async def _poll_result(self, prompt_id: str, poll_interval: float = 1.0) -> bytes:
        """Poll ComfyUI history until the generation completes."""
        deadline = time.monotonic() + self._timeout

        while time.monotonic() < deadline:
            try:
                resp = await self._client.get(f"/history/{prompt_id}", timeout=_CONNECT_TIMEOUT)
            except Exception:
                await _async_sleep(poll_interval)
                continue

            if resp.status_code != 200:
                await _async_sleep(poll_interval)
                continue

            history = resp.json()
            entry = history.get(prompt_id)
            if not entry:
                await _async_sleep(poll_interval)
                continue

            outputs = entry.get("outputs", {})
            # Find the SaveImage node output
            for node_id, node_out in outputs.items():
                images = node_out.get("images", [])
                if images:
                    filename = images[0].get("filename")
                    subfolder = images[0].get("subfolder", "")
                    img_type = images[0].get("type", "output")
                    return await self._fetch_image(filename, subfolder, img_type)

            await _async_sleep(poll_interval)

        raise GenerationTimeoutError(self._name, self._timeout)

    async def _fetch_image(self, filename: str, subfolder: str, img_type: str) -> bytes:
        """Download a generated image from ComfyUI."""
        params = {"filename": filename, "subfolder": subfolder, "type": img_type}
        resp = await self._client.get("/view", params=params)
        if resp.status_code != 200:
            raise GenerationError(
                f"Failed to fetch image '{filename}' from ComfyUI",
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
            "v1-5-pruned-emaonly.safetensors",
            "sd_xl_base_1.0.safetensors",
            "flux1-schnell-fp8.safetensors",
        ]


# ============================================================================
# DALL-E (OpenAI)
# ============================================================================


class DallEProvider(ImageProvider):
    """
    Connects to OpenAI's DALL-E API for image generation.

    Requires an OpenAI API key set via:
    - VERSAAI_MODELS__OPENAI__API_KEY environment variable
    - config.yaml models.openai.api_key

    Supports:
    - DALL-E 3: Best quality, 1024x1024, 1024x1792, 1792x1024
    - DALL-E 2: Faster, cheaper, 256x256 to 1024x1024
    """

    _VALID_SIZES_DALLE3 = {"1024x1024", "1024x1792", "1792x1024"}
    _VALID_SIZES_DALLE2 = {"256x256", "512x512", "1024x1024"}

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        default_model: str = "dall-e-3",
        timeout: float = 120.0,
    ):
        super().__init__("dalle")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._default_model = default_model
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(connect=_CONNECT_TIMEOUT, read=timeout, write=30.0, pool=10.0),
        )

    def _get_api_key(self) -> str:
        """Resolve API key from init param or config."""
        if self._api_key:
            return self._api_key
        from versaai.config import settings
        key = settings.models.openai.api_key
        if not key:
            raise GenerationError(
                "OpenAI API key not configured. Set VERSAAI_MODELS__OPENAI__API_KEY "
                "or configure models.openai.api_key",
                provider=self._name,
            )
        return key

    def _resolve_size(self, request: GenerationRequest) -> str:
        """Map requested dimensions to nearest valid DALL-E size."""
        model = request.model or self._default_model
        requested = f"{request.width}x{request.height}"

        if "dall-e-3" in model:
            if requested in self._VALID_SIZES_DALLE3:
                return requested
            # Pick closest valid size
            aspect = request.width / request.height
            if aspect > 1.3:
                return "1792x1024"
            elif aspect < 0.77:
                return "1024x1792"
            return "1024x1024"
        else:
            if requested in self._VALID_SIZES_DALLE2:
                return requested
            if request.width <= 384:
                return "256x256"
            if request.width <= 768:
                return "512x512"
            return "1024x1024"

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate image via OpenAI DALL-E API."""
        api_key = self._get_api_key()
        model = request.model or self._default_model
        size = self._resolve_size(request)

        payload: Dict[str, Any] = {
            "model": model,
            "prompt": request.prompt,
            "n": min(request.num_images, 1 if "dall-e-3" in model else 4),
            "size": size,
            "response_format": "b64_json",
        }

        if "dall-e-3" in model:
            quality = request.extra.get("quality", "standard")
            style = request.extra.get("style", "vivid")
            payload["quality"] = quality
            payload["style"] = style

        self._logger.info(f"DALL-E: model={model}, size={size}")

        try:
            resp = await self._client.post(
                "/images/generations",
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
        except httpx.ConnectError as exc:
            raise ProviderUnavailableError(self._name, str(exc)) from exc
        except httpx.ReadTimeout as exc:
            raise GenerationTimeoutError(self._name, 120.0) from exc

        if resp.status_code == 400:
            body = resp.json()
            error_msg = body.get("error", {}).get("message", "")
            if "content_policy" in error_msg.lower() or "safety" in error_msg.lower():
                raise ContentPolicyError(self._name, error_msg)
            raise GenerationError(
                f"DALL-E error: {error_msg}",
                provider=self._name,
                status_code=400,
            )

        if resp.status_code != 200:
            raise GenerationError(
                f"DALL-E API error {resp.status_code}: {resp.text[:500]}",
                provider=self._name,
                status_code=resp.status_code,
            )

        data = resp.json()
        images = data.get("data", [])
        if not images:
            raise GenerationError("No images returned from DALL-E", provider=self._name)

        img_bytes = base64.b64decode(images[0]["b64_json"])
        revised_prompt = images[0].get("revised_prompt", request.prompt)

        result = GenerationResult(
            data=img_bytes,
            mime_type="image/png",
            generation_type=GenerationType.IMAGE,
            provider_name=self._name,
            model_name=model,
            metadata={
                "prompt": request.prompt,
                "revised_prompt": revised_prompt,
                "size": size,
                "model": model,
            },
        )

        for extra_img in images[1:]:
            result.additional_results.append(GenerationResult(
                data=base64.b64decode(extra_img["b64_json"]),
                mime_type="image/png",
                generation_type=GenerationType.IMAGE,
                provider_name=self._name,
                model_name=model,
            ))

        return result

    async def check_health(self) -> ProviderStatus:
        """Check if the DALL-E API is reachable and key is valid."""
        try:
            api_key = self._get_api_key()
            resp = await self._client.get(
                "/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=_CONNECT_TIMEOUT,
            )
            if resp.status_code == 200:
                self._status = ProviderStatus.AVAILABLE
            elif resp.status_code == 401:
                self._status = ProviderStatus.UNAVAILABLE
            else:
                self._status = ProviderStatus.DEGRADED
        except Exception:
            self._status = ProviderStatus.UNAVAILABLE
        return self._status

    def supported_models(self) -> List[str]:
        return ["dall-e-3", "dall-e-2"]


# ============================================================================
# Helpers
# ============================================================================


async def _async_sleep(seconds: float) -> None:
    """Non-blocking sleep."""
    import asyncio
    await asyncio.sleep(seconds)
