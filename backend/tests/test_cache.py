"""Unit tests for the in-memory TTL cache."""
import cache as cache_module
from cache import TTLCache


def test_set_then_get_returns_value():
    c = TTLCache(ttl_seconds=60)
    c.set("k", {"a": 1})
    assert c.get("k") == {"a": 1}


def test_missing_key_returns_none():
    assert TTLCache().get("nope") is None


def test_entry_expires_after_ttl(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(cache_module.time, "time", lambda: now[0])
    c = TTLCache(ttl_seconds=10)
    c.set("k", "v")
    now[0] += 11  # move the clock past the TTL
    assert c.get("k") is None


def test_per_entry_ttl_overrides_default(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(cache_module.time, "time", lambda: now[0])
    c = TTLCache(ttl_seconds=10)
    c.set("live", "score", ttl=60)
    now[0] += 30
    assert c.get("live") == "score"
