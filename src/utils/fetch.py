"""The only place a network request is allowed to originate in this codebase.

Every agent fetch goes through `fetch()`. The ToS allowlist (sources/
allowlist.yaml) is checked here, before any request leaves the process —
a network-layer gate, not a prompt instruction an agent could ignore under
pressure to find data. A blocked domain is logged to data/omissions.json
with its reason instead of raising silently.
"""

import re
from collections.abc import Awaitable, Callable
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import yaml

# Strips <script>/<style>/<head>/<nav>/<footer> wholesale (never useful —
# tracking JS, anti-devtools code, boilerplate chrome), then every remaining
# tag, then collapses whitespace. Measured on a real press page: raw HTML
# ~30x noisier than this by char count, which is what agents actually pay
# for in tokens — html_to_text() is what both Research (what it reads) and
# the Verifier (what it re-checks quotes against) should see, so a quote
# extracted from one is a literal substring of the other.
_STRIP_BLOCKS = re.compile(r"(?is)<(script|style|head|nav|footer)[^>]*>.*?</\1>")
_STRIP_TAGS = re.compile(r"(?s)<[^>]+>")
_COLLAPSE_WS = re.compile(r"\s+")

ALLOWLIST_PATH = Path(__file__).resolve().parents[2] / "sources" / "allowlist.yaml"

# The signature every injectable `fetcher` must satisfy — fetch below is the
# real implementation, tests pass fakes.
Fetcher = Callable[[str], Awaitable[str]]


class BlockedByAllowlist(Exception):
    def __init__(self, domain: str, reason: str):
        self.domain = domain
        self.reason = reason
        super().__init__(f"{domain} is not allowed: {reason}")


@lru_cache(maxsize=1)
def _load_allowlist() -> dict[str, dict[str, Any]]:
    # Read once per process — every candidate URL goes through is_allowed(),
    # and the allowlist only changes with a code change + restart anyway.
    entries = yaml.safe_load(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    return {e["domain"]: e for e in entries}


def is_allowed(url: str) -> tuple[bool, str]:
    """Match `url`'s domain against the allowlist, subdomains included.

    An entry covers its subdomains, so `banyansoftware.com` also governs
    `news.banyansoftware.com`. Without that, a live run dropped acquirers'
    own press coverage purely because search surfaced the apex domain while
    the allowlist happened to name the news subdomain (or vice versa).

    Suffix matching is anchored on a dot, so `notbanyansoftware.com` does
    not match `banyansoftware.com`. Where several entries match, the most
    specific wins — a blocked subdomain stays blocked under an allowed
    parent, and an allowed subdomain still works under a blocked parent.
    """
    domain = urlparse(url).netloc.removeprefix("www.")
    matches = [
        (candidate, entry)
        for candidate, entry in _load_allowlist().items()
        if domain == candidate or domain.endswith(f".{candidate}")
    ]
    if not matches:
        return False, "domain not in allowlist — treated as disallowed by default"
    _, entry = max(matches, key=lambda pair: len(pair[0]))
    return bool(entry["allowed"]), str(entry["reason"])


async def fetch(url: str) -> str:
    allowed, reason = is_allowed(url)
    if not allowed:
        raise BlockedByAllowlist(urlparse(url).netloc, reason)
    # Redirects are followed because not following them breaks ordinary
    # sources — http→https, trailing-slash canonicalisation and legacy
    # .html paths are all 301s, and a real acquirer press room was being
    # dropped entirely over one. The allowlist is then re-checked against
    # the URL actually served: a redirect is a domain change, and clearing
    # the gate on the requested URL says nothing about where it landed.
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        response = await client.get(url)
        final_url = str(response.url)
        if final_url != url:
            allowed, reason = is_allowed(final_url)
            if not allowed:
                raise BlockedByAllowlist(urlparse(final_url).netloc, f"redirected here — {reason}")
        response.raise_for_status()
        # httpx's encoding auto-detection guesses wrong often enough on real
        # sites (accented characters silently corrupt to U+FFFD) to not be
        # trusted blindly — most modern pages are UTF-8 regardless of what
        # the server declares, so that's tried first and only falls back to
        # httpx's own guess if the bytes genuinely aren't valid UTF-8.
        try:
            return response.content.decode("utf-8")
        except UnicodeDecodeError:
            return response.text


def html_to_text(html: str) -> str:
    """Visible-text view of a fetched page — tags and boilerplate stripped,
    whitespace collapsed. Not HTML-aware parsing (no BeautifulSoup dependency
    for a regex-shaped problem); good enough because we only need the text a
    reader would see, not a DOM."""
    body = _STRIP_BLOCKS.sub(" ", html)
    body = _STRIP_TAGS.sub(" ", body)
    return _COLLAPSE_WS.sub(" ", body).strip()
