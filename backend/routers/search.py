from fastapi import APIRouter

import api_football
import mock_data

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search")
async def search(q: str = ""):
    """Tìm đội + cầu thủ theo tên (cho ô search ở header)."""
    return await api_football.search(q)


@router.get("/match-search")
async def match_search(q: str = ""):
    """Tìm trận đấu. Gõ 'A vs B' -> đối đầu 2 đội; gõ 1 đội -> lịch đấu đội đó.
    Trả {mode, teamA/teamB hoặc team, recent: [...], upcoming: [...]}."""
    if not (q or "").strip():
        return {"mode": "team", "team": None, "recent": [], "upcoming": []}
    return await api_football.match_search(q)


@router.get("/_debug/players")
async def debug_players(search: str = ""):
    """Xem nguyên văn API trả về cho tìm kiếm cầu thủ (để chẩn lỗi)."""
    try:
        return await api_football.raw_request("/players/profiles", {"search": search})
    except Exception as e:
        return {"error": str(e)}


@router.get("/leagues")
def leagues():
    """Danh sách giải để đổ vào bộ lọc."""
    return {"response": mock_data.CURATED_LEAGUES}


@router.get("/leagues/all")
async def leagues_all():
    """Danh sách MỌI giải (rút gọn, cache 24h) cho ô tìm kiếm giải/quốc gia ở client."""
    return {"response": await api_football.get_all_leagues()}
