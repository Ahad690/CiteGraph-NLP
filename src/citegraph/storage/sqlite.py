import sqlite3
import json
import logging
import threading
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from citegraph.models.run import RunResult
from citegraph.config import settings

logger = logging.getLogger(__name__)

class SQLiteStore:
    _lock = threading.Lock()

    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.sqlite_path
        self._init_db()

    def _get_connection(self):
        # Using a fresh connection per call is fine if we have a lock for writes
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_db(self):
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS runs (
                        run_id TEXT PRIMARY KEY,
                        status TEXT NOT NULL,
                        error TEXT,
                        result_json TEXT,
                        created_at TEXT,
                        updated_at TEXT
                    )
                """)
                conn.commit()

    def create_run(self, run_id: str):
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT INTO runs (run_id, status, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    (run_id, "started", now, now)
                )
                conn.commit()

    def update_status(self, run_id: str, status: str, error: Optional[str] = None):
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE runs SET status = ?, error = ?, updated_at = ? WHERE run_id = ?",
                    (status, error, now, run_id)
                )
                conn.commit()

    def save_result(self, run_id: str, result: RunResult):
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE runs SET status = ?, result_json = ?, updated_at = ? WHERE run_id = ?",
                    ("completed", result.model_dump_json(), now, run_id)
                )
                conn.commit()

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None
