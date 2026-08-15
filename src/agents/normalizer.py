"""Stage 2 — Normalizer. Mostly deterministic code, not an LLM agent.

Collapses duplicate DealCandidates (the same deal reported by several
outlets) into one canonical deal_id, applies the tracking window filter,
and applies the acquisition definition from domain.deal_definition —
config, not prompt text, so it's testable and auditable.
"""

from src.domain.models import DealCandidate


def normalize(candidates: list[DealCandidate]) -> list[DealCandidate]:
    """Dedup + window-filter + apply the acquisition definition.

    Candidates excluded by the acquisition definition (minority stakes,
    intra-portfolio mergers) are logged to data/omissions.json, not
    silently dropped.
    """
    raise NotImplementedError
