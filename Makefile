.PHONY: install dev run test lint format typecheck check up down static launcher

install:
	pip install -r requirements-dev.txt

# Serves the dashboard API against the last committed snapshot — no LLM calls.
dev:
	python -m uvicorn src.api.main:app --reload --port 8000

# Runs the full agent pipeline against the live Claude API for one acquirer.
# Usage: make run ACQUIRER=volaris
run:
	python -m src.orchestrator.run --acquirer $(ACQUIRER)

test:
	pytest tests/ -v --cov=src

lint:
	ruff check src/ tests/ launcher/
	ruff format --check src/ tests/ launcher/

format:
	ruff check --fix src/ tests/ launcher/
	ruff format src/ tests/ launcher/

typecheck:
	mypy src/ launcher/

# Rebuilds Tombstone.exe (the double-click launcher) at the repo root.
# Windows only — PyInstaller emits a binary for the OS it runs on.
launcher:
	python -m PyInstaller launcher/tombstone.spec --noconfirm --distpath . --workpath build/pyinstaller

# Everything CI runs, in one command — run this before pushing.
check: lint typecheck test
	cd frontend && npm run lint

# Full local stack: API + orchestrator, wired to the frontend dev server.
up:
	docker compose up --build

down:
	docker compose down

# Static build of the dashboard against the committed snapshot — no backend needed.
static:
	cd frontend && npm run build
