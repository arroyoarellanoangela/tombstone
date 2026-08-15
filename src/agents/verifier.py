"""Stage 5 — Verifier. Trusts nothing upstream.

For every Claim in a DealRecord, re-fetches the cited source_url and checks
the verbatim_quote appears in the page content via literal substring match —
deterministic, not model-graded, and not an LLM call at all. A hallucinated
quote does not exist on any real page, so this check cannot be talked past
the way a second LLM opinion could be. Claims that fail are downgraded to
NOT_FOUND, not silently kept.

Every downgrade is recorded in `conflicts` — surfaced on the DealRecord,
never silently resolved. Can bounce the record back to Research (the
orchestrator decides based on `needs_rework`), capped at
MAX_VERIFICATION_ROUNDS to bound cost.
"""

import logging

from src.config import settings
from src.domain.models import Claim, ClaimStatus, DealRecord
from src.utils.fetch import Fetcher, fetch

logger = logging.getLogger(__name__)

_FIELDS = [
    "acquirer",
    "target",
    "date_announced",
    "target_description",
    "geography",
    "adviser",
    "purchase_price",
]


class VerificationResult:
    def __init__(self, record: DealRecord, needs_rework: bool, conflicts: list[str]):
        self.record = record
        self.needs_rework = needs_rework
        self.conflicts = conflicts


def _quote_present(source_text: str, claim: Claim) -> bool:
    if not claim.verbatim_quote:
        return False
    return claim.verbatim_quote.strip() in source_text


async def _fetch_sources(record: DealRecord, fetcher: Fetcher) -> dict[str, str | None]:
    """One fetch per distinct source_url on the record, not one per claim."""
    urls = {
        getattr(record, field).source_url for field in _FIELDS if getattr(record, field).source_url
    }
    pages: dict[str, str | None] = {}
    for url in urls:
        try:
            pages[url] = await fetcher(url)
        except Exception as exc:  # noqa: BLE001 — any fetch failure means "can't verify"
            logger.warning("Verifier could not re-fetch %s: %s", url, exc)
            pages[url] = None
    return pages


async def verify(
    record: DealRecord, round_number: int, fetcher: Fetcher = fetch
) -> VerificationResult:
    """Re-fetch and quote-match every claim in `record`.

    `fetcher` defaults to the real allowlist-gated fetch; tests inject a
    fake that returns canned page text, so this runs with no network.
    """
    pages = await _fetch_sources(record, fetcher)
    conflicts: list[str] = []
    updated: dict[str, Claim] = {}

    for field in _FIELDS:
        claim = getattr(record, field)

        if claim.status == ClaimStatus.NOT_FOUND:
            updated[field] = claim
            continue

        page_text = pages.get(claim.source_url) if claim.source_url else None
        if page_text is None:
            conflicts.append(f"{field}: source could not be re-fetched, downgraded to not_found")
            updated[field] = Claim(field=field, status=ClaimStatus.NOT_FOUND)
            continue

        if _quote_present(page_text, claim):
            updated[field] = claim.model_copy(update={"verified": True})
        else:
            conflicts.append(
                f"{field}: quote not found verbatim in re-fetched source, downgraded to not_found"
            )
            updated[field] = Claim(field=field, status=ClaimStatus.NOT_FOUND)

    verified_record = record.model_copy(update=updated)
    needs_rework = bool(conflicts) and round_number < settings.max_verification_rounds

    return VerificationResult(
        record=verified_record, needs_rework=needs_rework, conflicts=conflicts
    )
