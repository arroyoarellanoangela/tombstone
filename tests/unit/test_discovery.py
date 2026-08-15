"""Discovery is tested against a fake agent_caller — no network, no API key,
no cost. This is the pattern the rest of the agents (research, verifier,
adviser_hunter) should follow once implemented.
"""

import json

import pytest

from src.agents import discovery
from src.domain.models import AcquirerProfile

VOLARIS_PROFILE = AcquirerProfile(
    name="Volaris Group",
    slug="volaris",
    allowed_domains=["volarisgroup.com"],
    primary_language="en",
    source_type="press_room",
)


def _fake_agent(response_json: str):
    async def _caller(prompt: str, system_prompt: str, allowed_tools=None, model=None):
        return response_json

    return _caller


@pytest.mark.asyncio
async def test_allowed_candidate_is_kept():
    response = json.dumps(
        [
            {
                "url": "https://volarisgroup.com/press-room/acme-acquisition",
                "published_at": "2026-06-01",
                "snippet": "Volaris Group acquires Acme Software.",
            }
        ]
    )
    candidates = await discovery.run(VOLARIS_PROFILE, window_days=90, agent_caller=_fake_agent(response))

    assert len(candidates) == 1
    assert candidates[0].url == "https://volarisgroup.com/press-room/acme-acquisition"
    assert candidates[0].acquirer_slug == "volaris"


@pytest.mark.asyncio
async def test_disallowed_domain_is_dropped():
    response = json.dumps(
        [
            {
                "url": "https://linkedin.com/posts/some-acquisition-rumor",
                "published_at": "2026-06-01",
                "snippet": "Rumor of an acquisition.",
            },
            {
                "url": "https://volarisgroup.com/press-room/real-deal",
                "published_at": "2026-06-02",
                "snippet": "The real announcement.",
            },
        ]
    )
    candidates = await discovery.run(VOLARIS_PROFILE, window_days=90, agent_caller=_fake_agent(response))

    assert len(candidates) == 1
    assert candidates[0].url.startswith("https://volarisgroup.com")


@pytest.mark.asyncio
async def test_malformed_json_returns_empty_list():
    candidates = await discovery.run(
        VOLARIS_PROFILE, window_days=90, agent_caller=_fake_agent("not json at all")
    )
    assert candidates == []


@pytest.mark.asyncio
async def test_empty_array_returns_empty_list():
    candidates = await discovery.run(VOLARIS_PROFILE, window_days=90, agent_caller=_fake_agent("[]"))
    assert candidates == []


@pytest.mark.asyncio
async def test_published_at_is_timezone_aware():
    # The model returns a bare "YYYY-MM-DD" — datetime.fromisoformat() on
    # that is naive, but the Normalizer compares it against an aware cutoff.
    # A naive published_at here would raise TypeError downstream.
    response = json.dumps(
        [
            {
                "url": "https://volarisgroup.com/press-room/acme-acquisition",
                "published_at": "2026-06-01",
                "snippet": "Volaris Group acquires Acme Software.",
            }
        ]
    )
    candidates = await discovery.run(VOLARIS_PROFILE, window_days=90, agent_caller=_fake_agent(response))

    assert candidates[0].published_at.tzinfo is not None
