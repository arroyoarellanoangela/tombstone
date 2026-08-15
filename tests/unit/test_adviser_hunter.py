import json

import pytest

from src.agents import adviser_hunter
from src.domain.models import Claim, ClaimStatus, DealRecord

_NOT_FOUND = Claim(field="_", status=ClaimStatus.NOT_FOUND)


def _record(**overrides) -> DealRecord:
    fields = {
        "acquirer": Claim(
            field="acquirer",
            status=ClaimStatus.VERIFIED,
            value="Volaris Group",
            source_url="https://volarisgroup.com/x",
            verbatim_quote="Volaris Group",
        ),
        "target": Claim(
            field="target",
            status=ClaimStatus.VERIFIED,
            value="Acme Software",
            source_url="https://volarisgroup.com/x",
            verbatim_quote="Acme Software",
        ),
        "date_announced": _NOT_FOUND,
        "target_description": _NOT_FOUND,
        "geography": _NOT_FOUND,
        "adviser": _NOT_FOUND,
        "purchase_price": _NOT_FOUND,
    }
    fields.update(overrides)
    return DealRecord(deal_id="volaris-acme", **fields)


def _fake_agent(response_json: str):
    async def _caller(prompt: str, system_prompt: str, allowed_tools=None, model=None):
        return response_json

    return _caller


@pytest.mark.asyncio
async def test_found_adviser_with_source_is_kept():
    response = json.dumps(
        {
            "status": "verified",
            "value": "Houlihan Lokey",
            "quote": "Houlihan Lokey advised Acme Software on its sale",
            "source_url": "https://houlihanlokey.com/transactions/acme",
        }
    )
    claim = await adviser_hunter.run(_record(), agent_caller=_fake_agent(response))

    assert claim.status == ClaimStatus.VERIFIED
    assert claim.value == "Houlihan Lokey"
    assert claim.source_url == "https://houlihanlokey.com/transactions/acme"


@pytest.mark.asyncio
async def test_verified_without_source_url_is_downgraded():
    # A claim the Verifier has nothing to re-fetch and check is not trusted.
    response = json.dumps(
        {
            "status": "verified",
            "value": "Some Bank",
            "quote": "advised by Some Bank",
            "source_url": None,
        }
    )
    claim = await adviser_hunter.run(_record(), agent_caller=_fake_agent(response))

    assert claim.status == ClaimStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_not_found_is_the_expected_common_case():
    response = json.dumps({"status": "not_found", "value": None, "quote": None, "source_url": None})
    claim = await adviser_hunter.run(_record(), agent_caller=_fake_agent(response))

    assert claim.status == ClaimStatus.NOT_FOUND
    assert claim.field == "adviser"


@pytest.mark.asyncio
async def test_malformed_json_does_not_crash():
    claim = await adviser_hunter.run(_record(), agent_caller=_fake_agent("not json"))
    assert claim.status == ClaimStatus.NOT_FOUND
