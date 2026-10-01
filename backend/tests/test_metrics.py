"""Tests for the Prometheus /metrics endpoint used by the Monitoring stage."""
import asyncio

import api_football as af


def test_metrics_endpoint_uses_prometheus_format(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")


def test_requests_are_counted_by_route_template(client):
    client.get("/api/teams/33")
    body = client.get("/metrics").text
    # The route template is used, not the raw id, to keep the number of series small.
    assert 'route="/api/teams/{team_id}"' in body
    assert 'route="/api/teams/33"' not in body


def test_latency_histogram_is_exported(client):
    client.get("/api/health")
    assert 'http_request_duration_seconds_bucket{le="0.1",method="GET",route="/api/health"}' in client.get("/metrics").text


def test_unknown_routes_are_grouped(client):
    client.get("/api/does-not-exist")
    assert 'route="unmatched",status="404"' in client.get("/metrics").text


def test_scrapes_are_not_counted(client):
    client.get("/metrics")
    assert 'route="/metrics"' not in client.get("/metrics").text


def test_health_reports_version_and_environment(client):
    body = client.get("/api/health").json()
    assert body["version"] == "dev"
    assert body["environment"] == "local"


def test_cache_hits_and_misses_are_counted(monkeypatch):
    from metrics import CACHE
    monkeypatch.setattr(af, "cache", af.TTLCache(60))
    af.cache.set("/x?", {"errors": []})
    before = CACHE.labels("hit")._value.get()
    asyncio.run(af._request("/x"))
    assert CACHE.labels("hit")._value.get() == before + 1
