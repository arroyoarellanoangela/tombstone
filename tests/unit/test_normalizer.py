from datetime import UTC, datetime, timedelta

from src.agents.normalizer import normalize
from src.domain.models import DealCandidate

NOW = datetime(2026, 8, 15, tzinfo=UTC)


def _candidate(url: str, snippet: str, days_ago: int | None = None) -> DealCandidate:
    published_at = NOW - timedelta(days=days_ago) if days_ago is not None else None
    return DealCandidate(acquirer_slug="volaris", url=url, published_at=published_at, snippet=snippet)


def test_duplicate_urls_are_collapsed():
    candidates = [
        _candidate("https://volarisgroup.com/a", "acquires Acme", days_ago=10),
        _candidate("https://volarisgroup.com/a", "acquires Acme", days_ago=10),
    ]
    result = normalize(candidates, window_days=90, now=NOW)
    assert len(result.kept) == 1


def test_out_of_window_candidate_is_omitted():
    candidates = [_candidate("https://volarisgroup.com/old", "acquires Acme", days_ago=200)]
    result = normalize(candidates, window_days=90, now=NOW)

    assert result.kept == []
    assert len(result.omitted) == 1
    assert result.omitted[0].stage == "window"


def test_candidate_with_no_date_is_kept_not_penalized():
    candidates = [_candidate("https://volarisgroup.com/undated", "acquires Acme", days_ago=None)]
    result = normalize(candidates, window_days=90, now=NOW)
    assert len(result.kept) == 1


def test_minority_stake_is_omitted_with_deal_definition_reason():
    candidates = [_candidate("https://volarisgroup.com/minority", "acquires a minority stake in Acme", days_ago=5)]
    result = normalize(candidates, window_days=90, now=NOW)

    assert result.kept == []
    assert result.omitted[0].stage == "deal_definition"


def test_majority_acquisition_within_window_is_kept():
    candidates = [_candidate("https://volarisgroup.com/real-deal", "acquires Acme Software", days_ago=30)]
    result = normalize(candidates, window_days=90, now=NOW)

    assert len(result.kept) == 1
    assert result.omitted == []
