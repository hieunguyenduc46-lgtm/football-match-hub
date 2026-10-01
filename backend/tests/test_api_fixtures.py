"""Integration tests for the fixtures endpoints (mock data, no network)."""


def test_fixtures_list_has_expected_shape(client):
    r = client.get("/api/fixtures")
    assert r.status_code == 200
    data = r.json()["response"]
    assert len(data) > 0
    for f in data:
        assert {"fixture", "league", "teams", "goals"} <= f.keys()


def test_fixtures_filter_by_date(client):
    first = client.get("/api/fixtures").json()["response"][0]
    day = first["fixture"]["date"][:10]
    data = client.get(f"/api/fixtures?date={day}").json()["response"]
    assert data, "expected at least one fixture on that date"
    assert all(f["fixture"]["date"].startswith(day) for f in data)


def test_fixtures_filter_by_league(client):
    data = client.get("/api/fixtures?league=39").json()["response"]
    assert all(f["league"]["id"] == 39 for f in data)


def test_invalid_date_does_not_crash_server(client):
    # A bad date with a league filter must fall back to a default season, not return HTTP 500.
    r = client.get("/api/fixtures?league=39&date=abc")
    assert r.status_code == 200
    assert isinstance(r.json()["response"], list)


def test_fixture_detail_by_id(client):
    fid = client.get("/api/fixtures").json()["response"][0]["fixture"]["id"]
    data = client.get(f"/api/fixtures/{fid}").json()["response"]
    assert len(data) == 1
    assert data[0]["fixture"]["id"] == fid


def test_fixture_id_must_be_an_integer(client):
    # Input validation: FastAPI rejects a non-numeric id with 422 instead of crashing.
    assert client.get("/api/fixtures/abc").status_code == 422
