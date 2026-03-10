"""
Agent API routes — execute tasks via specialized agents.

Endpoints:
    POST /v1/agents/execute    — Run a task on a named agent (JSON or SSE stream)
    GET  /v1/agents            — List available agents and their capabilities
"""

import asyncio
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
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
    status: str = "active"


class AgentListResponse(BaseModel):
    """List of available agents."""
    agents: List[AgentInfo]


# ============================================================================
# Execution tracking
# ============================================================================

@dataclass
class ExecutionRecord:
    """Tracks a running or completed agent execution."""
    id: str
    agent: str
    task: str
    status: str = "running"  # running, completed, cancelled, error
    cancelled: threading.Event = field(default_factory=threading.Event)
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    result: Optional[str] = None
    error: Optional[str] = None

    def elapsed(self) -> float:
        end = self.completed_at or time.time()
        return end - self.started_at


_executions: Dict[str, ExecutionRecord] = {}
_EXECUTION_TTL = 600  # Keep completed records for 10 min


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
        from versaai.agents.reasoning_agent import ReasoningAgent
        agent = ReasoningAgent()
        agent.initialize(cfg)

    elif key == "planning":
        from versaai.agents.planning_agent import PlanningAgent
        agent = PlanningAgent()
        agent.initialize(cfg)

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

    Returns an execution ID that can be used to poll status or cancel.
    """
    start = time.time()
    request_id = f"agent-{uuid.uuid4().hex[:12]}"
    agent_name = request.agent.lower()
    timeout = request.timeout or 300.0

    # Garbage-collect old execution records
    _gc_executions()

    # Register execution
    record = ExecutionRecord(id=request_id, agent=agent_name, task=request.task)
    _executions[request_id] = record

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
        record.status = "completed"
        record.completed_at = time.time()
        record.result = result.result
        return result

    except asyncio.TimeoutError:
        record.status = "error"
        record.completed_at = time.time()
        record.error = f"Timed out after {timeout}s"
        logger.error(f"[{request_id}] Agent timed out after {timeout}s")
        raise InferenceTimeoutError(timeout_seconds=timeout, provider=agent_name)
    except HTTPException:
        record.status = "error"
        record.completed_at = time.time()
        raise
    except Exception as exc:
        record.status = "error"
        record.completed_at = time.time()
        record.error = str(exc)
        logger.error(f"[{request_id}] Execution failed: {exc}", exc_info=True)
        raise InferenceError(f"Agent execution error: {exc}")


@router.get("/executions/{execution_id}")
async def get_execution_status(execution_id: str):
    """Poll the status of a running or completed agent execution."""
    record = _executions.get(execution_id)
    if not record:
        raise InvalidRequestError(
            f"Execution '{execution_id}' not found", param="execution_id",
        )
    return {
        "id": record.id,
        "agent": record.agent,
        "task": record.task,
        "status": record.status,
        "elapsed": record.elapsed(),
        "result": record.result,
        "error": record.error,
    }


@router.post("/executions/{execution_id}/cancel")
async def cancel_execution(execution_id: str):
    """Cancel a running agent execution."""
    record = _executions.get(execution_id)
    if not record:
        raise InvalidRequestError(
            f"Execution '{execution_id}' not found", param="execution_id",
        )
    if record.status != "running":
        return {"id": record.id, "status": record.status, "message": "Not running"}

    record.cancelled.set()
    record.status = "cancelled"
    record.completed_at = time.time()
    logger.info(f"[{execution_id}] Execution cancelled by user")
    return {"id": record.id, "status": "cancelled", "elapsed": record.elapsed()}


def _gc_executions():
    """Remove execution records older than TTL."""
    now = time.time()
    expired = [
        eid for eid, rec in _executions.items()
        if rec.completed_at and (now - rec.completed_at) > _EXECUTION_TTL
    ]
    for eid in expired:
        del _executions[eid]


# ============================================================================
# Dispatch helper (non-streaming)
# ============================================================================

async def _dispatch_agent(
    agent, agent_name: str, request: AgentExecuteRequest,
    cfg: dict, request_id: str, start: float,
    step_callback=None,
) -> AgentExecuteResponse:
    """Run the appropriate agent method in a thread and return the response.

    If *step_callback* is provided it will be injected into the agent's
    execution context so intermediate steps are reported in real-time.
    """

    # Build context dict, injecting the callback when available
    ctx = dict(request.context or {})
    if step_callback is not None:
        ctx["status_callback"] = step_callback

    if agent_name == "coding":
        raw = await asyncio.to_thread(agent.execute, request.task, ctx)
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
        raw = await asyncio.to_thread(agent.execute, request.task, ctx)
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
        if strategy:
            ctx["strategy"] = strategy
        raw = await asyncio.to_thread(agent.execute, request.task, ctx)
        return AgentExecuteResponse(
            id=request_id,
            agent=agent_name,
            task=request.task,
            result=raw.get("result", ""),
            steps=raw.get("steps", []),
            confidence=raw.get("confidence"),
            metadata={
                "strategy_used": raw.get("strategy_used"),
                "verified": raw.get("verified"),
            },
            execution_time=raw.get("execution_time", time.time() - start),
            status="success",
        )

    elif agent_name == "planning":
        ctx["action"] = cfg.get("action", "plan")
        if cfg.get("constraints"):
            ctx["constraints"] = cfg["constraints"]
        if cfg.get("plan_id"):
            ctx["plan_id"] = cfg["plan_id"]
        raw = await asyncio.to_thread(agent.execute, request.task, ctx)
        return AgentExecuteResponse(
            id=request_id,
            agent=agent_name,
            task=request.task,
            result=raw.get("result", ""),
            steps=raw.get("steps", []),
            metadata=raw.get("metadata", {}),
            execution_time=raw.get("execution_time", time.time() - start),
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
    SSE stream for agent execution with **real-time** step delivery.

    Uses an asyncio.Queue bridged from the agent's synchronous
    ``status_callback`` (which runs in a worker thread) so that each
    step/thought/action is sent to the client as it happens.

    Emits events:
        event: step     — intermediate progress / ReAct steps
        event: result   — final result
        event: error    — on failure or timeout
        data: [DONE]    — end marker
    """
    def _sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"

    # Queue for cross-thread step delivery
    loop = asyncio.get_running_loop()
    step_queue: asyncio.Queue = asyncio.Queue()
    step_counter = 0

    def _step_callback(message: str):
        """Called from agent thread — pushes a step onto the async queue."""
        nonlocal step_counter
        step_counter += 1
        loop.call_soon_threadsafe(
            step_queue.put_nowait,
            {
                "id": request_id,
                "agent": agent_name,
                "type": "step",
                "step_index": step_counter,
                "message": message,
                "elapsed": time.time() - start,
            },
        )

    # Emit start event
    yield _sse("step", {
        "id": request_id,
        "agent": agent_name,
        "type": "start",
        "message": f"Starting {agent_name} agent...",
        "elapsed": 0.0,
    })

    # Launch the agent in a background task so we can drain the queue
    dispatch_task = asyncio.create_task(
        asyncio.wait_for(
            _dispatch_agent(
                agent, agent_name, request, cfg, request_id, start,
                step_callback=_step_callback,
            ),
            timeout=timeout,
        )
    )

    # Drain step_queue and yield SSE events until the agent finishes
    while True:
        try:
            item = await asyncio.wait_for(step_queue.get(), timeout=0.25)
            yield _sse("step", item)
            continue
        except asyncio.TimeoutError:
            pass  # No step arrived in 250ms — check if task is done

        if dispatch_task.done():
            # Flush any remaining queued steps
            while not step_queue.empty():
                try:
                    item = step_queue.get_nowait()
                    yield _sse("step", item)
                except asyncio.QueueEmpty:
                    break
            break

    # Handle task result / exception
    try:
        result = dispatch_task.result()
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
