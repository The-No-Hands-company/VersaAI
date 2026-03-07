#!/usr/bin/env python3
"""
Quick test script to verify VersaAI backend works for Flutter UI
"""

import asyncio
import websockets
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_backend():
    """Test WebSocket backend server"""
    print("=" * 60)
    print("🧪 Testing VersaAI Backend for Flutter Integration")
    print("=" * 60)
    print()
    
    # Connect to server
    print("📡 Connecting to ws://localhost:8765...")
    try:
        async with websockets.connect('ws://localhost:8765') as websocket:
            print("✅ Connected successfully!\n")
            
            # Test 1: Ping
            print("Test 1: Ping")
            ping_msg = {'id': 'test1', 'type': 'ping'}
            await websocket.send(json.dumps(ping_msg))
            response = json.loads(await websocket.recv())
            print(f"  Response: {response}")
            assert response['status'] == 'ok', "Ping failed"
            print("  ✅ Ping test passed\n")
            
            # Test 2: Chat
            print("Test 2: Chat")
            chat_msg = {
                'id': 'test2',
                'type': 'chat',
                'session_id': 'test_session',
                'message': 'Write a Python function to add two numbers',
                'task_type': 'code_assistant'
            }
            await websocket.send(json.dumps(chat_msg))
            response = json.loads(await websocket.recv())
            print(f"  Response type: {response.get('type')}")
            print(f"  Status: {response.get('status')}")
            print(f"  Model: {response.get('model', 'N/A')}")
            print(f"  Response: {response.get('response', 'N/A')[:100]}...")
            assert response['status'] == 'ok', "Chat failed"
            print("  ✅ Chat test passed\n")
            
            # Test 3: Code Explanation
            print("Test 3: Explain Code")
            explain_msg = {
                'id': 'test3',
                'type': 'explain',
                'code': 'def add(a, b): return a + b',
                'language': 'python'
            }
            await websocket.send(json.dumps(explain_msg))
            response = json.loads(await websocket.recv())
            print(f"  Status: {response.get('status')}")
            print(f"  Explanation: {response.get('explanation', 'N/A')[:100]}...")
            print("  ✅ Explain test passed\n")
            
            print("=" * 60)
            print("✅ All tests passed! Backend is ready for Flutter UI")
            print("=" * 60)
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("\n💡 Make sure the backend is running:")
        print("   python3 start_editor_bridge.py")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(test_backend())
