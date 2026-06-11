from typing import Optional

from fastapi import APIRouter, HTTPException

import api_football
from config import CALENDAR_YEAR_LEAGUES, default_season, settings

router = APIRouter(prefix="/api", tags=["fixtures"])


@router.get("/fixtures")
async def list_fixtures(date: Optional[str] = None, league: Optional[int] = None,
                        season: Optional[int] = None, tz: Optional[str] = None):
    """Danh sách trận. Lọc theo ?date=YYYY-MM-DD, ?league=, ?season=, ?tz=múi-giờ.

    API-Football: lọc theo league BẮT BUỘC kèm season. Nếu chưa có season,
    tự suy từ ngày (mùa bóng châu Âu: tháng >= 7 thuộc mùa năm đó, nhỏ hơn = năm trước).
    tz = múi giờ người xem -> API trả ngày & giờ theo đúng giờ địa phương của họ.
    """
    if league and not season:
        # Suy season từ ngày; date sai định dạng (vd "abc") thì rơi về season mặc định
        # thay vì ném ValueError -> tránh trả 500 cho người gọi.
        try:
            if date and len(date) >= 7:
                y, m = int(date[:4]), int(date[5:7])
                if league in CALENDAR_YEAR_LEAGUES:
                    season = y                       # giải năm dương lịch: dùng đúng năm
                else:
                    season = y if m >= 7 else y - 1  # giải châu Âu: mùa vắt 2 năm
            else:
                season = default_season()
        except (TypeError, ValueError):
            season = default_season()
    return {"response": await api_football.get_fixtures(date, league, season, tz)}


@router.get("/leagues/{league_id}/fixtures")
async def league_fixtures(league_id: int, season: Optional[int] = None):
    """Trận gần đây (kết quả) + sắp tới của 1 giải. Cho tab 'Lịch đấu' ở trang giải.
    season: lấy theo mùa đang chọn; không truyền -> trận mới nhất (live)."""
    return await api_football.get_league_fixtures(league_id, season=season)


@router.get("/country/{name}/fixtures")
async def country_fixtures(name: str):
    """Trận gần đây + sắp tới của đội tuyển quốc gia (chấp nhận tên tiếng Việt)."""
    return await api_football.get_country_fixtures(name)


@router.get("/leagues/{league_id}/bracket")
async def league_bracket(league_id: int, season: Optional[int] = None):
    """Các trận vòng knockout của giải -> client dựng sơ đồ nhánh đấu. [] nếu không có.
    season: mùa muốn xem (không truyền -> mùa mặc định theo giải)."""
    return {"response": await api_football.get_bracket(league_id, season)}


@router.get("/leagues/{league_id}/seasons")
async def league_seasons(league_id: int):
    """Danh sách mùa giải có dữ liệu (cho ô chọn mùa ở trang giải)."""
    return {"response": await api_football.get_league_seasons(league_id)}


@router.get("/_debug/fixtures")
async def debug_fixtures(date: Optional[str] = None, league: Optional[int] = None, season: Optional[int] = None):
    """Xem nguyên văn API trả về (để chẩn lỗi). CHỈ chạy khi DEBUG=true; prod trả 404."""
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
    """Chi tiết 1 trận theo id."""
    return {"response": await api_football.get_fixture(fixture_id)}


@router.get("/fixtures/{fixture_id}/lineups")
async def fixture_lineups(fixture_id: int):
    """Đội hình ra sân 2 đội (formation + vị trí grid)."""
    return {"response": await api_football.get_lineups(fixture_id)}


@router.get("/fixtures/{fixture_id}/events")
async def fixture_events(fixture_id: int):
    """Sự kiện trận: bàn thắng / thẻ / thay người theo phút."""
    return {"response": await api_football.get_events(fixture_id)}


@router.get("/fixtures/{fixture_id}/statistics")
async def fixture_statistics(fixture_id: int):
    """Thống kê trận: kiểm soát bóng, dứt điểm, xG..."""
    return {"response": await api_football.get_statistics(fixture_id)}


@router.get("/fixtures/{fixture_id}/players")
async def fixture_players(fixture_id: int):
    """Chấm điểm cầu thủ sau trận (rating)."""
    return {"response": await api_football.get_fixture_players(fixture_id)}


@router.get("/fixtures/{fixture_id}/h2h")
async def fixture_h2h(fixture_id: int, home: int = 0, away: int = 0):
    """Lịch sử đối đầu 2 đội của trận này."""
    return {"response": await api_football.get_h2h(fixture_id, home, away)}


@router.get("/fixtures/{fixture_id}/predictions")
async def fixture_predictions(fixture_id: int):
    """Dự đoán trận: xác suất thắng/hòa/thua + lời khuyên + so sánh phong độ. {} nếu không có."""
    return {"response": await api_football.get_predictions(fixture_id)}
