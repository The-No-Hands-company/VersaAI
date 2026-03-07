"""
VersaAI Code Model - Specialized coding assistant with full VersaAI integration

Integrates:
- Short-term memory (conversation tracking)
- Long-term memory (code knowledge base)
- Reasoning engine (problem-solving)
- Planning system (task decomposition)
- RAG system (code search & retrieval)
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from versaai.models.model_base import ModelBase, ModelMetadata
from versaai.memory.conversation import ConversationManager
from versaai.memory.vector_db import VectorDatabase
from versaai.memory.knowledge_graph import KnowledgeGraph
from versaai.memory.episodic import EpisodicMemory
from versaai.agents.reasoning import ReasoningEngine, ReasoningStrategy
from versaai.agents.planning import PlanningSystem, Task, TaskPriority
from versaai.rag.rag_system import RAGSystem
from versaai.models.code_llm import (
    CodeLLMBase, 
    create_code_llm, 
    GenerationConfig,
    build_code_prompt,
    extract_code_from_response
)


class CodeTaskType(Enum):
    """Types of coding tasks"""
    GENERATION = "generation"          # Generate new code
    EXPLANATION = "explanation"        # Explain existing code
    REVIEW = "review"                  # Review code for issues
    DEBUG = "debug"                    # Debug errors
    REFACTOR = "refactor"             # Refactor/improve code
    TEST = "test"                      # Generate tests
    DOCUMENTATION = "documentation"    # Generate docs
    OPTIMIZATION = "optimization"      # Optimize performance


@dataclass
class CodeContext:
    """Context for code-related tasks"""
    language: str
    framework: Optional[str] = None
    file_path: Optional[str] = None
    existing_code: Optional[str] = None
    error_message: Optional[str] = None
    requirements: Optional[List[str]] = None
    constraints: Optional[List[str]] = None


class CodeModel(ModelBase):
    """
    Specialized coding assistant model with full VersaAI capabilities
    
    Features:
    - Code generation with reasoning
    - Code explanation and documentation
    - Bug detection and debugging
    - Code review and suggestions
    - Test generation
    - Refactoring recommendations
    - Multi-language support
    - Context-aware assistance
    """
    
    def __init__(
        self,
        model_id: str = "code-assistant-v1",
        max_context_tokens: int = 8192,
        enable_memory: bool = True,
        enable_rag: bool = True,
        knowledge_base_path: Optional[str] = None,
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None,
        **llm_kwargs
    ):
        # Create metadata
        metadata = ModelMetadata(
            name=model_id,
            format="custom",
            context_length=max_context_tokens
        )
        super().__init__(metadata)
        
        self.logger = logging.getLogger(__name__)
        self.max_context_tokens = max_context_tokens
        
        # Initialize LLM (if specified)
        self.llm: Optional[CodeLLMBase] = None
        if llm_provider and llm_model:
            try:
                self.llm = create_code_llm(llm_provider, llm_model, **llm_kwargs)
                self.logger.info(f"Initialized {llm_provider} LLM: {llm_model}")
            except Exception as e:
                self.logger.warning(f"Failed to initialize LLM: {e}. Using placeholder mode.")
                self.llm = None
        
        # Short-term memory (conversation)
        self.conversation = ConversationManager(
            model_id=model_id,
            max_context_tokens=max_context_tokens
        ) if enable_memory else None
        
        # Long-term memory (code knowledge)
        if enable_memory:
            self.vector_db = VectorDatabase(
                backend="chroma",
                persist_dir=f"./data/code_kb/{model_id}"
            )
            self.knowledge_graph = KnowledgeGraph(
                persist_dir=f"./data/code_kg/{model_id}"
            )
            self.episodic_memory = EpisodicMemory(
                self.vector_db,
                self.knowledge_graph
            )
        else:
            self.vector_db = None
            self.knowledge_graph = None
            self.episodic_memory = None
        
        # Reasoning and planning
        self.reasoning_engine = ReasoningEngine(strategy=ReasoningStrategy.CHAIN_OF_THOUGHT)
        self.planner = PlanningSystem()
        
        # RAG for code search
        self.rag = RAGSystem(
            vector_db=self.vector_db,
            knowledge_graph=self.knowledge_graph
        ) if enable_rag and self.vector_db else None
        
        # Load knowledge base if provided
        if knowledge_base_path and self.rag:
            self._load_knowledge_base(knowledge_base_path)
        
        # Code-specific prompts
        self._init_prompts()
        
        self.logger.info(f"CodeModel initialized: {model_id}")
    
    def _init_prompts(self):
        """Initialize code-specific prompts"""
        self.system_prompts = {
            CodeTaskType.GENERATION: (
                "You are an expert software engineer. Generate clean, efficient, "
                "well-documented code following best practices."
            ),
            CodeTaskType.EXPLANATION: (
                "You are a patient coding instructor. Explain code clearly and "
                "thoroughly, suitable for learners."
            ),
            CodeTaskType.REVIEW: (
                "You are a senior code reviewer. Identify bugs, security issues, "
                "performance problems, and suggest improvements."
            ),
            CodeTaskType.DEBUG: (
                "You are a debugging expert. Analyze errors systematically, "
                "identify root causes, and provide fixes."
            ),
            CodeTaskType.REFACTOR: (
                "You are a refactoring specialist. Improve code quality, "
                "readability, and maintainability while preserving functionality."
            ),
            CodeTaskType.TEST: (
                "You are a testing expert. Write comprehensive, meaningful tests "
                "with good coverage."
            ),
            CodeTaskType.DOCUMENTATION: (
                "You are a technical writer. Create clear, comprehensive "
                "documentation."
            ),
            CodeTaskType.OPTIMIZATION: (
                "You are a performance optimization expert. Identify bottlenecks "
                "and suggest optimizations."
            ),
        }
    
    def _load_knowledge_base(self, path: str):
        """Load code knowledge base"""
        try:
            # TODO: Implement knowledge base loading
            # - Load code examples
            # - Load documentation
            # - Build vector embeddings
            self.logger.info(f"Loading knowledge base from {path}")
        except Exception as e:
            self.logger.error(f"Failed to load knowledge base: {e}")
    
    def generate_code(
        self,
        task: str,
        context: CodeContext,
        use_reasoning: bool = True,
        use_planning: bool = False
    ) -> Dict[str, Any]:
        """
        Generate code for a given task
        
        Args:
            task: Description of what to generate
            context: Code context (language, framework, etc.)
            use_reasoning: Use reasoning engine
            use_planning: Use planning system for complex tasks
            
        Returns:
            Dict with 'code', 'explanation', 'reasoning_steps'
        """
        self.logger.info(f"Generating code: {task}")
        
        # Build prompt
        system_prompt = self.system_prompts[CodeTaskType.GENERATION]
        user_prompt = self._build_generation_prompt(task, context)
        
        # Add conversation context
        if self.conversation:
            self.conversation.add_turn("user", task)
        
        # Use RAG to find relevant examples
        relevant_examples = []
        if self.rag:
            try:
                rag_results = self.rag.retrieve(
                    query=task,
                    top_k=3,
                    filters={"language": context.language}
                )
                relevant_examples = rag_results.get("documents", [])
            except Exception as e:
                self.logger.warning(f"RAG retrieval failed: {e}")
        
        # Use planning for complex tasks
        if use_planning:
            plan = self.planner.create_plan(
                goal=task,
                context={
                    "language": context.language,
                    "framework": context.framework,
                    "requirements": context.requirements or []
                }
            )
            self.logger.info(f"Created plan with {len(plan.tasks)} tasks")
        
        # Use reasoning
        if use_reasoning:
            reasoning_result = self.reasoning_engine.reason(
                task=user_prompt,
                context={
                    "system_prompt": system_prompt,
                    "examples": relevant_examples,
                    "language": context.language
                }
            )
            
            code = reasoning_result.answer
            explanation = self._extract_explanation(reasoning_result)
            steps = [step.content for step in reasoning_result.steps]
        else:
            # Direct generation (placeholder for actual LLM call)
            code = self._generate_code_direct(user_prompt, context)
            explanation = "Code generated"
            steps = []
        
        # Store in memory
        if self.conversation:
            self.conversation.add_turn("assistant", code)
        
        if self.episodic_memory:
            self.episodic_memory.add_episode(
                conversation_id=self.conversation.conversation_id if self.conversation else "default",
                messages=[
                    {"role": "user", "content": task},
                    {"role": "assistant", "content": code}
                ],
                importance=0.7,
                metadata={
                    "task_type": "code_generation",
                    "language": context.language
                }
            )
        
        return {
            "code": code,
            "explanation": explanation,
            "reasoning_steps": steps,
            "language": context.language
        }
    
    def explain_code(
        self,
        code: str,
        context: CodeContext,
        detail_level: str = "medium"
    ) -> Dict[str, Any]:
        """
        Explain existing code
        
        Args:
            code: Code to explain
            context: Code context
            detail_level: "brief", "medium", or "detailed"
            
        Returns:
            Dict with 'explanation', 'key_concepts', 'suggestions'
        """
        self.logger.info(f"Explaining code ({len(code)} chars)")
        
        # Use reasoning for detailed explanation
        reasoning_result = self.reasoning_engine.reason(
            task=f"Explain this {context.language} code:\n\n{code}",
            context={
                "detail_level": detail_level,
                "language": context.language
            },
            strategy=ReasoningStrategy.CHAIN_OF_THOUGHT
        )
        
        explanation = reasoning_result.answer
        key_concepts = self._extract_key_concepts(code, context)
        suggestions = self._generate_suggestions(code, context)
        
        return {
            "explanation": explanation,
            "key_concepts": key_concepts,
            "suggestions": suggestions,
            "complexity_analysis": self._analyze_complexity(code)
        }
    
    def review_code(
        self,
        code: str,
        context: CodeContext
    ) -> Dict[str, Any]:
        """
        Review code for issues and improvements
        
        Args:
            code: Code to review
            context: Code context
            
        Returns:
            Dict with 'issues', 'suggestions', 'score'
        """
        self.logger.info(f"Reviewing code ({len(code)} chars)")
        
        # Use reasoning for systematic review
        reasoning_result = self.reasoning_engine.reason(
            task=f"Review this {context.language} code for bugs, security issues, and improvements:\n\n{code}",
            context={"language": context.language},
            strategy=ReasoningStrategy.REACT
        )
        
        issues = self._extract_issues(reasoning_result)
        suggestions = self._extract_suggestions(reasoning_result)
        score = self._calculate_code_score(code, issues)
        
        return {
            "issues": issues,
            "suggestions": suggestions,
            "score": score,
            "review_summary": reasoning_result.answer
        }
    
    def debug_error(
        self,
        code: str,
        error: str,
        context: CodeContext
    ) -> Dict[str, Any]:
        """
        Debug an error in code
        
        Args:
            code: Code with error
            error: Error message
            context: Code context
            
        Returns:
            Dict with 'root_cause', 'fix', 'explanation'
        """
        self.logger.info(f"Debugging error: {error[:100]}")
        
        # Use ReAct reasoning for systematic debugging
        reasoning_result = self.reasoning_engine.reason(
            task=f"Debug this {context.language} error:\n\nCode:\n{code}\n\nError:\n{error}",
            context={
                "language": context.language,
                "file_path": context.file_path
            },
            strategy=ReasoningStrategy.REACT
        )
        
        root_cause = self._extract_root_cause(reasoning_result)
        fix = self._extract_fix(reasoning_result)
        
        return {
            "root_cause": root_cause,
            "fix": fix,
            "explanation": reasoning_result.answer,
            "debugging_steps": [step.content for step in reasoning_result.steps]
        }
    
    def refactor_code(
        self,
        code: str,
        context: CodeContext,
        goals: List[str] = None
    ) -> Dict[str, Any]:
        """
        Refactor code to improve quality
        
        Args:
            code: Code to refactor
            context: Code context
            goals: Refactoring goals (e.g., ["readability", "performance"])
            
        Returns:
            Dict with 'refactored_code', 'changes', 'improvements'
        """
        self.logger.info(f"Refactoring code ({len(code)} chars)")
        
        goals = goals or ["readability", "maintainability"]
        
        # Create refactoring plan
        plan = self.planner.create_plan(
            goal=f"Refactor code for: {', '.join(goals)}",
            context={
                "language": context.language,
                "code_length": len(code),
                "goals": goals
            }
        )
        
        # Use reasoning for refactoring
        reasoning_result = self.reasoning_engine.reason(
            task=f"Refactor this {context.language} code for {', '.join(goals)}:\n\n{code}",
            context={"language": context.language, "goals": goals}
        )
        
        refactored_code = reasoning_result.answer
        changes = self._identify_changes(code, refactored_code)
        improvements = self._analyze_improvements(code, refactored_code, goals)
        
        return {
            "refactored_code": refactored_code,
            "changes": changes,
            "improvements": improvements,
            "plan": plan.to_dict()
        }
    
    def generate_tests(
        self,
        code: str,
        context: CodeContext,
        test_framework: str = "pytest"
    ) -> Dict[str, Any]:
        """
        Generate tests for code
        
        Args:
            code: Code to test
            context: Code context
            test_framework: Testing framework to use
            
        Returns:
            Dict with 'test_code', 'coverage_areas', 'test_count'
        """
        self.logger.info(f"Generating tests for code ({len(code)} chars)")
        
        reasoning_result = self.reasoning_engine.reason(
            task=f"Generate {test_framework} tests for this {context.language} code:\n\n{code}",
            context={
                "language": context.language,
                "framework": test_framework
            }
        )
        
        test_code = reasoning_result.answer
        coverage_areas = self._identify_coverage_areas(code)
        
        return {
            "test_code": test_code,
            "coverage_areas": coverage_areas,
            "test_framework": test_framework,
            "estimated_coverage": self._estimate_coverage(code, test_code)
        }
    
    # Helper methods
    
    def _build_generation_prompt(self, task: str, context: CodeContext) -> str:
        """Build prompt for code generation"""
        prompt = f"Generate {context.language} code for: {task}"
        
        if context.framework:
            prompt += f"\nFramework: {context.framework}"
        
        if context.requirements:
            prompt += f"\nRequirements:\n" + "\n".join(f"- {req}" for req in context.requirements)
        
        if context.constraints:
            prompt += f"\nConstraints:\n" + "\n".join(f"- {con}" for con in context.constraints)
        
        if context.existing_code:
            prompt += f"\n\nExisting code:\n{context.existing_code}"
        
        return prompt
    
    def _generate_code_direct(self, prompt: str, context: CodeContext) -> str:
        """Direct code generation with real LLM or placeholder"""
        if self.llm and self.llm.is_loaded():
            # Use real LLM
            try:
                # Build structured prompt
                full_prompt = build_code_prompt(
                    task=prompt,
                    language=context.language,
                    framework=context.framework,
                    requirements=context.requirements,
                    existing_code=context.existing_code
                )
                
                # Generate with LLM
                config = GenerationConfig(
                    max_tokens=1024,
                    temperature=0.7,
                    stop_sequences=["```\n", "\n\n\n"]
                )
                
                response = self.llm.generate(full_prompt, config)
                
                # Extract code from response
                code = extract_code_from_response(response, context.language)
                
                self.logger.info(f"Generated {len(code)} chars of {context.language} code")
                return code
                
            except Exception as e:
                self.logger.error(f"LLM generation failed: {e}. Falling back to placeholder.")
                # Fall through to placeholder
        
        # Placeholder (no LLM available)
        return f"# Generated {context.language} code for:\n# {prompt}\n\npass  # TODO: Implement with LLM"
    
    def _extract_explanation(self, reasoning_result) -> str:
        """Extract explanation from reasoning result"""
        # Extract from reasoning steps
        return reasoning_result.answer
    
    def _extract_key_concepts(self, code: str, context: CodeContext) -> List[str]:
        """Extract key concepts from code"""
        # TODO: Implement concept extraction
        return ["concept1", "concept2"]
    
    def _generate_suggestions(self, code: str, context: CodeContext) -> List[str]:
        """Generate improvement suggestions"""
        # TODO: Implement suggestion generation
        return []
    
    def _analyze_complexity(self, code: str) -> Dict[str, Any]:
        """Analyze code complexity"""
        lines = len(code.split('\n'))
        return {
            "lines": lines,
            "estimated_complexity": "medium" if lines < 100 else "high"
        }
    
    def _extract_issues(self, reasoning_result) -> List[Dict[str, Any]]:
        """Extract issues from review"""
        # TODO: Parse issues from reasoning result
        return []
    
    def _extract_suggestions(self, reasoning_result) -> List[str]:
        """Extract suggestions from review"""
        return []
    
    def _calculate_code_score(self, code: str, issues: List) -> float:
        """Calculate code quality score"""
        base_score = 100.0
        penalty = len(issues) * 5
        return max(0, base_score - penalty)
    
    def _extract_root_cause(self, reasoning_result) -> str:
        """Extract root cause from debugging"""
        return reasoning_result.answer
    
    def _extract_fix(self, reasoning_result) -> str:
        """Extract fix from debugging"""
        return reasoning_result.answer
    
    def _identify_changes(self, original: str, refactored: str) -> List[Dict[str, str]]:
        """Identify changes between original and refactored code"""
        # TODO: Implement diff analysis
        return []
    
    def _analyze_improvements(self, original: str, refactored: str, goals: List[str]) -> Dict[str, Any]:
        """Analyze improvements from refactoring"""
        return {
            "goals_met": goals,
            "improvement_percentage": 20.0
        }
    
    def _identify_coverage_areas(self, code: str) -> List[str]:
        """Identify test coverage areas"""
        # TODO: Implement coverage analysis
        return ["main_functionality", "edge_cases", "error_handling"]
    
    def _estimate_coverage(self, code: str, test_code: str) -> float:
        """Estimate test coverage percentage"""
        # Simple heuristic
        return min(100.0, (len(test_code) / len(code)) * 50)
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get conversation history"""
        if self.conversation:
            return self.conversation.get_messages()
        return []
    
    def clear_conversation(self):
        """Clear conversation history"""
        if self.conversation:
            self.conversation.clear()
            self.logger.info("Conversation history cleared")
    
    # Implement abstract methods from ModelBase
    
    def load(self) -> None:
        """Load the code model (no-op for now)"""
        self._loaded = True
        self.logger.info(f"CodeModel {self.model_id} loaded")
    
    def unload(self) -> None:
        """Unload the code model"""
        self._loaded = False
        self.logger.info(f"CodeModel {self.model_id} unloaded")
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 100,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop_sequences: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """
        Generate text from prompt
        
        TODO: Integrate with actual LLM (OpenAI, Anthropic, local model, etc.)
        For now, returns placeholder
        """
        # Placeholder - will be replaced with actual LLM integration
        return f"# Generated response for: {prompt[:50]}...\n# TODO: Integrate with LLM"
    
    def get_embeddings(self, text: str) -> List[float]:
        """
        Get embeddings for text
        
        TODO: Integrate with embedding model (sentence-transformers, OpenAI, etc.)
        For now, returns dummy embeddings
        """
        # Placeholder - will be replaced with actual embedding model
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        # Generate 384-dimensional dummy embedding
        return [(hash_val >> i) % 256 / 256.0 for i in range(384)]
