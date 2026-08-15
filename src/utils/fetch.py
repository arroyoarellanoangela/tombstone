"""The only place a network request is allowed to originate in this codebase.

Every agent fetch goes through `fetch()`. The ToS allowlist (sources/
allowlist.yaml) is checked here, before any request leaves the process —
a network-layer gate, not a prompt instruction an agent could ignore under
pressure to find data. A blocked domain is logged to data/omissions.json
with its reason instead of raising silently.
"""

from pathlib import Path
from urllib.parse import urlparse

import httpx
import yaml

ALLOWLIST_PATH = Path(__file__).resolve().parents[2] / "sources" / "allowlist.yaml"


class BlockedByAllowlist(Exception):
    def __init__(self, domain: str, reason: str):
        self.domain = domain
        self.reason = reason
        super().__init__(f"{domain} is not allowed: {reason}")


def _load_allowlist() -> dict[str, dict]:
    entries = yaml.safe_load(ALLOWLIST_PATH.read_text())
    return {e["domain"]: e for e in entries}


def is_allowed(url: str) -> tuple[bool, str]:
    domain = urlparse(url).netloc.removeprefix("www.")
    entry = _load_allowlist().get(domain)
    if entry is None:
        return False, "domain not in allowlist — treated as disallowed by default"
    return entry["allowed"], entry["reason"]


async def fetch(url: str) -> str:
    allowed, reason = is_allowed(url)
    if not allowed:
        raise BlockedByAllowlist(urlparse(url).netloc, reason)
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url)
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
