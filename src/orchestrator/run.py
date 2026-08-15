"""Entrypoint. Wires discovery -> normalizer -> research -> (adviser_hunter)
-> verifier -> scorer into the pipeline in docs/ARCHITECTURE_NOTE.html, Fig. 2.

Usage (run from the repo root):
    python -m src.orchestrator.run --acquirer volaris
    python -m src.orchestrator.run --all
"""

import argparse
import asyncio

from src.config import settings
from src.orchestrator.budget import RunBudget
from src.orchestrator.cache import Cache


async def run_for_acquirer(acquirer_slug: str, budget: RunBudget, cache: Cache) -> None:
    """One full pass: discovery -> normalize -> [research -> verify]* -> score,
    for a single acquirer. Writes results into data/snapshot_<date>.json.
    """
    raise NotImplementedError


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acquirer", help="Acquirer slug, e.g. 'volaris'")
    parser.add_argument("--all", action="store_true", help="Run every configured acquirer")
    args = parser.parse_args()

    budget = RunBudget(ceiling_usd=settings.run_budget_usd)
    cache = Cache()

    if args.all:
        raise NotImplementedError
    elif args.acquirer:
        asyncio.run(run_for_acquirer(args.acquirer, budget, cache))
    else:
        parser.error("pass --acquirer <slug> or --all")


if __name__ == "__main__":
    main()
