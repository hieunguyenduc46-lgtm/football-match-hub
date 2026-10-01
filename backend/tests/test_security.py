"""Security-related behaviour: debug endpoints, unknown routes, rate limiting and CORS."""
import pytest


@pytest.mark.parametrize("path", [
    "/api/_debug/fixtures",
    "/api/_debug/players",
    "/api/_debug/player/874",
])
def test_debug_endpoints_are_hidden_when_debug_is_off(client, path):
    # Debug endpoints expose raw API output; in production (DEBUG=false) they must return 404.
    assert client.get(path).status_code == 404


def test_unknown_route_returns_404(client):
    assert client.get("/api/does-not-exist").status_code == 404


def test_search_is_rate_limited(client):
    # /api/search allows 40 requests/minute per IP; the 41st must be rejected with 429.
    for _ in range(40):
        assert client.get("/api/search?q=messi").status_code == 200
    assert client.get("/api/search?q=messi").status_code == 429


def test_cors_allows_the_frontend_origin(client):
    r = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_blocks_unknown_origins(client):
    r = client.get("/api/health", headers={"Origin": "https://evil.example.com"})
    assert "access-control-allow-origin" not in r.headers
