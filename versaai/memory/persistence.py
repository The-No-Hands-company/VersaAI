"""
VersaAI Conversation Persistence — SQLite-backed async conversation storage.

Stores conversations, messages, and metadata in a local SQLite database.
Designed for async FastAPI integration via aiosqlite, with a sync wrapper
for use in non-async agent code.

Usage (async):
    >>> from versaai.memory.persistence import ConversationDB
    >>> db = ConversationDB()
    >>> await db.initialize()
    >>> conv_id = await db.create_conversation(title="My Chat")
    >>> await db.add_message(conv_id, role="user", content="Hello!")
    >>> await db.add_message(conv_id, role="assistant", content="Hi there!")
    >>> messages = await db.get_messages(conv_id)
    >>> conversations = await db.list_conversations()

Usage (sync):
    >>> db = ConversationDB()
    >>> db.initialize_sync()
    >>> conv_id = db.create_conversation_sync(title="My Chat")
    >>> db.add_message_sync(conv_id, "user", "Hello!")
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from versaai.config import settings

logger = logging.getLogger(__name__)


class ConversationDB:
    """
    Async-first SQLite conversation store.

    Tables:
        conversations: id, title, created_at, updated_at, metadata_json
        messages:      id, conversation_id, role, content, created_at, metadata_json

    Thread safety: aiosqlite provides connection-per-coroutine isolation.
    Sync wrappers run a one-shot event loop for agent code.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self._db_path = Path(db_path)
        else:
            base = Path(os.path.expanduser(settings.memory.persistence_dir))
            self._db_path = base / "conversations.db"

        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = None  # aiosqlite connection (lazy)

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    async def initialize(self):
        """Create tables if they don't exist."""
        import aiosqlite

        self._conn = await aiosqlite.connect(str(self._db_path))
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")

        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id          TEXT PRIMARY KEY,
                title       TEXT NOT NULL DEFAULT '',
                created_at  REAL NOT NULL,
                updated_at  REAL NOT NULL,
                metadata    TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS messages (
                id              TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role            TEXT NOT NULL,
                content         TEXT NOT NULL,
                created_at      REAL NOT NULL,
                metadata        TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY (conversation_id)
                    REFERENCES conversations(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conv
                ON messages(conversation_id, created_at);
        """)
        await self._conn.commit()
        logger.info("ConversationDB initialized at %s", self._db_path)

    def initialize_sync(self):
        """Sync wrapper for initialize()."""
        self._run_sync(self.initialize())

    async def _ensure_conn(self):
        if self._conn is None:
            await self.initialize()

    # ------------------------------------------------------------------
    # Conversations
    # ------------------------------------------------------------------

    async def create_conversation(
        self,
        title: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None,
    ) -> str:
        """Create a new conversation; returns its ID."""
        await self._ensure_conn()
        cid = conversation_id or uuid.uuid4().hex
        now = time.time()
        await self._conn.execute(
            "INSERT INTO conversations (id, title, created_at, updated_at, metadata) "
            "VALUES (?, ?, ?, ?, ?)",
            (cid, title, now, now, json.dumps(metadata or {})),
        )
        await self._conn.commit()
        logger.debug("Created conversation %s", cid)
        return cid

    def create_conversation_sync(self, **kw) -> str:
        return self._run_sync(self.create_conversation(**kw))

    async def list_conversations(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List conversations ordered by most recently updated."""
        await self._ensure_conn()
        cursor = await self._conn.execute(
            "SELECT id, title, created_at, updated_at, metadata "
            "FROM conversations ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": r[0],
                "title": r[1],
                "created_at": r[2],
                "updated_at": r[3],
                "metadata": json.loads(r[4]) if r[4] else {},
            }
            for r in rows
        ]

    def list_conversations_sync(self, **kw) -> List[Dict[str, Any]]:
        return self._run_sync(self.list_conversations(**kw))

    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get a single conversation by ID."""
        await self._ensure_conn()
        cursor = await self._conn.execute(
            "SELECT id, title, created_at, updated_at, metadata "
            "FROM conversations WHERE id = ?",
            (conversation_id,),
        )
        r = await cursor.fetchone()
        if not r:
            return None
        return {
            "id": r[0],
            "title": r[1],
            "created_at": r[2],
            "updated_at": r[3],
            "metadata": json.loads(r[4]) if r[4] else {},
        }

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and its messages."""
        await self._ensure_conn()
        cursor = await self._conn.execute(
            "DELETE FROM conversations WHERE id = ?", (conversation_id,)
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    async def update_conversation_title(
        self, conversation_id: str, title: str,
    ) -> None:
        """Set the title of an existing conversation."""
        await self._ensure_conn()
        await self._conn.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            (title, time.time(), conversation_id),
        )
        await self._conn.commit()

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        message_id: Optional[str] = None,
    ) -> str:
        """Add a message to a conversation; returns message ID."""
        await self._ensure_conn()
        mid = message_id or uuid.uuid4().hex
        now = time.time()
        await self._conn.execute(
            "INSERT INTO messages (id, conversation_id, role, content, created_at, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (mid, conversation_id, role, content, now, json.dumps(metadata or {})),
        )
        # Touch conversation updated_at
        await self._conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id),
        )
        await self._conn.commit()
        return mid

    def add_message_sync(self, conversation_id: str, role: str, content: str, **kw) -> str:
        return self._run_sync(self.add_message(conversation_id, role, content, **kw))

    async def get_messages(
        self,
        conversation_id: str,
        limit: int = 200,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get messages for a conversation, ordered by creation time."""
        await self._ensure_conn()
        cursor = await self._conn.execute(
            "SELECT id, role, content, created_at, metadata "
            "FROM messages WHERE conversation_id = ? "
            "ORDER BY created_at ASC LIMIT ? OFFSET ?",
            (conversation_id, limit, offset),
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": r[0],
                "role": r[1],
                "content": r[2],
                "created_at": r[3],
                "metadata": json.loads(r[4]) if r[4] else {},
            }
            for r in rows
        ]

    def get_messages_sync(self, conversation_id: str, **kw) -> List[Dict[str, Any]]:
        return self._run_sync(self.get_messages(conversation_id, **kw))

    async def count_messages(self, conversation_id: str) -> int:
        await self._ensure_conn()
        cursor = await self._conn.execute(
            "SELECT COUNT(*) FROM messages WHERE conversation_id = ?",
            (conversation_id,),
        )
        row = await cursor.fetchone()
        return row[0] if row else 0

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search_messages(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Full-text search across messages (SQLite LIKE)."""
        await self._ensure_conn()
        pattern = f"%{query}%"
        if conversation_id:
            cursor = await self._conn.execute(
                "SELECT m.id, m.conversation_id, m.role, m.content, m.created_at, m.metadata "
                "FROM messages m WHERE m.conversation_id = ? AND m.content LIKE ? "
                "ORDER BY m.created_at DESC LIMIT ?",
                (conversation_id, pattern, limit),
            )
        else:
            cursor = await self._conn.execute(
                "SELECT m.id, m.conversation_id, m.role, m.content, m.created_at, m.metadata "
                "FROM messages m WHERE m.content LIKE ? "
                "ORDER BY m.created_at DESC LIMIT ?",
                (pattern, limit),
            )
        rows = await cursor.fetchall()
        return [
            {
                "id": r[0],
                "conversation_id": r[1],
                "role": r[2],
                "content": r[3],
                "created_at": r[4],
                "metadata": json.loads(r[5]) if r[5] else {},
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    async def stats(self) -> Dict[str, Any]:
        await self._ensure_conn()
        conv_cursor = await self._conn.execute("SELECT COUNT(*) FROM conversations")
        msg_cursor = await self._conn.execute("SELECT COUNT(*) FROM messages")
        conv_count = (await conv_cursor.fetchone())[0]
        msg_count = (await msg_cursor.fetchone())[0]
        return {
            "db_path": str(self._db_path),
            "conversations": conv_count,
            "messages": msg_count,
        }

    def stats_sync(self) -> Dict[str, Any]:
        return self._run_sync(self.stats())

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None

    def close_sync(self):
        self._run_sync(self.close())

    # ------------------------------------------------------------------
    # Sync helper
    # ------------------------------------------------------------------

    @staticmethod
    def _run_sync(coro):
        """Run an async coroutine synchronously.

        If an event loop is already running (e.g., inside FastAPI/uvicorn),
        fall back to creating a new loop in a separate thread.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result(timeout=30)
        else:
            return asyncio.run(coro)
