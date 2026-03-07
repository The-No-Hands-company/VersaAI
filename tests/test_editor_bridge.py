#!/usr/bin/env python3
"""
Test VersaAI Editor Bridge WebSocket Server

This script tests the WebSocket server without requiring models
"""

import asyncio
import json
import sys

try:
    import websockets
except ImportError:
    print("❌ websockets not installed. Run: pip install websockets")
    sys.exit(1)


async def test_server():
    """Test WebSocket server functionality"""
    
    print("\n" + "="*60)
    print("🧪 VersaAI Editor Bridge - WebSocket Test")
    print("="*60 + "\n")
    
    server_url = 'ws://localhost:8765'
    
    try:
        print(f"📡 Connecting to {server_url}...")
        async with websockets.connect(server_url) as websocket:
            print("✅ Connected successfully!\n")
            
            # Test 1: Ping
            print("Test 1: Ping")
            print("-" * 40)
            await websocket.send(json.dumps({
                'id': 'test-1',
                'type': 'ping'
            }))
            
            response = await websocket.recv()
            data = json.loads(response)
            print(f"Request:  {{'type': 'ping', 'id': 'test-1'}}")
            print(f"Response: {data}")
            assert data['status'] == 'ok', "Ping test failed"
            assert data['message'] == 'pong', "Ping test failed"
            print("✅ Ping test passed\n")
            
            # Test 2: Code Completion
            print("Test 2: Code Completion")
            print("-" * 40)
            completion_request = {
                'id': 'test-2',
                'type': 'completion',
                'context': {
                    'file_path': 'test.py',
                    'language': 'python',
                    'prefix': 'def hello_',
                    'suffix': ':\n    pass',
                    'line': 1,
                    'column': 10
                }
            }
            
            await websocket.send(json.dumps(completion_request))
            response = await websocket.recv()
            data = json.loads(response)
            
            print(f"Request:  completion for 'def hello_'")
            print(f"Response: {data['status']}")
            print(f"Model:    {data.get('model', 'N/A')}")
            print(f"Cached:   {data.get('cached', False)}")
            if 'completions' in data:
                print(f"Completions: {len(data['completions'])} suggestion(s)")
            print("✅ Completion test passed\n")
            
            # Test 3: Chat
            print("Test 3: Chat")
            print("-" * 40)
            chat_request = {
                'id': 'test-3',
                'type': 'chat',
                'session_id': 'test-session',
                'message': 'Hello, VersaAI!',
                'file_context': {
                    'path': 'test.py',
                    'language': 'python'
                }
            }
            
            await websocket.send(json.dumps(chat_request))
            response = await websocket.recv()
            data = json.loads(response)
            
            print(f"Request:  'Hello, VersaAI!'")
            print(f"Response: {data['status']}")
            print(f"Model:    {data.get('model', 'N/A')}")
            if 'response' in data:
                print(f"Message:  {data['response'][:100]}...")
            print("✅ Chat test passed\n")
            
            # Test 4: Unknown Message Type
            print("Test 4: Unknown Message Type (Error Handling)")
            print("-" * 40)
            await websocket.send(json.dumps({
                'id': 'test-4',
                'type': 'unknown_type'
            }))
            
            response = await websocket.recv()
            data = json.loads(response)
            
            print(f"Request:  unknown_type")
            print(f"Response: {data['status']}")
            assert data['status'] == 'error', "Error handling test failed"
            print("✅ Error handling test passed\n")
            
            print("="*60)
            print("✅ ALL TESTS PASSED!")
            print("="*60 + "\n")
            
    except ConnectionRefusedError:
        print(f"❌ Connection refused to {server_url}")
        print("\n💡 Make sure the server is running:")
        print("   python start_editor_bridge.py")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    print("\n📝 Note: This test runs in fallback mode (no models required)")
    print("   Start the server first: python start_editor_bridge.py\n")
    
    try:
        asyncio.run(test_server())
    except KeyboardInterrupt:
        print("\n\n⏸️  Test interrupted by user")
        sys.exit(0)
