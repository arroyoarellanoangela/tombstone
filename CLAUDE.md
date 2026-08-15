# Tombstone

Multi-agent competitor acquisition tracker, built for Abingdon Software Group.
Full reasoning: [docs/ARCHITECTURE_NOTE.html](docs/ARCHITECTURE_NOTE.html) · [docs/PROJECT_PROPOSAL.md](docs/PROJECT_PROPOSAL.md).

## Quick Facts

- Stack: Python 3.12, Claude Agent SDK, FastAPI, React + Vite + Tailwind, SQLite (local cache only)
- Install: `pip install -r requirements-dev.txt` (deps live in requirements.txt / requirements-dev.txt — no pyproject.toml packaging)
- Test: `pytest tests/ -v --cov=src`
- Lint: `ruff check src/ tests/`
- Typecheck: `mypy src/`
- Local full run: `docker compose up --build` (API `:8000`, frontend `:5173`)
- Dashboard API (no LLM calls, serves the committed snapshot): `make dev`
- Live pipeline run: `make run ACQUIRER=volaris`

## Key Directories

The repo root itself is the backend — `src/` is a flat, plain package (`src/domain/`, `src/agents/`, ...), not a nested `src/tombstone/` folder. This repo isn't pip-installed; `src` is imported directly (`from src.domain.models import Claim`), same convention as the rest of the Crata repos. `frontend/` is the one subfolder that isn't part of `src/`.

- `src/domain/` — Claim, DealRecord, scoring rubric, deal definition. Pure logic, **no framework imports**. If you need FastAPI or the Agent SDK to write a test here, the code is in the wrong place.
- `src/agents/` — one file per pipeline stage (discovery, normalizer, research, adviser_hunter, verifier, scorer). Each does one job; see each file's docstring for its contract.
- `src/orchestrator/` — deterministic control flow: budget, cache, retries, run state. Never delegate this to an LLM call.
- `src/utils/fetch.py` — the **only** place a network request may originate. Every fetch goes through the ToS allowlist here first.
- `sources/allowlist.yaml` — per-domain ToS gate. A domain absent from this file is disallowed by default (fail closed).
- `sources/profiles/` — one YAML per acquirer (domains, language, source type). Adding an acquirer is a new profile, not a code change.
- `data/` — only `snapshot_*.json` and `omissions.json` are committed. `cache.db` is gitignored local state.
- `frontend/` — the dashboard; reads `data/*.json` directly for the public static deployment, or the live API in local dev.

## Code Style

- Python: snake_case for functions/variables, PascalCase for classes, `StrEnum` for closed string sets (see `domain/models.py`).
- Pydantic models are the source of truth for every cross-boundary data shape — no bare dicts crossing an agent/API boundary.
- `__init__.py` files stay empty. No re-exports, no side effects on import.
- Async for anything that fetches or calls the API; sync for pure domain logic.

## NEVER Do

- Put a value in a `Claim` without a `verbatim_quote` — the model validator will already reject it; don't work around that.
- Fetch a URL outside `utils.fetch.fetch()` — it's the only place the allowlist is enforced.
- Let an agent report its own confidence score — confidence is computed in `domain/scoring.py`, always.
- Translate a source document before extraction — quote-grounding must match the original page text; translate only for display, after extraction.
- Deploy the API (`src/api/`) publicly — it spends the client's real prepaid credits on every request. Public access is the static frontend reading `data/*.json` only.
- Commit `data/cache.db` — it's local run state, not a deliverable.

## Architecture Decisions

- Claude Agent SDK over LangGraph — the workflow is a bounded fan-out/fan-in with one conditional loop, not a complex stateful graph.
- Verifier re-fetches and does literal quote substring matching, not a second LLM opinion — a hallucinated quote can't exist on a real fetched page.
- Three-state Claim status (`verified` / `explicitly_undisclosed` / `not_found`) — a well-handled "undisclosed" is a first-class pass, not a gap.
- Compliance allowlist enforced at the fetch layer, not by prompt instruction — a network gate can't be talked past under pressure to find data.

Full rationale for every decision above: [docs/PROJECT_PROPOSAL.md](docs/PROJECT_PROPOSAL.md), section 7.
