"""
Tests for generative media features — image, video, 3D generation, and companion agent.

Covers:
- Generation data model construction and serialization
- Provider instantiation and configuration
- GenerationManager initialization and provider listing
- Agent construction, metadata, and capabilities
- Orchestrator classification for generation tasks
- Companion agent personality, mood tracking, and memory
- Multimodal pipeline registration of new processors
- API endpoints for /v1/generate/* and new agents
- Config GenerationConfig validation
"""

import base64
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ============================================================================
# Generation Base Types
# ============================================================================


class TestGenerationBaseTypes:
    """Test generation data models, enums, and error types."""

    def test_generation_type_enum(self):
        from versaai.generation.base import GenerationType
        assert GenerationType.IMAGE == "image"
        assert GenerationType.VIDEO == "video"
        assert GenerationType.THREE_D == "3d"

    def test_provider_status_enum(self):
        from versaai.generation.base import ProviderStatus
        assert ProviderStatus.AVAILABLE == "available"
        assert ProviderStatus.UNAVAILABLE == "unavailable"
        assert ProviderStatus.DEGRADED == "degraded"

    def test_image_format_enum(self):
        from versaai.generation.base import ImageFormat
        assert ImageFormat.PNG == "png"
        assert ImageFormat.JPEG == "jpeg"
        assert ImageFormat.WEBP == "webp"

    def test_video_format_enum(self):
        from versaai.generation.base import VideoFormat
        assert VideoFormat.MP4 == "mp4"
        assert VideoFormat.GIF == "gif"
        assert VideoFormat.WEBM == "webm"

    def test_model_3d_format_enum(self):
        from versaai.generation.base import Model3DFormat
        assert Model3DFormat.GLB == "glb"
        assert Model3DFormat.OBJ == "obj"
        assert Model3DFormat.STL == "stl"

    def test_generation_request_defaults(self):
        from versaai.generation.base import GenerationRequest, GenerationType
        req = GenerationRequest(prompt="A cat", generation_type=GenerationType.IMAGE)
        assert req.prompt == "A cat"
        assert req.generation_type == GenerationType.IMAGE
        assert req.width == 1024
        assert req.height == 1024
        assert req.steps == 30
        assert req.guidance_scale == 7.5
        assert req.negative_prompt == ""
        assert req.seed is None

    def test_generation_request_custom(self):
        from versaai.generation.base import GenerationRequest, GenerationType
        req = GenerationRequest(
            prompt="A landscape",
            generation_type=GenerationType.IMAGE,
            width=1024,
            height=768,
            steps=50,
            guidance_scale=12.0,
            negative_prompt="blurry, low quality",
            seed=42,
            num_images=2,
        )
        assert req.width == 1024
        assert req.height == 768
        assert req.steps == 50
        assert req.num_images == 2
        assert req.seed == 42

    def test_generation_result_construction(self):
        from versaai.generation.base import GenerationResult, GenerationType
        result = GenerationResult(
            data=b"\x89PNG\r\n\x1a\n" + b"\x00" * 100,
            mime_type="image/png",
            generation_type=GenerationType.IMAGE,
            provider_name="stable_diffusion",
            model_name="sd_xl_base_1.0",
            generation_time=3.5,
            seed_used=42,
            metadata={"sampler": "euler_a"},
        )
        assert result.provider_name == "stable_diffusion"
        assert result.generation_time == 3.5
        assert result.seed_used == 42

    def test_generation_result_to_base64(self):
        from versaai.generation.base import GenerationResult, GenerationType
        data = b"\x89PNG_FAKE"
        result = GenerationResult(
            data=data,
            mime_type="image/png",
            generation_type=GenerationType.IMAGE,
            provider_name="test",
            generation_time=0.1,
        )
        b64 = result.to_base64()
        assert base64.b64decode(b64) == data

    def test_generation_result_to_data_uri(self):
        from versaai.generation.base import GenerationResult, GenerationType
        data = b"test_data"
        result = GenerationResult(
            data=data,
            mime_type="image/png",
            generation_type=GenerationType.IMAGE,
            provider_name="test",
            generation_time=0.1,
        )
        uri = result.to_data_uri()
        assert uri.startswith("data:image/png;base64,")

    def test_generation_result_save(self, tmp_path):
        from versaai.generation.base import GenerationResult, GenerationType
        data = b"fake_image_content"
        result = GenerationResult(
            data=data,
            mime_type="image/png",
            generation_type=GenerationType.IMAGE,
            provider_name="test",
            generation_time=0.1,
        )
        path = tmp_path / "output.png"
        result.save(str(path))
        assert path.read_bytes() == data

    def test_generation_error_hierarchy(self):
        from versaai.generation.base import (
            GenerationError,
            ProviderUnavailableError,
            GenerationTimeoutError,
            ContentPolicyError,
        )
        assert issubclass(ProviderUnavailableError, GenerationError)
        assert issubclass(GenerationTimeoutError, GenerationError)
        assert issubclass(ContentPolicyError, GenerationError)

        err = ProviderUnavailableError("sd", "Connection refused")
        assert "sd" in str(err)


# ============================================================================
# Providers — Construction Only (no network)
# ============================================================================


class TestProviderConstruction:
    """Test that providers can be instantiated with correct configs."""

    def test_stable_diffusion_provider(self):
        from versaai.generation.image_gen import StableDiffusionProvider
        p = StableDiffusionProvider(base_url="http://localhost:7860")
        assert p.name == "stable_diffusion"
        assert p.generation_type.value == "image"

    def test_comfyui_provider(self):
        from versaai.generation.image_gen import ComfyUIImageProvider
        p = ComfyUIImageProvider(base_url="http://localhost:8188")
        assert p.name == "comfyui"

    def test_dalle_provider(self):
        from versaai.generation.image_gen import DallEProvider
        p = DallEProvider(api_key="sk-test-key")
        assert p.name == "dalle"
        assert p.generation_type.value == "image"

    def test_stable_video_provider(self):
        from versaai.generation.video_gen import StableVideoProvider
        p = StableVideoProvider(base_url="http://localhost:8188")
        assert p.name == "stable_video"
        assert p.generation_type.value == "video"

    def test_triposr_provider(self):
        from versaai.generation.model_3d_gen import TripoSRProvider
        p = TripoSRProvider(base_url="http://localhost:8090")
        assert p.name == "triposr"
        assert p.generation_type.value == "3d"

    def test_meshy_provider(self):
        from versaai.generation.model_3d_gen import MeshyProvider
        p = MeshyProvider(api_key="test-key")
        assert p.name == "meshy"
        assert p.generation_type.value == "3d"


# ============================================================================
# GenerationManager
# ============================================================================


class TestGenerationManager:
    """Test GenerationManager initialization and provider management."""

    def test_default_construction(self):
        from versaai.generation.manager import GenerationManager
        manager = GenerationManager()
        assert manager is not None

    def test_construction_with_config(self):
        from versaai.generation.manager import GenerationManager
        config = {
            "image": {
                "provider": "stable_diffusion",
                "stable_diffusion": {"base_url": "http://localhost:7860"},
            },
            "video": {
                "provider": "stable_video",
                "stable_video": {"base_url": "http://localhost:8188"},
            },
            "3d": {
                "provider": "triposr",
                "triposr": {"base_url": "http://localhost:8090"},
            },
        }
        manager = GenerationManager()
        manager.initialize(config)
        providers = manager.list_providers()
        assert isinstance(providers, dict)
        assert len(providers) > 0

    def test_list_providers_includes_all_types(self):
        from versaai.generation.manager import GenerationManager
        manager = GenerationManager()
        manager.initialize()
        providers = manager.list_providers()
        assert "image" in providers
        assert "video" in providers
        assert "3d" in providers

    def test_provider_names_unique(self):
        from versaai.generation.manager import GenerationManager
        manager = GenerationManager()
        manager.initialize()
        providers = manager.list_providers()
        for gen_type, provider_list in providers.items():
            names = [p["name"] for p in provider_list]
            assert len(names) == len(set(names)), f"Duplicate names in {gen_type}"


# ============================================================================
# Generation Agents — Construction and Metadata
# ============================================================================


class TestGenerationAgents:
    """Test that generation agents can be constructed and have correct metadata."""

    def test_image_gen_agent_construct(self):
        from versaai.agents.image_gen_agent import ImageGenAgent
        agent = ImageGenAgent()
        assert agent.metadata.name == "ImageGenAgent"
        assert "text_to_image" in agent.metadata.capabilities

    def test_video_gen_agent_construct(self):
        from versaai.agents.video_gen_agent import VideoGenAgent
        agent = VideoGenAgent()
        assert agent.metadata.name == "VideoGenAgent"
        assert "text_to_video" in agent.metadata.capabilities

    def test_model_gen_agent_construct(self):
        from versaai.agents.model_gen_agent import ModelGenAgent
        agent = ModelGenAgent()
        assert agent.metadata.name == "ModelGenAgent"
        assert "text_to_3d" in agent.metadata.capabilities

    def test_companion_agent_construct(self):
        from versaai.agents.companion_agent import CompanionAgent
        agent = CompanionAgent()
        assert agent.metadata.name == "CompanionAgent"
        assert "conversational_ai" in agent.metadata.capabilities
        assert "emotional_intelligence" in agent.metadata.capabilities

    def test_companion_agent_default_personality(self):
        from versaai.agents.companion_agent import CompanionAgent
        agent = CompanionAgent()
        assert agent.personality.name == "Versa"
        assert "friendly" in agent.personality.traits
        assert agent.personality.humor_level == 0.5
        assert agent.personality.empathy_level == 0.8

    def test_companion_agent_custom_personality(self):
        from versaai.agents.companion_agent import CompanionAgent, CompanionPersonality
        personality = CompanionPersonality(
            name="Luna",
            traits=["playful", "creative", "energetic"],
            communication_style="casual and fun",
            humor_level=0.9,
        )
        agent = CompanionAgent(personality=personality)
        assert agent.personality.name == "Luna"
        assert "playful" in agent.personality.traits
        assert agent.personality.humor_level == 0.9


# ============================================================================
# Companion Personality and Mood
# ============================================================================


class TestCompanionPersonality:
    """Test companion personality system and mood tracking."""

    def test_personality_to_system_prompt(self):
        from versaai.agents.companion_agent import CompanionPersonality
        p = CompanionPersonality(name="TestBot", traits=["calm", "analytical"])
        prompt = p.to_system_prompt()
        assert "TestBot" in prompt
        assert "calm" in prompt
        assert "analytical" in prompt
        assert "PERSONALITY" in prompt
        assert "BEHAVIOR GUIDELINES" in prompt

    def test_mood_state_update(self):
        from versaai.agents.companion_agent import MoodState
        mood = MoodState()
        assert mood.current_sentiment == "neutral"
        assert mood.turn_count == 0

        mood.update("positive", 0.8)
        assert mood.current_sentiment == "positive"
        assert mood.sentiment_score == 0.8
        assert mood.turn_count == 1
        assert len(mood.mood_history) == 1

    def test_mood_dominant_mood_tracking(self):
        from versaai.agents.companion_agent import MoodState
        mood = MoodState()
        # Need 3+ entries for dominant mood to activate
        mood.update("positive", 0.8)
        mood.update("positive", 0.6)
        mood.update("positive", 0.9)
        assert mood.dominant_mood == "positive"

    def test_mood_negative_trend(self):
        from versaai.agents.companion_agent import MoodState
        mood = MoodState()
        mood.update("negative", -0.5)
        mood.update("negative", -0.7)
        mood.update("negative", -0.4)
        assert mood.dominant_mood == "negative"

    def test_mood_history_capped(self):
        from versaai.agents.companion_agent import MoodState
        mood = MoodState()
        for i in range(25):
            mood.update("neutral", 0.0)
        assert len(mood.mood_history) == 20
        assert mood.turn_count == 25

    def test_mood_context_string(self):
        from versaai.agents.companion_agent import MoodState
        mood = MoodState()
        # Empty initially
        assert mood.to_context_string() == ""

        mood.update("positive", 0.7)
        ctx = mood.to_context_string()
        assert "positive" in ctx
        assert "0.70" in ctx


# ============================================================================
# Companion Memory
# ============================================================================


class TestCompanionMemory:
    """Test conversation memory management."""

    def test_memory_add_message(self):
        from versaai.agents.companion_agent import ConversationMemory
        mem = ConversationMemory()
        mem.add_message("user", "Hello!")
        mem.add_message("assistant", "Hi there!")
        assert len(mem.messages) == 2

    def test_memory_rolling_window(self):
        from versaai.agents.companion_agent import ConversationMemory
        mem = ConversationMemory(max_messages=5)
        for i in range(10):
            mem.add_message("user", f"msg {i}")
        assert len(mem.messages) <= 5

    def test_memory_facts(self):
        from versaai.agents.companion_agent import ConversationMemory
        mem = ConversationMemory()
        mem.add_fact("name", "Alice")
        mem.add_fact("location", "New York")
        assert mem.user_facts["name"] == "Alice"
        assert mem.user_facts["location"] == "New York"

    def test_memory_topics(self):
        from versaai.agents.companion_agent import ConversationMemory
        mem = ConversationMemory()
        mem.add_topic("machine learning")
        mem.add_topic("game development")
        mem.add_topic("machine learning")  # Duplicate ignored
        assert len(mem.topics_discussed) == 2

    def test_memory_context_summary(self):
        from versaai.agents.companion_agent import ConversationMemory
        mem = ConversationMemory()
        mem.add_fact("name", "Bob")
        mem.add_topic("AI systems")
        summary = mem.get_context_summary()
        assert "Bob" in summary
        assert "AI systems" in summary


# ============================================================================
# Companion Sentiment Analysis
# ============================================================================


class TestCompanionSentiment:
    """Test the companion agent's sentiment analysis."""

    def _analyze(self, text: str):
        from versaai.agents.companion_agent import CompanionAgent
        agent = CompanionAgent()
        return agent._analyze_sentiment(text)

    def test_positive_sentiment(self):
        result = self._analyze("I'm so happy and excited about this!")
        assert result["sentiment"] == "positive"
        assert result["score"] > 0

    def test_negative_sentiment(self):
        result = self._analyze("I'm really frustrated and angry right now")
        assert result["sentiment"] == "negative"
        assert result["score"] < 0

    def test_neutral_sentiment(self):
        result = self._analyze("The meeting is at 3pm tomorrow")
        assert result["sentiment"] == "neutral"
        assert result["score"] == 0.0


# ============================================================================
# Companion Fact Extraction
# ============================================================================


class TestCompanionFactExtraction:
    """Test the companion's ability to extract facts from user messages."""

    def _extract(self, text: str):
        from versaai.agents.companion_agent import CompanionAgent
        agent = CompanionAgent()
        return agent._extract_facts(text)

    def test_extract_name(self):
        facts = self._extract("My name is Alice and I like coding")
        assert facts.get("name") == "Alice"

    def test_extract_location(self):
        facts = self._extract("I live in Seattle")
        assert "location" in facts
        assert "Seattle" in facts["location"]

    def test_extract_occupation(self):
        facts = self._extract("I work as a software engineer")
        assert "occupation" in facts

    def test_extract_age(self):
        facts = self._extract("I'm 28 years old")
        assert facts.get("age") == "28"

    def test_no_facts_in_plain_query(self):
        facts = self._extract("What's the weather like?")
        assert len(facts) == 0


# ============================================================================
# Companion Topic Extraction
# ============================================================================


class TestCompanionTopicExtraction:
    """Test topic extraction from user messages."""

    def _topics(self, text: str):
        from versaai.agents.companion_agent import CompanionAgent
        agent = CompanionAgent()
        return agent._extract_topics(text)

    def test_extract_about_topic(self):
        topics = self._topics("Tell me about machine learning")
        assert any("machine learning" in t for t in topics)

    def test_extract_interest_topic(self):
        topics = self._topics("I'm interested in game development and AI")
        assert len(topics) >= 1

    def test_no_topics_in_greeting(self):
        topics = self._topics("Hello!")
        assert len(topics) == 0


# ============================================================================
# Orchestrator Classification — New Patterns
# ============================================================================


class TestOrchestratorNewPatterns:
    """Test classifier for new generation and companion subtask types."""

    def test_classify_image_generation(self):
        from versaai.agents.orchestrator import classify_subtask
        assert classify_subtask("Generate an image of a sunset") == "image_gen"
        assert classify_subtask("Draw a picture of a cat") == "image_gen"
        assert classify_subtask("Create an image of a forest") == "image_gen"

    def test_classify_video_generation(self):
        from versaai.agents.orchestrator import classify_subtask
        assert classify_subtask("Generate a video of waves crashing") == "video_gen"
        assert classify_subtask("Create a short animation of a bouncing ball") == "video_gen"

    def test_classify_3d_generation(self):
        from versaai.agents.orchestrator import classify_subtask
        assert classify_subtask("Generate a 3D model of a chair") == "model_gen"
        assert classify_subtask("Create a 3D object of a sword") == "model_gen"

    def test_classify_companion(self):
        from versaai.agents.orchestrator import classify_subtask
        assert classify_subtask("Let's just talk about life") == "companion"
        assert classify_subtask("I'm bored, chat with me") == "companion"


# ============================================================================
# Multimodal Pipeline — New Processors
# ============================================================================


class TestMultimodalNewProcessors:
    """Test that new generation processors are registered in the pipeline."""

    def test_pipeline_has_text_to_image(self):
        from versaai.multimodal import MultimodalPipeline, Modality
        pipeline = MultimodalPipeline()
        proc = pipeline.registry.get(Modality.TEXT, Modality.IMAGE)
        assert proc is not None
        assert proc.capability().name == "text_to_image"

    def test_pipeline_has_text_to_video(self):
        from versaai.multimodal import MultimodalPipeline, Modality
        pipeline = MultimodalPipeline()
        proc = pipeline.registry.get(Modality.TEXT, Modality.VIDEO)
        assert proc is not None
        assert proc.capability().name == "text_to_video"

    def test_pipeline_has_text_to_3d(self):
        from versaai.multimodal import MultimodalPipeline, Modality
        pipeline = MultimodalPipeline()
        proc = pipeline.registry.get(Modality.TEXT, Modality.THREE_D)
        assert proc is not None
        assert proc.capability().name == "text_to_3d"

    def test_pipeline_routes_include_generation(self):
        from versaai.multimodal import MultimodalPipeline
        pipeline = MultimodalPipeline()
        routes = pipeline.available_routes()
        route_names = {r["name"] for r in routes}
        assert "text_to_image" in route_names
        assert "text_to_video" in route_names
        assert "text_to_3d" in route_names

    def test_pipeline_finds_path_text_to_image(self):
        from versaai.multimodal import MultimodalPipeline, Modality
        pipeline = MultimodalPipeline()
        path = pipeline.registry.find_path(Modality.TEXT, Modality.IMAGE)
        assert path is not None
        assert len(path) == 1
        assert path[0] == (Modality.TEXT, Modality.IMAGE)


# ============================================================================
# Config — GenerationConfig
# ============================================================================


class TestGenerationConfig:
    """Test generation configuration model."""

    def test_default_config(self):
        from versaai.config import GenerationConfig
        cfg = GenerationConfig()
        assert cfg.image_provider == "stable_diffusion"
        assert cfg.video_provider == "stable_video"
        assert cfg.model_3d_provider == "triposr"

    def test_stable_diffusion_defaults(self):
        from versaai.config import GenerationConfig
        cfg = GenerationConfig()
        assert cfg.stable_diffusion.base_url == "http://localhost:7860"
        assert cfg.stable_diffusion.enabled is True

    def test_dalle_disabled_by_default(self):
        from versaai.config import GenerationConfig
        cfg = GenerationConfig()
        assert cfg.dalle.enabled is False

    def test_meshy_disabled_by_default(self):
        from versaai.config import GenerationConfig
        cfg = GenerationConfig()
        assert cfg.meshy.enabled is False

    def test_settings_has_generation(self):
        from versaai.config import settings
        assert hasattr(settings, "generation")
        assert settings.generation.image_provider == "stable_diffusion"


# ============================================================================
# Agent Registry — New Agents Listed
# ============================================================================


class TestAgentRegistryNewAgents:
    """Test that new agents appear in the agents __init__ exports."""

    def test_exports_image_gen_agent(self):
        from versaai.agents import ImageGenAgent
        assert ImageGenAgent is not None

    def test_exports_video_gen_agent(self):
        from versaai.agents import VideoGenAgent
        assert VideoGenAgent is not None

    def test_exports_model_gen_agent(self):
        from versaai.agents import ModelGenAgent
        assert ModelGenAgent is not None

    def test_exports_companion_agent(self):
        from versaai.agents import CompanionAgent
        assert CompanionAgent is not None


# ============================================================================
# API Agent Info — New Agents Listed
# ============================================================================


class TestAgentInfoNewAgents:
    """Test that new agents appear in the AGENT_INFO list."""

    def test_agent_info_includes_new_agents(self):
        from versaai.api.routes.agents import AGENT_INFO
        names = {a.name for a in AGENT_INFO}
        assert "image_gen" in names
        assert "video_gen" in names
        assert "model_gen" in names
        assert "companion" in names

    def test_agent_info_count(self):
        from versaai.api.routes.agents import AGENT_INFO
        # 5 original + 4 new = 9
        assert len(AGENT_INFO) == 9


# ============================================================================
# API Agent Factory — New Agents Creatable
# ============================================================================


class TestAgentFactoryNewAgents:
    """Test that agent factory can create new agent types."""

    def test_create_image_gen_agent(self):
        from versaai.api.routes.agents import _get_or_create_agent, _agent_instances
        _agent_instances.pop("image_gen", None)
        agent = _get_or_create_agent("image_gen")
        assert agent.metadata.name == "ImageGenAgent"
        _agent_instances.pop("image_gen", None)

    def test_create_video_gen_agent(self):
        from versaai.api.routes.agents import _get_or_create_agent, _agent_instances
        _agent_instances.pop("video_gen", None)
        agent = _get_or_create_agent("video_gen")
        assert agent.metadata.name == "VideoGenAgent"
        _agent_instances.pop("video_gen", None)

    def test_create_model_gen_agent(self):
        from versaai.api.routes.agents import _get_or_create_agent, _agent_instances
        _agent_instances.pop("model_gen", None)
        agent = _get_or_create_agent("model_gen")
        assert agent.metadata.name == "ModelGenAgent"
        _agent_instances.pop("model_gen", None)

    def test_create_companion_agent(self):
        from versaai.api.routes.agents import _get_or_create_agent, _agent_instances
        _agent_instances.pop("companion", None)
        agent = _get_or_create_agent("companion")
        assert agent.metadata.name == "CompanionAgent"
        _agent_instances.pop("companion", None)


# ============================================================================
# Generation API Route Schemas
# ============================================================================


class TestGenerationAPISchemas:
    """Test generation API request/response schemas."""

    def test_image_request_defaults(self):
        from versaai.api.routes.generation import ImageGenerateRequest
        req = ImageGenerateRequest(prompt="A cat")
        assert req.width == 512
        assert req.height == 512
        assert req.num_inference_steps == 30
        assert req.guidance_scale == 7.5
        assert req.num_images == 1

    def test_video_request_defaults(self):
        from versaai.api.routes.generation import VideoGenerateRequest
        req = VideoGenerateRequest(prompt="Ocean waves")
        assert req.duration == 4.0
        assert req.fps == 8
        assert req.motion_strength == 0.7

    def test_3d_request_defaults(self):
        from versaai.api.routes.generation import Model3DGenerateRequest
        req = Model3DGenerateRequest(prompt="A chair")
        assert req.format == "glb"
        assert req.texture_resolution == 1024
        assert req.mesh_quality == "medium"


# ============================================================================
# Generation Package Imports
# ============================================================================


class TestGenerationPackageImports:
    """Test that the generation package exports everything correctly."""

    def test_imports_base_types(self):
        from versaai.generation import (
            GenerationType,
            GenerationRequest,
            GenerationResult,
            GenerationError,
            GenerationProvider,
            ProviderStatus,
        )
        assert GenerationType.IMAGE.value == "image"

    def test_imports_providers(self):
        from versaai.generation import (
            StableDiffusionProvider,
            ComfyUIImageProvider,
            DallEProvider,
            StableVideoProvider,
            TripoSRProvider,
            MeshyProvider,
        )
        assert StableDiffusionProvider is not None

    def test_imports_manager(self):
        from versaai.generation import GenerationManager
        assert GenerationManager is not None
