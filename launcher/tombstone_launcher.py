"""Double-click launcher for Tombstone - built into Tombstone.exe.

Not a bundled application: the pipeline shells out to the `claude` Node CLI,
the dashboard is served by Vite and the API by uvicorn, so the thing that
actually runs Tombstone is docker-compose. This is the wrapper that makes
that a double-click instead of a README to follow - it collects the API key
into .env, checks Docker is up, brings the stack online and opens the
dashboard.

Build:  python -m PyInstaller launcher/tombstone.spec --noconfirm
Output: dist/Tombstone.exe
"""

from __future__ import annotations

import contextlib
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from getpass import getpass
from pathlib import Path
from typing import NoReturn

DASHBOARD_URL = "http://localhost:5173"
STARTUP_TIMEOUT_SECONDS = 300
KEY_PREFIX = "sk-ant-"

# Everything this file prints is deliberately ASCII, because a Windows console
# is usually cp850/cp1252 and renders anything else as a replacement glyph.
# The project path is the exception - it comes from the filesystem, so a user
# called e.g. "Jose Ramirez" with an accent would otherwise crash the launcher
# on an encoding error before it printed anything useful. Degrading those
# characters is fine; dying over them is not.
for _stream in (sys.stdout, sys.stderr):
    with contextlib.suppress(AttributeError, OSError, ValueError):
        _stream.reconfigure(errors="replace")  # type: ignore[union-attr]


# ---------------------------------------------------------------- presentation


def hr() -> None:
    print("-" * 66)


def ask(prompt: str) -> str:
    """input() that treats a closed stdin as an empty answer rather than an
    exception - every prompt here has a safe default, so a redirected or
    piped run should take it, not crash."""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return ""


def banner() -> None:
    print()
    print("  TOMBSTONE")
    print("  Competitor acquisition intelligence for Abingdon Software Group")
    hr()


def die(message: str, *, hint: str = "") -> NoReturn:
    """Every exit path ends at the same pause - a launcher that vanishes on
    error tells a double-clicking user nothing at all."""
    print()
    print(f"  ERROR: {message}")
    if hint:
        print()
        for line in hint.strip().splitlines():
            print(f"  {line.strip()}")
    print()
    with contextlib.suppress(EOFError, KeyboardInterrupt):
        input("  Press Enter to close...")
    sys.exit(1)


# ------------------------------------------------------------------- locating


def find_project_root() -> Path:
    """Walk up from wherever this is running until docker-compose.yml appears.

    Handles the exe sitting in dist/ as happily as the script running from
    launcher/, so the build output can be moved without breaking.
    """
    start = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent
    for candidate in (start, *start.parents):
        if (candidate / "docker-compose.yml").is_file():
            return candidate
    die(
        "Could not find the Tombstone project files.",
        hint="""
        Tombstone.exe must stay inside the repository folder - it starts the
        stack described by docker-compose.yml, which lives alongside it.
        If you moved the .exe somewhere else, move it back next to
        docker-compose.yml (or into dist/) and run it again.
        """,
    )


# --------------------------------------------------------------------- docker


def run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60, **kwargs)  # type: ignore[call-overload,no-any-return]


def check_docker() -> None:
    """Docker missing and Docker installed-but-asleep are different problems
    with different fixes, so they get different messages."""
    print("  Checking Docker...")
    try:
        run(["docker", "--version"])
    except (FileNotFoundError, OSError):
        die(
            "Docker Desktop is not installed.",
            hint="""
            Tombstone runs in containers so it behaves the same on any machine.
            Install Docker Desktop, start it, then run this again:
              https://www.docker.com/products/docker-desktop/
            """,
        )
    except subprocess.TimeoutExpired:
        die("Docker did not respond. Is Docker Desktop still starting up?")

    try:
        probe = run(["docker", "info"])
    except subprocess.TimeoutExpired:
        die("Docker is installed but not responding. Try restarting Docker Desktop.")

    if probe.returncode != 0:
        die(
            "Docker Desktop is installed but not running.",
            hint="""
            Start Docker Desktop, wait for the whale icon to stop animating,
            then run this again.
            """,
        )
    print("  Docker is running.")


# ------------------------------------------------------------------------ env


def read_env(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key, _, value = stripped.partition("=")
            values[key.strip()] = value.strip()
    return values


def write_key_into_env(root: Path, key: str) -> None:
    """Writes the key into .env, seeding the file from .env.example so the
    budget ceiling and tracking window arrive documented rather than absent.
    Only the key line is rewritten - any other local edits survive.
    """
    env_path = root / ".env"
    template_path = root / ".env.example"

    if env_path.is_file():
        source = env_path.read_text(encoding="utf-8")
    elif template_path.is_file():
        source = template_path.read_text(encoding="utf-8")
    else:
        die(".env.example is missing from the project folder.")

    lines = source.splitlines()
    replaced = False
    for i, line in enumerate(lines):
        if line.strip().startswith("ANTHROPIC_API_KEY="):
            lines[i] = f"ANTHROPIC_API_KEY={key}"
            replaced = True
            break
    if not replaced:
        lines.append(f"ANTHROPIC_API_KEY={key}")

    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_secret(prompt: str) -> str:
    """Masked read when a human is at a console, plain read when not.

    On Windows getpass reads straight from the console device and ignores
    piped stdin entirely, so a redirected run hangs forever waiting for a
    keystroke that can never arrive. Branching on isatty keeps the masking
    for the double-click case while letting the launcher be driven by a
    script or a test.
    """
    if sys.stdin is not None and sys.stdin.isatty():
        return getpass(prompt)
    print(prompt, end="", flush=True)
    line = sys.stdin.readline() if sys.stdin is not None else ""
    if not line:
        raise EOFError
    return line


def prompt_for_key() -> str:
    """The key is never echoed back, never logged, and never printed - it
    goes straight into .env, which is gitignored."""
    print()
    print("  Paste your Anthropic API key (starts with sk-ant-).")
    print("  Nothing appears as you type or paste - that is intentional.")
    print("  It is saved only to the local .env file, which is never committed.")
    print()
    print("  Press Enter with no key to browse the existing results instead")
    print("  (the dashboard opens read-only; no key needed, nothing is spent).")
    print()

    while True:
        try:
            key = read_secret("  API key: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return ""

        if not key:
            return ""
        if key.startswith(KEY_PREFIX):
            return key

        print()
        print(f"  That does not look like an Anthropic key - they start with '{KEY_PREFIX}'.")
        print("  Try again, or press Enter to continue without one.")
        print()


def ensure_key(root: Path) -> bool:
    """True if a key is configured. Never reprints a stored key, and never
    silently replaces one - an existing key is confirmed, not clobbered."""
    existing = read_env(root / ".env").get("ANTHROPIC_API_KEY", "")

    if existing:
        print()
        print(f"  An API key is already saved in .env (ends ...{existing[-4:]}).")
        answer = ask("  Press Enter to keep it, or type 'new' to replace it: ").lower()
        if answer != "new":
            return True

    key = prompt_for_key()
    if not key:
        print()
        print("  No key set - starting in read-only mode.")
        print("  The dashboard will show the results committed to the repository.")
        return False

    write_key_into_env(root, key)
    print()
    print("  Key saved to .env.")
    return True


# ------------------------------------------------------------------- lifecycle


def compose(root: Path, *args: str) -> int:
    """Streams output rather than capturing it - the first build pulls images
    and takes minutes, and a silent window reads as a hang."""
    return subprocess.call(["docker", "compose", *args], cwd=root)


def wait_for_dashboard() -> bool:
    print()
    print("  Waiting for the dashboard to come up...")
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(DASHBOARD_URL, timeout=3) as response:
                if response.status < 500:
                    return True
        except (urllib.error.URLError, OSError, TimeoutError):
            time.sleep(2)
    return False


def main() -> None:
    banner()
    root = find_project_root()
    print(f"  Project: {root}")
    print()

    check_docker()
    has_key = ensure_key(root)

    print()
    hr()
    print("  Starting Tombstone. The first run builds the images and can take")
    print("  several minutes; later runs start in seconds.")
    hr()
    print()

    if compose(root, "up", "--build", "-d") != 0:
        die(
            "Docker failed to start the stack.",
            hint="""
            The output above has the reason. The usual causes are port 5173 or
            8000 already being in use by another process, or Docker Desktop
            running low on disk space.
            """,
        )

    if not wait_for_dashboard():
        die(
            "The stack started but the dashboard never became reachable.",
            hint=f"""
            Check what the containers are saying:
              docker compose logs
            Then stop them with:
              docker compose down
            The dashboard should have appeared at {DASHBOARD_URL}
            """,
        )

    print()
    hr()
    print(f"  Tombstone is running:  {DASHBOARD_URL}")
    hr()
    print()
    print("  The dashboard shows the acquisitions already researched and")
    print("  verified, with the source quote behind every field.")
    print()

    if has_key:
        print("  To research a competitor live (this spends against your key,")
        print("  bounded by RUN_BUDGET_USD in .env), run in another terminal:")
        print()
        print('    curl -X POST "http://localhost:8000/runs?acquirer=volaris"')
        print()
        print("  Acquirer slugs: volaris, valsoft, everfield, banyan,")
        print("                  snowball, tss_topicus, bsg")
    else:
        print("  No API key is configured, so live runs are unavailable.")
        print("  Run this launcher again and paste a key to enable them.")

    print()
    webbrowser.open(DASHBOARD_URL)

    print()
    ask("  Press Enter to stop Tombstone and shut the containers down...")
    print()
    print("  Stopping...")
    compose(root, "down")
    print("  Stopped.")
    time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print("  Cancelled.")
    except Exception as exc:  # noqa: BLE001 - last resort: never vanish silently
        die(f"Unexpected problem: {exc}")
