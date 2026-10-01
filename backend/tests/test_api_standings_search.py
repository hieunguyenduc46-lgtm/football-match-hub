"""Integration tests for standings, leagues and search endpoints."""


def test_standings_default_is_premier_league(client):
    r = client.get("/api/standings")
    assert r.status_code == 200
    league = r.json()["response"][0]["league"]
    assert league["id"] == 39
    assert league["name"] == "Premier League"


def test_standings_rows_are_sorted_by_rank(client):
    league = client.get("/api/standings?league=140").json()["response"][0]["league"]
    assert league["name"] == "La Liga"
    table = league["standings"][0]
    ranks = [row["rank"] for row in table]
    assert ranks == sorted(ranks)
    assert ranks[0] == 1


def test_leagues_list_contains_premier_league(client):
    leagues = client.get("/api/leagues").json()["response"]
    assert {"id": 39, "name": "Premier League"} in leagues


def test_search_finds_player_by_name(client):
    players = client.get("/api/search?q=messi").json()["players"]
    assert any(p["id"] == 154 for p in players)


def test_match_search_with_empty_query_returns_empty_result(client):
    r = client.get("/api/match-search?q=")
    assert r.status_code == 200
    assert r.json() == {"mode": "team", "team": None, "recent": [], "upcoming": []}
