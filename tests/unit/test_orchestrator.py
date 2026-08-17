"""Integration-style tests for run_for_acquirer — every agent monkeypatched,
DATA_DIR redirected to tmp_path, so the whole pipeline runs offline with no
key and no cost. Verifies the wiring (bounce loop, budget stop, snapshot
writing), not the agents themselves — those have their own tests.
"""

import json
from datetime import date

import pytest

from src.domain.models import (
    AcquirerProfile,
    Claim,
    ClaimStatus,
    DealCandidate,
    DealRecord,
    Omission,
)
from src.orchestrator import run as orchestrator
from src.orchestrator.budget import BudgetExceeded, RunBudget
from src.orchestrator.cache import Cache

PROFILE = AcquirerProfile(
    name="Volaris Group",
    slug="volaris",
    allowed_domains=["volarisgroup.com"],
)

CANDIDATE = DealCandidate(
    acquirer_slug="volaris",
    url="https://volarisgroup.com/press-room/acme",
    snippet="Volaris Group acquires Acme Software",
)


def _record(verified: bool = True) -> DealRecord:
    claim = Claim(
        field="target",
        status=ClaimStatus.VERIFIED,
        value="Acme Software",
        source_url=CANDIDATE.url,
        verbatim_quote="acquired Acme Software",
        verified=verified,
    )
    not_found = Claim(field="_", status=ClaimStatus.NOT_FOUND)
    return DealRecord(
        deal_id="volaris-acme-software",
        acquirer=claim.model_copy(update={"field": "acquirer", "value": "Volaris Group"}),
        target=claim,
        date_announced=not_found,
        target_description=not_found,
        geography=not_found,
        adviser=claim.model_copy(update={"field": "adviser", "value": "Some Bank"}),
        purchase_price=not_found,
        source_urls=[CANDIDATE.url],
    )


@pytest.fixture
def offline_pipeline(monkeypatch, tmp_path):
    """Patch every agent + data dir; returns a dict of call counters the
    tests can assert against."""
    calls = {"discovery": 0, "research": 0, "adviser_hunter": 0, "verify": 0}

    monkeypatch.setattr(orchestrator, "DATA_DIR", tmp_path)
    monkeypatch.setattr(orchestrator, "_load_profile", lambda slug: PROFILE)

    async def fake_discovery(profile, window_days, agent_caller=None):
        calls["discovery"] += 1
        return orchestrator.discovery.DiscoveryResult(candidates=[CANDIDATE])

    async def fake_research(
        candidate, acquirer_name, language="en", agent_caller=None, fetcher=None
    ):
        calls["research"] += 1
        return _record()

    async def fake_adviser_hunter(record, agent_caller=None):
        calls["adviser_hunter"] += 1
        return orchestrator.adviser_hunter.AdviserResult(
            claim=Claim(field="adviser", status=ClaimStatus.NOT_FOUND)
        )

    async def fake_verify_clean(record, round_number, fetcher=None):
        calls["verify"] += 1
        return orchestrator.verifier.VerificationResult(
            record=record, needs_rework=False, conflicts=[]
        )

    monkeypatch.setattr(orchestrator.discovery, "run", fake_discovery)
    monkeypatch.setattr(orchestrator.research, "run", fake_research)
    monkeypatch.setattr(orchestrator.adviser_hunter, "run", fake_adviser_hunter)
    monkeypatch.setattr(orchestrator.verifier, "verify", fake_verify_clean)

    return calls


@pytest.mark.asyncio
async def test_happy_path_writes_snapshot(offline_pipeline, tmp_path):
    budget = RunBudget(ceiling_usd=1.00)
    records = await orchestrator.run_for_acquirer("volaris", budget, Cache(tmp_path / "c.db"))

    assert len(records) == 1
    assert records[0].confidence is not None

    snapshots = list(tmp_path.glob("snapshot_*.json"))
    assert len(snapshots) == 1
    data = json.loads(snapshots[0].read_text(encoding="utf-8"))
    assert data[0]["deal_id"] == "volaris-acme-software"


@pytest.mark.asyncio
async def test_adviser_hunter_not_called_when_research_found_one(offline_pipeline, tmp_path):
    # fake_research returns a record whose adviser is already VERIFIED.
    await orchestrator.run_for_acquirer(
        "volaris", RunBudget(ceiling_usd=1.00), Cache(tmp_path / "c.db")
    )
    assert offline_pipeline["adviser_hunter"] == 0


@pytest.mark.asyncio
async def test_bounce_loop_reresearches_once_then_stops(offline_pipeline, monkeypatch, tmp_path):
    async def always_needs_rework(record, round_number, fetcher=None):
        offline_pipeline["verify"] += 1
        return orchestrator.verifier.VerificationResult(
            record=record,
            needs_rework=round_number < 2,  # bounce after round 1, stop at cap
            conflicts=["target: quote not found"],
        )

    monkeypatch.setattr(orchestrator.verifier, "verify", always_needs_rework)

    await orchestrator.run_for_acquirer(
        "volaris", RunBudget(ceiling_usd=1.00), Cache(tmp_path / "c.db")
    )

    assert offline_pipeline["research"] == 2  # initial + one bounce
    assert offline_pipeline["verify"] == 2  # round 1 + round 2


@pytest.mark.asyncio
async def test_budget_exhaustion_mid_run_keeps_completed_deals(
    offline_pipeline, monkeypatch, tmp_path
):
    async def broke_research(
        candidate, acquirer_name, language="en", agent_caller=None, fetcher=None
    ):
        raise BudgetExceeded(ceiling_usd=0.10, spent_usd=0.10)

    monkeypatch.setattr(orchestrator.research, "run", broke_research)

    records = await orchestrator.run_for_acquirer(
        "volaris", RunBudget(ceiling_usd=0.10), Cache(tmp_path / "c.db")
    )

    # The exhausted deal is dropped, not fabricated; the run itself completes.
    assert records == []
    snapshots = list(tmp_path.glob("snapshot_*.json"))
    assert json.loads(snapshots[0].read_text(encoding="utf-8")) == []

    # ...and it's disclosed rather than silently vanishing.
    omissions = json.loads((tmp_path / "omissions.json").read_text(encoding="utf-8"))
    assert [o["stage"] for o in omissions] == ["budget_exhausted"]


@pytest.mark.asyncio
async def test_discovery_stage_omissions_reach_the_omissions_file(
    offline_pipeline, monkeypatch, tmp_path
):
    """A lead Discovery found outside the allowlist (ranging beyond the
    starting domains, per the brief) must be disclosed, not just dropped —
    "if in doubt, leave it out and say so" as a file the client can read."""

    async def fake_discovery_with_omission(profile, window_days, agent_caller=None):
        return orchestrator.discovery.DiscoveryResult(
            candidates=[CANDIDATE],
            omitted=[
                Omission(
                    url="https://sector-press.example.com/volaris-deal",
                    reason="domain not in allowlist — treated as disallowed by default",
                    stage="allowlist",
                )
            ],
        )

    monkeypatch.setattr(orchestrator.discovery, "run", fake_discovery_with_omission)

    await orchestrator.run_for_acquirer(
        "volaris", RunBudget(ceiling_usd=1.00), Cache(tmp_path / "c.db")
    )

    omissions = json.loads((tmp_path / "omissions.json").read_text(encoding="utf-8"))
    assert [o["stage"] for o in omissions] == ["allowlist"]
    assert omissions[0]["url"] == "https://sector-press.example.com/volaris-deal"


@pytest.mark.asyncio
async def test_all_not_found_record_becomes_an_omission_not_a_deal(
    offline_pipeline, monkeypatch, tmp_path
):
    """A candidate we discovered but could extract nothing from is an
    omission to disclose, not an all-empty row implying a known deal."""
    not_found = Claim(field="_", status=ClaimStatus.NOT_FOUND)

    async def empty_research(
        candidate, acquirer_name, language="en", agent_caller=None, fetcher=None
    ):
        return DealRecord(
            deal_id="volaris-unknown-acme",
            acquirer=not_found,
            target=not_found,
            date_announced=not_found,
            target_description=not_found,
            geography=not_found,
            adviser=not_found,
            purchase_price=not_found,
            source_urls=[CANDIDATE.url],
        )

    monkeypatch.setattr(orchestrator.research, "run", empty_research)

    records = await orchestrator.run_for_acquirer(
        "volaris", RunBudget(ceiling_usd=1.00), Cache(tmp_path / "c.db")
    )

    assert records == []
    assert json.loads((tmp_path / f"snapshot_{date.today().isoformat()}.json").read_text()) == []

    omissions = json.loads((tmp_path / "omissions.json").read_text(encoding="utf-8"))
    assert [o["stage"] for o in omissions] == ["extraction_failed"]
    assert omissions[0]["url"] == CANDIDATE.url
