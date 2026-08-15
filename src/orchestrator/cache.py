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
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "cache.db"


def _input_hash(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, default=str).encode()
    return hashlib.sha256(blob).hexdigest()


class Cache:
    def __init__(self, db_path: Path = DB_PATH):
        self._db_path = db_path
        self._init_schema()

    def _init_schema(self) -> None:
        raise NotImplementedError

    def get(self, agent_name: str, payload: Any) -> Any | None:
        raise NotImplementedError

    def set(self, agent_name: str, payload: Any, result: Any) -> None:
        raise NotImplementedError
