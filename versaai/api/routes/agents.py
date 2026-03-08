"""
Agent API routes — execute tasks via specialized agents.

Endpoints:
    POST /v1/agents/execute    — Run a task on a named agent (JSON or SSE stream)
    GET  /v1/agents            — List available agents and their capabilities
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from versaai.api.errors import InvalidRequestError, InferenceError, InferenceTimeoutError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/agents")


# ============================================================================
# Schemas
# ============================================================================

class AgentExecuteRequest(BaseModel):
    """Request to execute a task on an agent."""
    agent: str = Field(
        description="Agent name: 'coding', 'research', 'reasoning', 'planning'"
    )
    task: str = Field(
        description="The task to execute (natural language)"
    )
    model: Optional[str] = Field(
        default=None,
        description="Override model ID (e.g. 'ollama/qwen2.5-coder:7b')",
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional context for the agent (file_content, constraints, etc.)",
    )
    config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Agent-specific configuration overrides",
    )
    stream: bool = Field(
        default=False,
        description="If true, returns SSE stream with intermediate steps as they execute.",
    )
    timeout: Optional[float] = Field(
        default=300.0,
        ge=1.0,
        le=3600.0,
        description="Maximum execution time in seconds (default 300s / 5min).",
    )


class AgentExecuteResponse(BaseModel):
    """Response from agent execution."""
    id: str
    agent: str
    task: str
    result: str
    steps: List[Any] = []
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = {}
    execution_time: float = 0.0
    status: str = "success"


class AgentInfo(BaseModel):
    """Information about an available agent."""
    name: str
    description: str
    version: str
    capabilities: List[str]


class AgentListResponse(BaseModel):
    """List of available agents."""
    agents: List[AgentInfo]


# ============================================================================
# Agent registry (lazy singleton)
# ============================================================================

_agent_instances: Dict[str, Any] = {}


def _get_or_create_agent(agent_name: str, config: Optional[Dict[str, Any]] = None):
    """
    Get or lazily create and initialize an agent instance.

    Agents are cached after first creation.
    """
    key = agent_name.lower()

    if key in _agent_instances:
        return _agent_instances[key]

    cfg = config or {}

    if key == "coding":
        from versaai.agents.coding_agent import CodingAgent
        agent = CodingAgent()
        agent.initialize(cfg)

    elif key == "research":
        from versaai.agents.research_agent import ResearchAgent
        agent = ResearchAgent()
        agent.initialize(cfg)

    elif key == "reasoning":
        from versaai.agents.reasoning import ReasoningEngine
        from versaai.agents.llm_client import LLMClient
        llm = LLMClient(
            model=cfg.get("model"),
            temperature=cfg.get("temperature", 0.7),
        )
        agent = ReasoningEngine(
            llm_function=llm,
            strategy="cot",  # default; callers override per-request
        )

    elif key == "planning":
        from versaai.agents.planning import PlanningSystem
        from versaai.agents.llm_client import LLMClient
        llm = LLMClient(
            model=cfg.get("model"),
            temperature=cfg.get("temperature", 0.4),
        )
        agent = PlanningSystem(llm_function=llm)

    else:
        raise InvalidRequestError(
            f"Unknown agent: '{agent_name}'. Available: coding, research, reasoning, planning",
            param="agent",
        )

    _agent_instances[key] = agent
    return agent


# ============================================================================
# Endpoints
# ============================================================================

AGENT_INFO = [
    AgentInfo(
        name="coding",
        description="Code generation, analysis, and debugging via ReAct loop",
        version="2.0.0",
        capabilities=["code_generation", "code_analysis", "debugging", "file_system_access", "shell_execution"],
    ),
    AgentInfo(
        name="research",
        description="Research with adaptive retrieval and LLM self-correction",
        version="2.0.0",
        capabilities=["information_retrieval", "document_qa", "fact_verification", "citation_generation"],
    ),
    AgentInfo(
        name="reasoning",
        description="Chain-of-Thought, ReAct, Tree-of-Thoughts, Self-Consistency reasoning",
        version="2.0.0",
        capabilities=["chain_of_thought", "react", "tree_of_thoughts", "self_consistency", "zero_shot"],
    ),
    AgentInfo(
        name="planning",
        description="LLM-powered goal decomposition and task planning",
        version="2.0.0",
        capabilities=["goal_decomposition", "dependency_resolution", "execution_scheduling"],
    ),
]


@router.get("", response_model=AgentListResponse)
async def list_agents():
    """List all available agents and their capabilities."""
    return AgentListResponse(agents=AGENT_INFO)


@router.post("/execute", response_model=AgentExecuteResponse)
async def execute_agent(request: AgentExecuteRequest):
    """
    Execute a task on a named agent.

    The agent will be lazily created and initialized on first call.
    Subsequent calls reuse the same instance.

    If stream=true, returns SSE with intermediate progress events,
    followed by a final result event.
    """
    start = time.time()
    request_id = f"agent-{uuid.uuid4().hex[:12]}"
    agent_name = request.agent.lower()
    timeout = request.timeout or 300.0

    logger.info(
        f"[{request_id}] Agent={agent_name} Task={request.task[:100]}... "
        f"stream={request.stream} timeout={timeout}s"
    )

    # Merge model override into config
    cfg = dict(request.config or {})
    if request.model:
        cfg["model"] = request.model

    try:
        agent = _get_or_create_agent(agent_name, cfg)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[{request_id}] Agent creation failed: {exc}", exc_info=True)
        raise InferenceError(f"Agent initialization error: {exc}")

    # Streaming mode: return SSE
    if request.stream:
        return StreamingResponse(
            _stream_agent_execution(agent, agent_name, request, cfg, request_id, start, timeout),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Non-streaming mode: run with timeout
    try:
        result = await asyncio.wait_for(
            _dispatch_agent(agent, agent_name, request, cfg, request_id, start),
            timeout=timeout,
        )
        return result

    except asyncio.TimeoutError:
        logger.error(f"[{request_id}] Agent timed out after {timeout}s")
        raise InferenceTimeoutError(timeout_seconds=timeout, provider=agent_name)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[{request_id}] Execution failed: {exc}", exc_info=True)
        raise InferenceError(f"Agent execution error: {exc}")


# ============================================================================
# Dispatch helper (non-streaming)
# ============================================================================

async def _dispatch_agent(
    agent, agent_name: str, request: AgentExecuteRequest,
    cfg: dict, request_id: str, start: float,
) -> AgentExecuteResponse:
    """Run the appropriate agent method in a thread and return the response."""

    if agent_name == "coding":
        raw = await asyncio.to_thread(agent.execute, request.task, request.context)
        return AgentExecuteResponse(
            id=request_id,
            agent=agent_name,
            task=request.task,
            result=raw.get("result", ""),
            steps=raw.get("steps", []),
            metadata={"files_modified": raw.get("files_modified", [])},
            execution_time=time.time() - start,
            status=raw.get("status", "success"),
        )

    elif agent_name == "research":
        raw = await asyncio.to_thread(agent.execute, request.task, request.context)
        return AgentExecuteResponse(
            id=request_id,
            agent=agent_name,
            task=request.task,
            result=raw.get("result", ""),
            steps=raw.get("steps", []),
            confidence=raw.get("confidence"),
            metadata=raw.get("metadata", {}),
            execution_time=time.time() - start,
            status="success",
        )

    elif agent_name == "reasoning":
        ctx = request.context or {}
        _STRATEGY_ALIASES = {
            "chain_of_thought": "cot", "chain-of-thought": "cot",
            "react": "react",
            "tree_of_thoughts": "tot", "tree-of-thoughts": "tot",
            "self_consistency": "self_consistency", "self-consistency": "self_consistency",
            "zero_shot": "zero_shot", "zero-shot": "zero_shot",
            "cot": "cot", "tot": "tot",
        }
        raw_strat = cfg.get("strategy")
        strategy = _STRATEGY_ALIASES.get(raw_strat, raw_strat) if raw_strat else None
        result = await asyncio.to_thread(
            agent.reason,
            task=request.task,
            context=ctx,
            strategy=strategy,
        )
        return AgentExecuteResponse(
            id=request_id,
            agent=agent_name,
            task=request.task,
            result=result.answer,
            steps=[s.to_dict() for s in result.steps],
            confidence=result.confidence,
            metadata=result.metadata,
            execution_time=result.execution_time,
            status="success",
        )

    elif agent_name == "planning":
        ctx = request.context or {}
        plan = await asyncio.to_thread(
            agent.create_plan,
            goal=request.task,
            context=ctx,
            constraints=cfg.get("constraints"),
        )
        return AgentExecuteResponse(
            id=request_id,
            agent=agent_name,
            task=request.task,
            result=f"Plan created with {len(plan.tasks)} tasks",
            steps=[t.to_dict() for t in plan.tasks],
            metadata={
                "plan_id": plan.plan_id,
                "total_estimated_duration": plan.total_estimated_duration,
            },
            execution_time=time.time() - start,
            status="success",
        )

    else:
        raise InvalidRequestError(f"Unknown agent: {agent_name}", param="agent")


# ============================================================================
# Streaming helper
# ============================================================================

async def _stream_agent_execution(
    agent, agent_name: str, request: AgentExecuteRequest,
    cfg: dict, request_id: str, start: float, timeout: float,
) -> AsyncGenerator[str, None]:
    """
    SSE stream for agent execution.

    Emits events:
        event: step     — intermediate progress / ReAct steps
        event: result   — final result
        event: error    — on failure or timeout
        data: [DONE]    — end marker
    """
    def _sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"

    # Emit start event
    yield _sse("step", {
        "id": request_id,
        "agent": agent_name,
        "type": "start",
        "message": f"Starting {agent_name} agent...",
        "elapsed": 0.0,
    })

    try:
        result = await asyncio.wait_for(
            _dispatch_agent(agent, agent_name, request, cfg, request_id, start),
            timeout=timeout,
        )

        # Emit each step as a separate event
        for i, step in enumerate(result.steps):
            yield _sse("step", {
                "id": request_id,
                "agent": agent_name,
                "type": "step",
                "step_index": i,
                "step": step if isinstance(step, dict) else str(step),
                "elapsed": time.time() - start,
            })

        # Emit final result
        yield _sse("result", result.model_dump())

    except asyncio.TimeoutError:
        yield _sse("error", {
            "id": request_id,
            "agent": agent_name,
            "error": f"Execution timed out after {timeout}s",
            "elapsed": time.time() - start,
        })
    except Exception as exc:
        yield _sse("error", {
            "id": request_id,
            "agent": agent_name,
            "error": str(exc),
            "elapsed": time.time() - start,
        })

    yield "data: [DONE]\n\n"
