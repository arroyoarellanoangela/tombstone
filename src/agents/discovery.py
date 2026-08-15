"""Stage 1 — Discovery. One instance per acquirer, run in parallel.

Receives a declarative AcquirerProfile (allowed domains, language, source
type — see sources/profiles/). Returns raw DealCandidates only: url, date,
snippet. Never interprets or judges what counts as a deal — that's the
Normalizer's job, so the acquisition definition lives in one testable place.

WebSearch is an Anthropic-hosted tool — it runs outside this process, so it
never passes through utils.fetch's allowlist gate. To keep the "nothing
gets acted on outside the allowlist" guarantee, every candidate URL the
model surfaces is re-checked against sources/allowlist.yaml here, in
Python, before it's ever returned as a DealCandidate. A disallowed URL is
dropped and logged, not silently trusted because the model found it.
"""

import json
import logging
from datetime import UTC, datetime, timedelta

from src.domain.models import AcquirerProfile, DealCandidate
from src.utils.fetch import is_allowed
from src.utils.llm import run_agent, strip_json_fences

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are the discovery agent for Tombstone, a competitive-\
intelligence system tracking software company acquisitions for Abingdon \
Software Group.

Search for acquisitions announced by the named acquirer within the given \
date window, using the WebSearch tool. You are reporting leads, not \
verifying deals — do not judge whether something qualifies as an \
acquisition (minority stake vs. majority acquisition, etc.); that \
distinction is made downstream. Include anything that looks like an \
acquisition announcement.

You only have WebSearch — you cannot fetch or browse full pages. Base your \
answer entirely on the titles, URLs and snippets WebSearch returns. Do not \
attempt to visit, fetch, or verify any page. Run WebSearch once or twice at \
most, then immediately give your final answer — do not narrate your plan \
or say what you're about to do next.

Your final message must be ONLY a JSON array, no prose before or after, no \
markdown code fences, each item shaped:
{"url": "...", "published_at": "YYYY-MM-DD" or null, "snippet": "..."}
If you find nothing, respond with []."""


def _build_prompt(profile: AcquirerProfile, window_days: int) -> str:
    cutoff = (datetime.now(UTC) - timedelta(days=window_days)).date().isoformat()
    site_filters = " OR ".join(f"site:{domain}" for domain in profile.allowed_domains)
    return (
        f"Acquirer: {profile.name}\n"
        f"Search in: {profile.primary_language}\n"
        f"Primary source type: {profile.source_type}\n"
        f"Restrict search to: {site_filters}\n"
        f"Only include announcements dated on or after {cutoff}.\n"
        f"Context: {profile.notes or 'none'}\n"
    )


def _parse_and_filter(raw_output: str, acquirer_slug: str) -> list[DealCandidate]:
    try:
        items = json.loads(strip_json_fences(raw_output))
    except json.JSONDecodeError:
        logger.warning(
            "Discovery for %s returned non-JSON output, treating as zero candidates: %r",
            acquirer_slug,
            raw_output[:200],
        )
        return []

    candidates: list[DealCandidate] = []
    for item in items:
        url = item.get("url")
        if not url:
            continue

        allowed, reason = is_allowed(url)
        if not allowed:
            logger.info("Dropping candidate outside allowlist: %s (%s)", url, reason)
            continue

        published_at = None
        if item.get("published_at"):
            try:
                published_at = datetime.fromisoformat(item["published_at"])
                if published_at.tzinfo is None:
                    published_at = published_at.replace(tzinfo=UTC)
            except ValueError:
                pass

        candidates.append(
            DealCandidate(
                acquirer_slug=acquirer_slug,
                url=url,
                published_at=published_at,
                snippet=item.get("snippet", ""),
            )
        )
    return candidates


async def run(
    profile: AcquirerProfile,
    window_days: int,
    agent_caller=run_agent,
) -> list[DealCandidate]:
    """Search `profile`'s allowed sources for acquisitions announced within
    the last `window_days`. Returns candidates, not deals — see module docstring.

    `agent_caller` defaults to the real Claude Agent SDK wrapper; tests pass
    a fake async callable with the same signature to run this without
    touching the network or spending the client's key.
    """
    prompt = _build_prompt(profile, window_days)
    raw_output = await agent_caller(
        prompt=prompt,
        system_prompt=_SYSTEM_PROMPT,
        allowed_tools=["WebSearch"],
    )
    return _parse_and_filter(raw_output, profile.slug)
