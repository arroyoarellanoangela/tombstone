"""Stage 4 — Adviser Hunter. Conditionally invoked, only when Research
leaves the M&A adviser field empty.

A distinct search strategy from Research: advisory-side sources (adviser
tombstone announcements, sector press, the target's own release in its
local language) rather than the acquirer's press room, which the brief
notes "often" omits the adviser. This is the clearest real delegation in
the system — a different agent handed the problem because the first
approach didn't work, not run in parallel by default for every deal.

Like Discovery, this agent gets WebSearch but not WebFetch — it works from
search snippets, not full pages. Whatever it reports still gets re-checked
by the Verifier against the actual page before being trusted.
"""

import json
import logging
from dataclasses import dataclass, field

from src.domain.models import Claim, ClaimStatus, DealRecord, Omission
from src.utils.fetch import is_allowed
from src.utils.llm import AgentCaller, run_agent, strip_json_fences

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are the adviser hunter for Tombstone, a competitive-\
intelligence system tracking software company acquisitions for Abingdon \
Software Group.

Research already tried and failed to find the financial (M&A) adviser for \
this deal from the acquirer's own announcement — that's why you're being \
asked. Your job is a lateral search, not a repeat of theirs:

- Search for the adviser's own tombstone/deal announcement (advisory firms \
  publicize deals they worked on)
- Search sector press or M&A trade coverage of this specific deal
- Search the TARGET company's own announcement, not just the acquirer's — \
  it sometimes names its own adviser even when the acquirer's release doesn't

You are looking for the FINANCIAL adviser only — the M&A house that ran \
the sale process. Not legal counsel, not tax advisers, not technical due \
diligence firms. If a source names one of those instead, that is not a hit.

You only have WebSearch — base your answer entirely on titles, URLs and \
snippets it returns; do not fetch or browse pages.

Respond with ONLY a JSON object, no prose, no markdown fences:
{"status": "verified" or "not_found", "value": "<adviser name>" or null, \
"quote": "<exact snippet text naming the adviser>" or null, "source_url": \
"<url the quote came from>" or null}

If you can't find a financial adviser after searching, respond with \
{"status": "not_found", "value": null, "quote": null, "source_url": null} \
— this is the expected outcome for many deals, not a failure."""


def _build_prompt(acquirer_name: str, target_name: str) -> str:
    return f"Acquirer: {acquirer_name}\nTarget: {target_name}\n"


@dataclass
class AdviserResult:
    claim: Claim
    omitted: list[Omission] = field(default_factory=list)


def _parse(raw_output: str) -> AdviserResult:
    not_found = Claim(field="adviser", status=ClaimStatus.NOT_FOUND)

    try:
        item = json.loads(strip_json_fences(raw_output))
    except json.JSONDecodeError:
        logger.warning("Adviser Hunter returned non-JSON output: %r", raw_output[:200])
        return AdviserResult(claim=not_found)

    quote = item.get("quote")
    source_url = item.get("source_url")
    status_raw = item.get("status", "not_found")

    # A claim this agent can't point back to a checkable source isn't worth
    # keeping — the Verifier has nothing to re-fetch and confirm.
    if status_raw != "verified" or not quote or not source_url:
        return AdviserResult(claim=not_found)

    # This agent searches adviser-side sources by design, and those are
    # exactly the domains an allowlist built from acquirer press rooms does
    # not contain. Checking here rather than letting the Verifier discover
    # it later matters twice over: the Verifier's re-fetch would be blocked
    # anyway, and the resulting "conflict" would bounce the deal back to
    # Research — a retry that cannot possibly succeed, paid for in full.
    allowed, reason = is_allowed(source_url)
    if not allowed:
        logger.info("Adviser found at a source outside the allowlist: %s (%s)", source_url, reason)
        return AdviserResult(
            claim=not_found,
            omitted=[
                Omission(
                    url=source_url,
                    reason=f"names an M&A adviser, but {reason}",
                    stage="adviser_allowlist",
                )
            ],
        )

    return AdviserResult(
        claim=Claim(
            field="adviser",
            status=ClaimStatus.VERIFIED,
            value=item.get("value"),
            source_url=source_url,
            verbatim_quote=quote,
        )
    )


async def run(record: DealRecord, agent_caller: AgentCaller = run_agent) -> AdviserResult:
    """Lateral search for `record`'s M&A adviser. Returns a Claim —
    status=NOT_FOUND (not a guess) if no source names one — plus any
    adviser-naming source the compliance gate excluded, so a genuine find we
    are not allowed to use is disclosed rather than looking like a miss.
    """
    acquirer_name = record.acquirer.value or record.deal_id.split("-")[0]
    target_name = record.target.value or "the target company"
    prompt = _build_prompt(acquirer_name, target_name)
    raw_output = await agent_caller(
        prompt=prompt,
        system_prompt=_SYSTEM_PROMPT,
        allowed_tools=["WebSearch"],
    )
    return _parse(raw_output)
