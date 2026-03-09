#!/usr/bin/env python3
"""
Test script for VersaAI integration
Tests:
1. Model Router - Model selection and generation
2. API Server - Health and basic endpoints
"""

import logging
from versaai.models.model_router import ModelRouter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_model_router():
    """Test Model Router functionality"""
    logger.info("=" * 60)
    logger.info("TEST 1: Model Router")
    logger.info("=" * 60)

    router = ModelRouter()

    # Test model selection
    model_id, model_spec = router.select_model(
        task="Write a Python function to calculate fibonacci",
        language="python",
        prefer_quality=True
    )
    logger.info(f"✅ Selected model: {model_spec.name} (ID: {model_id})")

    # Test generation (will use placeholder for now)
    try:
        result = router.route(
            prompt="Write a Python function to calculate fibonacci numbers",
            task_type="code_generation",
            language="python",
            max_tokens=512
        )
        logger.info(f"✅ Generated response ({len(result['response'])} chars)")
        logger.info(f"   Model used: {result['model']}")
        logger.info(f"   Response preview: {result['response'][:100]}...")
        return True
    except Exception as e:
        logger.error(f"❌ Generation failed: {e}")
        return False


def test_api_health():
    """Test API health endpoint via TestClient."""
    try:
        from starlette.testclient import TestClient
        from versaai.api.app import app
    except Exception:
        logger.warning("FastAPI app could not be imported, skipping API test")
        return

    client = TestClient(app)
    response = client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    logger.info(f"✅ API health: {data['status']}")
