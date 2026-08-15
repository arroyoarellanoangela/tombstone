.PHONY: install dev run test lint typecheck build up down

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
	ruff check src/ tests/

typecheck:
	mypy src/

# Full local stack: API + orchestrator, wired to the frontend dev server.
up:
	docker compose up --build

down:
	docker compose down

# Static build of the dashboard against the committed snapshot — no backend needed.
static:
	cd frontend && npm run build
