"""Integration tests for the health endpoint (used by Deploy smoke tests and Monitoring)."""


def test_health_returns_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health_reports_mock_mode_in_tests(client):
    # Proves the test setup works: the pipeline never calls the paid API.
    assert client.get("/api/health").json()["mock_mode"] is True


def test_health_accepts_head_for_uptime_monitors(client):
    # Uptime monitors often ping with HEAD; a 405 here would be reported as 'Down'.
    assert client.head("/api/health").status_code == 200
