# Tombstone

A multi-agent system that tracks acquisitions announced by Abingdon Software Group's competitors, researches each deal, verifies every extracted fact against its cited source, and publishes the result to a filterable dashboard.

Prepared for Abingdon Software Group by Angela Arroyo. Full reasoning and architecture: [docs/PROJECT_PROPOSAL.md](docs/PROJECT_PROPOSAL.md) · [docs/ARCHITECTURE_NOTE.html](docs/ARCHITECTURE_NOTE.html).

## Quick start

Three ways to look at this, easiest first:

**1. Double-click `Tombstone.exe` (Windows)**

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and start it — wait for the whale icon to stop animating.
2. Download this repository: green **Code** button → **Download ZIP** (or `git clone`).
3. **Unzip it.** Windows lets you open a ZIP as though it were a folder; running the `.exe` from inside that preview will not work.
4. Open the unzipped `tombstone-main` folder and double-click **`Tombstone.exe`**, leaving it where it is.

> ⚠️ **Do not move `Tombstone.exe` out of the folder** — not to your Desktop, not to Downloads.
> It is a launcher, not a self-contained application. It starts the containers defined in `docker-compose.yml`, which it locates by looking in its own folder and the folders above it. On its own it has nothing to launch, and it will say so rather than fail silently.

The launcher checks Docker, prompts for your Anthropic API key, writes it into `.env`, brings the stack up and opens the dashboard. Press Enter at the key prompt to skip it: the dashboard then opens read-only against the results committed to this repo, which costs nothing and needs no key. The first run builds the images and takes a few minutes; later runs start in seconds. Press Enter in the launcher window to stop everything and clean up the containers.

Source: [`launcher/tombstone_launcher.py`](launcher/tombstone_launcher.py); rebuild with `make launcher`. On macOS or Linux, use option 3 below — the `.exe` is Windows-only.

**2. Just browse the results (no setup, no cost)**
Open the dashboard link in the walkthrough invite — it's a static site reading the committed `data/snapshot_*.json`, no API key required, no cost to you.

**3. Run the full pipeline yourself**

```bash
cp .env.example .env        # add your ANTHROPIC_API_KEY
docker compose up --build
```

- Dashboard: [http://localhost:5173](http://localhost:5173)
- API: [http://localhost:8000](http://localhost:8000)

Starting the stack spends nothing: it serves the API and the dashboard against the committed snapshot. A live run is triggered explicitly, and only then does it spend against the key in `.env`:

```bash
curl -X POST "http://localhost:8000/runs?acquirer=volaris"
```

`RUN_BUDGET_USD` in `.env.example` is the hard ceiling per run. One acquirer costs roughly $0.50–$1.00 and takes a few minutes; the ceiling stops new agent calls once reached, so the run degrades to `not_found` fields rather than overspending. To browse with no API at all, run `make dev` — dashboard only, reading the last committed snapshot.

## Repository layout

The repo root itself is the backend — a flat `src/` (not pip-installed; imported directly as `from src.domain... `). `frontend/` is the one subfolder that sits outside `src/`.

```
tombstone/
├── Tombstone.exe    # double-click launcher (Windows) — see Quick start
├── src/             # agent pipeline, orchestrator, FastAPI dashboard API
├── sources/         # ToS allowlist + one profile per acquirer
├── tests/
├── launcher/        # source + PyInstaller spec for Tombstone.exe
├── frontend/        # React + Vite + Tailwind — the dashboard
├── data/            # committed snapshot + omissions log (the only data/ files tracked)
├── docs/            # proposal, architecture note
├── requirements.txt
└── requirements-dev.txt
```

Full directory-by-directory rationale: [docs/ARCHITECTURE_NOTE.html](docs/ARCHITECTURE_NOTE.html#repository-structure).

## Frontend

React 18 + TypeScript + Vite + Tailwind. Every field is rendered with its status (`verified` / `undisclosed` / `not found`) and its verbatim source quote on hover — an empty cell means no source supported that field, never a guess. Filters by acquirer, minimum confidence, price-disclosure status, and whether an adviser was identified; a separate Omissions tab lists every source the pipeline deliberately excluded and why.

```bash
cd frontend
npm install
npm run dev     # dev server on :5173
npm run build   # static production build into dist/
```

Two run modes, same codebase:

1. **Local dev**, against the live API — `docker-compose.yml` sets `VITE_API_URL=http://localhost:8000` and the dashboard reads `/deals` and `/omissions`.
2. **Static production build** — with no `VITE_API_URL` set, a prebuild step copies the committed `data/snapshot_*.json` and `data/omissions.json` into `public/data/` and the built site fetches those as plain files. No API, no key, nothing anyone can spend. This is the only mode ever deployed publicly (Vercel/Netlify free tier).

## What this is not

Not a live monitoring service and not exposed publicly with a working API key — see `CLAUDE.md` for why. The public link is read-only by design.
