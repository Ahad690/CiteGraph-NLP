import aiosqlite
import json
import logging
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from citegraph.models.run import RunResult
from citegraph.config import settings

logger = logging.getLogger(__name__)

class SQLiteStore:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.sqlite_path
        self._db: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

    async def connect(self):
        """Idempotent connect with locking."""
        async with self._lock:
            if not self._db:
                logger.info(f"Connecting to SQLite: {self.db_path}")
                self._db = await aiosqlite.connect(self.db_path)
                self._db.row_factory = aiosqlite.Row
                await self._init_db_locked()

    async def close(self):
        """Safe close with locking."""
        async with self._lock:
            if self._db:
                logger.info("Closing SQLite connection")
                await self._db.close()
                self._db = None

    async def _init_db_locked(self):
        """Internal initialization, assumes lock is held."""
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                error TEXT,
                result_json TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        await self._db.commit()

    async def _execute(self, query: str, params: tuple = (), commit: bool = False) -> Any:
        """Helper to ensure connection and execute query safely under lock."""
        await self.connect()
        async with self._lock:
            if not self._db:
                raise RuntimeError("Database connection closed unexpectedly")
            cursor = await self._db.execute(query, params)
            if commit:
                await self._db.commit()
            return cursor

    async def create_run(self, run_id: str):
        now = datetime.now(timezone.utc).isoformat()
        await self._execute(
            "INSERT INTO runs (run_id, status, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (run_id, "started", now, now),
            commit=True
        )

    async def update_status(self, run_id: str, status: str, error: Optional[str] = None):
        now = datetime.now(timezone.utc).isoformat()
        await self._execute(
            "UPDATE runs SET status = ?, error = ?, updated_at = ? WHERE run_id = ?",
            (status, error, now, run_id),
            commit=True
        )

    async def save_result(self, run_id: str, result: RunResult):
        now = datetime.now(timezone.utc).isoformat()
        await self._execute(
            "UPDATE runs SET status = ?, result_json = ?, updated_at = ? WHERE run_id = ?",
            ("completed", result.model_dump_json(), now, run_id),
            commit=True
        )

    async def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        await self.connect()
        async with self._lock:
            if not self._db:
                raise RuntimeError("Database connection closed unexpectedly")
            async with self._db.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
        return None

