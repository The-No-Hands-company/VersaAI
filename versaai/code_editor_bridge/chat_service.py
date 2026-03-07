"""
Editor Chat Service

Provides conversational AI interface for code editors with file context awareness
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
from versaai.agents import ResearchAgent, CodingAgent


class ConversationSession:
    """Manages a single conversation session"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages: List[Dict[str, str]] = []
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.file_context: Optional[Dict[str, Any]] = None
    
    def add_message(self, role: str, content: str):
        """Add a message to the conversation"""
        self.messages.append({
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        })
        self.last_activity = datetime.now()
    
    def get_history(self, max_messages: int = 10) -> List[Dict[str, str]]:
        """Get recent conversation history"""
        return self.messages[-max_messages:]
    
    def set_file_context(self, file_context: Dict[str, Any]):
        """Update current file context"""
        self.file_context = file_context
        self.last_activity = datetime.now()


class EditorChatService:
    """
    Handles conversational AI interactions from code editors
    
    Features:
    - Multi-session support
    - File context awareness
    - RAG-enhanced responses
    - Code-specific prompting
    """
    
    def __init__(self, model_router=None, rag_system=None):
        """
        Initialize chat service
        
        Args:
            model_router: VersaAI ModelRouter instance
            rag_system: RAG system for codebase search
        """
        self.router = model_router
        self.rag = rag_system
        self.sessions: Dict[str, ConversationSession] = {}
        
        # Initialize Agents
        self.research_agent = ResearchAgent()
        self.coding_agent = CodingAgent()
        
        # Initialize agents with available configuration
        # In production, these should come from a proper config source
        try:
            self.research_agent.initialize({"enable_web_search": True}) # Mock/Stub
            self.coding_agent.initialize({})
        except Exception as e:
            print(f"Warning: Failed to auto-initialize agents: {e}")

        # System prompts for different tasks
        
        # System prompts for different tasks
        self.system_prompts = {
            'general': """You are VersaAI, an expert programming assistant integrated into a code editor.
You help developers write better code by providing explanations, suggestions, and solutions.
Be concise, accurate, and helpful. Always consider the context of the current file.""",
            
            'explain': """You are VersaAI, a code explanation expert.
Explain the given code clearly and concisely. Break down complex logic into understandable parts.
Focus on what the code does, how it works, and any important patterns or potential issues.""",
            
            'refactor': """You are VersaAI, a code refactoring expert.
Suggest improvements to make the code more readable, maintainable, and efficient.
Preserve functionality while improving code quality. Explain your suggestions.""",
            
            'debug': """You are VersaAI, a debugging expert.
Analyze the code for potential bugs, errors, and edge cases.
Suggest fixes and explain the root causes of issues.""",
            
            'test': """You are VersaAI, a test generation expert.
Generate comprehensive unit tests for the given code.
Cover edge cases, error conditions, and typical use cases."""
        }
    
    def _get_or_create_session(self, session_id: str) -> ConversationSession:
        """Get existing session or create new one"""
        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationSession(session_id)
        return self.sessions[session_id]
    
    def _build_context_prompt(
        self,
        message: str,
        file_context: Optional[Dict[str, Any]] = None,
        code_context: Optional[str] = None
    ) -> str:
        """
        Build prompt with file and code context
        
        Args:
            message: User message
            file_context: Current file information
            code_context: Retrieved code context from RAG
        
        Returns:
            Enhanced prompt with context
        """
        parts = []
        
        # Add file context
        if file_context:
            parts.append(f"Current file: {file_context.get('path', 'unknown')}")
            parts.append(f"Language: {file_context.get('language', 'unknown')}")
            
            if 'selected_code' in file_context:
                parts.append(f"\nSelected code:\n```{file_context['language']}\n{file_context['selected_code']}\n```")
        
        # Add retrieved context from codebase
        if code_context:
            parts.append(f"\nRelevant code from project:\n{code_context}")
        
        # Add user message
        parts.append(f"\nUser: {message}")
        
        return '\n'.join(parts)
    
    async def chat(
        self,
        session_id: str,
        message: str,
        file_context: Optional[Dict[str, Any]] = None,
        task_type: str = 'general'
    ) -> Dict[str, Any]:
        """
        Handle chat message with file context
        
        Args:
            session_id: Unique session identifier
            message: User message
            file_context: Current file information
            task_type: Type of task (general, explain, refactor, debug, test)
        
        Returns:
            Dictionary with response and metadata
        """
        # Get or create session
        session = self._get_or_create_session(session_id)
        
        # Update file context
        if file_context:
            session.set_file_context(file_context)
        
        # Retrieve relevant code context using RAG
        code_context = None
        if self.rag and file_context:
            try:
                # Search codebase for relevant context
                results = await asyncio.to_thread(
                    self.rag.search,
                    query=message,
                    max_results=3
                )
                
                # Format results
                if results:
                    code_context = '\n\n'.join([
                        f"From {r.get('file', 'unknown')}:\n{r.get('content', '')}"
                        for r in results
                    ])
            except Exception as e:
                print(f"RAG retrieval error: {e}")
        
        # Build enhanced prompt
        enhanced_prompt = self._build_context_prompt(
            message=message,
            file_context=file_context,
            code_context=code_context
        )
        
        # Add to session history
        session.add_message('user', message)
        
        # Route to best model or Agent for chat
        
        # Check specific agents first
        if task_type == 'research':
            # Use ResearchAgent
            result = self.research_agent.execute(message)
            assistant_response = result.get('result', '')
            model_used = 'ResearchAgent'
            
            # Append sources if available
            if result.get('sources'):
                sources_text = "\n\nSources:\n" + "\n".join([f"- {s.get('content','')} ({s.get('source','')})" for s in result['sources']])
                assistant_response += sources_text
                
        elif task_type in ['coding', 'debug', 'refactor', 'test']:
            # Use CodingAgent
            if not self.coding_agent.is_initialized():
                 # Should rely on initial init, but safeguard
                 pass

            agent_context = {
                'file_context': file_context,
                'code_context': code_context
            }
            
            result = self.coding_agent.execute(message, context=agent_context)
            assistant_response = result.get('result', '')
            model_used = 'CodingAgent'
            
        elif self.router:
            # Default to ModelRouter for general chat
            try:
                # Get system prompt
                system_prompt = self.system_prompts.get(task_type, self.system_prompts['general'])
                
                # Get conversation history
                history = session.get_history(max_messages=10)
                
                response = await asyncio.to_thread(
                    self.router.route,
                    prompt=enhanced_prompt,
                    system_prompt=system_prompt,
                    task_type='code_assistant',
                    conversation_history=history
                )
                
                assistant_response = response.get('response', 'I apologize, but I could not generate a response.')
                model_used = response.get('model', 'unknown')
            except Exception as e:
                import traceback
                print(f"Model router error: {e}")
                traceback.print_exc()
                assistant_response = f"Error: {str(e)}"
                model_used = "error"
        else:
            # Fallback response
            assistant_response = self._fallback_response(message, task_type)
            model_used = "fallback"
        
        # Add response to session history
        session.add_message('assistant', assistant_response)
        
        return {
            'response': assistant_response,
            'model': model_used,
            'session_id': session_id,
            'has_code_context': code_context is not None
        }
    
    def _fallback_response(self, message: str, task_type: str) -> str:
        """Fallback response when no model is available"""
        responses = {
            'general': "I'm VersaAI, your coding assistant. I'm currently running in fallback mode. Please connect a language model to enable full functionality.",
            'explain': "To explain code, I need access to a language model. Please configure VersaAI with a model.",
            'refactor': "Code refactoring requires a language model. Please set up VersaAI with a code model.",
            'debug': "Debugging assistance requires a language model. Please configure VersaAI.",
            'test': "Test generation requires a language model. Please set up VersaAI with a code model."
        }
        return responses.get(task_type, responses['general'])
    
    async def explain_code(
        self,
        session_id: str,
        code: str,
        language: str,
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Explain selected code
        
        Args:
            session_id: Session ID
            code: Code to explain
            language: Programming language
            file_path: Optional file path
        
        Returns:
            Explanation response
        """
        file_context = {
            'path': file_path or 'selection',
            'language': language,
            'selected_code': code
        }
        
        message = "Please explain what this code does."
        
        return await self.chat(
            session_id=session_id,
            message=message,
            file_context=file_context,
            task_type='explain'
        )
    
    async def refactor_code(
        self,
        session_id: str,
        code: str,
        language: str,
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Suggest refactoring for selected code"""
        file_context = {
            'path': file_path or 'selection',
            'language': language,
            'selected_code': code
        }
        
        message = "Please suggest refactoring improvements for this code."
        
        return await self.chat(
            session_id=session_id,
            message=message,
            file_context=file_context,
            task_type='refactor'
        )
    
    async def debug_code(
        self,
        session_id: str,
        code: str,
        language: str,
        error_message: Optional[str] = None,
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Help debug code"""
        file_context = {
            'path': file_path or 'selection',
            'language': language,
            'selected_code': code
        }
        
        message = "Please help me debug this code."
        if error_message:
            message += f"\n\nError message: {error_message}"
        
        return await self.chat(
            session_id=session_id,
            message=message,
            file_context=file_context,
            task_type='debug'
        )
    
    async def generate_tests(
        self,
        session_id: str,
        code: str,
        language: str,
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate unit tests for code"""
        file_context = {
            'path': file_path or 'selection',
            'language': language,
            'selected_code': code
        }
        
        message = "Please generate comprehensive unit tests for this code."
        
        return await self.chat(
            session_id=session_id,
            message=message,
            file_context=file_context,
            task_type='test'
        )
    
    def clear_session(self, session_id: str):
        """Clear a conversation session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a session"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            return {
                'session_id': session.session_id,
                'message_count': len(session.messages),
                'created_at': session.created_at.isoformat(),
                'last_activity': session.last_activity.isoformat(),
                'file_context': session.file_context
            }
        return None
