from typing import Optional

from fastapi import APIRouter

import api_football
import config

router = APIRouter(prefix="/api", tags=["standings"])


@router.get("/standings")
async def standings(league: int = 39, season: Optional[int] = None):
    """Bảng xếp hạng 1 giải. Mặc định Premier League (39).
    Mùa tự chọn theo giải (vd World Cup -> 2026) nếu client không truyền season."""
    return {"response": await api_football.get_standings(league, season or config.season_for(league))}
