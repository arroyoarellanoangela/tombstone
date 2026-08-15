"""Research is tested against fake agent_caller and fetcher — no network,
no API key, no cost. Same pattern as test_discovery.py.
"""

import json

import pytest

from src.agents import research
from src.domain.models import ClaimStatus, DealCandidate

CANDIDATE = DealCandidate(
    acquirer_slug="volaris",
    url="https://volarisgroup.com/press-room/acme-acquisition",
    snippet="Volaris Group acquires Acme Software.",
)


def _fake_fetcher(page_text: str):
    async def _fetch(url: str) -> str:
        return page_text

    return _fetch


def _fake_agent(response_json: str):
    async def _caller(prompt: str, system_prompt: str, allowed_tools=None, model=None):
        return response_json

    return _caller


@pytest.mark.asyncio
async def test_verified_and_undisclosed_fields_are_extracted():
    response = json.dumps(
        {
            "acquirer": {
                "status": "verified",
                "value": "Volaris Group",
                "quote": "Volaris Group today announced",
            },
            "target": {"status": "verified", "value": "Acme Software", "quote": "acquired Acme Software"},
            "date_announced": {
                "status": "verified",
                "value": "2026-06-01",
                "quote": "announced on June 1, 2026",
            },
            "target_description": {
                "status": "verified",
                "value": "workflow software for logistics",
                "quote": "provider of workflow software for logistics",
            },
            "geography": {"status": "verified", "value": "Canada", "quote": "Canada-based Acme"},
            "adviser": {"status": "not_found", "value": None, "quote": None},
            "purchase_price": {
                "status": "explicitly_undisclosed",
                "value": None,
                "quote": "financial terms were not disclosed",
            },
        }
    )
    page_text = (
        "Volaris Group today announced it has acquired Acme Software, a Canada-based "
        "provider of workflow software for logistics, announced on June 1, 2026. "
        "Financial terms were not disclosed."
    )

    record = await research.run(
        CANDIDATE,
        acquirer_name="Volaris Group",
        agent_caller=_fake_agent(response),
        fetcher=_fake_fetcher(page_text),
    )

    assert record.target.status == ClaimStatus.VERIFIED
    assert record.target.value == "Acme Software"
    assert record.target.source_url == CANDIDATE.url
    assert record.adviser.status == ClaimStatus.NOT_FOUND
    assert record.purchase_price.status == ClaimStatus.EXPLICITLY_UNDISCLOSED
    assert record.purchase_price.verbatim_quote == "financial terms were not disclosed"
    assert record.deal_id == "volaris-acme-software"
    assert record.source_urls == [CANDIDATE.url]


@pytest.mark.asyncio
async def test_missing_quote_becomes_not_found_even_if_status_says_verified():
    response = json.dumps(
        {
            "acquirer": {"status": "verified", "value": "Volaris Group", "quote": None},
            "target": {"status": "not_found", "value": None, "quote": None},
            "date_announced": {"status": "not_found", "value": None, "quote": None},
            "target_description": {"status": "not_found", "value": None, "quote": None},
            "geography": {"status": "not_found", "value": None, "quote": None},
            "adviser": {"status": "not_found", "value": None, "quote": None},
            "purchase_price": {"status": "not_found", "value": None, "quote": None},
        }
    )
    record = await research.run(
        CANDIDATE,
        acquirer_name="Volaris Group",
        agent_caller=_fake_agent(response),
        fetcher=_fake_fetcher("irrelevant page text"),
    )

    # A "verified" status with no quote is not trusted — downgraded to not_found.
    assert record.acquirer.status == ClaimStatus.NOT_FOUND
    assert record.target.status == ClaimStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_malformed_json_yields_all_not_found_without_crashing():
    record = await research.run(
        CANDIDATE,
        acquirer_name="Volaris Group",
        agent_caller=_fake_agent("not json"),
        fetcher=_fake_fetcher("irrelevant page text"),
    )

    assert record.target.status == ClaimStatus.NOT_FOUND
    assert record.purchase_price.status == ClaimStatus.NOT_FOUND
    # Falls back to a URL-derived slug, not a bare acquirer slug, so two
    # candidates that both fail extraction don't collide on deal_id.
    assert record.deal_id == "volaris-unknown-acme-acquisition"
