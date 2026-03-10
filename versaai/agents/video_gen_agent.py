"""
VideoGenAgent — specialized agent for AI video generation.

Uses LLMClient for scene understanding and prompt crafting, then
dispatches to the video generation pipeline (AnimateDiff, SVD).

The agent handles:
1. Scene analysis and decomposition from natural language
2. Motion planning — inferring camera movement, subject motion
3. Prompt optimization for video-specific models
4. Source image selection for img2vid workflows
"""

import base64
import logging
from typing import Any, Dict, List, Optional

from versaai.agents.agent_base import AgentBase, AgentMetadata

logger = logging.getLogger(__name__)

_VIDEO_PROMPT_SYSTEM = """\
You are an expert AI video generation prompt engineer. Transform user requests
into optimized prompts for video generation models (AnimateDiff, SVD).

Rules:
1. Describe motion explicitly: "camera panning left", "subject walking forward"
2. Keep temporal consistency in mind — describe a single coherent scene
3. Add quality tokens: "smooth motion, high quality, cinematic"
4. Specify atmosphere: lighting, time of day, mood
5. Keep prompts concise (under 150 words)

Respond in EXACTLY this JSON format:
{
    "prompt": "<optimized video prompt>",
    "negative_prompt": "<what to avoid>",
    "motion_description": "<description of intended motion>",
    "suggested_duration": <float seconds>,
    "suggested_fps": <int>,
    "suggested_width": <int>,
    "suggested_height": <int>,
    "suggested_motion_strength": <float 0.0-1.0>
}
"""


class VideoGenAgent(AgentBase):
    """
    Agent for AI-powered video generation from natural language.

    Capabilities:
    - Text-to-video via AnimateDiff
    - Image-to-video via Stable Video Diffusion
    - Scene analysis and motion planning
    - Prompt optimization for temporal coherence
    """

    def __init__(self):
        metadata = AgentMetadata(
            name="VideoGenAgent",
            description="AI-powered video generation with scene analysis and motion planning",
            version="1.0.0",
            capabilities=[
                "text_to_video",
                "image_to_video",
                "scene_analysis",
                "motion_planning",
                "prompt_optimization",
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
        self.logger.info("Initializing VideoGenAgent")

        from versaai.agents.llm_client import LLMClient
        self.llm = LLMClient(
            model=self.config.get("model"),
            system_prompt=_VIDEO_PROMPT_SYSTEM,
            temperature=0.7,
            max_tokens=1024,
        )

        from versaai.generation.manager import GenerationManager
        self.generation_manager = GenerationManager()
        self.generation_manager.initialize(self.config.get("generation", {}))

        self._initialized = True
        self.logger.info("VideoGenAgent initialized")

    def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a video from a natural language description.

        Args:
            task: Natural language video description.
            context: Optional:
                - source_image: bytes for img2vid (SVD)
                - duration: float seconds
                - fps: int
                - width/height: dimensions
                - provider: force provider
                - skip_prompt_optimization: bool

        Returns:
            {
                "result": str,
                "video_data": str (base64),
                "optimized_prompt": str,
                "metadata": {...},
                "steps": [...],
                "status": "success"
            }
        """
        if not self._initialized:
            raise RuntimeError("VideoGenAgent not initialized")

        import asyncio
        ctx = context or {}
        steps = []
        status_cb = ctx.get("status_callback")

        # Step 1: Optimize prompt
        if ctx.get("skip_prompt_optimization"):
            optimized = {
                "prompt": task,
                "negative_prompt": ctx.get("negative_prompt", ""),
                "motion_description": "",
                "suggested_duration": ctx.get("duration", 4.0),
                "suggested_fps": ctx.get("fps", 8),
                "suggested_width": ctx.get("width", 512),
                "suggested_height": ctx.get("height", 512),
                "suggested_motion_strength": ctx.get("motion_strength", 0.5),
            }
        else:
            if status_cb:
                status_cb("Analyzing scene and optimizing prompt...")
            optimized = self._optimize_prompt(task)

        steps.append({
            "step": 1,
            "action": "prompt_optimization",
            "optimized": optimized.get("prompt", task),
            "motion": optimized.get("motion_description", ""),
        })

        # Step 2: Apply overrides
        duration = ctx.get("duration", optimized.get("suggested_duration", 4.0))
        fps = ctx.get("fps", optimized.get("suggested_fps", 8))
        width = ctx.get("width", optimized.get("suggested_width", 512))
        height = ctx.get("height", optimized.get("suggested_height", 512))
        motion = ctx.get("motion_strength", optimized.get("suggested_motion_strength", 0.5))

        if status_cb:
            status_cb(f"Generating video ({width}x{height}, {duration}s at {fps}fps)...")

        # Step 3: Generate
        try:
            coro = self.generation_manager.generate_video(
                prompt=optimized.get("prompt", task),
                negative_prompt=optimized.get("negative_prompt", ""),
                width=width,
                height=height,
                duration_seconds=duration,
                fps=fps,
                motion_strength=motion,
                source_image=ctx.get("source_image"),
                provider=ctx.get("provider"),
                model=ctx.get("model"),
                seed=ctx.get("seed"),
            )
            try:
                result = asyncio.get_event_loop().run_until_complete(coro)
            except RuntimeError:
                result = asyncio.run(coro)
        except Exception as exc:
            self.logger.error(f"Video generation failed: {exc}")
            return {
                "result": f"Video generation failed: {exc}",
                "steps": steps,
                "status": "error",
            }

        steps.append({
            "step": 2,
            "action": "video_generation",
            "provider": result.provider_name,
            "generation_time": result.generation_time,
            "size_bytes": result.size_bytes,
        })

        return {
            "result": f"Video generated ({result.size_bytes} bytes, "
                      f"{result.generation_time:.1f}s via {result.provider_name})",
            "video_data": result.to_base64(),
            "mime_type": result.mime_type,
            "optimized_prompt": optimized.get("prompt", task),
            "motion_description": optimized.get("motion_description", ""),
            "steps": steps,
            "metadata": result.metadata,
            "status": "success",
        }

    def _optimize_prompt(self, user_request: str) -> Dict[str, Any]:
        """Use LLM to optimize video generation prompt."""
        import json
        try:
            response = self.llm.chat(
                f"Optimize this video generation request:\n\n{user_request}",
                temperature=0.7,
                max_tokens=512,
            )
            text = response.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
            return json.loads(text)
        except (json.JSONDecodeError, Exception) as exc:
            self.logger.warning(f"Video prompt optimization failed ({exc})")
            return {
                "prompt": user_request,
                "negative_prompt": "blurry, low quality, distorted, flickering, watermark",
                "motion_description": "smooth natural motion",
                "suggested_duration": 4.0,
                "suggested_fps": 8,
                "suggested_width": 512,
                "suggested_height": 512,
                "suggested_motion_strength": 0.5,
            }

    def reset(self) -> None:
        self.logger.info("VideoGenAgent reset")
