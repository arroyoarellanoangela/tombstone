from src.orchestrator.cache import Cache


def test_miss_returns_none(tmp_path):
    cache = Cache(db_path=tmp_path / "cache.db")
    assert cache.get("discovery", {"acquirer": "volaris"}) is None


def test_set_then_get_round_trips(tmp_path):
    cache = Cache(db_path=tmp_path / "cache.db")
    cache.set("discovery", {"acquirer": "volaris"}, {"candidates": ["a", "b"]})
    assert cache.get("discovery", {"acquirer": "volaris"}) == {"candidates": ["a", "b"]}


def test_different_payloads_are_different_keys(tmp_path):
    cache = Cache(db_path=tmp_path / "cache.db")
    cache.set("discovery", {"acquirer": "volaris"}, "volaris-result")
    cache.set("discovery", {"acquirer": "banyan"}, "banyan-result")

    assert cache.get("discovery", {"acquirer": "volaris"}) == "volaris-result"
    assert cache.get("discovery", {"acquirer": "banyan"}) == "banyan-result"


def test_different_agent_same_payload_are_different_keys(tmp_path):
    cache = Cache(db_path=tmp_path / "cache.db")
    cache.set("discovery", {"x": 1}, "from-discovery")
    cache.set("research", {"x": 1}, "from-research")

    assert cache.get("discovery", {"x": 1}) == "from-discovery"
    assert cache.get("research", {"x": 1}) == "from-research"


def test_set_overwrites_existing_key(tmp_path):
    cache = Cache(db_path=tmp_path / "cache.db")
    cache.set("discovery", {"x": 1}, "first")
    cache.set("discovery", {"x": 1}, "second")

    assert cache.get("discovery", {"x": 1}) == "second"
