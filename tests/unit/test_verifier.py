"""Verifier needs no LLM at all — it's pure fetch + substring match. Tests
inject a fake fetcher returning canned page text, same DI pattern as the
other agents.
"""

import pytest

from src.agents import verifier
from src.domain.models import Claim, ClaimStatus, DealRecord

URL = "https://volarisgroup.com/press-room/acme-acquisition"

_NOT_FOUND = Claim(field="_", status=ClaimStatus.NOT_FOUND)


def _record(**overrides) -> DealRecord:
    fields = {
        "acquirer": _NOT_FOUND,
        "target": _NOT_FOUND,
        "date_announced": _NOT_FOUND,
        "target_description": _NOT_FOUND,
        "geography": _NOT_FOUND,
        "adviser": _NOT_FOUND,
        "purchase_price": _NOT_FOUND,
    }
    fields.update(overrides)
    return DealRecord(deal_id="volaris-acme", source_urls=[URL], **fields)


def _fake_fetcher(page_text: str):
    async def _fetch(url: str) -> str:
        return page_text

    return _fetch


def _failing_fetcher():
    async def _fetch(url: str) -> str:
        raise ConnectionError("simulated network failure")

    return _fetch


@pytest.mark.asyncio
async def test_matching_quote_stays_verified():
    record = _record(
        target=Claim(
            field="target",
            status=ClaimStatus.VERIFIED,
            value="Acme Software",
            source_url=URL,
            verbatim_quote="acquired Acme Software",
        )
    )
    result = await verifier.verify(
        record, round_number=1, fetcher=_fake_fetcher("Volaris acquired Acme Software today.")
    )

    assert result.record.target.status == ClaimStatus.VERIFIED
    assert result.record.target.verified is True
    assert result.conflicts == []


@pytest.mark.asyncio
async def test_quote_not_on_page_downgrades_to_not_found():
    record = _record(
        target=Claim(
            field="target",
            status=ClaimStatus.VERIFIED,
            value="Acme Software",
            source_url=URL,
            verbatim_quote="a quote that never appears on the real page",
        )
    )
    result = await verifier.verify(
        record, round_number=1, fetcher=_fake_fetcher("Completely different content.")
    )

    assert result.record.target.status == ClaimStatus.NOT_FOUND
    assert len(result.conflicts) == 1
    assert "target" in result.conflicts[0]


@pytest.mark.asyncio
async def test_not_found_claim_skips_fetch_entirely():
    calls = []

    async def _tracking_fetch(url: str) -> str:
        calls.append(url)
        return "irrelevant"

    record = _record()  # everything NOT_FOUND, no source_urls set on any claim
    result = await verifier.verify(record, round_number=1, fetcher=_tracking_fetch)

    assert calls == []
    assert result.conflicts == []


@pytest.mark.asyncio
async def test_explicitly_undisclosed_with_matching_quote_stays():
    record = _record(
        purchase_price=Claim(
            field="purchase_price",
            status=ClaimStatus.EXPLICITLY_UNDISCLOSED,
            source_url=URL,
            verbatim_quote="terms were not disclosed",
        )
    )
    result = await verifier.verify(
        record,
        round_number=1,
        fetcher=_fake_fetcher("The terms were not disclosed by either party."),
    )

    assert result.record.purchase_price.status == ClaimStatus.EXPLICITLY_UNDISCLOSED


@pytest.mark.asyncio
async def test_fetch_failure_downgrades_claim():
    record = _record(
        target=Claim(
            field="target",
            status=ClaimStatus.VERIFIED,
            value="Acme",
            source_url=URL,
            verbatim_quote="acquired Acme",
        )
    )
    result = await verifier.verify(record, round_number=1, fetcher=_failing_fetcher())

    assert result.record.target.status == ClaimStatus.NOT_FOUND
    assert "could not be re-fetched" in result.conflicts[0]


@pytest.mark.asyncio
async def test_needs_rework_true_under_round_limit_with_conflicts():
    record = _record(
        target=Claim(
            field="target",
            status=ClaimStatus.VERIFIED,
            value="X",
            source_url=URL,
            verbatim_quote="missing",
        )
    )
    result = await verifier.verify(record, round_number=1, fetcher=_fake_fetcher("nothing matches"))
    assert result.needs_rework is True


@pytest.mark.asyncio
async def test_allowlist_blocked_source_does_not_trigger_a_retry():
    """Re-running Research cannot un-block a domain — the second pass would
    reach the same source and fail identically, on the client's key."""
    from src.utils.fetch import BlockedByAllowlist

    async def _blocked_fetch(url: str) -> str:
        raise BlockedByAllowlist("fusacq.com", "domain not in allowlist")

    record = _record(
        adviser=Claim(
            field="adviser",
            status=ClaimStatus.VERIFIED,
            value="Clairfield",
            source_url=URL,
            verbatim_quote="Clairfield conseille la cession",
        )
    )
    result = await verifier.verify(record, round_number=1, fetcher=_blocked_fetch)

    assert result.record.adviser.status == ClaimStatus.NOT_FOUND
    assert result.needs_rework is False  # settled, not unlucky
    assert "outside the compliance allowlist" in result.conflicts[0]


@pytest.mark.asyncio
async def test_transient_fetch_failure_still_triggers_a_retry():
    """A network blip is worth one more attempt — unlike a blocked domain."""
    record = _record(
        target=Claim(
            field="target",
            status=ClaimStatus.VERIFIED,
            value="Acme",
            source_url=URL,
            verbatim_quote="acquired Acme",
        )
    )
    result = await verifier.verify(record, round_number=1, fetcher=_failing_fetcher())

    assert result.needs_rework is True


@pytest.mark.asyncio
async def test_needs_rework_false_once_round_limit_reached():
    record = _record(
        target=Claim(
            field="target",
            status=ClaimStatus.VERIFIED,
            value="X",
            source_url=URL,
            verbatim_quote="missing",
        )
    )
    # settings.max_verification_rounds defaults to 2 (see .env.example)
    result = await verifier.verify(record, round_number=2, fetcher=_fake_fetcher("nothing matches"))
    assert result.needs_rework is False


@pytest.mark.asyncio
async def test_conflicts_are_carried_on_the_record_not_just_returned():
    """A rejection the client can't see in the snapshot may as well not have
    happened — under-claiming is the behaviour being demonstrated."""
    record = _record(
        target=Claim(
            field="target",
            status=ClaimStatus.VERIFIED,
            value="Acme",
            source_url=URL,
            verbatim_quote="a quote that is not on the page",
        )
    )
    result = await verifier.verify(record, round_number=1, fetcher=_fake_fetcher("Other content."))

    assert len(result.record.conflicts) == 1
    assert "target" in result.record.conflicts[0]


@pytest.mark.asyncio
async def test_conflicts_accumulate_across_verification_rounds():
    record = _record(
        target=Claim(
            field="target",
            status=ClaimStatus.VERIFIED,
            value="Acme",
            source_url=URL,
            verbatim_quote="missing quote",
        )
    )
    record.conflicts = ["round 1: something was already rejected"]

    result = await verifier.verify(record, round_number=2, fetcher=_fake_fetcher("nothing matches"))

    assert len(result.record.conflicts) == 2
    assert result.record.conflicts[0] == "round 1: something was already rejected"


@pytest.mark.asyncio
async def test_legal_adviser_quote_is_rejected_even_though_it_is_on_the_page():
    """The brief asks for the financial (M&A) adviser specifically. A quote
    naming a law firm passes the substring check honestly but does not
    support the claim — presence and support are different questions."""
    page = "Clifford Chance acted as legal counsel to Acme on the transaction."
    record = _record(
        adviser=Claim(
            field="adviser",
            status=ClaimStatus.VERIFIED,
            value="Clifford Chance",
            source_url=URL,
            verbatim_quote="Clifford Chance acted as legal counsel",
        )
    )
    result = await verifier.verify(record, round_number=1, fetcher=_fake_fetcher(page))

    assert result.record.adviser.status == ClaimStatus.NOT_FOUND
    assert "financial (M&A) adviser" in result.record.conflicts[0]


@pytest.mark.asyncio
async def test_quote_naming_both_advisers_keeps_the_financial_one():
    """Releases routinely name both sides in one sentence — that's the
    financial adviser being disclosed, not a wrong-type match."""
    page = "Jefferies acted as financial adviser and Clifford Chance as legal counsel."
    record = _record(
        adviser=Claim(
            field="adviser",
            status=ClaimStatus.VERIFIED,
            value="Jefferies",
            source_url=URL,
            verbatim_quote=(
                "Jefferies acted as financial adviser and Clifford Chance as legal counsel"
            ),
        )
    )
    result = await verifier.verify(record, round_number=1, fetcher=_fake_fetcher(page))

    assert result.record.adviser.status == ClaimStatus.VERIFIED
    assert result.record.adviser.value == "Jefferies"
    assert result.record.conflicts == []


@pytest.mark.asyncio
async def test_one_fetch_per_distinct_url_not_per_claim():
    calls = []

    async def _counting_fetch(url: str) -> str:
        calls.append(url)
        return "Acme was acquired. Terms were not disclosed."

    record = _record(
        target=Claim(
            field="target",
            status=ClaimStatus.VERIFIED,
            value="Acme",
            source_url=URL,
            verbatim_quote="Acme was acquired",
        ),
        purchase_price=Claim(
            field="purchase_price",
            status=ClaimStatus.EXPLICITLY_UNDISCLOSED,
            source_url=URL,
            verbatim_quote="Terms were not disclosed",
        ),
    )
    await verifier.verify(record, round_number=1, fetcher=_counting_fetch)

    assert calls == [URL]
