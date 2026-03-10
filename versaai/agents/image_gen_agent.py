"""
ImageGenAgent — specialized agent for AI image generation.

Uses LLMClient for intelligent prompt engineering and the generation
pipeline for actual image synthesis. The agent:

1. Analyzes the user's request and refines it into an optimal generation prompt
2. Selects appropriate parameters (resolution, style, guidance)
3. Dispatches to the image generation pipeline
4. Returns the result with metadata and prompt explanation

This bridges natural language requests to the technical generation API,
handling prompt optimization, style detection, and parameter tuning.
"""

import base64
import logging
from typing import Any, Dict, List, Optional

from versaai.agents.agent_base import AgentBase, AgentMetadata

logger = logging.getLogger(__name__)

# System prompt for the LLM that optimizes image generation prompts
_PROMPT_ENGINEER_SYSTEM = """\
You are an expert AI image generation prompt engineer. Your role is to transform
user requests into optimized prompts for Stable Diffusion / DALL-E image generation.

Rules:
1. Expand vague descriptions into detailed, vivid prompts
2. Add quality boosters: "masterpiece, best quality, highly detailed, 8k"
3. Specify art style if not mentioned: "digital art", "photorealistic", "oil painting"
4. Include lighting, composition, and atmosphere details
5. Keep the prompt under 200 words
6. Generate a negative prompt that avoids common artifacts

Respond in EXACTLY this JSON format:
{
    "prompt": "<optimized positive prompt>",
    "negative_prompt": "<negative prompt>",
    "style": "<detected art style>",
    "suggested_width": <int>,
    "suggested_height": <int>,
    "suggested_steps": <int>,
    "suggested_cfg": <float>
}
"""


class ImageGenAgent(AgentBase):
    """
    Agent for intelligent image generation from natural language.

    Capabilities:
    - Natural language to image generation
    - Automatic prompt optimization via LLM
    - Style detection and parameter tuning
    - Image-to-image transformation
    - Multi-image batch generation
    """

    def __init__(self):
        metadata = AgentMetadata(
            name="ImageGenAgent",
            description="AI-powered image generation with intelligent prompt engineering",
            version="1.0.0",
            capabilities=[
                "text_to_image",
                "image_to_image",
                "prompt_optimization",
                "style_transfer",
                "batch_generation",
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
        self.logger.info("Initializing ImageGenAgent")

        # LLM for prompt engineering
        from versaai.agents.llm_client import LLMClient
        self.llm = LLMClient(
            model=self.config.get("model"),
            system_prompt=_PROMPT_ENGINEER_SYSTEM,
            temperature=0.7,
            max_tokens=1024,
        )

        # Generation pipeline
        from versaai.generation.manager import GenerationManager
        self.generation_manager = GenerationManager()
        self.generation_manager.initialize(self.config.get("generation", {}))

        self._initialized = True
        self.logger.info("ImageGenAgent initialized")

    def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate an image from a natural language description.

        The agent uses the LLM to optimize the prompt, then dispatches
        to the generation pipeline.

        Args:
            task: Natural language image description.
            context: Optional context:
                - source_image: bytes for img2img
                - width/height: Override dimensions
                - provider: Force a specific provider
                - skip_prompt_optimization: bool (use raw prompt)
                - num_images: int (batch size)

        Returns:
            {
                "result": "Image generated successfully",
                "image_data": str (base64),
                "optimized_prompt": str,
                "negative_prompt": str,
                "metadata": {...},
                "steps": [...],
                "status": "success"
            }
        """
        if not self._initialized:
            raise RuntimeError("ImageGenAgent not initialized")

        import asyncio
        ctx = context or {}
        steps = []
        status_cb = ctx.get("status_callback")

        # Step 1: Optimize prompt via LLM (unless skipped)
        if ctx.get("skip_prompt_optimization"):
            optimized = {
                "prompt": task,
                "negative_prompt": ctx.get("negative_prompt", ""),
                "style": "unspecified",
                "suggested_width": ctx.get("width", 1024),
                "suggested_height": ctx.get("height", 1024),
                "suggested_steps": ctx.get("steps", 30),
                "suggested_cfg": ctx.get("guidance_scale", 7.5),
            }
            steps.append({"step": 1, "action": "prompt_passthrough", "result": "Used raw prompt"})
        else:
            if status_cb:
                status_cb("Optimizing prompt with AI...")
            optimized = self._optimize_prompt(task)
            steps.append({
                "step": 1,
                "action": "prompt_optimization",
                "original": task,
                "optimized": optimized.get("prompt", task),
                "style": optimized.get("style", ""),
            })

        # Step 2: Apply context overrides
        width = ctx.get("width", optimized.get("suggested_width", 1024))
        height = ctx.get("height", optimized.get("suggested_height", 1024))
        gen_steps = ctx.get("steps", optimized.get("suggested_steps", 30))
        cfg = ctx.get("guidance_scale", optimized.get("suggested_cfg", 7.5))
        provider = ctx.get("provider")
        num_images = ctx.get("num_images", 1)

        # Step 3: Generate
        if status_cb:
            status_cb(f"Generating image ({width}x{height}, {gen_steps} steps)...")

        try:
            result = asyncio.get_event_loop().run_until_complete(
                self.generation_manager.generate_image(
                    prompt=optimized.get("prompt", task),
                    negative_prompt=optimized.get("negative_prompt", ""),
                    width=width,
                    height=height,
                    steps=gen_steps,
                    guidance_scale=cfg,
                    seed=ctx.get("seed"),
                    num_images=num_images,
                    source_image=ctx.get("source_image"),
                    source_image_strength=ctx.get("source_image_strength", 0.75),
                    provider=provider,
                    model=ctx.get("model"),
                )
            )
        except RuntimeError:
            # No event loop running — create one
            result = asyncio.run(
                self.generation_manager.generate_image(
                    prompt=optimized.get("prompt", task),
                    negative_prompt=optimized.get("negative_prompt", ""),
                    width=width,
                    height=height,
                    steps=gen_steps,
                    guidance_scale=cfg,
                    seed=ctx.get("seed"),
                    num_images=num_images,
                    source_image=ctx.get("source_image"),
                    source_image_strength=ctx.get("source_image_strength", 0.75),
                    provider=provider,
                    model=ctx.get("model"),
                )
            )

        steps.append({
            "step": 2,
            "action": "image_generation",
            "provider": result.provider_name,
            "model": result.model_name,
            "generation_time": result.generation_time,
            "size_bytes": result.size_bytes,
        })

        img_b64 = result.to_base64()

        return {
            "result": f"Image generated successfully ({result.size_bytes} bytes, "
                      f"{result.generation_time:.1f}s via {result.provider_name})",
            "image_data": img_b64,
            "mime_type": result.mime_type,
            "optimized_prompt": optimized.get("prompt", task),
            "negative_prompt": optimized.get("negative_prompt", ""),
            "seed_used": result.seed_used,
            "steps": steps,
            "metadata": result.metadata,
            "status": "success",
        }

    def _optimize_prompt(self, user_request: str) -> Dict[str, Any]:
        """Use LLM to transform user request into optimal generation prompt."""
        import json

        try:
            response = self.llm.chat(
                f"Optimize this image generation request:\n\n{user_request}",
                temperature=0.7,
                max_tokens=512,
            )

            # Parse JSON from response
            # Handle markdown code blocks
            text = response.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
            return json.loads(text)

        except (json.JSONDecodeError, Exception) as exc:
            self.logger.warning(f"Prompt optimization failed ({exc}), using raw prompt")
            return {
                "prompt": user_request,
                "negative_prompt": (
                    "blurry, low quality, distorted, deformed, ugly, "
                    "bad anatomy, watermark, text, signature"
                ),
                "style": "unspecified",
                "suggested_width": 1024,
                "suggested_height": 1024,
                "suggested_steps": 30,
                "suggested_cfg": 7.5,
            }

    def reset(self) -> None:
        self.logger.info("ImageGenAgent reset")
