"""Stage 3 — Research. One instance per deal, run in parallel.

Fetches the candidate's page via utils.fetch (allowlist-gated, deterministic
HTTP — not the SDK's WebFetch tool, so the same network gate that governs
every other fetch in this system also governs this one), reduces it to
visible text via html_to_text() (raw HTML runs ~30x noisier per char than
the visible article — mostly <script>/tracking boilerplate that costs
tokens and tells the model nothing), and extracts every field as a Claim
grounded in that text. The model gets no tools at all: it works from the
text it's handed, nothing else, so a verbatim_quote it emits is at least
claimed to be a literal substring of text we ourselves retrieved — the
Verifier re-checks that claim later by re-fetching and matching against the
same html_to_text() view, this stage doesn't need to.

Adviser is extracted the same way as everything else; if it comes back
NOT_FOUND, the orchestrator — not this module — decides whether to hand the
deal to adviser_hunter. See _needs_adviser_hunt.
"""

import json
import logging
import re
from typing import Any

from src.domain.models import Claim, ClaimStatus, DealCandidate, DealRecord
from src.utils.fetch import Fetcher, fetch, html_to_text
from src.utils.llm import AgentCaller, run_agent, strip_json_fences

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

# Pure structured extraction from text we already fetched — no search, no
# judgment call, just "read this and copy the quote". Measured against the
# same extracted-text prompt: haiku costs $0.00201/call vs sonnet's
# $0.00846 (10.7x). Safe to downgrade because the Verifier re-checks every
# quote regardless of which model wrote it — a weaker model can only ever
# lose a claim to not_found, never smuggle a bad one through. Discovery and
# Adviser Hunter stay on the default model: both do WebSearch-driven
# judgment (query formulation, relevance filtering), not extraction.
_MODEL = "claude-haiku-4-5"

_SYSTEM_PROMPT = """You are the research agent for Tombstone, a competitive-\
intelligence system tracking software company acquisitions for Abingdon \
Software Group.

You will be given the acquirer's name, a source URL, and the raw text of \
that page. Extract these fields, each grounded in a literal quote from the \
page text — never from outside knowledge, never inferred:

- acquirer: confirm the named acquirer is who the page says made the deal
- target: the company being acquired
- date_announced: when announced (YYYY-MM-DD if the page gives a full date)
- target_description: what the target company does
- geography: where the target operates
- adviser: the financial (M&A) adviser — NOT legal, tax, or technical due \
  diligence advisers. This is frequently absent from the acquirer's own \
  release; that is expected, not an error.
- purchase_price: the deal value

For each field, respond with one of three states:
- If the page states it plainly: {"status": "verified", "value": "...", \
  "quote": "<exact substring copied from the page text>"}
- If the page explicitly says the fact is not being disclosed (e.g. "terms \
  were not disclosed"): {"status": "explicitly_undisclosed", "value": null, \
  "quote": "<exact substring showing the non-disclosure statement>"}
- If the page simply doesn't address it: {"status": "not_found", "value": \
  null, "quote": null}

Never invent a quote and never paraphrase into the quote field — copy the \
exact text. A quote that doesn't literally appear on the page is worse \
than no answer, because it will be checked against the page and rejected.

Respond with ONLY a JSON object, no prose, no markdown fences, shaped:
{"acquirer": {...}, "target": {...}, "date_announced": {...}, \
"target_description": {...}, "geography": {...}, "adviser": {...}, \
"purchase_price": {...}}

<example>
Page text: "Acme Group today announced it has acquired Widgetsoft, a \
Germany-based maker of inventory management software. Terms of the \
transaction were not disclosed. The deal is expected to close in Q3."

{"acquirer": {"status": "verified", "value": "Acme Group", "quote": \
"Acme Group today announced"}, "target": {"status": "verified", "value": \
"Widgetsoft", "quote": "acquired Widgetsoft"}, "date_announced": \
{"status": "not_found", "value": null, "quote": null}, \
"target_description": {"status": "verified", "value": "maker of inventory \
management software", "quote": "Germany-based maker of inventory \
management software"}, "geography": {"status": "verified", "value": \
"Germany", "quote": "Germany-based"}, "adviser": {"status": "not_found", \
"value": null, "quote": null}, "purchase_price": {"status": \
"explicitly_undisclosed", "value": null, "quote": "Terms of the \
transaction were not disclosed"}}
</example>"""


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "unknown"


def _build_prompt(acquirer_name: str, url: str, page_text: str) -> str:
    # page_text is html_to_text() output, not raw HTML — measured ~30x
    # denser in useful content per char, so the same visible article fits in
    # a fraction of the tokens raw HTML (with its <script>/tracking noise)
    # cost. Still bounded, for the same reason as before: a truncated page
    # yields more not_found fields rather than a runaway-cost prompt.
    excerpt = page_text[:12000]
    return f"Acquirer: {acquirer_name}\n" f"Source URL: {url}\n\n" f"Page text:\n{excerpt}"


def _claim(field: str, item: dict[str, Any], url: str, language: str) -> Claim:
    status_raw = item.get("status", "not_found")
    try:
        status = ClaimStatus(status_raw)
    except ValueError:
        status = ClaimStatus.NOT_FOUND

    quote = item.get("quote")
    if status == ClaimStatus.NOT_FOUND or not quote:
        return Claim(field=field, status=ClaimStatus.NOT_FOUND)

    return Claim(
        field=field,
        status=status,
        value=item.get("value"),
        source_url=url,
        verbatim_quote=quote,
        source_language=language,
    )


def _parse(raw_output: str, url: str, language: str) -> dict[str, Claim]:
    try:
        data = json.loads(strip_json_fences(raw_output))
    except json.JSONDecodeError:
        logger.warning("Research for %s returned non-JSON output: %r", url, raw_output[:200])
        data = {}

    return {field: _claim(field, data.get(field, {}), url, language) for field in _FIELDS}


async def run(
    candidate: DealCandidate,
    acquirer_name: str,
    language: str = "en",
    agent_caller: AgentCaller = run_agent,
    fetcher: Fetcher = fetch,
) -> DealRecord:
    """Produce a DealRecord for `candidate`. Fields with no supporting quote
    are emitted as status=NOT_FOUND, never fabricated.

    `agent_caller` and `fetcher` default to the real implementations; tests
    inject fakes for both, so this runs with no network and no cost.
    """
    page_html = await fetcher(candidate.url)
    prompt = _build_prompt(acquirer_name, candidate.url, html_to_text(page_html))
    raw_output = await agent_caller(
        prompt=prompt, system_prompt=_SYSTEM_PROMPT, allowed_tools=[], model=_MODEL
    )
    claims = _parse(raw_output, candidate.url, language)

    if claims["target"].value:
        deal_id = f"{candidate.acquirer_slug}-{_slugify(claims['target'].value)}"
    else:
        # Target extraction failed — fall back to a slug of the URL's last
        # path segment so multiple failed candidates for the same acquirer
        # don't collapse into one colliding deal_id.
        url_tail = candidate.url.rstrip("/").rsplit("/", 1)[-1]
        deal_id = f"{candidate.acquirer_slug}-unknown-{_slugify(url_tail)}"

    return DealRecord(
        deal_id=deal_id,
        acquirer=claims["acquirer"],
        target=claims["target"],
        date_announced=claims["date_announced"],
        target_description=claims["target_description"],
        geography=claims["geography"],
        adviser=claims["adviser"],
        purchase_price=claims["purchase_price"],
        source_urls=[candidate.url],
    )
