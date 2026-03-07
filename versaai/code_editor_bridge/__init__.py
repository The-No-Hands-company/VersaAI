"""
VersaAI Code Editor Bridge

Provides WebSocket/HTTP server for real-time AI-powered code assistance
in external code editors (NLPL Editor, VS Code, etc.)
"""

from .server import VersaAIEditorServer
from .completion_service import CodeCompletionService
from .chat_service import EditorChatService

__all__ = [
    'VersaAIEditorServer',
    'CodeCompletionService',
    'EditorChatService',
]
