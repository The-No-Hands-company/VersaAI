"""
VersaAI Editor Bridge Server

WebSocket server for real-time communication with code editors
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

try:
    import websockets
    from websockets.server import serve, WebSocketServerProtocol
except ImportError:
    websockets = None
    print("Warning: websockets not installed. Run: pip install websockets")

from .completion_service import CodeCompletionService
from .chat_service import EditorChatService


logger = logging.getLogger(__name__)


class VersaAIEditorServer:
    """
    WebSocket server for VersaAI code editor integration
    
    Provides real-time code completion, chat, and code analysis
    for external code editors.
    """
    
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 8765,
        model_router=None,
        rag_system=None
    ):
        """
        Initialize editor server
        
        Args:
            host: Server host (default: localhost)
            port: Server port (default: 8765)
            model_router: VersaAI ModelRouter instance
            rag_system: RAG system for codebase search
        """
        if websockets is None:
            raise ImportError("websockets library required. Install with: pip install websockets")
        
        self.host = host
        self.port = port
        self.model_router = model_router
        self.rag_system = rag_system
        
        # Initialize services
        self.completion_service = CodeCompletionService(model_router)
        self.chat_service = EditorChatService(model_router, rag_system)
        
        # Track connected clients
        self.clients: set = set()
        
        logger.info(f"VersaAI Editor Server initialized on {host}:{port}")
    
    async def handle_message(self, websocket: 'WebSocketServerProtocol', path: str):
        """
        Handle incoming WebSocket messages
        
        Args:
            websocket: WebSocket connection
            path: Request path
        """
        # Register client
        self.clients.add(websocket)
        client_id = id(websocket)
        logger.info(f"Client {client_id} connected from {websocket.remote_address}")
        
        try:
            async for message in websocket:
                try:
                    # Parse message
                    data = json.loads(message)
                    msg_type = data.get('type')
                    msg_id = data.get('id', 'unknown')
                    
                    logger.debug(f"Received message type={msg_type} id={msg_id}")
                    
                    # Route to appropriate handler
                    if msg_type == 'completion':
                        result = await self._handle_completion(data)
                    elif msg_type == 'chat':
                        result = await self._handle_chat(data)
                    elif msg_type == 'explain':
                        result = await self._handle_explain(data)
                    elif msg_type == 'refactor':
                        result = await self._handle_refactor(data)
                    elif msg_type == 'debug':
                        result = await self._handle_debug(data)
                    elif msg_type == 'test':
                        result = await self._handle_test(data)
                    elif msg_type == 'index_project':
                        result = await self._handle_index_project(data)
                    elif msg_type == 'ping':
                        result = {'status': 'ok', 'message': 'pong'}
                    else:
                        result = {
                            'status': 'error',
                            'message': f'Unknown message type: {msg_type}'
                        }
                    
                    # Add message ID to response
                    result['id'] = msg_id
                    
                    # Send response
                    await websocket.send(json.dumps(result))
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                    await websocket.send(json.dumps({
                        'status': 'error',
                        'message': 'Invalid JSON format'
                    }))
                except Exception as e:
                    logger.error(f"Error handling message: {e}", exc_info=True)
                    await websocket.send(json.dumps({
                        'status': 'error',
                        'message': str(e)
                    }))
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} disconnected")
        finally:
            # Unregister client
            self.clients.discard(websocket)
    
    async def _handle_completion(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle code completion request"""
        context = data.get('context', {})
        
        result = await self.completion_service.get_completion(context)
        
        return {
            'status': 'ok',
            'type': 'completion',
            **result
        }
    
    async def _handle_chat(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle chat request"""
        session_id = data.get('session_id', 'default')
        message = data.get('message', '')
        file_context = data.get('file_context')
        task_type = data.get('task_type', 'general')
        
        result = await self.chat_service.chat(
            session_id=session_id,
            message=message,
            file_context=file_context,
            task_type=task_type
        )
        
        return {
            'status': 'ok',
            'type': 'chat',
            **result
        }
    
    async def _handle_explain(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle code explanation request"""
        session_id = data.get('session_id', 'default')
        code = data.get('code', '')
        language = data.get('language', 'text')
        file_path = data.get('file_path')
        
        result = await self.chat_service.explain_code(
            session_id=session_id,
            code=code,
            language=language,
            file_path=file_path
        )
        
        return {
            'status': 'ok',
            'type': 'explain',
            **result
        }
    
    async def _handle_refactor(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle code refactoring request"""
        session_id = data.get('session_id', 'default')
        code = data.get('code', '')
        language = data.get('language', 'text')
        file_path = data.get('file_path')
        
        result = await self.chat_service.refactor_code(
            session_id=session_id,
            code=code,
            language=language,
            file_path=file_path
        )
        
        return {
            'status': 'ok',
            'type': 'refactor',
            **result
        }
    
    async def _handle_debug(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle debugging request"""
        session_id = data.get('session_id', 'default')
        code = data.get('code', '')
        language = data.get('language', 'text')
        error_message = data.get('error_message')
        file_path = data.get('file_path')
        
        result = await self.chat_service.debug_code(
            session_id=session_id,
            code=code,
            language=language,
            error_message=error_message,
            file_path=file_path
        )
        
        return {
            'status': 'ok',
            'type': 'debug',
            **result
        }
    
    async def _handle_test(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle test generation request"""
        session_id = data.get('session_id', 'default')
        code = data.get('code', '')
        language = data.get('language', 'text')
        file_path = data.get('file_path')
        
        result = await self.chat_service.generate_tests(
            session_id=session_id,
            code=code,
            language=language,
            file_path=file_path
        )
        
        return {
            'status': 'ok',
            'type': 'test',
            **result
        }
    
    async def _handle_index_project(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle project indexing request"""
        project_path = data.get('project_path', '')
        
        if not self.rag_system:
            return {
                'status': 'error',
                'message': 'RAG system not available'
            }
        
        try:
            # Index project in background
            # This would integrate with the RAG system
            # For now, return success
            
            return {
                'status': 'ok',
                'type': 'index_project',
                'message': f'Indexing project: {project_path}',
                'project_path': project_path
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Indexing failed: {str(e)}'
            }
    
    async def start(self):
        """Start the WebSocket server"""
        logger.info(f"Starting VersaAI Editor Bridge on ws://{self.host}:{self.port}")
        
        async with serve(self.handle_message, self.host, self.port):
            logger.info(f"✅ VersaAI Editor Bridge running on ws://{self.host}:{self.port}")
            print(f"\n{'='*60}")
            print(f"🚀 VersaAI Editor Bridge Server")
            print(f"{'='*60}")
            print(f"WebSocket: ws://{self.host}:{self.port}")
            print(f"Status: Ready for connections")
            print(f"\nAvailable features:")
            print(f"  - Code completion")
            print(f"  - AI chat assistant")
            print(f"  - Code explanation")
            print(f"  - Refactoring suggestions")
            print(f"  - Debugging assistance")
            print(f"  - Test generation")
            print(f"\nPress Ctrl+C to stop")
            print(f"{'='*60}\n")
            
            # Run forever
            await asyncio.Future()
    
    def run(self):
        """Run the server (blocking)"""
        try:
            asyncio.run(self.start())
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
            print("\n\n✅ VersaAI Editor Bridge stopped")


def main():
    """CLI entry point for running the server"""
    import argparse
    
    parser = argparse.ArgumentParser(description='VersaAI Code Editor Bridge Server')
    parser.add_argument('--host', default='localhost', help='Server host')
    parser.add_argument('--port', type=int, default=8765, help='Server port')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Try to initialize VersaAI components
    try:
        from versaai.models.model_router import ModelRouter
        # Initialize with only available models
        model_router = ModelRouter(
            available_models=['deepseek', 'codellama', 'starcoder2'],
            available_ram_gb=16
        )
        logger.info("✅ Model Router initialized")
    except Exception as e:
        logger.warning(f"Could not initialize Model Router: {e}")
        model_router = None
    
    try:
        from versaai.rag import RAGPipeline, RAGConfig
        rag_config = RAGConfig()
        rag_system = RAGPipeline(rag_config)
        logger.info("✅ RAG System initialized")
    except Exception as e:
        logger.warning(f"Could not initialize RAG System: {e}")
        rag_system = None
    
    # Create and run server
    server = VersaAIEditorServer(
        host=args.host,
        port=args.port,
        model_router=model_router,
        rag_system=rag_system
    )
    
    server.run()


if __name__ == '__main__':
    main()
