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
    result = await discovery.run(
        VOLARIS_PROFILE, window_days=90, agent_caller=_fake_agent(response)
    )

    assert len(result.candidates) == 1
    assert result.candidates[0].url == "https://volarisgroup.com/press-room/acme-acquisition"
    assert result.candidates[0].acquirer_slug == "volaris"
    assert result.omitted == []


@pytest.mark.asyncio
async def test_disallowed_domain_is_dropped_but_disclosed():
    # Ranging beyond the profile's starting domains (per the brief) means
    # Discovery will surface leads outside the allowlist — those must be
    # excluded from candidates but still disclosed as an Omission, not just
    # logged and forgotten. "If in doubt, leave it out and say so."
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
    result = await discovery.run(
        VOLARIS_PROFILE, window_days=90, agent_caller=_fake_agent(response)
    )

    assert len(result.candidates) == 1
    assert result.candidates[0].url.startswith("https://volarisgroup.com")
    assert len(result.omitted) == 1
    assert result.omitted[0].url == "https://linkedin.com/posts/some-acquisition-rumor"
    assert result.omitted[0].stage == "allowlist"


@pytest.mark.asyncio
async def test_malformed_json_returns_empty_result():
    result = await discovery.run(
        VOLARIS_PROFILE, window_days=90, agent_caller=_fake_agent("not json at all")
    )
    assert result.candidates == []
    assert result.omitted == []


@pytest.mark.asyncio
async def test_empty_array_returns_empty_result():
    result = await discovery.run(VOLARIS_PROFILE, window_days=90, agent_caller=_fake_agent("[]"))
    assert result.candidates == []
    assert result.omitted == []


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
    result = await discovery.run(
        VOLARIS_PROFILE, window_days=90, agent_caller=_fake_agent(response)
    )

    assert result.candidates[0].published_at.tzinfo is not None
