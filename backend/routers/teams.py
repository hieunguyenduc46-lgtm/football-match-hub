from fastapi import APIRouter

import api_football

router = APIRouter(prefix="/api", tags=["teams"])


@router.get("/teams/{team_id}")
async def team_detail(team_id: int):
    """Thông tin đội + sân + (mock) squad."""
    return {"response": await api_football.get_team(team_id)}


@router.get("/teams/{team_id}/fixtures")
async def team_fixtures(team_id: int):
    """Lịch/kết quả gần đây của đội (cho phong độ W-D-L)."""
    return {"response": await api_football.get_team_fixtures(team_id)}


@router.get("/teams/{team_id}/upcoming")
async def team_upcoming(team_id: int):
    """Các trận sắp đá của đội."""
    return {"response": await api_football.get_team_upcoming(team_id)}


@router.get("/teams/{team_id}/insights")
async def team_insights(team_id: int):
    """Thống kê mùa (phong độ, thắng/hòa/thua, bàn TB, sạch lưới, chuỗi) + DS chấn thương.
    Tải LƯỜI ở trang đội. Trả {statistics, injuries}."""
    return await api_football.get_team_insights(team_id)
