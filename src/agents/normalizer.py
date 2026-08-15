"""Stage 2 — Normalizer. Mostly deterministic code, not an LLM agent.

Collapses duplicate DealCandidates (the same deal reported by several
outlets) into one canonical deal_id, applies the tracking window filter,
and applies the acquisition definition from domain.deal_definition —
config, not prompt text, so it's testable and auditable.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from src.domain.deal_definition import classify, is_in_scope
from src.domain.models import DealCandidate, Omission


@dataclass
class NormalizeResult:
    kept: list[DealCandidate] = field(default_factory=list)
    omitted: list[Omission] = field(default_factory=list)


def normalize(candidates: list[DealCandidate], window_days: int, now: datetime | None = None) -> NormalizeResult:
    """Dedup + window-filter + apply the acquisition definition.

    Candidates excluded by the acquisition definition (minority stakes,
    intra-portfolio mergers) or falling outside the tracking window are
    recorded as Omissions, not silently dropped.
    """
    now = now or datetime.now(UTC)
    cutoff = now - timedelta(days=window_days)

    result = NormalizeResult()
    seen_urls: set[str] = set()

    for candidate in candidates:
        if candidate.url in seen_urls:
            continue
        seen_urls.add(candidate.url)

        if candidate.published_at is not None and candidate.published_at < cutoff:
            result.omitted.append(
                Omission(
                    url=candidate.url,
                    reason=f"published {candidate.published_at.date()}, outside the "
                    f"{window_days}-day tracking window",
                    stage="window",
                )
            )
            continue

        kind = classify(candidate.snippet)
        if not is_in_scope(kind):
            result.omitted.append(
                Omission(
                    url=candidate.url,
                    reason=f"classified as {kind.value}, not a majority acquisition",
                    stage="deal_definition",
                )
            )
            continue

        result.kept.append(candidate)

    return result
