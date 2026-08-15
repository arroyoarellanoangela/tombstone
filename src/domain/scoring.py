"""Confidence scoring — a deterministic rubric, never an LLM-produced number.

An LLM-reported confidence score would itself be an unverified claim. This
function is the only place a DealRecord's `confidence` is set, and it is a
pure function of Verifier outcomes: reviewable in code review, reproducible
from the same inputs, independent of any model's behavior.
"""

from src.domain.models import Claim, ClaimStatus, DealRecord

# Source tiers — higher trust sources score closer to 1.0. Config, not code,
# so it stays reviewable independent of the scoring logic below.
SOURCE_TIER_WEIGHTS: dict[str, float] = {
    "regulatory_filing": 1.0,
    "acquirer_press_release": 0.9,
    "adviser_tombstone": 0.85,
    "sector_press": 0.6,
    "aggregator": 0.4,
}

RUBRIC_WEIGHTS = {
    "source_tier": 0.35,
    "corroboration": 0.25,
    "verifier_pass_rate": 0.25,
    "completeness": 0.15,
}


def score_claim(claim: Claim, source_tier: str, corroborating_domains: int) -> float:
    """Per-field confidence, folded into the DealRecord-level score by `score_deal`."""
    raise NotImplementedError


def score_deal(record: DealRecord, source_tiers: dict[str, str]) -> float:
    """Aggregate confidence for a DealRecord.

    completeness = fraction of fields with status != NOT_FOUND.
    verifier_pass_rate = fraction of claims with status == VERIFIED among
    those that carry a value (EXPLICITLY_UNDISCLOSED claims count as passes —
    they are correctly-handled facts, not gaps).
    """
    raise NotImplementedError


def _is_pass(claim: Claim) -> bool:
    return claim.status in (ClaimStatus.VERIFIED, ClaimStatus.EXPLICITLY_UNDISCLOSED)
