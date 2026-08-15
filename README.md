# Tombstone

A multi-agent system that tracks acquisitions announced by Abingdon Software Group's competitors, researches each deal, verifies every extracted fact against its cited source, and publishes the result to a filterable dashboard.

Prepared for Abingdon Software Group by Angela Arroyo. Full reasoning and architecture: [docs/PROJECT_PROPOSAL.md](docs/PROJECT_PROPOSAL.md) · [docs/ARCHITECTURE_NOTE.html](docs/ARCHITECTURE_NOTE.html).

## Quick start

Two ways to look at this, depending on what you want:

**Just browse the results (no setup, no cost)**
Open the dashboard link in the walkthrough invite — it's a static site reading the committed `data/snapshot_*.json`, no API key required, no cost to you.

**Run the full pipeline yourself**

```bash
cp .env.example .env        # add your ANTHROPIC_API_KEY
docker compose up --build
```

- Dashboard: [http://localhost:5173](http://localhost:5173)
- API: [http://localhost:8000](http://localhost:8000)

This runs the live agent pipeline against the key in `.env` and will spend against it — see `RUN_BUDGET_USD` in `.env.example` for the hard ceiling. To browse without spending anything, run `make dev` instead: it serves the dashboard against the last committed snapshot only, no LLM calls.

## Repository layout

The repo root itself is the backend — a flat `src/` (not pip-installed; imported directly as `from src.domain... `). `frontend/` is the one subfolder that sits outside `src/`.

```
tombstone/
├── src/             # agent pipeline, orchestrator, FastAPI dashboard API
├── sources/         # ToS allowlist + one profile per acquirer
├── tests/
├── frontend/        # React + Vite + Tailwind — the dashboard
├── data/            # committed snapshot + omissions log (the only data/ files tracked)
├── docs/            # proposal, architecture note
├── requirements.txt
└── requirements-dev.txt
```

Full directory-by-directory rationale: [docs/ARCHITECTURE_NOTE.html](docs/ARCHITECTURE_NOTE.html#repository-structure).

## Frontend

Not yet scaffolded. Planned:

```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install -D tailwindcss postcss autoprefixer
```

React 18 + TypeScript + Vite + Tailwind. Filters by acquirer, geography, confidence, and price-disclosure status; an Omissions tab reads `data/omissions.json` directly. Two run modes, same codebase:

1. **Local dev**, against the live API (`docker-compose.yml` sets `VITE_API_URL=http://localhost:8000`) — can trigger a live pipeline run via `POST /runs`.
2. **Static production build**, reading `data/snapshot_*.json` and `data/omissions.json` directly at build time, no API calls at runtime. This is the only mode ever deployed publicly — planned on Vercel/Netlify's free tier, on a subdomain of the author's own domain, with no backend involved, so nobody can spend Abingdon's API credits by finding the link. Last item on the build list, a bonus on top of the deliverable — `docker compose up` alone already satisfies "runnable by us."

## What this is not

Not a live monitoring service and not exposed publicly with a working API key — see `CLAUDE.md` for why. The public link is read-only by design.
