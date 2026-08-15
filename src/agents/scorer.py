"""Stage 6 — Scorer. Thin wrapper around domain.scoring — deterministic,
no LLM call. Kept as its own pipeline stage (rather than inlined in the
Verifier) so the orchestrator's stage list matches the architecture
diagram one-to-one, and scoring can be re-run standalone against a cached
DealRecord without re-verifying it.
"""

from src.domain.models import DealRecord
from src.domain.scoring import score_deal


def run(record: DealRecord, source_tiers: dict[str, str]) -> DealRecord:
    record.confidence = score_deal(record, source_tiers)
    return record
