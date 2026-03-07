"""
VersaAI Agents — production-grade AI agents with real LLM inference.

Core components:
- AgentBase: Abstract base class for all agents
- CodingAgent: Code generation, analysis, debugging (ReAct loop)
- ResearchAgent: Research with RAG and self-correction
- ReasoningEngine: CoT, ReAct, ToT, Self-Consistency strategies
- PlanningSystem: LLM-powered goal decomposition
- LLMClient: Unified LLM interface for all agents
"""

from versaai.agents.agent_base import AgentBase, AgentMetadata
from versaai.agents.coding_agent import CodingAgent
from versaai.agents.research_agent import ResearchAgent
from versaai.agents.reasoning import ReasoningEngine, ReasoningResult, ReasoningStep
from versaai.agents.planning import PlanningSystem, ExecutionPlan, Task
from versaai.agents.llm_client import LLMClient

__all__ = [
    "AgentBase",
    "AgentMetadata",
    "CodingAgent",
    "ResearchAgent",
    "ReasoningEngine",
    "ReasoningResult",
    "ReasoningStep",
    "PlanningSystem",
    "ExecutionPlan",
    "Task",
    "LLMClient",
]
