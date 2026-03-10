"""
3D model generation providers — TripoSR, Meshy.

Supports text-to-3D and image-to-3D pipelines with output in
GLB, OBJ, STL, and other standard 3D formats.

TripoSR:
    - Local or self-hosted inference server
    - Image-to-3D in ~0.5 seconds on GPU
    - Outputs textured mesh in GLB format
    - Based on the TripoSR architecture (fast feed-forward 3D reconstruction)

Meshy:
    - Cloud API at https://api.meshy.ai
    - Text-to-3D and image-to-3D
    - High quality with PBR textures
    - Two-stage: preview (fast) → refine (quality)
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
    Model3DFormat,
    ProviderStatus,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)

_CONNECT_TIMEOUT = 10.0
_GENERATE_TIMEOUT = 600.0  # 3D gen can be very slow


class Model3DProvider(GenerationProvider, ABC):
    """Base class for 3D model generation providers."""

    def __init__(self, name: str):
        super().__init__(name, GenerationType.THREE_D)


# ============================================================================
# TripoSR (Local / Self-hosted)
# ============================================================================


class TripoSRProvider(Model3DProvider):
    """
    3D model generation via TripoSR inference server.

    TripoSR is a fast feed-forward 3D reconstruction model that
    converts a single image into a textured 3D mesh in ~0.5 seconds.

    Server API (Gradio-based or custom REST):
    - POST /api/generate — Submit image for 3D reconstruction
    - Body: multipart/form-data with image file
    - Response: GLB binary or base64-encoded mesh

    Setup:
        pip install triposr
        # Or use the Hugging Face Spaces API

    This provider also supports the Tripo3D cloud API (https://api.tripo3d.ai)
    as a fallback.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8090",
        timeout: float = _GENERATE_TIMEOUT,
        use_tripo_cloud: bool = False,
        tripo_api_key: Optional[str] = None,
    ):
        super().__init__("triposr")
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._use_cloud = use_tripo_cloud
        self._api_key = tripo_api_key
        self._cloud_url = "https://api.tripo3d.ai/v2/openapi"
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=_CONNECT_TIMEOUT, read=timeout, write=60.0, pool=10.0),
        )

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate 3D model from image or text."""
        if self._use_cloud and self._api_key:
            return await self._generate_cloud(request)
        return await self._generate_local(request)

    async def _generate_local(self, request: GenerationRequest) -> GenerationResult:
        """Generate via local TripoSR server."""
        if not request.source_image:
            raise GenerationError(
                "TripoSR local mode requires a source image. "
                "Provide source_image bytes or use text-to-3D via Meshy.",
                provider=self._name,
            )

        import io

        self._logger.info(
            f"TripoSR local: image-to-3D, "
            f"texture_res={request.texture_resolution}"
        )

        files = {
            "file": ("input.png", io.BytesIO(request.source_image), "image/png"),
        }
        data = {
            "foreground_ratio": str(request.extra.get("foreground_ratio", 0.85)),
            "mc_resolution": str(request.extra.get("mc_resolution", 256)),
        }

        try:
            resp = await self._client.post(
                f"{self._base_url}/api/generate",
                files=files,
                data=data,
            )
        except httpx.ConnectError as exc:
            raise ProviderUnavailableError(
                self._name,
                f"Cannot connect to TripoSR at {self._base_url}: {exc}",
            ) from exc
        except httpx.ReadTimeout as exc:
            raise GenerationTimeoutError(self._name, self._timeout) from exc

        if resp.status_code != 200:
            raise GenerationError(
                f"TripoSR error {resp.status_code}: {resp.text[:500]}",
                provider=self._name,
                status_code=resp.status_code,
            )

        # Response could be raw GLB or JSON with base64
        content_type = resp.headers.get("content-type", "")
        if "application/octet-stream" in content_type or "model/gltf-binary" in content_type:
            mesh_bytes = resp.content
        elif "application/json" in content_type:
            body = resp.json()
            mesh_b64 = body.get("mesh", body.get("model", body.get("output", "")))
            if not mesh_b64:
                raise GenerationError("No mesh data in TripoSR response", provider=self._name)
            mesh_bytes = base64.b64decode(mesh_b64)
        else:
            mesh_bytes = resp.content

        mime_map = {
            Model3DFormat.GLB: "model/gltf-binary",
            Model3DFormat.GLTF: "model/gltf+json",
            Model3DFormat.OBJ: "text/plain",
            Model3DFormat.STL: "application/octet-stream",
        }

        return GenerationResult(
            data=mesh_bytes,
            mime_type=mime_map.get(request.model_3d_format, "model/gltf-binary"),
            generation_type=GenerationType.THREE_D,
            provider_name=self._name,
            model_name="triposr-v1",
            metadata={
                "mode": "image_to_3d",
                "format": request.model_3d_format.value,
                "texture_resolution": request.texture_resolution,
            },
        )

    async def _generate_cloud(self, request: GenerationRequest) -> GenerationResult:
        """Generate via Tripo3D cloud API."""
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        # Determine mode: text-to-3D or image-to-3D
        if request.source_image:
            # Upload image first
            image_token = await self._upload_image_cloud(request.source_image, headers)
            payload = {
                "type": "image_to_model",
                "file": {"type": "png", "file_token": image_token},
            }
        else:
            payload = {
                "type": "text_to_model",
                "prompt": request.prompt,
            }

        if request.negative_prompt:
            payload["negative_prompt"] = request.negative_prompt

        self._logger.info(f"Tripo3D cloud: mode={payload['type']}")

        # Create generation task
        try:
            resp = await self._client.post(
                f"{self._cloud_url}/task",
                json=payload,
                headers=headers,
            )
        except httpx.ConnectError as exc:
            raise ProviderUnavailableError(self._name, str(exc)) from exc

        if resp.status_code != 200:
            raise GenerationError(
                f"Tripo3D API error {resp.status_code}: {resp.text[:500]}",
                provider=self._name,
                status_code=resp.status_code,
            )

        task_id = resp.json().get("data", {}).get("task_id")
        if not task_id:
            raise GenerationError("No task_id from Tripo3D", provider=self._name)

        # Poll for completion
        mesh_url = await self._poll_cloud_task(task_id, headers)

        # Download the mesh
        mesh_resp = await self._client.get(mesh_url)
        if mesh_resp.status_code != 200:
            raise GenerationError(
                f"Failed to download mesh from Tripo3D",
                provider=self._name,
            )

        return GenerationResult(
            data=mesh_resp.content,
            mime_type="model/gltf-binary",
            generation_type=GenerationType.THREE_D,
            provider_name=self._name,
            model_name="tripo3d-cloud",
            metadata={
                "mode": payload["type"],
                "task_id": task_id,
                "format": "glb",
            },
        )

    async def _upload_image_cloud(self, image_data: bytes, headers: Dict) -> str:
        """Upload image to Tripo3D and get file token."""
        import io

        resp = await self._client.post(
            f"{self._cloud_url}/upload",
            headers={"Authorization": headers["Authorization"]},
            files={"file": ("input.png", io.BytesIO(image_data), "image/png")},
        )
        if resp.status_code != 200:
            raise GenerationError(
                f"Image upload to Tripo3D failed: {resp.status_code}",
                provider=self._name,
            )
        return resp.json().get("data", {}).get("image_token", "")

    async def _poll_cloud_task(
        self, task_id: str, headers: Dict, poll_interval: float = 3.0
    ) -> str:
        """Poll Tripo3D task until complete. Returns the model download URL."""
        import asyncio

        deadline = time.monotonic() + self._timeout

        while time.monotonic() < deadline:
            try:
                resp = await self._client.get(
                    f"{self._cloud_url}/task/{task_id}",
                    headers=headers,
                    timeout=_CONNECT_TIMEOUT,
                )
            except Exception:
                await asyncio.sleep(poll_interval)
                continue

            if resp.status_code != 200:
                await asyncio.sleep(poll_interval)
                continue

            data = resp.json().get("data", {})
            status = data.get("status", "")

            if status == "success":
                output = data.get("output", {})
                model_url = output.get("model", output.get("pbr_model", ""))
                if model_url:
                    return model_url
                raise GenerationError("No model URL in completed task", provider=self._name)

            if status in ("failed", "cancelled"):
                raise GenerationError(
                    f"Tripo3D task {status}: {data.get('message', 'unknown')}",
                    provider=self._name,
                )

            await asyncio.sleep(poll_interval)

        raise GenerationTimeoutError(self._name, self._timeout)

    async def check_health(self) -> ProviderStatus:
        try:
            if self._use_cloud:
                resp = await self._client.get(
                    f"{self._cloud_url}/task",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    timeout=_CONNECT_TIMEOUT,
                )
            else:
                resp = await self._client.get(
                    f"{self._base_url}/api/health",
                    timeout=_CONNECT_TIMEOUT,
                )
            if resp.status_code in (200, 401):
                self._status = ProviderStatus.AVAILABLE
            else:
                self._status = ProviderStatus.DEGRADED
        except Exception:
            self._status = ProviderStatus.UNAVAILABLE
        return self._status

    def supported_models(self) -> List[str]:
        return ["triposr-v1", "tripo3d-cloud"]


# ============================================================================
# Meshy (Cloud API)
# ============================================================================


class MeshyProvider(Model3DProvider):
    """
    3D model generation via Meshy.ai cloud API.

    Supports:
    - Text-to-3D: Generate 3D model from text description
    - Image-to-3D: Generate 3D model from a reference image
    - AI texturing: Apply textures to existing meshes

    Two-stage pipeline:
    1. Preview: Quick low-poly generation (~30s)
    2. Refine: High-quality with PBR textures (~2-5min)

    API: https://api.meshy.ai (API key required)
    Docs: https://docs.meshy.ai
    """

    _API_BASE = "https://api.meshy.ai/v2"

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = _GENERATE_TIMEOUT,
        auto_refine: bool = True,
    ):
        super().__init__("meshy")
        self._api_key = api_key
        self._timeout = timeout
        self._auto_refine = auto_refine
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=_CONNECT_TIMEOUT, read=timeout, write=30.0, pool=10.0),
        )

    def _get_api_key(self) -> str:
        """Resolve API key."""
        if self._api_key:
            return self._api_key
        import os
        key = os.environ.get("MESHY_API_KEY", "")
        if not key:
            raise GenerationError(
                "Meshy API key not configured. Set MESHY_API_KEY environment variable.",
                provider=self._name,
            )
        return key

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._get_api_key()}",
            "Content-Type": "application/json",
        }

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate 3D model via Meshy API."""
        if request.source_image:
            return await self._image_to_3d(request)
        return await self._text_to_3d(request)

    async def _text_to_3d(self, request: GenerationRequest) -> GenerationResult:
        """Text-to-3D via Meshy."""
        payload = {
            "mode": "preview",
            "prompt": request.prompt,
            "negative_prompt": request.negative_prompt or "",
            "art_style": request.extra.get("art_style", "realistic"),
            "seed": request.seed if request.seed is not None else 0,
        }

        self._logger.info(f"Meshy text-to-3D: prompt='{request.prompt[:80]}...'")

        try:
            resp = await self._client.post(
                f"{self._API_BASE}/text-to-3d",
                json=payload,
                headers=self._headers(),
            )
        except httpx.ConnectError as exc:
            raise ProviderUnavailableError(self._name, str(exc)) from exc

        if resp.status_code not in (200, 202):
            raise GenerationError(
                f"Meshy text-to-3D error {resp.status_code}: {resp.text[:500]}",
                provider=self._name,
                status_code=resp.status_code,
            )

        task = resp.json()
        task_id = task.get("result")
        if not task_id:
            raise GenerationError("No task ID from Meshy", provider=self._name)

        # Poll preview
        preview_data = await self._poll_task(
            f"{self._API_BASE}/text-to-3d/{task_id}"
        )

        # Auto-refine if enabled
        if self._auto_refine:
            try:
                preview_data = await self._refine(task_id, request)
            except GenerationError as exc:
                self._logger.warning(f"Refinement failed, using preview: {exc}")

        # Download the GLB
        model_url = preview_data.get("model_urls", {}).get("glb", "")
        if not model_url:
            raise GenerationError("No GLB URL in Meshy response", provider=self._name)

        mesh_bytes = await self._download_model(model_url)

        return GenerationResult(
            data=mesh_bytes,
            mime_type="model/gltf-binary",
            generation_type=GenerationType.THREE_D,
            provider_name=self._name,
            model_name="meshy-text-to-3d",
            metadata={
                "prompt": request.prompt,
                "mode": "text_to_3d",
                "task_id": task_id,
                "art_style": payload["art_style"],
                "refined": self._auto_refine,
                "thumbnail_url": preview_data.get("thumbnail_url", ""),
                "texture_urls": preview_data.get("texture_urls", {}),
            },
        )

    async def _image_to_3d(self, request: GenerationRequest) -> GenerationResult:
        """Image-to-3D via Meshy."""
        # Upload image as base64 data URI
        img_b64 = base64.b64encode(request.source_image).decode("ascii")
        image_url = f"data:image/png;base64,{img_b64}"

        payload = {
            "image_url": image_url,
            "enable_pbr": request.generate_textures,
        }

        self._logger.info("Meshy image-to-3D generation")

        try:
            resp = await self._client.post(
                f"{self._API_BASE}/image-to-3d",
                json=payload,
                headers=self._headers(),
            )
        except httpx.ConnectError as exc:
            raise ProviderUnavailableError(self._name, str(exc)) from exc

        if resp.status_code not in (200, 202):
            raise GenerationError(
                f"Meshy image-to-3D error {resp.status_code}: {resp.text[:500]}",
                provider=self._name,
                status_code=resp.status_code,
            )

        task = resp.json()
        task_id = task.get("result")
        if not task_id:
            raise GenerationError("No task ID from Meshy", provider=self._name)

        result_data = await self._poll_task(
            f"{self._API_BASE}/image-to-3d/{task_id}"
        )

        model_url = result_data.get("model_urls", {}).get("glb", "")
        if not model_url:
            raise GenerationError("No GLB URL in Meshy response", provider=self._name)

        mesh_bytes = await self._download_model(model_url)

        return GenerationResult(
            data=mesh_bytes,
            mime_type="model/gltf-binary",
            generation_type=GenerationType.THREE_D,
            provider_name=self._name,
            model_name="meshy-image-to-3d",
            metadata={
                "mode": "image_to_3d",
                "task_id": task_id,
                "pbr_enabled": request.generate_textures,
            },
        )

    async def _refine(self, preview_task_id: str, request: GenerationRequest) -> Dict:
        """Submit refinement task for a preview model."""
        payload = {
            "mode": "refine",
            "preview_task_id": preview_task_id,
            "texture_richness": request.extra.get("texture_richness", "high"),
        }

        resp = await self._client.post(
            f"{self._API_BASE}/text-to-3d",
            json=payload,
            headers=self._headers(),
        )
        if resp.status_code not in (200, 202):
            raise GenerationError(
                f"Meshy refine error {resp.status_code}: {resp.text[:500]}",
                provider=self._name,
            )

        refine_id = resp.json().get("result")
        return await self._poll_task(f"{self._API_BASE}/text-to-3d/{refine_id}")

    async def _poll_task(self, url: str, poll_interval: float = 3.0) -> Dict:
        """Poll a Meshy task until complete."""
        import asyncio

        deadline = time.monotonic() + self._timeout

        while time.monotonic() < deadline:
            try:
                resp = await self._client.get(url, headers=self._headers(), timeout=_CONNECT_TIMEOUT)
            except Exception:
                await asyncio.sleep(poll_interval)
                continue

            if resp.status_code != 200:
                await asyncio.sleep(poll_interval)
                continue

            data = resp.json()
            status = data.get("status", "")

            if status == "SUCCEEDED":
                return data

            if status in ("FAILED", "EXPIRED"):
                raise GenerationError(
                    f"Meshy task {status}: {data.get('task_error', {}).get('message', 'unknown')}",
                    provider=self._name,
                )

            await asyncio.sleep(poll_interval)

        raise GenerationTimeoutError(self._name, self._timeout)

    async def _download_model(self, url: str) -> bytes:
        """Download model file from URL."""
        resp = await self._client.get(url)
        if resp.status_code != 200:
            raise GenerationError(
                f"Failed to download model from Meshy: {resp.status_code}",
                provider=self._name,
            )
        return resp.content

    async def check_health(self) -> ProviderStatus:
        try:
            resp = await self._client.get(
                f"{self._API_BASE}/text-to-3d",
                headers=self._headers(),
                timeout=_CONNECT_TIMEOUT,
            )
            # Even 401 means the API is reachable
            if resp.status_code in (200, 401, 403):
                self._status = ProviderStatus.AVAILABLE
            else:
                self._status = ProviderStatus.DEGRADED
        except GenerationError:
            self._status = ProviderStatus.UNAVAILABLE
        except Exception:
            self._status = ProviderStatus.UNAVAILABLE
        return self._status

    def supported_models(self) -> List[str]:
        return ["meshy-text-to-3d", "meshy-image-to-3d"]
