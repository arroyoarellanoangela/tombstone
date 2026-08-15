"""FastAPI app. Thin by design — holds no business logic that isn't already
in domain/ or agents/. Two jobs: serve the committed snapshot, and (local
use only — see docker-compose.yml) trigger a live run.

Never deploy this publicly with a real ANTHROPIC_API_KEY: every /runs POST
spends the client's prepaid credits. The public-facing dashboard reads
data/*.json as static files instead (see docs/ARCHITECTURE_NOTE.html,
"Deployment").
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router

app = FastAPI(title="Tombstone API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
)
app.include_router(router)
