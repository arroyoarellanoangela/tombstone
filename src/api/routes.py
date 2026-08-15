"""Routes.

GET  /deals       -> the committed snapshot, filterable by acquirer/geography/
                      confidence/price-status (query params)
GET  /omissions   -> data/omissions.json — blocked sources + reasons
POST /runs        -> triggers a live orchestrator run (local/demo use only)
"""

import json
from pathlib import Path

from fastapi import APIRouter, Query

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

router = APIRouter()


@router.get("/deals")
def list_deals(
    acquirer: str | None = Query(default=None),
    min_confidence: float | None = Query(default=None),
) -> list[dict]:
    raise NotImplementedError


@router.get("/omissions")
def list_omissions() -> list[dict]:
    path = DATA_DIR / "omissions.json"
    if not path.exists():
        return []
    return json.loads(path.read_text())


@router.post("/runs")
def trigger_run(acquirer: str) -> dict:
    """Local/demo use only — see module docstring. Not exposed in the
    static public deployment.
    """
    raise NotImplementedError
