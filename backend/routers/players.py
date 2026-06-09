from typing import Optional

from fastapi import APIRouter, HTTPException, Request

import api_football
import config
from ratelimit import limiter

router = APIRouter(prefix="/api", tags=["players"])


@router.get("/topscorers")
async def topscorers(league: int = 39, season: Optional[int] = None):
    """Top scorers (vua phá lưới) của 1 giải. Mặc định Premier League.
    Mùa tự chọn theo giải (vd World Cup -> 2026) nếu client không truyền season."""
    return {"response": await api_football.get_topscorers(league, season or config.season_for(league))}


@router.get("/players/{player_id}")
async def player_detail(player_id: int, season: Optional[int] = None):
    """Chi tiết cầu thủ: ảnh mặt + thống kê (bàn thắng, kiến tạo, số trận...)."""
    return {"response": await api_football.get_player(player_id, season or config.default_season())}


@router.get("/players/{player_id}/career")
@limiter.shared_limit("30/minute", scope="player_heavy")
async def player_career(request: Request, player_id: int):
    """Tổng bàn thắng chính thức cả sự nghiệp (mọi CLB + ĐTQG, bỏ giao hữu).
    Tải riêng vì phải gọi nhiều mùa -> để không làm chậm trang chi tiết.
    Rate limit: endpoint nặng (quét nhiều mùa) -> chặn gọi dồn nhiều id khác nhau."""
    return await api_football.get_player_career(player_id)


@router.get("/players/{player_id}/motm")
@limiter.shared_limit("30/minute", scope="player_heavy")
async def player_motm(request: Request, player_id: int, season: Optional[int] = None):
    """Số lần 'Cầu thủ hay nhất trận' (rating cao nhất) trong MÙA đang xem.
    API-Football không có sẵn -> tự tính bằng cách quét fixtures. Tải riêng (lazy)
    vì tốn nhiều request; kết quả được cache 6h ở tầng api_football.
    Rate limit: endpoint NẶNG nhất (~50 request/lần) -> chặn 1 IP gọi nhiều id khác nhau."""
    return await api_football.get_player_motm(player_id, season or config.default_season())


@router.get("/_debug/player/{player_id}")
async def debug_player(player_id: int, season: Optional[int] = None):
    """Debug: liệt kê MỌI mục statistics (đội / giải / bàn / số trận) qua 3 mùa,
    để soi vì sao thiếu số liệu ĐTQG. Mở: /api/_debug/player/<id>
    CHỈ chạy khi DEBUG=true; ở production trả 404 để không lộ dữ liệu + không tốn quota."""
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
