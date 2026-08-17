"""Entrypoint. Wires discovery -> normalizer -> research -> (adviser_hunter)
-> verifier -> scorer into the pipeline in docs/ARCHITECTURE_NOTE.html, Fig. 2.

Usage (run from the repo root):
    python -m src.orchestrator.run --acquirer volaris
    python -m src.orchestrator.run --all

Control flow lives here, deterministically — budget ceiling, cache, the
Verifier<->Research bounce loop, parallelism. Agents never decide any of it.
"""

import argparse
import asyncio
import functools
import json
import logging
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from src.agents import adviser_hunter, discovery, normalizer, research, verifier
from src.agents.scorer import run as score_run
from src.config import settings
from src.domain.models import AcquirerProfile, ClaimStatus, DealCandidate, DealRecord, Omission
from src.orchestrator.budget import BudgetExceeded, RunBudget
from src.orchestrator.cache import Cache
from src.utils.llm import AgentCaller, run_agent

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILES_DIR = REPO_ROOT / "sources" / "profiles"
DATA_DIR = REPO_ROOT / "data"

# Each concurrent agent call spawns its own CLI subprocess; more parallelism
# than this buys little and makes the budget ceiling sloppier (calls already
# in flight when the ceiling is hit still complete).
MAX_CONCURRENT_DEALS = 3

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


def _has_no_usable_fields(record: DealRecord) -> bool:
    """True when every field is NOT_FOUND — nothing was extracted at all."""
    return all(getattr(record, field).status == ClaimStatus.NOT_FOUND for field in _FIELDS)


def _source_tiers(profile: AcquirerProfile, record: DealRecord) -> dict[str, str]:
    base_tier = (
        "regulatory_filing"
        if profile.source_type == "regulatory_filing"
        else "acquirer_press_release"
    )
    tiers = {field: base_tier for field in _FIELDS}
    if record.adviser.source_url and record.adviser.source_url not in record.source_urls:
        tiers["adviser"] = "adviser_tombstone"
    return tiers


def _write_snapshot(records: list[DealRecord]) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"snapshot_{date.today().isoformat()}.json"
    existing: list[dict[str, Any]] = []
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
    existing_ids = {r["deal_id"] for r in existing}
    new_records = [
        json.loads(r.model_dump_json()) for r in records if r.deal_id not in existing_ids
    ]
    path.write_text(
        json.dumps(existing + new_records, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return path


def _append_omissions(omissions: list[Omission]) -> None:
    if not omissions:
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / "omissions.json"
    existing: list[dict[str, Any]] = (
        json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    )
    existing.extend(json.loads(o.model_dump_json()) for o in omissions)
    path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")


async def _discover(
    profile: AcquirerProfile, cache: Cache, agent_caller: AgentCaller
) -> discovery.DiscoveryResult:
    """Discovery, cached per (acquirer, window, day) — re-running the same
    acquirer on the same day is free. Caches the full result, omissions
    included, so a cache hit still discloses what the compliance gate
    excluded rather than only replaying the kept candidates."""
    cache_key = {
        "slug": profile.slug,
        "window": settings.tracking_window_days,
        "day": date.today().isoformat(),
    }
    # A cache file outlives the code that wrote it. An entry from a build
    # before omissions were cached is shaped differently, and crashing on
    # someone else's stale cache is a worse failure than paying to redo one
    # search — so an unrecognised shape is simply a miss.
    if isinstance(hit := cache.get("discovery", cache_key), dict):
        logger.info("Discovery (cache hit): %s", profile.name)
        return discovery.DiscoveryResult(
            candidates=[DealCandidate.model_validate(c) for c in hit["candidates"]],
            omitted=[Omission.model_validate(o) for o in hit["omitted"]],
        )

    logger.info("Discovery: %s", profile.name)
    result = await discovery.run(profile, settings.tracking_window_days, agent_caller=agent_caller)
    cache.set(
        "discovery",
        cache_key,
        {
            "candidates": [json.loads(c.model_dump_json()) for c in result.candidates],
            "omitted": [json.loads(o.model_dump_json()) for o in result.omitted],
        },
    )
    return result


async def _research_deal(
    candidate: DealCandidate,
    profile: AcquirerProfile,
    cache: Cache,
    agent_caller: AgentCaller,
    use_cache: bool = True,
) -> DealRecord:
    """Research, cached per candidate URL. The bounce loop passes
    use_cache=False — a rework retry with the same input must actually
    re-run, or it would just replay the exact output that failed."""
    cache_key = {"url": candidate.url, "acquirer": profile.name}
    if use_cache and (hit := cache.get("research", cache_key)) is not None:
        logger.info("Research (cache hit): %s", candidate.url)
        return DealRecord.model_validate(hit)

    logger.info("Research: %s", candidate.url)
    record = await research.run(
        candidate,
        acquirer_name=profile.name,
        language=profile.primary_language,
        agent_caller=agent_caller,
    )
    cache.set("research", cache_key, json.loads(record.model_dump_json()))
    return record


async def _enrich(
    candidate: DealCandidate,
    profile: AcquirerProfile,
    cache: Cache,
    agent_caller: AgentCaller,
    use_cache: bool,
) -> DealRecord:
    """Research + conditional Adviser Hunter — one unit, so a bounce retry
    redoes both (the hunter's earlier find would otherwise be silently lost
    when Research produces a fresh record)."""
    record = await _research_deal(candidate, profile, cache, agent_caller, use_cache=use_cache)
    if record.adviser.status == ClaimStatus.NOT_FOUND:
        logger.info("Adviser Hunter: %s x %s", profile.name, record.target.value)
        adviser_result = await adviser_hunter.run(record, agent_caller=agent_caller)
        record.adviser = adviser_result.claim
        _append_omissions(adviser_result.omitted)
    return record


async def _process_candidate(
    candidate: DealCandidate,
    profile: AcquirerProfile,
    cache: Cache,
    agent_caller: AgentCaller,
    semaphore: asyncio.Semaphore,
) -> DealRecord:
    """[Research -> Adviser Hunter] -> Verifier, bouncing back to Research
    while verification flags conflicts and the round cap allows it."""
    async with semaphore:
        record = await _enrich(candidate, profile, cache, agent_caller, use_cache=True)

        round_number = 1
        result = await verifier.verify(record, round_number=round_number)
        while result.needs_rework:
            round_number += 1
            logger.info(
                "Verifier bounced %s back to Research (round %d): %s",
                result.record.deal_id,
                round_number,
                result.conflicts,
            )
            record = await _enrich(candidate, profile, cache, agent_caller, use_cache=False)
            result = await verifier.verify(record, round_number=round_number)

        if result.conflicts:
            logger.info("Verifier flagged %s: %s", result.record.deal_id, result.conflicts)

        return score_run(result.record, source_tiers=_source_tiers(profile, result.record))


async def run_for_acquirer(acquirer_slug: str, budget: RunBudget, cache: Cache) -> list[DealRecord]:
    """One full pass: discovery -> normalize -> [research -> verify]* -> score,
    for a single acquirer. Writes results into data/snapshot_<date>.json.

    On BudgetExceeded, stops issuing new agent calls and finishes with what
    completed — partially processed deals surface as not_found fields with
    low confidence, never as fabricated values.
    """
    profile = _load_profile(acquirer_slug)
    agent_caller = functools.partial(run_agent, budget=budget)

    try:
        discovery_result = await _discover(profile, cache, agent_caller)
    except BudgetExceeded as exc:
        logger.warning("Stopping before discovery of %s: %s", profile.name, exc)
        return []

    _append_omissions(discovery_result.omitted)
    norm_result = normalizer.normalize(discovery_result.candidates, settings.tracking_window_days)
    _append_omissions(norm_result.omitted)
    logger.info("Normalizer: %d kept, %d omitted", len(norm_result.kept), len(norm_result.omitted))

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_DEALS)
    outcomes = await asyncio.gather(
        *(
            _process_candidate(candidate, profile, cache, agent_caller, semaphore)
            for candidate in norm_result.kept
        ),
        return_exceptions=True,
    )

    records: list[DealRecord] = []
    failures: list[Omission] = []
    for candidate, outcome in zip(norm_result.kept, outcomes):
        if isinstance(outcome, BudgetExceeded):
            logger.warning(
                "Budget exhausted before %s completed — recorded as omission", candidate.url
            )
            failures.append(
                Omission(url=candidate.url, reason=str(outcome), stage="budget_exhausted")
            )
        elif isinstance(outcome, BaseException):
            logger.error("Deal %s failed: %s", candidate.url, outcome)
            failures.append(
                Omission(url=candidate.url, reason=f"processing failed: {outcome}", stage="error")
            )
        elif _has_no_usable_fields(outcome):
            # Every field came back not_found — the candidate was discovered
            # but nothing could be extracted or verified from it. That's an
            # omission to disclose, not a deal to report: an all-empty row in
            # the snapshot would imply we found a deal and knew nothing about
            # it, when in fact we never confirmed there was one.
            logger.warning("No usable fields for %s — recorded as omission", candidate.url)
            failures.append(
                Omission(
                    url=candidate.url,
                    reason="discovered as a candidate, but no field could be "
                    "extracted and verified",
                    stage="extraction_failed",
                )
            )
        else:
            records.append(outcome)

    _append_omissions(failures)
    _write_snapshot(records)
    logger.info(
        "%s done: %d deal(s), $%.4f spent of $%.2f",
        profile.name,
        len(records),
        budget.spent_usd,
        budget.ceiling_usd,
    )
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
