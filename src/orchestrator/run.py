"""Entrypoint. Wires discovery -> normalizer -> research -> (adviser_hunter)
-> verifier -> scorer into the pipeline in docs/ARCHITECTURE_NOTE.html, Fig. 2.

Usage (run from the repo root):
    python -m src.orchestrator.run --acquirer volaris
    python -m src.orchestrator.run --all
"""

import argparse
import asyncio
import json
import logging
from datetime import UTC, date, datetime
from pathlib import Path

import yaml

from src.agents import adviser_hunter, discovery, normalizer, research, verifier
from src.agents.research import _needs_adviser_hunt
from src.agents.scorer import run as score_run
from src.config import settings
from src.domain.models import AcquirerProfile, DealRecord, Omission
from src.orchestrator.budget import RunBudget
from src.orchestrator.cache import Cache

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILES_DIR = REPO_ROOT / "sources" / "profiles"
DATA_DIR = REPO_ROOT / "data"

_FIELDS = [
    "acquirer",
    "target",
    "date_announced",
    "target_description",
    "geography",
    "adviser",
    "purchase_price",
]


def _load_profile(acquirer_slug: str) -> AcquirerProfile:
    path = PROFILES_DIR / f"{acquirer_slug}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"No profile at {path} — add one under sources/profiles/")
    return AcquirerProfile(**yaml.safe_load(path.read_text(encoding="utf-8")))


def _source_tiers(profile: AcquirerProfile, record: DealRecord) -> dict[str, str]:
    base_tier = "regulatory_filing" if profile.source_type == "regulatory_filing" else "acquirer_press_release"
    tiers = {field: base_tier for field in _FIELDS}
    if record.adviser.source_url and record.adviser.source_url not in record.source_urls:
        tiers["adviser"] = "adviser_tombstone"
    return tiers


def _write_snapshot(records: list[DealRecord]) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"snapshot_{date.today().isoformat()}.json"
    existing: list[dict] = []
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
    existing_ids = {r["deal_id"] for r in existing}
    new_records = [json.loads(r.model_dump_json()) for r in records if r.deal_id not in existing_ids]
    path.write_text(json.dumps(existing + new_records, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _append_omissions(omissions: list[Omission]) -> None:
    if not omissions:
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / "omissions.json"
    existing: list[dict] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    existing.extend(json.loads(o.model_dump_json()) for o in omissions)
    path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")


async def run_for_acquirer(acquirer_slug: str, budget: RunBudget, cache: Cache) -> list[DealRecord]:
    """One full pass: discovery -> normalize -> [research -> verify]* -> score,
    for a single acquirer. Writes results into data/snapshot_<date>.json.
    """
    profile = _load_profile(acquirer_slug)
    logger.info("Discovery: %s", profile.name)
    candidates = await discovery.run(profile, settings.tracking_window_days)

    norm_result = normalizer.normalize(candidates, settings.tracking_window_days)
    _append_omissions(norm_result.omitted)
    logger.info(
        "Normalizer: %d kept, %d omitted", len(norm_result.kept), len(norm_result.omitted)
    )

    records: list[DealRecord] = []
    for candidate in norm_result.kept:
        logger.info("Research: %s", candidate.url)
        record = await research.run(
            candidate, acquirer_name=profile.name, language=profile.primary_language
        )

        if _needs_adviser_hunt(record.adviser):
            logger.info("Adviser Hunter: %s x %s", profile.name, record.target.value)
            record.adviser = await adviser_hunter.run(record)

        result = await verifier.verify(record, round_number=1)
        record = result.record
        if result.conflicts:
            logger.info("Verifier flagged %s: %s", record.deal_id, result.conflicts)

        record = score_run(record, source_tiers=_source_tiers(profile, record))
        records.append(record)

    _write_snapshot(records)
    return records


async def run_all(budget: RunBudget, cache: Cache) -> list[DealRecord]:
    all_records: list[DealRecord] = []
    for path in sorted(PROFILES_DIR.glob("*.yaml")):
        all_records.extend(await run_for_acquirer(path.stem, budget, cache))
    return all_records


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acquirer", help="Acquirer slug, e.g. 'volaris'")
    parser.add_argument("--all", action="store_true", help="Run every configured acquirer")
    args = parser.parse_args()

    budget = RunBudget(ceiling_usd=settings.run_budget_usd)
    cache = Cache()

    if args.all:
        asyncio.run(run_all(budget, cache))
    elif args.acquirer:
        asyncio.run(run_for_acquirer(args.acquirer, budget, cache))
    else:
        parser.error("pass --acquirer <slug> or --all")


if __name__ == "__main__":
    main()
