from typing import Optional

from fastapi import APIRouter

import api_football
import config

router = APIRouter(prefix="/api", tags=["standings"])


@router.get("/standings")
async def standings(league: int = 39, season: Optional[int] = None):
    """Standings of a competition. Defaults to the Premier League (39).
    The season is chosen per league (e.g. World Cup -> 2026) if the client does not pass one."""
    return {"response": await api_football.get_standings(league, season or config.season_for(league))}
