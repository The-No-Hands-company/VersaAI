"""
Code Completion Service

Provides intelligent code completion using VersaAI's model router
"""

import asyncio
from typing import Dict, List, Optional, Any
import time
from pathlib import Path


class CompletionCache:
    """Simple in-memory cache for completions"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 300):
        self.cache: Dict[str, tuple[List[str], float]] = {}
        self.max_size = max_size
        self.ttl = ttl
    
    def get(self, key: str) -> Optional[List[str]]:
        if key in self.cache:
            completions, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return completions
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, completions: List[str]):
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            oldest = min(self.cache.items(), key=lambda x: x[1][1])
            del self.cache[oldest[0]]
        
        self.cache[key] = (completions, time.time())


class CodeCompletionService:
    """
    Handles code completion requests from code editors
    
    Uses VersaAI's model router to select the best model for code completion
    based on language, task complexity, and available models.
    """
    
    def __init__(self, model_router=None):
        """
        Initialize completion service
        
        Args:
            model_router: VersaAI ModelRouter instance (optional)
        """
        self.router = model_router
        self.cache = CompletionCache()
        
        # Language-specific settings
        self.language_settings = {
            'python': {'max_tokens': 128, 'temperature': 0.2},
            'javascript': {'max_tokens': 128, 'temperature': 0.2},
            'typescript': {'max_tokens': 128, 'temperature': 0.2},
            'cpp': {'max_tokens': 128, 'temperature': 0.2},
            'c': {'max_tokens': 128, 'temperature': 0.2},
            'java': {'max_tokens': 128, 'temperature': 0.2},
            'nlpl': {'max_tokens': 128, 'temperature': 0.2},
            'default': {'max_tokens': 128, 'temperature': 0.3}
        }
    
    def _build_completion_prompt(self, context: Dict[str, Any]) -> str:
        """
        Build completion prompt from context
        
        Args:
            context: Dictionary containing:
                - file_path: Path to the file
                - language: Programming language
                - prefix: Code before cursor
                - suffix: Code after cursor
                - line: Current line number
                - column: Current column number
        
        Returns:
            Formatted prompt for the model
        """
        file_path = context.get('file_path', '')
        language = context.get('language', 'text')
        prefix = context.get('prefix', '')
        suffix = context.get('suffix', '')
        
        # For FIM (Fill-In-Middle) models like DeepSeek/StarCoder
        prompt = f"<|fim_prefix|>{prefix}<|fim_suffix|>{suffix}<|fim_middle|>"
        
        return prompt
    
    def _parse_completion(self, raw_completion: str, context: Dict[str, Any]) -> List[str]:
        """
        Parse and clean completion from model output
        
        Args:
            raw_completion: Raw completion from model
            context: Original context
        
        Returns:
            List of completion suggestions
        """
        # Remove FIM tokens if present
        completion = raw_completion.replace('<|fim_middle|>', '')
        completion = completion.replace('<|fim_suffix|>', '')
        completion = completion.replace('<|fim_prefix|>', '')
        completion = completion.replace('<|endoftext|>', '')
        
        # Split into lines and take first few
        lines = completion.strip().split('\n')
        
        # For now, return single completion
        # TODO: Generate multiple alternatives
        suggestions = [completion.strip()]
        
        return suggestions
    
    async def get_completion(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get code completion based on context
        
        Args:
            context: Completion context dictionary
        
        Returns:
            Dictionary with completions and metadata
        """
        # Generate cache key
        cache_key = f"{context.get('file_path', '')}:{context.get('line', 0)}:{context.get('prefix', '')[-100:]}"
        
        # Check cache
        cached = self.cache.get(cache_key)
        if cached:
            return {
                'completions': cached,
                'cached': True,
                'model': 'cache'
            }
        
        # Build prompt
        prompt = self._build_completion_prompt(context)
        
        # Get language settings
        language = context.get('language', 'default')
        settings = self.language_settings.get(language, self.language_settings['default'])
        
        # Get completion from model router
        if self.router:
            try:
                # Route to best code model
                response = await asyncio.to_thread(
                    self.router.route,
                    prompt=prompt,
                    task_type='code_completion',
                    language=language,
                    **settings
                )
                
                raw_completion = response.get('response', '')
                model_used = response.get('model', 'unknown')
            except Exception as e:
                import traceback
                print(f"Model router error: {e}")
                traceback.print_exc()
                raw_completion = ""
                model_used = "error"
        else:
            # Fallback: Simple completion
            raw_completion = self._fallback_completion(context)
            model_used = "fallback"
        
        # Parse completion
        completions = self._parse_completion(raw_completion, context)
        
        # Cache result
        self.cache.set(cache_key, completions)
        
        return {
            'completions': completions,
            'cached': False,
            'model': model_used
        }
    
    def _fallback_completion(self, context: Dict[str, Any]) -> str:
        """
        Fallback completion when no model is available
        
        Returns basic context-aware suggestions
        """
        prefix = context.get('prefix', '')
        
        # Simple heuristic-based completion
        if prefix.strip().endswith('def '):
            return 'function_name():\n    pass'
        elif prefix.strip().endswith('class '):
            return 'ClassName:\n    pass'
        elif prefix.strip().endswith('if '):
            return 'condition:\n    pass'
        elif prefix.strip().endswith('for '):
            return 'item in items:\n    pass'
        else:
            return ''
    
    async def get_inline_suggestions(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get inline suggestions (ghost text) for the current cursor position
        
        Similar to GitHub Copilot's inline suggestions
        """
        return await self.get_completion(context)
