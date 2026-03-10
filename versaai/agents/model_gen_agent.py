"""
ModelGenAgent — specialized agent for AI 3D model generation.

Uses LLMClient for prompt design and the 3D generation pipeline
(TripoSR, Meshy) for mesh synthesis.

The agent handles:
1. Object description analysis and prompt optimization
2. Format selection based on use case (game asset, 3D printing, AR/VR)
3. Quality/speed tradeoff decision
4. Image-to-3D pipeline coordination
"""

import base64
import logging
from typing import Any, Dict, List, Optional

from versaai.agents.agent_base import AgentBase, AgentMetadata

logger = logging.getLogger(__name__)

_3D_PROMPT_SYSTEM = """\
You are an expert 3D model generation prompt engineer. Transform user requests
into optimized prompts for 3D model generation (TripoSR, Meshy).

Rules:
1. Describe the object from a neutral perspective
2. Include material details: "metallic", "wooden", "glass", "stone"
3. Specify intended use if apparent: "game asset", "3D print", "AR model"
4. Mention topology preferences: "low poly", "high detail", "smooth"
5. Keep the prompt concise and specific

Respond in EXACTLY this JSON format:
{
    "prompt": "<optimized 3D generation prompt>",
    "negative_prompt": "<what to avoid>",
    "art_style": "<realistic|cartoon|low_poly|sculpture|pbr>",
    "suggested_format": "<glb|obj|stl>",
    "suggested_texture_resolution": <int>,
    "mesh_quality": "<low|medium|high>",
    "use_case": "<game_asset|3d_printing|ar_vr|visualization|animation>"
}
"""


class ModelGenAgent(AgentBase):
    """
    Agent for AI-powered 3D model generation.

    Capabilities:
    - Text-to-3D model generation
    - Image-to-3D reconstruction
    - Format optimization for target platform
    - Quality/speed tradeoff management
    - Prompt optimization for 3D-specific models
    """

    def __init__(self):
        metadata = AgentMetadata(
            name="ModelGenAgent",
            description="AI-powered 3D model generation with format optimization",
            version="1.0.0",
            capabilities=[
                "text_to_3d",
                "image_to_3d",
                "format_optimization",
                "prompt_optimization",
                "mesh_quality_control",
            ],
        )
        super().__init__(metadata)

        self.llm = None
        self.generation_manager = None
        self.config: Dict[str, Any] = {}

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        if self._initialized:
            return

        self.config = config or {}
        self.logger.info("Initializing ModelGenAgent")

        from versaai.agents.llm_client import LLMClient
        self.llm = LLMClient(
            model=self.config.get("model"),
            system_prompt=_3D_PROMPT_SYSTEM,
            temperature=0.7,
            max_tokens=1024,
        )

        from versaai.generation.manager import GenerationManager
        self.generation_manager = GenerationManager()
        self.generation_manager.initialize(self.config.get("generation", {}))

        self._initialized = True
        self.logger.info("ModelGenAgent initialized")

    def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a 3D model from a natural language description or image.

        Args:
            task: Natural language object description.
            context: Optional:
                - source_image: bytes for image-to-3D
                - format: "glb", "obj", "stl"
                - provider: force provider
                - texture_resolution: int
                - generate_textures: bool
                - skip_prompt_optimization: bool

        Returns:
            {
                "result": str,
                "model_data": str (base64),
                "optimized_prompt": str,
                "metadata": {...},
                "steps": [...],
                "status": "success"
            }
        """
        if not self._initialized:
            raise RuntimeError("ModelGenAgent not initialized")

        import asyncio
        from versaai.generation.base import Model3DFormat

        ctx = context or {}
        steps = []
        status_cb = ctx.get("status_callback")

        # Step 1: Optimize prompt
        if ctx.get("skip_prompt_optimization") or ctx.get("source_image"):
            optimized = {
                "prompt": task,
                "negative_prompt": ctx.get("negative_prompt", ""),
                "art_style": ctx.get("art_style", "realistic"),
                "suggested_format": ctx.get("format", "glb"),
                "suggested_texture_resolution": ctx.get("texture_resolution", 1024),
                "mesh_quality": ctx.get("mesh_quality", "high"),
                "use_case": "general",
            }
        else:
            if status_cb:
                status_cb("Analyzing object description...")
            optimized = self._optimize_prompt(task)

        steps.append({
            "step": 1,
            "action": "prompt_optimization",
            "optimized": optimized.get("prompt", task),
            "art_style": optimized.get("art_style", ""),
            "use_case": optimized.get("use_case", ""),
        })

        # Step 2: Resolve format
        format_str = ctx.get("format", optimized.get("suggested_format", "glb"))
        format_map = {
            "glb": Model3DFormat.GLB,
            "gltf": Model3DFormat.GLTF,
            "obj": Model3DFormat.OBJ,
            "stl": Model3DFormat.STL,
            "fbx": Model3DFormat.FBX,
            "usdz": Model3DFormat.USDZ,
        }
        model_format = format_map.get(format_str, Model3DFormat.GLB)
        tex_res = ctx.get("texture_resolution", optimized.get("suggested_texture_resolution", 1024))

        if status_cb:
            status_cb(f"Generating 3D model ({format_str}, tex={tex_res})...")

        # Step 3: Generate
        try:
            coro = self.generation_manager.generate_3d(
                prompt=optimized.get("prompt", task),
                negative_prompt=optimized.get("negative_prompt", ""),
                model_3d_format=model_format,
                texture_resolution=tex_res,
                generate_textures=ctx.get("generate_textures", True),
                mesh_quality=optimized.get("mesh_quality", "high"),
                source_image=ctx.get("source_image"),
                provider=ctx.get("provider"),
                model=ctx.get("model"),
                seed=ctx.get("seed"),
                art_style=optimized.get("art_style", "realistic"),
            )
            try:
                result = asyncio.get_event_loop().run_until_complete(coro)
            except RuntimeError:
                result = asyncio.run(coro)
        except Exception as exc:
            self.logger.error(f"3D generation failed: {exc}")
            return {
                "result": f"3D model generation failed: {exc}",
                "steps": steps,
                "status": "error",
            }

        steps.append({
            "step": 2,
            "action": "3d_generation",
            "provider": result.provider_name,
            "generation_time": result.generation_time,
            "size_bytes": result.size_bytes,
            "format": format_str,
        })

        return {
            "result": f"3D model generated ({result.size_bytes} bytes, "
                      f"{format_str} via {result.provider_name})",
            "model_data": result.to_base64(),
            "mime_type": result.mime_type,
            "optimized_prompt": optimized.get("prompt", task),
            "art_style": optimized.get("art_style", ""),
            "steps": steps,
            "metadata": result.metadata,
            "status": "success",
        }

    def _optimize_prompt(self, user_request: str) -> Dict[str, Any]:
        """Use LLM to optimize 3D generation prompt."""
        import json
        try:
            response = self.llm.chat(
                f"Optimize this 3D model generation request:\n\n{user_request}",
                temperature=0.7,
                max_tokens=512,
            )
            text = response.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
            return json.loads(text)
        except (json.JSONDecodeError, Exception) as exc:
            self.logger.warning(f"3D prompt optimization failed ({exc})")
            return {
                "prompt": user_request,
                "negative_prompt": "low quality, broken geometry, flat texture",
                "art_style": "realistic",
                "suggested_format": "glb",
                "suggested_texture_resolution": 1024,
                "mesh_quality": "high",
                "use_case": "general",
            }

    def reset(self) -> None:
        self.logger.info("ModelGenAgent reset")
