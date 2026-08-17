"""Thin wrapper around the Claude Agent SDK — the only place `query()` is called.

Every pipeline stage depends on `run_agent`, not on `claude_agent_sdk` directly, so
tests can inject a fake async callable with the same signature and never touch the
network or spend the client's key. See tests/unit/test_discovery.py for the pattern.
"""

import asyncio
import logging
import re
import tempfile
from collections.abc import Awaitable, Callable

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
)

from src.config import settings
from src.orchestrator.budget import RunBudget

logger = logging.getLogger(__name__)

_CODE_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

# Every agent call spawns a `claude` CLI subprocess, and under the
# orchestrator's parallelism that spawn occasionally times out before the
# process is up. A live run lost a whole deal to one. The failure happens
# before any request reaches the API, so no tokens were spent and a retry
# is free — unlike a mid-response failure, which is not retried here
# because it may already have been billed.
_SPAWN_ATTEMPTS = 3
_SPAWN_BACKOFF_SECONDS = 2.0
_TRANSIENT_SPAWN_MARKERS = (
    "control request timeout",
    "initialize",
    "connection closed",
    "transport closed",
)


# The CLI reports account-level failures as an ordinary assistant message
# rather than raising, so "Credit balance is too low" arrives looking exactly
# like a model that chose to reply in prose. Every agent then treats it as
# unparseable output and degrades to "found nothing" — which is the most
# dangerous possible failure here: a client with an exhausted key would see
# an empty dashboard and conclude their competitors made no acquisitions.
# These runs must fail loudly instead.
_ACCOUNT_FAILURE_MARKERS = (
    "credit balance is too low",
    "authentication_error",
    "invalid x-api-key",
    "rate limit",
    "quota",
)


class AgentAccountError(RuntimeError):
    """The account, not the model, refused the call — a run-stopping problem."""


def _account_failure(text: str) -> str | None:
    """The marker matched in `text`, if it reads as an account-level refusal."""
    lowered = text.strip().lower()
    # Anchored to short responses: a genuine extraction quoting the phrase
    # from some article should not take the whole run down.
    if len(lowered) > 200:
        return None
    return next((m for m in _ACCOUNT_FAILURE_MARKERS if m in lowered), None)


def _is_transient_spawn_failure(exc: Exception) -> bool:
    """True for failures that happened while starting the subprocess, i.e.
    before the prompt could have been billed."""
    message = str(exc).lower()
    return any(marker in message for marker in _TRANSIENT_SPAWN_MARKERS)

# The signature every agent's injectable `agent_caller` must satisfy —
# run_agent below is the real implementation, tests pass fakes.
AgentCaller = Callable[..., Awaitable[str]]

# The SDK shells out to the `claude` CLI as a subprocess. If that CLI finds a
# stored OAuth session under the caller's home directory (e.g. a developer's
# own Claude Code login), it uses that instead of ANTHROPIC_API_KEY — and
# fails outright if that session happens to be expired, regardless of the
# key. Pointing HOME/USERPROFILE at an empty directory makes every run start
# from a clean slate, so the client's key is the only credential the CLI can
# ever find. A fresh container (e.g. the shipped docker-compose setup) has
# no stored session either way, so this only matters for local dev machines
# that already have their own Claude Code login.
_ISOLATED_HOME = tempfile.mkdtemp(prefix="tombstone_claude_home_")


def _subprocess_env() -> dict[str, str]:
    """Environment for the `claude` CLI subprocess — isolated from any
    developer login, forced into UTF-8 mode, and scrubbed of this process's
    own Claude Code session identity if it happens to be running inside one.
    """
    return {
        "ANTHROPIC_API_KEY": settings.anthropic_api_key,
        "HOME": _ISOLATED_HOME,
        "USERPROFILE": _ISOLATED_HOME,
        # A live run produced accented text ("Informática", "IVèS") that
        # came back mojibake'd — the classic signature of UTF-8 bytes
        # decoded as the Windows console's ANSI codepage somewhere
        # between the CLI subprocess and this process. Forcing UTF-8
        # mode removes that ambiguity regardless of exactly which layer
        # (this process, the subprocess, or something it spawns) would
        # otherwise fall back to a locale default.
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        # If this process is itself running inside a Claude Code session
        # (e.g. launched from a dev's own terminal session), these leak
        # into os.environ and the nested CLI gets confused trying to
        # attach to that outer session instead of starting cleanly.
        # A real deployment (fresh container) never has these set.
        "CLAUDECODE": "",
        "CLAUDE_CODE_SESSION_ID": "",
        "CLAUDE_CODE_CHILD_SESSION": "",
        "CLAUDE_CODE_HOST_SESSION_ID": "",
        "CLAUDE_CODE_EXECPATH": "",
    }


async def run_agent(
    prompt: str,
    system_prompt: str,
    allowed_tools: list[str] | None = None,
    model: str | None = None,
    budget: RunBudget | None = None,
) -> str:
    """Runs one agentic turn and returns its concatenated final text output.

    When a `budget` is passed (the orchestrator binds one via
    functools.partial, so individual agents never handle money), the ceiling
    is checked *before* spawning the call — raising BudgetExceeded instead
    of starting work that would overspend — and the actual cost the SDK
    reports on completion is recorded against it.
    """
    if budget is not None:
        budget.check()
    options = ClaudeAgentOptions(
        system_prompt=system_prompt,
        allowed_tools=allowed_tools or [],
        model=model,
        env=_subprocess_env(),
        # Runs unattended (orchestrator, CI, tests) — nobody is present to
        # approve tool calls interactively, so permission prompts must be
        # bypassed rather than hanging forever waiting for a human.
        permission_mode="bypassPermissions",
    )
    # ClaudeSDKClient sends the prompt over the subprocess's stdin (streaming
    # mode) rather than as a CLI argument. The one-shot `query()` function
    # passes the prompt as an argv string instead, which on Windows goes
    # through the OS's ANSI codepage conversion and silently corrupts any
    # non-ASCII character (accents, non-Latin scripts) before the model ever
    # sees it — stdin bytes bypass that conversion entirely.
    last_error: Exception | None = None
    for attempt in range(_SPAWN_ATTEMPTS):
        chunks: list[str] = []
        try:
            async with ClaudeSDKClient(options=options) as client:
                await client.query(prompt)
                async for message in client.receive_response():
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                chunks.append(block.text)
                    elif isinstance(message, ResultMessage):
                        if budget is not None and message.total_cost_usd:
                            budget.record_spend(message.total_cost_usd)
            response = "".join(chunks)
            if (marker := _account_failure(response)) is not None:
                raise AgentAccountError(
                    f"Anthropic account refused the call ({marker}) — stopping the run "
                    f"rather than reporting an empty result. Full response: {response!r}"
                )
            return response
        except Exception as exc:  # noqa: BLE001 — re-raised below if not transient
            if not _is_transient_spawn_failure(exc) or attempt == _SPAWN_ATTEMPTS - 1:
                raise
            last_error = exc
            logger.warning(
                "Agent subprocess failed to start (attempt %d/%d): %s — retrying",
                attempt + 1,
                _SPAWN_ATTEMPTS,
                exc,
            )
            await asyncio.sleep(_SPAWN_BACKOFF_SECONDS * (attempt + 1))

    raise RuntimeError(f"Agent subprocess never started: {last_error}")


def strip_json_fences(text: str) -> str:
    """Models wrap JSON in ```json fences even when told not to. Every agent
    that parses a JSON response runs its output through this first.

    Also rescues JSON that arrives with prose wrapped around it ("Here are
    the deals I found: [...]. Let me know if..."). A tool-using agent
    narrates far more readily than a plain one, and in a live run that
    narration cost a whole acquirer's discovery results — the JSON was
    perfectly valid, just not alone on the line. Only the outermost
    balanced array or object is returned; anything malformed is handed back
    untouched for the caller's own error handling to report.
    """
    stripped = _CODE_FENCE.sub("", text.strip()).strip()

    start = min(
        (i for i in (stripped.find("["), stripped.find("{")) if i != -1),
        default=-1,
    )
    if start == -1:
        return stripped

    opener = stripped[start]
    closer = "]" if opener == "[" else "}"
    depth = 0
    in_string = False
    escaped = False

    for i, char in enumerate(stripped[start:], start):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
        elif char == '"':
            in_string = not in_string
        elif not in_string:
            if char == opener:
                depth += 1
            elif char == closer:
                depth -= 1
                if depth == 0:
                    return stripped[start : i + 1]

    return stripped
