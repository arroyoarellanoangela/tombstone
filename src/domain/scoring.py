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


_FIELDS = [
    "acquirer",
    "target",
    "date_announced",
    "target_description",
    "geography",
    "adviser",
    "purchase_price",
]

_DEFAULT_TIER = "aggregator"


def score_deal(record: DealRecord, source_tiers: dict[str, str]) -> float:
    """Aggregate confidence for a DealRecord.

    completeness = fraction of the 7 fields with status != NOT_FOUND —
    what Research/Adviser Hunter managed to find, verified or not yet.
    verifier_pass_rate = fraction of fields the Verifier actually confirmed
    (claim.verified is True) — a stricter, later-stage signal than
    completeness. The two diverge on a record that hasn't been through the
    Verifier yet (completeness > 0, verifier_pass_rate == 0), which is
    intentional: an unverified extraction shouldn't score as trustworthy as
    a confirmed one, even though both "found" something.

    `source_tiers` maps field name -> tier string (see SOURCE_TIER_WEIGHTS);
    a field with no entry defaults to the lowest tier, "aggregator".
    """
    claims: dict[str, Claim] = {f: getattr(record, f) for f in _FIELDS}
    passing_fields = [f for f in _FIELDS if _is_pass(claims[f])]
    completeness = len(passing_fields) / len(_FIELDS)

    verifier_pass_rate = sum(claims[f].verified for f in _FIELDS) / len(_FIELDS)

    if passing_fields:
        tier_scores = [
            SOURCE_TIER_WEIGHTS.get(
                source_tiers.get(f, _DEFAULT_TIER), SOURCE_TIER_WEIGHTS[_DEFAULT_TIER]
            )
            for f in passing_fields
        ]
        avg_source_tier = sum(tier_scores) / len(tier_scores)
    else:
        avg_source_tier = 0.0

    corroboration = min(len(set(record.source_urls)) / 2, 1.0)

    score = (
        RUBRIC_WEIGHTS["source_tier"] * avg_source_tier
        + RUBRIC_WEIGHTS["corroboration"] * corroboration
        + RUBRIC_WEIGHTS["verifier_pass_rate"] * verifier_pass_rate
        + RUBRIC_WEIGHTS["completeness"] * completeness
    )
    return round(score, 4)


def _is_pass(claim: Claim) -> bool:
    return claim.status in (ClaimStatus.VERIFIED, ClaimStatus.EXPLICITLY_UNDISCLOSED)
