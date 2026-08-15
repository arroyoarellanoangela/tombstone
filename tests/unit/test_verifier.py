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
    result = await verifier.verify(record, round_number=1, fetcher=_fake_fetcher("Completely different content."))

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
        record, round_number=1, fetcher=_fake_fetcher("The terms were not disclosed by either party.")
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
            field="target", status=ClaimStatus.VERIFIED, value="X", source_url=URL, verbatim_quote="missing"
        )
    )
    result = await verifier.verify(record, round_number=1, fetcher=_fake_fetcher("nothing matches"))
    assert result.needs_rework is True


@pytest.mark.asyncio
async def test_needs_rework_false_once_round_limit_reached():
    record = _record(
        target=Claim(
            field="target", status=ClaimStatus.VERIFIED, value="X", source_url=URL, verbatim_quote="missing"
        )
    )
    # settings.max_verification_rounds defaults to 2 (see .env.example)
    result = await verifier.verify(record, round_number=2, fetcher=_fake_fetcher("nothing matches"))
    assert result.needs_rework is False


@pytest.mark.asyncio
async def test_one_fetch_per_distinct_url_not_per_claim():
    calls = []

    async def _counting_fetch(url: str) -> str:
        calls.append(url)
        return "Acme was acquired. Terms were not disclosed."

    record = _record(
        target=Claim(
            field="target", status=ClaimStatus.VERIFIED, value="Acme", source_url=URL, verbatim_quote="Acme was acquired"
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
