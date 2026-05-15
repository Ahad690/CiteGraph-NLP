import aiosqlite
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from citegraph.models.run import RunResult
from citegraph.config import settings

logger = logging.getLogger(__name__)

class SQLiteStore:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.sqlite_path

    async def _init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    error TEXT,
                    result_json TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            await db.commit()

    async def create_run(self, run_id: str):
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO runs (run_id, status, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (run_id, "started", now, now)
            )
            await db.commit()

    async def update_status(self, run_id: str, status: str, error: Optional[str] = None):
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE runs SET status = ?, error = ?, updated_at = ? WHERE run_id = ?",
                (status, error, now, run_id)
            )
            await db.commit()

    async def save_result(self, run_id: str, result: RunResult):
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE runs SET status = ?, result_json = ?, updated_at = ? WHERE run_id = ?",
                ("completed", result.model_dump_json(), now, run_id)
            )
            await db.commit()

    async def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
        return None
