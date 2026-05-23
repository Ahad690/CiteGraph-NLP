import aiosqlite
import json
import logging
import asyncio
import random
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from citegraph.models.run import RunResult
from citegraph.config import settings

logger = logging.getLogger(__name__)


class SQLiteStoreError(RuntimeError):
    """Contextual error raised when an SQLite operation fails after retries
    or hits an unrecoverable exception. Wraps the underlying cause."""

    def __init__(self, message: str, *, query: str = "", original: Optional[BaseException] = None):
        super().__init__(message)
        self.query = query
        self.original = original


class SQLiteStore:
    # Bounded backoff parameters for "database is locked" retries.
    _RETRY_BASE_S = 0.05
    _RETRY_CAP_S = 1.0
    _RETRY_ATTEMPTS = 5

    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.sqlite_path
        self._db: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

    async def connect(self):
        """Idempotent connect with locking."""
        async with self._lock:
            if not self._db:
                logger.info(f"Connecting to SQLite: {self.db_path}")
                if self.db_path != ":memory:":
                    Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
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

    @staticmethod
    def _is_lock_error(exc: BaseException) -> bool:
        """SQLite reports lock contention as OperationalError("database is locked")."""
        return isinstance(exc, aiosqlite.OperationalError) and "database is locked" in str(exc).lower()

    async def _execute(self, query: str, params: tuple = (), commit: bool = False) -> Any:
        """Run a query under the store lock with bounded retries for lock contention.

        Only "database is locked" errors are retried — any other exception (incl.
        non-lock OperationalError, ProgrammingError, IntegrityError) propagates
        immediately wrapped in SQLiteStoreError so callers see the real cause.
        """
        await self.connect()
        last_lock_exc: Optional[BaseException] = None
        for attempt in range(self._RETRY_ATTEMPTS):
            try:
                async with self._lock:
                    if not self._db:
                        raise SQLiteStoreError(
                            "Database connection closed unexpectedly",
                            query=query,
                        )
                    cursor = await self._db.execute(query, params)
                    if commit:
                        await self._db.commit()
                    return cursor
            except BaseException as exc:  # noqa: BLE001 — we re-raise after classifying
                if not self._is_lock_error(exc):
                    # Non-lock failure: surface immediately with context.
                    logger.error(
                        "SQLite execute failed (non-retryable): query=%r err=%s",
                        query, exc,
                    )
                    raise SQLiteStoreError(
                        f"SQLite execute failed: {exc}",
                        query=query, original=exc,
                    ) from exc

                last_lock_exc = exc
                # Exponential backoff with full jitter, capped.
                delay = min(
                    self._RETRY_CAP_S,
                    self._RETRY_BASE_S * (2 ** attempt),
                )
                delay = random.uniform(0, delay)
                logger.warning(
                    "SQLite database is locked; retrying (%s/%s) in %.3fs",
                    attempt + 1, self._RETRY_ATTEMPTS, delay,
                )
                await asyncio.sleep(delay)

        # Retry budget exhausted on lock contention.
        logger.error(
            "SQLite execute exhausted %s retries on lock contention: query=%r",
            self._RETRY_ATTEMPTS, query,
        )
        raise SQLiteStoreError(
            f"SQLite operation failed after {self._RETRY_ATTEMPTS} retries on lock contention",
            query=query, original=last_lock_exc,
        ) from last_lock_exc

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
        """Read a run row. Reads share the same lock/retry policy as writes so
        a concurrent writer holding a brief lock does not surface as an unhandled
        OperationalError on the read path."""
        await self.connect()
        last_lock_exc: Optional[BaseException] = None
        for attempt in range(self._RETRY_ATTEMPTS):
            try:
                async with self._lock:
                    if not self._db:
                        raise SQLiteStoreError(
                            "Database connection closed unexpectedly",
                            query="SELECT * FROM runs WHERE run_id = ?",
                        )
                    async with self._db.execute(
                        "SELECT * FROM runs WHERE run_id = ?", (run_id,)
                    ) as cursor:
                        row = await cursor.fetchone()
                        return dict(row) if row else None
            except BaseException as exc:  # noqa: BLE001
                if not self._is_lock_error(exc):
                    logger.error("SQLite read failed: run_id=%s err=%s", run_id, exc)
                    raise SQLiteStoreError(
                        f"SQLite read failed: {exc}",
                        query="SELECT * FROM runs WHERE run_id = ?",
                        original=exc,
                    ) from exc

                last_lock_exc = exc
                delay = min(
                    self._RETRY_CAP_S,
                    self._RETRY_BASE_S * (2 ** attempt),
                )
                delay = random.uniform(0, delay)
                await asyncio.sleep(delay)

        raise SQLiteStoreError(
            f"SQLite read failed after {self._RETRY_ATTEMPTS} retries on lock contention",
            query="SELECT * FROM runs WHERE run_id = ?",
            original=last_lock_exc,
        ) from last_lock_exc
