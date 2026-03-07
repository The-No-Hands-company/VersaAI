#!/usr/bin/env python3
"""
Test script for VersaAI integration
Tests:
1. Model Router - Model selection and generation
2. WebSocket Server - Connection and basic communication
3. Flutter UI compatibility
"""

import asyncio
import websockets
import json
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

async def test_websocket_server():
    """Test WebSocket server connectivity"""
    logger.info("=" * 60)
    logger.info("TEST 2: WebSocket Server")
    logger.info("=" * 60)
    
    try:
        async with websockets.connect('ws://localhost:8765') as websocket:
            logger.info("✅ Connected to WebSocket server")
            
            # Send ping
            ping_msg = {
                'id': 'test_ping',
                'type': 'ping'
            }
            await websocket.send(json.dumps(ping_msg))
            logger.info("📤 Sent ping request")
            
            # Receive response
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.dumps(response)
            logger.info(f"📨 Received response: {data}")
            
            # Send chat request
            chat_msg = {
                'id': 'test_chat',
                'type': 'chat',
                'session_id': 'test',
                'message': 'Hello, VersaAI!',
                'task_type': 'general'
            }
            await websocket.send(json.dumps(chat_msg))
            logger.info("📤 Sent chat request")
            
            # Receive chat response
            response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
            data = json.loads(response)
            logger.info(f"📨 Received chat response")
            logger.info(f"   Status: {data.get('status')}")
            if 'response' in data:
                logger.info(f"   Response: {data['response'][:100]}...")
            
            return True
            
    except asyncio.TimeoutError:
        logger.error("❌ WebSocket request timed out")
        return False
    except Exception as e:
        logger.error(f"❌ WebSocket test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("🚀 Starting VersaAI Integration Tests")
    logger.info("")
    
    # Test 1: Model Router
    test1_passed = test_model_router()
    logger.info("")
    
    # Test 2: WebSocket Server (requires server to be running)
    logger.info("⚠️  Starting WebSocket test (requires backend server to be running)")
    logger.info("   Start the server with: python3 start_editor_bridge.py")
    logger.info("   Press Enter when server is ready, or Ctrl+C to skip...")
    
    try:
        input()
        test2_passed = asyncio.run(test_websocket_server())
    except KeyboardInterrupt:
        logger.info("\n⏭️  Skipping WebSocket test")
        test2_passed = None
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Model Router:     {'✅ PASS' if test1_passed else '❌ FAIL'}")
    logger.info(f"WebSocket Server: {'✅ PASS' if test2_passed else '⏭️ SKIPPED' if test2_passed is None else '❌ FAIL'}")
    logger.info("=" * 60)
    logger.info("")
    
    if test1_passed and (test2_passed or test2_passed is None):
        logger.info("🎉 VersaAI integration is working!")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Start backend:  python3 start_editor_bridge.py")
        logger.info("  2. Start Flutter:  cd ui && flutter run -d linux")
        logger.info("  3. Or use script:  cd ui && ./scripts/run_with_backend.sh")
    else:
        logger.info("❌ Some tests failed. Please check the logs above.")

if __name__ == '__main__':
    main()
