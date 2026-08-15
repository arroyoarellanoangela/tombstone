"""SQLite cache keyed by (agent_name, input_hash).

Keeps repeat runs cheap against the client's prepaid key, and makes the
Verifier<->Research bounce loop cost-bounded rather than open-ended — a
retried step with unchanged input is a cache hit, not a new LLM call.

data/cache.db is gitignored — it's local run state, not a deliverable.
Only data/snapshot_*.json and data/omissions.json are committed.
"""

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "cache.db"

_INSERT = (
    "INSERT OR REPLACE INTO cache (agent_name, input_hash, result, created_at) "
    "VALUES (?, ?, ?, ?)"
)


def _input_hash(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, default=str).encode()
    return hashlib.sha256(blob).hexdigest()


class Cache:
    def __init__(self, db_path: Path = DB_PATH):
        self._db_path = db_path
        self._init_schema()

    def _init_schema(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    agent_name TEXT NOT NULL,
                    input_hash TEXT NOT NULL,
                    result TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (agent_name, input_hash)
                )
                """
            )

    def get(self, agent_name: str, payload: Any) -> Any | None:
        input_hash = _input_hash(payload)
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT result FROM cache WHERE agent_name = ? AND input_hash = ?",
                (agent_name, input_hash),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def set(self, agent_name: str, payload: Any, result: Any) -> None:
        input_hash = _input_hash(payload)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                _INSERT,
                (
                    agent_name,
                    input_hash,
                    json.dumps(result, default=str),
                    datetime.now(UTC).isoformat(),
                ),
            )
