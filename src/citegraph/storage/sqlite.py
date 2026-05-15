import sqlite3
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from citegraph.models.run import RunResult
from citegraph.config import settings

logger = logging.getLogger(__name__)

class SQLiteStore:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.sqlite_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    error TEXT,
                    result_json TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                )
            """)
            conn.commit()

    def create_run(self, run_id: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO runs (run_id, status, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (run_id, "started", datetime.utcnow(), datetime.utcnow())
            )
            conn.commit()

    def update_status(self, run_id: str, status: str, error: Optional[str] = None):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE runs SET status = ?, error = ?, updated_at = ? WHERE run_id = ?",
                (status, error, datetime.utcnow(), run_id)
            )
            conn.commit()

    def save_result(self, run_id: str, result: RunResult):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE runs SET status = ?, result_json = ?, updated_at = ? WHERE run_id = ?",
                ("completed", result.model_dump_json(), datetime.utcnow(), run_id)
            )
            conn.commit()

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
            row = cursor.fetchone()
            if row:
                data = dict(row)
                if data["result_json"]:
                    data["result"] = json.loads(data["result_json"])
                return data
        return None
