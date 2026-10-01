"""
Smoke test: every public GET endpoint answers 200 in mock mode.
Catches broken routes or import errors quickly before the Docker image is built.
"""
import pytest

ENDPOINTS = [
    "/api/fixtures/1001/lineups",
    "/api/fixtures/1001/events",
    "/api/fixtures/1001/statistics",
    "/api/fixtures/1001/players",
    "/api/fixtures/1001/h2h",
    "/api/fixtures/1001/predictions",
    "/api/leagues/39/fixtures",
    "/api/leagues/39/bracket",
    "/api/leagues/39/seasons",
    "/api/leagues/all",
    "/api/country/brazil/fixtures",
    "/api/topscorers",
    "/api/topassists",
    "/api/topyellowcards",
    "/api/topredcards",
    "/api/players/874",
    "/api/players/874/career",
    "/api/players/874/motm",
    "/api/players/874/history",
    "/api/teams/33",
    "/api/teams/33/fixtures",
    "/api/teams/33/upcoming",
    "/api/teams/33/insights",
    "/api/match-search?q=arsenal%20vs%20chelsea",
]


@pytest.mark.parametrize("path", ENDPOINTS)
def test_endpoint_responds_ok(client, path):
    assert client.get(path).status_code == 200
