"""
Unit tests for the real-API request path (_request) using a FAKE HTTP client.
No network call is made: httpx.AsyncClient is replaced with a stub that records calls.
"""
import asyncio

import pytest

import api_football as af


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def make_fake_client(payload, calls):
    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def get(self, url, params=None, headers=None):
            calls.append((url, params, headers))
            return FakeResponse(payload)

    return FakeClient


@pytest.fixture(autouse=True)
def fresh_cache(monkeypatch):
    monkeypatch.setattr(af, "cache", af.TTLCache(60))


def test_request_sends_api_key_header_and_caches(monkeypatch):
    calls = []
    monkeypatch.setattr(af.httpx, "AsyncClient", make_fake_client({"errors": [], "response": [1]}, calls))
    monkeypatch.setattr(af, "HEADERS", {"x-apisports-key": "test-key"})

    first = asyncio.run(af._request("/status"))
    second = asyncio.run(af._request("/status"))

    assert first == second == {"errors": [], "response": [1]}
    assert len(calls) == 1, "second call should be served from the cache"
    assert calls[0][2] == {"x-apisports-key": "test-key"}


def test_error_responses_are_not_cached(monkeypatch):
    # API-Football returns HTTP 200 + an 'errors' field when rate-limited; that must not be cached.
    calls = []
    monkeypatch.setattr(af.httpx, "AsyncClient", make_fake_client({"errors": {"rateLimit": "too many"}, "response": []}, calls))

    asyncio.run(af._request("/fixtures", {"date": "2026-10-01"}))
    asyncio.run(af._request("/fixtures", {"date": "2026-10-01"}))

    assert len(calls) == 2, "an error response must trigger a fresh request next time"
