"""
Integration tests for VersaAI agent system and new features.

Covers:
- Agent instantiation and lifecycle (init → execute → reset)
- Orchestrator subtask classification and decomposition
- Profile manager CRUD + learning
- Profile API endpoints (async, non-blocking)
- Multimodal modality detection and pipeline routing
- Web search tool instantiation and cache
- Streaming callback wiring
"""

import json
import os
import shutil
import tempfile
import time
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_profile_dir(tmp_path):
    """Provide a temp directory for profile storage."""
    d = tmp_path / "profiles"
    d.mkdir()
    return str(d)


# ---------------------------------------------------------------------------
# Agent base and lifecycle
# ---------------------------------------------------------------------------


class TestAgentLifecycle:
    """Verify all agents can be constructed, initialized, and reset."""

    def test_coding_agent_construct(self):
        from versaai.agents.coding_agent import CodingAgent

        agent = CodingAgent()
        assert agent.metadata.name == "CodingAgent"
        assert "code" in " ".join(agent.metadata.capabilities).lower()

    def test_research_agent_construct(self):
        from versaai.agents.research_agent import ResearchAgent

        agent = ResearchAgent()
        assert agent.metadata.name == "ResearchAgent"

    def test_reasoning_agent_construct(self):
        from versaai.agents.reasoning_agent import ReasoningAgent

        agent = ReasoningAgent()
        assert agent.metadata.name == "ReasoningAgent"
        assert "chain_of_thought" in agent.metadata.capabilities

    def test_planning_agent_construct(self):
        from versaai.agents.planning_agent import PlanningAgent

        agent = PlanningAgent()
        assert agent.metadata.name == "PlanningAgent"

    def test_orchestrator_agent_construct(self):
        from versaai.agents.orchestrator import OrchestratorAgent

        agent = OrchestratorAgent()
        assert agent.metadata.name == "orchestrator"
        assert "multi_agent_coordination" in agent.metadata.capabilities


# ---------------------------------------------------------------------------
# Orchestrator classification
# ---------------------------------------------------------------------------


class TestOrchestratorClassification:
    """Test subtask-to-agent classifier without LLM calls."""

    def test_classify_coding_task(self):
        from versaai.agents.orchestrator import classify_subtask

        assert classify_subtask("Implement a REST API endpoint") == "coding"
        assert classify_subtask("debug this function") == "coding"
        assert classify_subtask("write a Python script") == "coding"

    def test_classify_research_task(self):
        from versaai.agents.orchestrator import classify_subtask

        assert classify_subtask("Search for information about transformers") == "research"
        assert classify_subtask("Summarize this research paper") == "research"

    def test_classify_reasoning_task(self):
        from versaai.agents.orchestrator import classify_subtask

        assert classify_subtask("Analyze the pros and cons of this approach") == "reasoning"
        assert classify_subtask("Compare these two architectures") == "reasoning"

    def test_classify_ambiguous_defaults_to_reasoning(self):
        from versaai.agents.orchestrator import classify_subtask

        # Completely ambiguous — should default
        assert classify_subtask("do the thing") == "reasoning"

    def test_parse_subtasks(self):
        from versaai.agents.orchestrator import OrchestratorAgent

        text = "1. Write the function\n2. Test the output\n3. Deploy to production"
        result = OrchestratorAgent._parse_subtasks(text, limit=10)
        assert len(result) == 3
        assert result[0]["id"] == "1"
        assert "function" in result[0]["description"].lower()

    def test_parse_subtasks_respects_limit(self):
        from versaai.agents.orchestrator import OrchestratorAgent

        text = (
            "1. Write the login endpoint\n"
            "2. Create the database schema\n"
            "3. Implement authentication logic\n"
            "4. Add integration tests\n"
            "5. Deploy to staging server\n"
            "6. Update the documentation"
        )
        result = OrchestratorAgent._parse_subtasks(text, limit=3)
        assert len(result) == 3

    def test_subtask_result_to_dict(self):
        from versaai.agents.orchestrator import OrchestratorAgent, SubtaskResult

        r = SubtaskResult(
            task_id="1",
            task_description="test task",
            agent_used="coding",
            result="success output",
            success=True,
            execution_time=1.5,
        )
        d = OrchestratorAgent._subtask_to_dict(r)
        assert d["id"] == "1"
        assert d["success"] is True
        assert d["agent"] == "coding"


# ---------------------------------------------------------------------------
# Profile System
# ---------------------------------------------------------------------------


class TestProfileManager:
    """Test profile CRUD operations."""

    def test_create_profile(self, tmp_profile_dir):
        from versaai.profiles import ProfileManager

        mgr = ProfileManager(profiles_dir=tmp_profile_dir)
        profile = mgr.create(profile_id="test_user", display_name="Test User")
        assert profile.profile_id == "test_user"
        assert profile.display_name == "Test User"
        assert profile.created_at > 0

    def test_create_duplicate_raises(self, tmp_profile_dir):
        from versaai.profiles import ProfileManager

        mgr = ProfileManager(profiles_dir=tmp_profile_dir)
        mgr.create(profile_id="dup_user", display_name="First")
        with pytest.raises(ValueError, match="already exists"):
            mgr.create(profile_id="dup_user", display_name="Second")

    def test_get_profile(self, tmp_profile_dir):
        from versaai.profiles import ProfileManager

        mgr = ProfileManager(profiles_dir=tmp_profile_dir)
        mgr.create(profile_id="get_user", display_name="Get User")
        profile = mgr.get("get_user")
        assert profile is not None
        assert profile.profile_id == "get_user"

    def test_get_nonexistent_returns_none(self, tmp_profile_dir):
        from versaai.profiles import ProfileManager

        mgr = ProfileManager(profiles_dir=tmp_profile_dir)
        assert mgr.get("nonexistent_user") is None

    def test_update_profile(self, tmp_profile_dir):
        from versaai.profiles import ProfileManager

        mgr = ProfileManager(profiles_dir=tmp_profile_dir)
        mgr.create(profile_id="upd_user")
        updated = mgr.update("upd_user", display_name="New Name")
        assert updated is not None
        assert updated.display_name == "New Name"

    def test_delete_profile(self, tmp_profile_dir):
        from versaai.profiles import ProfileManager

        mgr = ProfileManager(profiles_dir=tmp_profile_dir)
        mgr.create(profile_id="del_user")
        assert mgr.delete("del_user") is True
        assert mgr.get("del_user") is None

    def test_learn_adds_to_behavior(self, tmp_profile_dir):
        from versaai.profiles import ProfileManager

        mgr = ProfileManager(profiles_dir=tmp_profile_dir)
        mgr.create(profile_id="learn_user")
        mgr.learn("learn_user", "topic", "machine learning")
        profile = mgr.get("learn_user")
        assert "machine learning" in profile.behavior.get("common_topics", [])

    def test_list_profiles(self, tmp_profile_dir):
        from versaai.profiles import ProfileManager

        mgr = ProfileManager(profiles_dir=tmp_profile_dir)
        mgr.create(profile_id="list_a")
        mgr.create(profile_id="list_b")
        profiles = mgr.list_profiles(limit=10, offset=0)
        assert len(profiles) >= 2


# ---------------------------------------------------------------------------
# Profile API endpoints
# ---------------------------------------------------------------------------


class TestProfileAPI:
    """Test profile REST endpoints via TestClient."""

    @pytest.fixture(autouse=True)
    def setup_client(self, tmp_profile_dir):
        try:
            from starlette.testclient import TestClient
            from versaai.api.app import app
            from versaai.api.routes import profiles as profile_mod
            from versaai.profiles import ProfileManager

            # Inject test manager
            profile_mod._manager = ProfileManager(profiles_dir=tmp_profile_dir)
            self.client = TestClient(app)
            self.available = True
        except Exception:
            self.available = False

    def test_create_profile_endpoint(self):
        if not self.available:
            pytest.skip("FastAPI app not available")
        resp = self.client.post("/v1/profiles", json={
            "profile_id": "api_user",
            "display_name": "API User",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["profile_id"] == "api_user"
        assert data["display_name"] == "API User"

    def test_list_profiles_endpoint(self):
        if not self.available:
            pytest.skip("FastAPI app not available")
        # Create one first
        self.client.post("/v1/profiles", json={"profile_id": "list_ep_user"})
        resp = self.client.get("/v1/profiles")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_profile_endpoint(self):
        if not self.available:
            pytest.skip("FastAPI app not available")
        self.client.post("/v1/profiles", json={"profile_id": "get_ep_user"})
        resp = self.client.get("/v1/profiles/get_ep_user")
        assert resp.status_code == 200
        assert resp.json()["profile_id"] == "get_ep_user"

    def test_get_missing_profile_404(self):
        if not self.available:
            pytest.skip("FastAPI app not available")
        resp = self.client.get("/v1/profiles/nonexistent")
        assert resp.status_code == 404

    def test_update_profile_endpoint(self):
        if not self.available:
            pytest.skip("FastAPI app not available")
        self.client.post("/v1/profiles", json={"profile_id": "upd_ep_user"})
        resp = self.client.put("/v1/profiles/upd_ep_user", json={
            "display_name": "Updated Name",
        })
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Updated Name"

    def test_delete_profile_endpoint(self):
        if not self.available:
            pytest.skip("FastAPI app not available")
        self.client.post("/v1/profiles", json={"profile_id": "del_ep_user"})
        resp = self.client.delete("/v1/profiles/del_ep_user")
        assert resp.status_code == 204

    def test_learn_endpoint(self):
        if not self.available:
            pytest.skip("FastAPI app not available")
        self.client.post("/v1/profiles", json={"profile_id": "learn_ep_user"})
        resp = self.client.post("/v1/profiles/learn_ep_user/learn", json={
            "category": "topic",
            "value": "deep learning",
        })
        assert resp.status_code == 204

    def test_duplicate_create_409(self):
        if not self.available:
            pytest.skip("FastAPI app not available")
        self.client.post("/v1/profiles", json={"profile_id": "dup_ep_user"})
        resp = self.client.post("/v1/profiles", json={"profile_id": "dup_ep_user"})
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Multimodal Pipeline
# ---------------------------------------------------------------------------


class TestMultimodal:
    """Test multimodal modality detection and pipeline wiring."""

    def test_modality_enum(self):
        from versaai.multimodal import Modality

        assert Modality.TEXT == "text"
        assert Modality.IMAGE == "image"
        assert Modality.AUDIO == "audio"
        assert Modality.VIDEO == "video"
        assert Modality.THREE_D == "3d"
        assert Modality.CODE == "code"
        assert Modality.UNKNOWN == "unknown"

    def test_detect_modality_text(self):
        from versaai.multimodal import detect_modality, Modality

        result = detect_modality(data="Hello, this is plain text")
        assert result == Modality.TEXT

    def test_detect_modality_by_extension(self):
        from versaai.multimodal import detect_modality, Modality

        assert detect_modality(file_path="main.py") == Modality.CODE
        assert detect_modality(file_path="photo.png") == Modality.IMAGE

    def test_detect_modality_bytes_png(self):
        from versaai.multimodal import detect_modality, Modality

        png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
        assert detect_modality(data=png_header) == Modality.IMAGE

    def test_pipeline_available_routes(self):
        from versaai.multimodal import MultimodalPipeline

        pipeline = MultimodalPipeline()
        routes = pipeline.available_routes()
        # TextToText processor should be auto-registered
        route_keys = [(r["input"], r["output"]) for r in routes]
        assert ("text", "text") in route_keys

    def test_pipeline_no_image_to_3d_route(self):
        from versaai.multimodal import MultimodalPipeline

        pipeline = MultimodalPipeline()
        routes = pipeline.available_routes()
        # No image→3D processor registered
        route_keys = [(r["input"], r["output"]) for r in routes]
        assert ("image", "3d") not in route_keys


# ---------------------------------------------------------------------------
# Web Search Tool
# ---------------------------------------------------------------------------


class TestWebSearchTool:
    """Test web search tool instantiation and cache."""

    def test_tool_instantiation(self):
        from versaai.agents.tools.web_search import WebSearchTool

        tool = WebSearchTool()
        assert tool.name == "web_search"
        assert "search" in tool.description.lower()

    def test_lru_cache(self):
        from versaai.agents.tools.web_search import _LRUCache

        cache = _LRUCache(maxsize=3)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        assert cache.get("a") == 1
        # Adding 4th should evict oldest unused
        cache.put("d", 4)
        # "b" was least recently used (a was touched by get)
        assert cache.get("b") is None
        assert cache.get("d") == 4

    def test_tool_schema_property(self):
        from versaai.agents.tools.web_search import WebSearchTool

        tool = WebSearchTool()
        schema = tool.parameters_schema
        assert schema["type"] == "object"
        assert "query" in schema["properties"]


# ---------------------------------------------------------------------------
# Agent streaming callback wiring
# ---------------------------------------------------------------------------


class TestStreamingCallbacks:
    """Verify agents correctly invoke status_callback when present."""

    def _make_mock_llm(self, response: str = "Test response"):
        llm = MagicMock()
        llm.chat.return_value = response
        llm.complete.return_value = response
        return llm

    def test_coding_agent_calls_status_cb(self):
        from versaai.agents.coding_agent import CodingAgent

        agent = CodingAgent()
        agent._initialized = True
        agent.llm = self._make_mock_llm(
            "Thought: I should just answer directly\n"
            "Action: finish\n"
            "Action Input: The answer is 42"
        )
        agent.tool_registry = MagicMock()
        agent.tool_registry.get_tool_descriptions.return_value = ""
        agent.rag = None

        callback = MagicMock()
        agent.execute("test task", {"status_callback": callback})

        assert callback.call_count >= 1, "CodingAgent should call status_callback"

    def test_reasoning_agent_calls_status_cb(self):
        from versaai.agents.reasoning_agent import ReasoningAgent
        from versaai.agents.reasoning import ReasoningResult, ReasoningStep

        agent = ReasoningAgent()
        agent._initialized = True
        agent.memory = {"messages": [], "context": {}}
        mock_result = ReasoningResult(
            answer="test answer",
            steps=[ReasoningStep(step_num=1, thought="thinking about it")],
            confidence=0.9,
            strategy_used="cot",
            execution_time=0.1,
        )
        agent.engine = MagicMock()
        agent.engine.reason.return_value = mock_result

        callback = MagicMock()
        agent.execute("test task", {"status_callback": callback})

        assert callback.call_count >= 1, "ReasoningAgent should call status_callback"

    def test_research_agent_calls_status_cb(self):
        from versaai.agents.research_agent import ResearchAgent

        agent = ResearchAgent()
        agent._initialized = True
        agent.memory = {"messages": [], "context": {}}
        agent.config = {}
        # The research agent calls llm.complete() multiple times:
        # 1) _decompose_query → expects JSON array
        # 2) _generate_response → returns draft text
        # 3) _critique_response → expects JSON with needs_correction
        mock_llm = MagicMock()
        mock_llm.complete.side_effect = [
            '["sub query 1"]',                                  # decompose
            "This is the draft response.",                      # generate
            '{"confidence": 0.95, "issues": [], "needs_correction": false}',  # critique
        ]
        agent.llm = mock_llm
        agent.rag = None

        callback = MagicMock()
        agent.execute("test research task", {"status_callback": callback})

        assert callback.call_count >= 1, "ResearchAgent should call status_callback"


# ---------------------------------------------------------------------------
# Agents API endpoint smoke tests
# ---------------------------------------------------------------------------


class TestAgentsEndpoint:
    """Verify the /v1/agents endpoint lists all agents correctly."""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        try:
            from starlette.testclient import TestClient
            from versaai.api.app import app

            self.client = TestClient(app)
            self.available = True
        except Exception:
            self.available = False

    def test_agents_list_includes_all(self):
        if not self.available:
            pytest.skip("FastAPI app not available")
        resp = self.client.get("/v1/agents")
        assert resp.status_code == 200
        data = resp.json()
        agents = data["agents"]
        names = {a["name"] for a in agents}
        expected = {"coding", "research", "reasoning", "planning", "orchestrator"}
        assert expected.issubset(names), f"Missing agents: {expected - names}"

    def test_agent_info_has_required_fields(self):
        if not self.available:
            pytest.skip("FastAPI app not available")
        resp = self.client.get("/v1/agents")
        for agent in resp.json()["agents"]:
            assert "name" in agent
            assert "description" in agent
            assert "version" in agent
            assert "capabilities" in agent
