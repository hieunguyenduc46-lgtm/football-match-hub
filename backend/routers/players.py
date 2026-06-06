from typing import Optional

from fastapi import APIRouter

import api_football
import config
from config import settings

router = APIRouter(prefix="/api", tags=["players"])


@router.get("/topscorers")
async def topscorers(league: int = 39, season: Optional[int] = None):
    """Top scorers (vua phá lưới) của 1 giải. Mặc định Premier League.
    Mùa tự chọn theo giải (vd World Cup -> 2026) nếu client không truyền season."""
    return {"response": await api_football.get_topscorers(league, season or config.season_for(league))}


@router.get("/players/{player_id}")
async def player_detail(player_id: int, season: Optional[int] = None):
    """Chi tiết cầu thủ: ảnh mặt + thống kê (bàn thắng, kiến tạo, số trận...)."""
    return {"response": await api_football.get_player(player_id, season or settings.season)}


@router.get("/players/{player_id}/career")
async def player_career(player_id: int):
    """Tổng bàn thắng chính thức cả sự nghiệp (mọi CLB + ĐTQG, bỏ giao hữu).
    Tải riêng vì phải gọi nhiều mùa -> để không làm chậm trang chi tiết."""
    return await api_football.get_player_career(player_id)


@router.get("/players/{player_id}/motm")
async def player_motm(player_id: int, season: Optional[int] = None):
    """Số lần 'Cầu thủ hay nhất trận' (rating cao nhất) trong MÙA đang xem.
    API-Football không có sẵn -> tự tính bằng cách quét fixtures. Tải riêng (lazy)
    vì tốn nhiều request; kết quả được cache 6h ở tầng api_football."""
    return await api_football.get_player_motm(player_id, season or settings.season)


@router.get("/_debug/player/{player_id}")
async def debug_player(player_id: int, season: Optional[int] = None):
    """Debug: liệt kê MỌI mục statistics (đội / giải / bàn / số trận) qua 3 mùa,
    để soi vì sao thiếu số liệu ĐTQG. Mở: /api/_debug/player/<id>"""
    base = season or settings.season
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
