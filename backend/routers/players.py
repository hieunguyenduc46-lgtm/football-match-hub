from typing import Optional

from fastapi import APIRouter, HTTPException, Request

import api_football
import config
from ratelimit import limiter

router = APIRouter(prefix="/api", tags=["players"])


@router.get("/topscorers")
async def topscorers(league: int = 39, season: Optional[int] = None):
    """Top scorers of a competition. Defaults to the Premier League.
    The season is chosen per league (e.g. World Cup -> 2026) if the client does not pass one."""
    return {"response": await api_football.get_topscorers(league, season or config.season_for(league))}


@router.get("/topassists")
async def topassists(league: int = 39, season: Optional[int] = None):
    """Top assists of a competition. Same parameters as /topscorers."""
    return {"response": await api_football.get_topassists(league, season or config.season_for(league))}


@router.get("/topyellowcards")
async def topyellowcards(league: int = 39, season: Optional[int] = None):
    """Players with the most yellow cards in a competition."""
    return {"response": await api_football.get_topyellowcards(league, season or config.season_for(league))}


@router.get("/topredcards")
async def topredcards(league: int = 39, season: Optional[int] = None):
    """Players with the most red cards in a competition."""
    return {"response": await api_football.get_topredcards(league, season or config.season_for(league))}


@router.get("/players/{player_id}")
async def player_detail(player_id: int, season: Optional[int] = None):
    """Player details: photo + statistics (goals, assists, apps...)."""
    return {"response": await api_football.get_player(player_id, season or config.default_season())}


@router.get("/players/{player_id}/career")
@limiter.shared_limit("30/minute", scope="player_heavy")
async def player_career(request: Request, player_id: int):
    """Total official career goals (all clubs + national team, excluding friendlies).
    Loaded separately because it needs many seasons -> does not slow down the detail page.
    Rate limit: heavy endpoint (scans many seasons) -> blocks rapid calls for many different ids."""
    return await api_football.get_player_career(player_id)


@router.get("/players/{player_id}/motm")
@limiter.shared_limit("30/minute", scope="player_heavy")
async def player_motm(request: Request, player_id: int, season: Optional[int] = None):
    """Number of 'Player of the Match' awards (highest rating) in the season being viewed.
    API-Football does not provide it -> calculated by scanning fixtures. Loaded separately (lazy)
    because it uses many requests; results are cached for 6h in the api_football layer.
    Rate limit: the HEAVIEST endpoint (~50 requests per call) -> stops one IP calling many different ids."""
    return await api_football.get_player_motm(player_id, season or config.default_season())


@router.get("/players/{player_id}/history")
@limiter.shared_limit("30/minute", scope="player_heavy")
async def player_history(request: Request, player_id: int):
    """Player history: trophies + transfers + injuries + per-season statistics.
    LAZY-loaded (the frontend only calls it when the profile is opened). Scans many seasons -> heavy rate-limit group."""
    return await api_football.get_player_history(player_id)


@router.get("/_debug/player/{player_id}")
async def debug_player(player_id: int, season: Optional[int] = None):
    """Debug: list EVERY statistics entry (team / league / goals / apps) across 3 seasons,
    to investigate missing national team data. Open: /api/_debug/player/<id>
    ONLY runs when DEBUG=true; returns 404 in production so no data is exposed and no quota is used."""
    if not config.settings.debug:
        raise HTTPException(status_code=404, detail="Not found")
    base = season or config.default_season()
    out = {}
    for s in (base, base + 1, base - 1):
        try:
            data = await api_football.raw_request("/players", {"id": player_id, "season": s})
            resp = data.get("response", [])
            stats = resp[0].get("statistics", []) if resp else []
            out[s] = {
                "errors": data.get("errors"),
                "results": data.get("results"),
                "entries": [
                    {
                        "team": (x.get("team") or {}).get("name"),
                        "league": (x.get("league") or {}).get("name"),
                        "goals": (x.get("goals") or {}).get("total"),
                        "apps": (x.get("games") or {}).get("appearences"),
                    }
                    for x in stats
                ],
            }
        except Exception as e:
            out[s] = {"error": str(e)}
    return out
