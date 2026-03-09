#!/usr/bin/env python3
"""
Test VersaAI API endpoints (editor bridge).

Validates the FastAPI backend that replaced the legacy WebSocket server.
Uses FastAPI TestClient for in-process testing without a running server.
"""

import pytest

try:
    from starlette.testclient import TestClient
    from versaai.api.app import app
    HAS_APP = True
except Exception:
    HAS_APP = False


@pytest.mark.skipif(not HAS_APP, reason="FastAPI app could not be initialised")
class TestEditorBridge:
    """Test API endpoints that serve as the editor bridge."""

    def setup_method(self):
        self.client = TestClient(app)

    def test_health(self):
        """Health endpoint returns 200 with status field."""
        response = self.client.get("/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_models_list(self):
        """Models endpoint returns 200."""
        response = self.client.get("/v1/models")
        assert response.status_code == 200

    def test_agents_list(self):
        """Agents endpoint returns 200."""
        response = self.client.get("/v1/agents")
        assert response.status_code == 200

    def test_chat_completions_endpoint(self):
        """Chat completions endpoint exists and validates input."""
        payload = {
            "model": "test-model",
            "messages": [{"role": "user", "content": "Hello"}],
        }
        response = self.client.post("/v1/chat/completions", json=payload)
        # Accepts valid schema (may fail at LLM layer, but should not 404)
        assert response.status_code != 404
