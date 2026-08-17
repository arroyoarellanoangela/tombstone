"""Routes.

GET  /deals       -> latest committed snapshot, filterable by acquirer /
                      minimum confidence / price-disclosure status
GET  /omissions   -> data/omissions.json — excluded sources + reasons
POST /runs        -> triggers a live orchestrator run (local/demo use only)
"""

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

router = APIRouter()

Deal = dict[str, Any]


def _latest_snapshot() -> list[Deal]:
    snapshots = sorted(DATA_DIR.glob("snapshot_*.json"))
    if not snapshots:
        return []
    deals: list[Deal] = json.loads(snapshots[-1].read_text(encoding="utf-8"))
    return deals


@router.get("/deals")
def list_deals(
    acquirer: str | None = Query(default=None, description="Filter by acquirer slug prefix"),
    min_confidence: float | None = Query(default=None, ge=0.0, le=1.0),
    price_status: str | None = Query(
        default=None, description="verified | explicitly_undisclosed | not_found"
    ),
) -> list[Deal]:
    deals = _latest_snapshot()
    if acquirer:
        deals = [d for d in deals if d["deal_id"].startswith(f"{acquirer}-")]
    if min_confidence is not None:
        deals = [d for d in deals if (d.get("confidence") or 0.0) >= min_confidence]
    if price_status:
        deals = [d for d in deals if d["purchase_price"]["status"] == price_status]
    return deals


@router.get("/omissions")
def list_omissions() -> list[Deal]:
    path = DATA_DIR / "omissions.json"
    if not path.exists():
        return []
    omissions: list[Deal] = json.loads(path.read_text(encoding="utf-8"))
    return omissions


@router.post("/runs")
async def trigger_run(acquirer: str) -> dict[str, Any]:
    """Local/demo use only — spends against the configured API key. Never
    exposed publicly; the public deployment is the static frontend reading
    data/*.json with no API behind it (see CLAUDE.md).
    """
    from src.config import settings
    from src.orchestrator.budget import RunBudget
    from src.orchestrator.cache import Cache
    from src.orchestrator.run import run_for_acquirer

    try:
        records = await run_for_acquirer(
            acquirer, RunBudget(ceiling_usd=settings.run_budget_usd), Cache()
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail=f"No profile for acquirer '{acquirer}'"
        ) from exc
    return {"acquirer": acquirer, "deals": len(records)}
