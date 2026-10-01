from fastapi import APIRouter, HTTPException, Request

import api_football
import config
import mock_data
from ratelimit import limiter

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search")
@limiter.shared_limit("40/minute", scope="search")
async def search(request: Request, q: str = ""):
    """Search teams + players by name (for the search box in the header).
    Rate limit: calls /players/profiles several times -> blocks spam but is loose enough for normal typing."""
    return await api_football.search(q)


@router.get("/match-search")
@limiter.shared_limit("40/minute", scope="search")
async def match_search(request: Request, q: str = ""):
    """Match search. Type 'A vs B' -> head-to-head of two teams; type one team -> that team's fixtures.
    Returns {mode, teamA/teamB or team, recent: [...], upcoming: [...]}."""
    if not (q or "").strip():
        return {"mode": "team", "team": None, "recent": [], "upcoming": []}
    return await api_football.match_search(q)


@router.get("/_debug/players")
async def debug_players(search: str = ""):
    """Show the raw API output for player search (for debugging).
    ONLY runs when DEBUG=true; returns 404 in production."""
    if not config.settings.debug:
        raise HTTPException(status_code=404, detail="Not found")
    try:
        return await api_football.raw_request("/players/profiles", {"search": search})
    except Exception as e:
        return {"error": str(e)}


@router.get("/leagues")
def leagues():
    """League list for the filter."""
    return {"response": mock_data.CURATED_LEAGUES}


@router.get("/leagues/all")
async def leagues_all():
    """List of ALL leagues (trimmed, cached 24h) for the client's league/country search box."""
    return {"response": await api_football.get_all_leagues()}
