from typing import Optional

from fastapi import APIRouter, HTTPException

import api_football
from config import CALENDAR_YEAR_LEAGUES, LEAGUE_SEASON, default_season, settings

router = APIRouter(prefix="/api", tags=["fixtures"])


@router.get("/fixtures")
async def list_fixtures(date: Optional[str] = None, league: Optional[int] = None,
                        season: Optional[int] = None, tz: Optional[str] = None):
    """Fixture list. Filter by ?date=YYYY-MM-DD, ?league=, ?season=, ?tz=timezone.

    API-Football: filtering by league REQUIRES a season. If no season is given,
    infer it from the date (European season: month >= 7 belongs to that year's season, earlier = previous year).
    tz = viewer's timezone -> the API returns dates and times in their local time.
    """
    if league and not season:
        # Infer the season from the date; an invalid date (e.g. "abc") falls back to the default season
        # instead of raising ValueError -> avoids returning a 500 to the caller.
        try:
            if league in LEAGUE_SEASON:
                # Special competitions (World Cup 2026, ...): the season is PINNED, NOT inferred from the month.
                # (Previously the World Cup on 13/6 was inferred as 2025 -> the filter returned nothing even though there were matches.)
                season = LEAGUE_SEASON[league]
            elif date and len(date) >= 7:
                y, m = int(date[:4]), int(date[5:7])
                if league in CALENDAR_YEAR_LEAGUES:
                    season = y                       # calendar-year league: use the exact year
                else:
                    season = y if m >= 7 else y - 1  # European league: season spans 2 years
            else:
                season = default_season()
        except (TypeError, ValueError):
            season = default_season()
    return {"response": await api_football.get_fixtures(date, league, season, tz)}


@router.get("/leagues/{league_id}/fixtures")
async def league_fixtures(league_id: int, season: Optional[int] = None):
    """Recent (results) + upcoming fixtures of a league. For the 'Fixtures' tab on the league page.
    season: use the selected season; if not given -> latest matches (live)."""
    return await api_football.get_league_fixtures(league_id, season=season)


@router.get("/country/{name}/fixtures")
async def country_fixtures(name: str):
    """Recent + upcoming matches of a national team (Vietnamese names accepted)."""
    return await api_football.get_country_fixtures(name)


@router.get("/leagues/{league_id}/bracket")
async def league_bracket(league_id: int, season: Optional[int] = None):
    """Knockout matches of a competition -> the client builds the bracket diagram. [] if none.
    season: the season to view (if not given -> the league's default season)."""
    return {"response": await api_football.get_bracket(league_id, season)}


@router.get("/leagues/{league_id}/seasons")
async def league_seasons(league_id: int):
    """Seasons that have data (for the season dropdown on the league page)."""
    return {"response": await api_football.get_league_seasons(league_id)}


@router.get("/_debug/fixtures")
async def debug_fixtures(date: Optional[str] = None, league: Optional[int] = None, season: Optional[int] = None):
    """Show the raw API output (for debugging). ONLY runs when DEBUG=true; returns 404 in production."""
    if not settings.debug:
        raise HTTPException(status_code=404, detail="Not found")
    params = {}
    if date:
        params["date"] = date
    if league:
        params["league"] = league
    if season:
        params["season"] = season
    try:
        return await api_football.raw_request("/fixtures", params)
    except Exception as e:
        return {"error": str(e)}


@router.get("/fixtures/{fixture_id}")
async def fixture_detail(fixture_id: int):
    """Details of one match by id."""
    return {"response": await api_football.get_fixture(fixture_id)}


@router.get("/fixtures/{fixture_id}/lineups")
async def fixture_lineups(fixture_id: int):
    """Starting line-ups of both teams (formation + grid positions)."""
    return {"response": await api_football.get_lineups(fixture_id)}


@router.get("/fixtures/{fixture_id}/events")
async def fixture_events(fixture_id: int):
    """Match events: goals / cards / substitutions by minute."""
    return {"response": await api_football.get_events(fixture_id)}


@router.get("/fixtures/{fixture_id}/statistics")
async def fixture_statistics(fixture_id: int):
    """Match statistics: possession, shots, xG..."""
    return {"response": await api_football.get_statistics(fixture_id)}


@router.get("/fixtures/{fixture_id}/players")
async def fixture_players(fixture_id: int):
    """Post-match player ratings."""
    return {"response": await api_football.get_fixture_players(fixture_id)}


@router.get("/fixtures/{fixture_id}/h2h")
async def fixture_h2h(fixture_id: int, home: int = 0, away: int = 0):
    """Head-to-head history of the two teams in this match."""
    return {"response": await api_football.get_h2h(fixture_id, home, away)}


@router.get("/fixtures/{fixture_id}/predictions")
async def fixture_predictions(fixture_id: int):
    """Match prediction: win/draw/loss probabilities + advice + form comparison. {} if none."""
    return {"response": await api_football.get_predictions(fixture_id)}
