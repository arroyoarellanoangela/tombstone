"""Stage 5 — Verifier. Trusts nothing upstream.

For every Claim in a DealRecord, re-fetches the cited source_url, reduces it
to visible text the same way Research does (html_to_text — see
utils/fetch.py), and checks the verbatim_quote appears via literal
substring match —
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
from src.utils.fetch import BlockedByAllowlist, Fetcher, fetch, html_to_text

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


# The brief is explicit that "adviser" means the financial (M&A) adviser —
# not legal, tax, or technical due diligence. A quote like "Clifford Chance
# advised Acme on the transaction" passes the substring check honestly: the
# text really is on the page. It just doesn't support the claim being made,
# because Clifford Chance is a law firm. Presence and support are different
# questions, and the substring match only answers the first.
#
# This stays deterministic rather than becoming a second LLM opinion: the
# wrong-adviser-type case has a checkable signature in the quote itself, and
# the whole reason this stage is trustworthy is that a hallucination cannot
# talk its way past it. A rejection here can only ever lose the claim to
# not_found — nothing in this module can author a replacement value.
_NON_FINANCIAL_ADVISER_MARKERS = (
    "legal advis",
    "legal counsel",
    "law firm",
    "counsel to",
    "tax advis",
    "due diligence",
)


def _adviser_quote_is_wrong_type(claim: Claim) -> bool:
    """True when an adviser quote names a legal/tax/DD adviser, not an M&A one."""
    if not claim.verbatim_quote:
        return False
    quote = claim.verbatim_quote.lower()
    if any(marker in quote for marker in _NON_FINANCIAL_ADVISER_MARKERS):
        # An explicit "financial adviser" in the same sentence outranks the
        # marker — releases naming both sides ("X acted as financial adviser
        # and Y as legal counsel") are common and shouldn't be thrown away.
        return "financial advis" not in quote
    return False


async def _fetch_sources(
    record: DealRecord, fetcher: Fetcher
) -> tuple[dict[str, str | None], set[str]]:
    """One fetch per distinct source_url on the record, not one per claim.

    Also returns the URLs the compliance gate refused. Both cases leave the
    claim unverifiable, but only one of them is worth retrying: a network
    blip may well succeed on a second pass, whereas a blocked domain will be
    blocked identically every time, forever.
    """
    urls = {
        getattr(record, field).source_url for field in _FIELDS if getattr(record, field).source_url
    }
    pages: dict[str, str | None] = {}
    blocked: set[str] = set()
    for url in urls:
        try:
            # Same html_to_text() view Research quoted from — matching a
            # quote against raw HTML would fail on whitespace it never saw
            # (newlines/indentation collapsed differently across tag
            # boundaries), false-downgrading correct claims to not_found.
            pages[url] = html_to_text(await fetcher(url))
        except BlockedByAllowlist as exc:
            logger.warning("Verifier may not re-fetch %s: %s", url, exc)
            pages[url] = None
            blocked.add(url)
        except Exception as exc:  # noqa: BLE001 — any fetch failure means "can't verify"
            logger.warning("Verifier could not re-fetch %s: %s", url, exc)
            pages[url] = None
    return pages, blocked


async def verify(
    record: DealRecord, round_number: int, fetcher: Fetcher = fetch
) -> VerificationResult:
    """Re-fetch and quote-match every claim in `record`.

    `fetcher` defaults to the real allowlist-gated fetch; tests inject a
    fake that returns canned page text, so this runs with no network.
    """
    pages, blocked = await _fetch_sources(record, fetcher)
    conflicts: list[str] = []
    # Conflicts a fresh Research pass could plausibly resolve. A blocked
    # domain or a wrong-type adviser is settled, not unlucky — bouncing on
    # those spends the client's key on a retry with a foregone conclusion.
    retryable_conflicts = 0
    updated: dict[str, Claim] = {}

    for field in _FIELDS:
        claim = getattr(record, field)

        if claim.status == ClaimStatus.NOT_FOUND:
            updated[field] = claim
            continue

        page_text = pages.get(claim.source_url) if claim.source_url else None
        if page_text is None:
            if claim.source_url in blocked:
                conflicts.append(
                    f"{field}: source is outside the compliance allowlist and cannot be "
                    "re-fetched to verify, downgraded to not_found"
                )
            else:
                conflicts.append(
                    f"{field}: source could not be re-fetched, downgraded to not_found"
                )
                retryable_conflicts += 1
            updated[field] = Claim(field=field, status=ClaimStatus.NOT_FOUND)
            continue

        if not _quote_present(page_text, claim):
            conflicts.append(
                f"{field}: quote not found verbatim in re-fetched source, downgraded to not_found"
            )
            retryable_conflicts += 1
            updated[field] = Claim(field=field, status=ClaimStatus.NOT_FOUND)
            continue

        if field == "adviser" and _adviser_quote_is_wrong_type(claim):
            conflicts.append(
                "adviser: quote names a legal/tax/due-diligence adviser, not the "
                "financial (M&A) adviser the brief asks for — downgraded to not_found"
            )
            updated[field] = Claim(field=field, status=ClaimStatus.NOT_FOUND)
            continue

        updated[field] = claim.model_copy(update={"verified": True})

    # Accumulate rather than replace: a bounce-back re-verification produces
    # a fresh record, and the earlier round's rejections are part of the
    # audit trail for this deal, not superseded by the retry's.
    verified_record = record.model_copy(
        update={**updated, "conflicts": record.conflicts + conflicts}
    )
    needs_rework = retryable_conflicts > 0 and round_number < settings.max_verification_rounds

    return VerificationResult(
        record=verified_record, needs_rework=needs_rework, conflicts=conflicts
    )
