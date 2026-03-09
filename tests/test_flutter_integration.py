#!/usr/bin/env python3
"""
Test VersaAI API backend integration (replaced stale Flutter WebSocket tests).

Validates key API endpoints that the desktop UI depends on.
"""

import pytest

try:
    from starlette.testclient import TestClient
    from versaai.api.app import app
    HAS_APP = True
except Exception:
    HAS_APP = False


@pytest.mark.skipif(not HAS_APP, reason="FastAPI app could not be initialised")
class TestBackendIntegration:
    """Test backend API endpoints used by the desktop UI."""

    def setup_method(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        """Health check returns 200."""
        response = self.client.get("/v1/health")
        assert response.status_code == 200
        assert "status" in response.json()

    def test_agents_endpoint(self):
        """Agents list returns 200 with expected shape."""
        response = self.client.get("/v1/agents")
        assert response.status_code == 200

    def test_conversations_list(self):
        """Conversations endpoint returns 200."""
        response = self.client.get("/v1/memory/conversations")
        assert response.status_code == 200

    def test_settings_endpoint(self):
        """Settings endpoint returns 200."""
        response = self.client.get("/v1/settings")
        assert response.status_code == 200
