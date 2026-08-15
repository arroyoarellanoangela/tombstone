"""Thin wrapper around the Claude Agent SDK — the only place `query()` is called.

Every pipeline stage depends on `run_agent`, not on `claude_agent_sdk` directly, so
tests can inject a fake async callable with the same signature and never touch the
network or spend the client's key. See tests/unit/test_discovery.py for the pattern.
"""

import re
import tempfile

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient, TextBlock

from src.config import settings

_CODE_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

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


async def run_agent(
    prompt: str,
    system_prompt: str,
    allowed_tools: list[str] | None = None,
    model: str | None = None,
) -> str:
    """Runs one agentic turn and returns its concatenated final text output."""
    options = ClaudeAgentOptions(
        system_prompt=system_prompt,
        allowed_tools=allowed_tools or [],
        model=model,
        env={
            "ANTHROPIC_API_KEY": settings.anthropic_api_key,
            "HOME": _ISOLATED_HOME,
            "USERPROFILE": _ISOLATED_HOME,
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
        },
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
    chunks: list[str] = []
    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        chunks.append(block.text)
    return "".join(chunks)


def strip_json_fences(text: str) -> str:
    """Models wrap JSON in ```json fences even when told not to. Every agent
    that parses a JSON response runs its output through this first.
    """
    return _CODE_FENCE.sub("", text.strip()).strip()
