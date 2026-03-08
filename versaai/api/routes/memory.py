"""
VersaAI Memory API — conversation persistence endpoints.

Endpoints:
    POST   /v1/memory/conversations           — Create a conversation
    GET    /v1/memory/conversations           — List conversations
    GET    /v1/memory/conversations/{id}      — Get conversation + messages
    DELETE /v1/memory/conversations/{id}      — Delete conversation
    POST   /v1/memory/conversations/{id}/messages — Add a message
    GET    /v1/memory/conversations/{id}/messages — Get messages (paginated)
    POST   /v1/memory/search                  — Search across messages
    GET    /v1/memory/stats                   — Memory system stats
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from versaai.memory.persistence import ConversationDB

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/memory")

# ---------------------------------------------------------------------------
# Singleton DB (lazy init)
# ---------------------------------------------------------------------------

_db: Optional[ConversationDB] = None


async def _get_db() -> ConversationDB:
    global _db
    if _db is None:
        _db = ConversationDB()
        await _db.initialize()
    return _db


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class CreateConversationRequest(BaseModel):
    title: str = Field("", description="Conversation title")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CreateConversationResponse(BaseModel):
    id: str
    title: str


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: float
    updated_at: float
    metadata: Dict[str, Any] = {}


class AddMessageRequest(BaseModel):
    role: str = Field(..., description="'user', 'assistant', or 'system'")
    content: str = Field(..., min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: float
    metadata: Dict[str, Any] = {}


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    conversation_id: Optional[str] = None
    limit: int = Field(20, ge=1, le=200)


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------


@router.post("/conversations", response_model=CreateConversationResponse)
async def create_conversation(req: CreateConversationRequest):
    db = await _get_db()
    cid = await db.create_conversation(title=req.title, metadata=req.metadata)
    return CreateConversationResponse(id=cid, title=req.title)


@router.get("/conversations", response_model=List[ConversationSummary])
async def list_conversations(limit: int = 50, offset: int = 0):
    db = await _get_db()
    convs = await db.list_conversations(limit=limit, offset=offset)
    return [ConversationSummary(**c) for c in convs]


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, include_messages: bool = True):
    db = await _get_db()
    conv = await db.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = {**conv}
    if include_messages:
        result["messages"] = await db.get_messages(conversation_id)
        result["message_count"] = len(result["messages"])
    return result


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    db = await _get_db()
    deleted = await db.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "deleted", "id": conversation_id}


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


@router.post("/conversations/{conversation_id}/messages")
async def add_message(conversation_id: str, req: AddMessageRequest):
    db = await _get_db()
    conv = await db.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    mid = await db.add_message(
        conversation_id=conversation_id,
        role=req.role,
        content=req.content,
        metadata=req.metadata,
    )
    return {"id": mid, "conversation_id": conversation_id, "role": req.role}


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageOut])
async def get_messages(conversation_id: str, limit: int = 200, offset: int = 0):
    db = await _get_db()
    msgs = await db.get_messages(conversation_id, limit=limit, offset=offset)
    return [MessageOut(**m) for m in msgs]


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


@router.post("/search")
async def search_messages(req: SearchRequest):
    db = await _get_db()
    results = await db.search_messages(
        query=req.query,
        conversation_id=req.conversation_id,
        limit=req.limit,
    )
    return {"results": results, "total": len(results)}


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


@router.get("/stats")
async def memory_stats():
    db = await _get_db()
    return await db.stats()
