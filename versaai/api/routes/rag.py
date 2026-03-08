"""
VersaAI RAG API — document ingestion and retrieval endpoints.

Endpoints:
    POST /v1/rag/ingest    — Ingest raw text (chunk → embed → store)
    POST /v1/rag/query     — Retrieve relevant chunks for a question
    GET  /v1/rag/stats     — RAG system statistics
    GET  /v1/rag/documents — List all stored documents (paginated)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from versaai.rag.rag_system import RAGSystem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/rag")

# ---------------------------------------------------------------------------
# Singleton RAG system (lazy init)
# ---------------------------------------------------------------------------

_rag: Optional[RAGSystem] = None


def _get_rag() -> RAGSystem:
    global _rag
    if _rag is None:
        _rag = RAGSystem()
    return _rag


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class IngestRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Raw document text to ingest")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional metadata")
    doc_id_prefix: Optional[str] = Field(None, description="Optional ID prefix for chunks")


class IngestResponse(BaseModel):
    status: str = "ok"
    chunks_stored: int
    total_ingested: int


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Search query")
    top_k: int = Field(5, ge=1, le=100, description="Number of results")
    filter_metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata filter")


class QueryResult(BaseModel):
    id: str
    document: str
    score: float
    metadata: Dict[str, Any] = {}


class QueryResponse(BaseModel):
    status: str = "ok"
    results: List[QueryResult]
    total_results: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(req: IngestRequest):
    """Ingest a document: chunk → embed → store."""
    try:
        rag = _get_rag()
        import asyncio

        chunks = await asyncio.to_thread(
            rag.ingest, req.text, req.metadata or None, req.doc_id_prefix
        )
        return IngestResponse(
            chunks_stored=chunks,
            total_ingested=rag._total_ingested,
        )
    except Exception as e:
        logger.error("Ingest failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=QueryResponse)
async def query_documents(req: QueryRequest):
    """Retrieve the most relevant document chunks for a question."""
    try:
        rag = _get_rag()
        import asyncio

        results = await asyncio.to_thread(
            rag.query, req.question, req.top_k, req.filter_metadata
        )
        return QueryResponse(
            results=[QueryResult(**r) for r in results],
            total_results=len(results),
        )
    except Exception as e:
        logger.error("Query failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def rag_stats():
    """Return RAG system statistics."""
    try:
        rag = _get_rag()
        return rag.stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents")
async def list_documents(limit: int = 100, offset: int = 0):
    """List all stored documents."""
    try:
        rag = _get_rag()
        import asyncio

        all_docs = await asyncio.to_thread(rag.get_all_documents)
        page = all_docs[offset : offset + limit]
        return {
            "documents": page,
            "total": len(all_docs),
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
