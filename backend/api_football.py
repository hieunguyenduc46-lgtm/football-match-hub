"""
Client gọi API-Football.
- Giấu API key (key chỉ nằm ở backend, frontend không bao giờ thấy).
- Cache mỗi response theo TTL để tiết kiệm quota.
- Nếu USE_MOCK = true -> trả dữ liệu mẫu, không gọi mạng.

Mọi hàm trả về list nằm trong field "response" của API-Football,
để frontend xử lý đồng nhất dù là mock hay dữ liệu thật.
"""
import asyncio
import copy
from datetime import datetime
from typing import Optional

import httpx

import config
from config import settings
from cache import TTLCache
import mock_data

cache = TTLCache(settings.cache_ttl_seconds)

# ===== TTL phân tầng (giây) =====
# Mục tiêu: live tươi ~30s; dữ liệu tĩnh cache lâu để giảm tối đa số lần gọi API.
# Vì cache DÙNG CHUNG cho mọi user, 100 người cùng xem cũng chỉ tốn 1 request / TTL / cache key.
# API-Football tự làm tươi dữ liệu live mỗi 15s -> đặt 15s là "không trễ" tối đa có thể;
# poll nhanh hơn 15s KHÔNG có dữ liệu mới hơn, chỉ tốn request vô ích.
LIVE_TTL = 15          # trận hôm nay / đang đá / sự kiện + thống kê live
UPCOMING_TTL = 1800    # trận sắp đá (30 phút): giờ, đội hình dự kiến ít đổi
STATIC_TTL = 21600     # standings, cầu thủ, đội, lịch sử, h2h, top scorer (6 giờ) - gần như không đổi
LEAGUES_TTL = 86400    # danh sách giải (cho ô tìm kiếm): gần như không đổi -> cache 24 giờ


def _today_in_tz(tz: Optional[str]) -> str:
    """Ngày 'hôm nay' (YYYY-MM-DD) theo múi giờ tz. Lỗi/không có tz -> dùng giờ local server."""
    if tz:
        try:
            from zoneinfo import ZoneInfo
            return datetime.now(ZoneInfo(tz)).strftime("%Y-%m-%d")
        except Exception:
            pass
    return datetime.now().strftime("%Y-%m-%d")


def _fixtures_ttl(date: Optional[str], timezone: Optional[str]) -> int:
    """Chọn TTL cho danh sách trận theo ngày: hôm nay = live ngắn, tương lai = vừa, quá khứ = dài."""
    if not date:
        return LIVE_TTL
    today = _today_in_tz(timezone)
    if date == today:
        return LIVE_TTL
    if date > today:
        return UPCOMING_TTL
    return STATIC_TTL  # ngày đã qua -> kết quả cố định

# Đổi URL + header theo cách đăng ký (dashboard trực tiếp hay qua RapidAPI).
if settings.api_football_via == "rapidapi":
    BASE_URL = "https://api-football-v1.p.rapidapi.com/v3"
    HEADERS = {
        "x-rapidapi-key": settings.api_football_key,
        "x-rapidapi-host": "api-football-v1.p.rapidapi.com",
    }
else:
    BASE_URL = f"https://{settings.api_football_host}"
    HEADERS = {"x-apisports-key": settings.api_football_key}


async def _request(path: str, params: Optional[dict] = None, ttl: Optional[int] = None) -> dict:
    params = params or {}
    cache_key = path + "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))

    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    headers = HEADERS
    async with httpx.AsyncClient(timeout=15) as http:
        resp = await http.get(f"{BASE_URL}{path}", params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    # API-Football trả HTTP 200 kèm field `errors` khi bị rate-limit (vd quá nhiều request
    # mỗi phút) -> response rỗng. TUYỆT ĐỐI KHÔNG cache response lỗi, nếu không số liệu rỗng
    # sẽ bị "đóng băng" 6h và làm sai thống kê (vd đếm MOTM thiếu trận). errors = [] khi OK.
    if not data.get("errors"):
        cache.set(cache_key, data, ttl)
    return data


async def get_fixtures(date=None, league=None, season=None, timezone=None) -> list:
    if settings.use_mock:
        return mock_data.fixtures_for(date, league)
    params = {}
    if date:
        params["date"] = date
    if league:
        params["league"] = league
    if season:
        params["season"] = season
    if timezone:
        params["timezone"] = timezone  # API trả lịch + giờ theo múi giờ người xem
    data = await _request("/fixtures", params, ttl=_fixtures_ttl(date, timezone))
    return data.get("response", [])


async def get_fixture(fixture_id: int) -> list:
    if settings.use_mock:
        return mock_data.fixture_by_id(fixture_id)
    # Trận đơn: có thể đang đá -> cache ngắn để frontend (poll 30s khi live) thấy tỉ số mới.
    data = await _request("/fixtures", {"id": fixture_id}, ttl=LIVE_TTL)
    return data.get("response", [])


async def get_standings(league: int, season: int) -> list:
    if settings.use_mock:
        return mock_data.standings_for(league)
    data = await _request("/standings", {"league": league, "season": season}, ttl=STATIC_TTL)
    return data.get("response", [])


async def get_team(team_id: int) -> list:
    if settings.use_mock:
        return mock_data.team_by_id(team_id)
    info = await _request("/teams", {"id": team_id}, ttl=STATIC_TTL)
    base = info.get("response", [])
    if not base:
        return []
    item = base[0]  # {team, venue}
    # Lấy thêm squad từ endpoint riêng để trang đội có danh sách cầu thủ.
    try:
        sq = await _request("/players/squads", {"team": team_id}, ttl=STATIC_TTL)
        squad_resp = sq.get("response", [])
        players = squad_resp[0].get("players", []) if squad_resp else []
        item = {**item, "squad": [
            {"id": p.get("id"), "name": p.get("name"), "number": p.get("number"),
             "pos": p.get("position"), "photo": p.get("photo")}
            for p in players
        ]}
    except Exception:
        item = {**item, "squad": []}
    return [item]


async def _team_primary_league(team_id: int, season: int):
    """Dò giải ĐẤU CHÍNH (VĐQG) của đội ở mùa cho trước -> (league_id, name, logo).
    Ưu tiên type='League'; không có thì lấy giải đầu tiên. (None, None, None) nếu trống."""
    data = await _request("/leagues", {"team": team_id, "season": season}, ttl=STATIC_TTL)
    leagues = data.get("response", [])
    pick = None
    for lg in leagues:
        if ((lg.get("league") or {}).get("type") or "").lower() == "league":
            pick = lg["league"]
            break
    if not pick and leagues:
        pick = leagues[0].get("league")
    if not pick:
        return (None, None, None)
    return (pick.get("id"), pick.get("name"), pick.get("logo"))


async def get_team_statistics(team_id: int) -> dict:
    """Thống kê mùa của đội ở giải VĐQG: phong độ, thắng/hòa/thua, bàn TB, sạch lưới, chuỗi...
    Tự dò giải + mùa (thử mùa trước nếu đầu mùa chưa có). {} nếu không có dữ liệu."""
    if settings.use_mock:
        return {}
    season = config.default_season()
    lid, lname, llogo = await _team_primary_league(team_id, season)
    if not lid:
        season -= 1
        lid, lname, llogo = await _team_primary_league(team_id, season)
    if not lid:
        return {}
    data = await _request(
        "/teams/statistics", {"team": team_id, "league": lid, "season": season}, ttl=STATIC_TTL
    )
    resp = data.get("response") or {}
    if not resp or not resp.get("fixtures"):
        return {}
    resp["_league"] = {"id": lid, "name": lname, "logo": llogo, "season": season}
    return resp


async def get_team_injuries(team_id: int) -> list:
    """Danh sách cầu thủ chấn thương/treo giò của đội (mùa hiện tại), gộp theo cầu thủ
    (giữ bản ghi mới nhất). [] nếu không có."""
    if settings.use_mock:
        return []
    season = config.default_season()
    data = await _request("/injuries", {"team": team_id, "season": season}, ttl=LIVE_TTL)
    resp = data.get("response", [])
    latest = {}
    for x in resp:
        p = x.get("player") or {}
        pid = p.get("id")
        if pid is None:
            continue
        d = (x.get("fixture") or {}).get("date") or ""
        if pid not in latest or d > latest[pid]["_d"]:
            latest[pid] = {
                "id": pid, "name": p.get("name"), "photo": p.get("photo"),
                "type": p.get("type"), "reason": p.get("reason"), "_d": d,
            }
    out = list(latest.values())
    for o in out:
        o.pop("_d", None)
    return out


async def get_team_insights(team_id: int) -> dict:
    """Gộp thống kê mùa + danh sách chấn thương của đội trong 1 lần gọi (song song)."""
    if settings.use_mock:
        return {"statistics": {}, "injuries": []}
    statistics, injuries = await asyncio.gather(
        get_team_statistics(team_id),
        get_team_injuries(team_id),
    )
    return {"statistics": statistics, "injuries": injuries}


# ========================= GHI ĐÈ THỐNG KÊ THỦ CÔNG =========================
# API-Football đôi khi trả SAI hoặc THIẾU một dòng giải (vd King's Cup Saudi trả số
# CỘNG DỒN nhiều mùa: Ronaldo 16 trận/14 bàn, lại còn league.id = null nên mất logo).
# Bảng này sửa thủ công các dòng đó theo nguồn chính thức.
# Khoá = (player_id, season). Mỗi rule khớp giải theo `match` (so khớp tên giải, chữ
# thường, dạng "chứa") rồi GHI ĐÈ các field cho sẵn (dict thì merge, còn lại gán đè).
# Đặt None cho field KHÔNG xác thực được -> frontend hiện "—" thay vì số bịa.
# Nguồn King's Cup 2025/26: Al-Nassr bị loại vòng 1/16 -> Ronaldo đá 1 trận, 0 bàn
# (Wikipedia "2025–26 Al-Nassr FC season", bảng số trận theo giải).
_MEDIA = "https://media.api-sports.io/football"

# Mỗi mục = {(player_id, season): {"patch": [...], "add": [...]}}
#  - patch: SỬA dòng giải đã có (khớp tên giải, chữ thường, dạng "chứa"); dict thì merge,
#           còn lại gán đè. Đặt None cho field không xác thực được -> frontend hiện "—".
#  - add:   CHÈN dòng giải mà API thiếu hẳn (kèm league id+logo để có icon).
# Nguồn số liệu: bảng thống kê chính thức mùa 2025/26 (Pro League 30/28/3, ACL Two 4/1/1,
# Super Cup 2/1/1, King's Cup 1/0/0). API trả: assists Pro League thiếu, ACL Two thiếu
# trận+bàn, King's Cup cộng dồn sai + mất id/logo, và THIẾU HẲN Super Cup.
STAT_OVERRIDES = {
    (874, 2025): {  # Cristiano Ronaldo — Al-Nassr
        "patch": [
            {"match": "pro league", "goals": {"assists": 3}},
            {"match": "champions league two",
             "games": {"appearences": 4}, "goals": {"total": 1}},
            {"match": "king's cup",
             "league": {"id": 504, "name": "King's Cup", "logo": f"{_MEDIA}/leagues/504.png"},
             "games": {"appearences": 1, "minutes": None, "rating": None},
             "goals": {"total": 0, "assists": 0},
             "shots": {"total": None}, "passes": {"accuracy": None},
             "cards": {"yellow": 0, "red": 0}},
        ],
        "add": [
            {  # Saudi Super Cup (id 826) — API không có dòng này cho mùa 2025
                "team": {"id": 2939, "name": "Al-Nassr", "logo": f"{_MEDIA}/teams/2939.png"},
                "league": {"id": 826, "name": "Saudi Super Cup", "season": 2025,
                           "country": "Saudi-Arabia", "logo": f"{_MEDIA}/leagues/826.png"},
                "games": {"appearences": 2, "minutes": None, "position": "Attacker", "rating": None},
                "goals": {"total": 1, "assists": 1, "conceded": 0, "saves": None},
                "shots": {"total": None, "on": None},
                "passes": {"accuracy": None},
                "cards": {"yellow": 0, "red": 0},
            },
        ],
    },
}


def _apply_stat_overrides(player_id: int, season: int, resp: list) -> list:
    """PATCH các dòng giải đã có + ADD các dòng API thiếu (theo STAT_OVERRIDES)."""
    rule = STAT_OVERRIDES.get((player_id, season))
    if not resp or not rule:
        return resp
    # QUAN TRỌNG: deep-copy trước khi sửa. resp là object NẰM TRONG CACHE, dùng chung với
    # _sum_official_goals (tính career goals) và get_player_motm. Nếu sửa tại chỗ sẽ làm
    # hỏng các số đó (vd career goals bị tụt). Chỉ sửa trên bản sao để trả riêng cho get_player.
    resp = copy.deepcopy(resp)
    stats = resp[0].setdefault("statistics", [])

    # PATCH
    for st in stats:
        lname = ((st.get("league") or {}).get("name") or "").lower()
        for p in rule.get("patch", []):
            if p["match"] not in lname:
                continue
            for key, val in p.items():
                if key == "match":
                    continue
                if isinstance(val, dict):
                    base = dict(st.get(key) or {})
                    base.update(val)
                    st[key] = base
                else:
                    st[key] = val

    # ADD (bỏ qua nếu giải đã xuất hiện -> tránh chèn trùng khi gọi lại trên cache)
    have_ids = {(s.get("league") or {}).get("id") for s in stats}
    have_names = {((s.get("league") or {}).get("name") or "").lower() for s in stats}
    for entry in rule.get("add", []):
        lid = (entry.get("league") or {}).get("id")
        lname = ((entry.get("league") or {}).get("name") or "").lower()
        if lid in have_ids or lname in have_names:
            continue
        stats.append(copy.deepcopy(entry))
    return resp


async def get_player(player_id: int, season: int = 2025) -> list:
    # Chỉ trả dữ liệu của ĐÚNG mùa đang xem. Frontend tự tách CLB vs ĐTQG;
    # nếu mùa đó không có trận ĐTQG thì phần đội tuyển để trống (không lấy mùa khác).
    if settings.use_mock:
        return mock_data.player_by_id(player_id)
    data = await _request("/players", {"id": player_id, "season": season}, ttl=STATIC_TTL)
    resp = data.get("response", [])

    # ===== Giải chạy theo NĂM DƯƠNG LỊCH (MLS...) =====
    # Default `season` (vd 2025) là mùa giải CHÂU ÂU (25/26). Nhưng MLS chạy tháng 1–12,
    # nên "mùa hiện tại" của cầu thủ Inter Miami là NĂM NAY (2026), không phải 2025.
    # Nếu cầu thủ có đá giải năm-dương-lịch ở mùa default -> lấy lại nguyên dữ liệu mùa = năm nay.
    cur_year = datetime.now().year
    if resp and cur_year != season:
        stats = resp[0].get("statistics", [])
        plays_calendar = any(
            ((s.get("league") or {}).get("id")) in config.CALENDAR_YEAR_LEAGUES
            for s in stats
        )
        if plays_calendar:
            try:
                cy = await _request(
                    "/players", {"id": player_id, "season": cur_year}, ttl=STATIC_TTL
                )
                cy_resp = cy.get("response", [])
                # Chỉ thay khi mùa năm nay thật sự có dữ liệu (tránh trả rỗng đầu năm).
                if cy_resp and cy_resp[0].get("statistics"):
                    return _apply_stat_overrides(player_id, cur_year, cy_resp)
            except Exception:
                pass
    return _apply_stat_overrides(player_id, season, resp)


# Đội trẻ / Olympic -> KHÔNG tính vào "official" (bảng official chỉ tính tuyển A + CLB).
_YOUTH_KEYWORDS = ("u15", "u16", "u17", "u18", "u19", "u20", "u21", "u23", "olympic", "youth")


def _is_official_goal_entry(stat: dict) -> bool:
    """Mục được tính vào tổng official: KHÔNG phải giao hữu, KHÔNG phải đội trẻ/Olympic."""
    team = ((stat.get("team") or {}).get("name") or "").lower()
    league = ((stat.get("league") or {}).get("name") or "").lower()
    if "friendl" in league:
        return False
    return not any(k in team or k in league for k in _YOUTH_KEYWORDS)


async def _sum_official_goals(player_id: int, seasons: list) -> int:
    """Cộng bàn official (CLB + tuyển A, bỏ giao hữu/đội trẻ) qua các mùa cho trước."""
    total = 0
    for s in seasons:
        try:
            data = await _request("/players", {"id": player_id, "season": s}, ttl=STATIC_TTL)
            resp = data.get("response", [])
        except Exception:
            continue
        for st in (resp[0].get("statistics", []) if resp else []):
            if _is_official_goal_entry(st):
                total += (st.get("goals") or {}).get("total") or 0
    return total


async def get_player_career(player_id: int) -> dict:
    """Tổng bàn thắng official cả sự nghiệp.
    - Nếu có MỐC nhập tay (config.CAREER_BASELINE): dùng mốc official + tự cộng bàn các mùa SAU mốc.
    - Nếu không: cộng dồn toàn bộ các mùa qua API (có thể lệch số official 'chuẩn')."""
    if settings.use_mock:
        return {"goals": 0, "source": "mock"}

    seasons_resp = await _request("/players/seasons", {"player": player_id}, ttl=STATIC_TTL)
    seasons = [s for s in (seasons_resp.get("response") or []) if isinstance(s, int)]

    baseline = config.CAREER_BASELINE.get(player_id)
    if baseline:
        through = baseline["through"]
        newer = [s for s in seasons if s > through]
        added = await _sum_official_goals(player_id, newer)
        return {
            "goals": baseline["goals"] + added,
            "baseline": baseline["goals"],
            "added": added,
            "through": through,
            "source": "official",
        }

    total = await _sum_official_goals(player_id, seasons)
    return {"goals": total, "seasons": len(seasons), "source": "api"}


# Cúp GIAO HỮU / BIỂU DIỄN tiền mùa giải + giải TRẺ -> KHÔNG tính là danh hiệu thật.
# (vd "Trofeo Joan Gamper", "Copa Catalunya" của Messi; "UEFA U19" của Mbappé.)
# Lưu ý: "Trophée des Champions" (Siêu cúp Pháp) KHÁC "Trofeo ..." (giao hữu Tây Ban Nha)
# nên match "trofeo" an toàn, không đụng cúp Pháp. GIỮ Olympic vì là danh hiệu thật.
_EXHIBITION_TROPHY_KW = (
    "trofeo", "catalunya", "audi cup", "emirates cup", "international champions cup",
    "florida cup", "berlusconi", "eusebio", "eusébio", "amsterdam tournament",
    "teresa herrera", "carranza", "naranja", "colombino", "bortolotti", "friendl",
    "u15", "u16", "u17", "u18", "u19", "u20", "u21", "u23", "youth",
)


def _is_exhibition_trophy(league: str) -> bool:
    name = (league or "").lower()
    return any(k in name for k in _EXHIBITION_TROPHY_KW)


async def get_player_trophies(player_id: int) -> list:
    """Danh hiệu cả sự nghiệp. API-Football /trophies.
    Làm sạch: BỎ bản ghi thiếu mùa (season rỗng -> entry lỗi của API, gây đếm thừa,
    vd Ronaldo bị +1 'UEFA Champions League' ảo) và KHỬ TRÙNG LẶP theo
    (quốc gia|giải|mùa|hạng). [] nếu không có."""
    if settings.use_mock:
        return []
    data = await _request("/trophies", {"player": player_id}, ttl=STATIC_TTL)
    resp = data.get("response", [])
    seen = set()
    out = []
    for t in resp:
        season = (t.get("season") or "").strip()
        if not season:
            continue  # bản ghi thiếu mùa -> dữ liệu rác, bỏ
        if _is_exhibition_trophy(t.get("league")):
            continue  # cúp giao hữu/biểu diễn hoặc giải trẻ -> KHÔNG tính là danh hiệu
        key = (t.get("country") or "", t.get("league") or "", season, t.get("place") or "")
        if key in seen:
            continue  # trùng -> bỏ
        seen.add(key)
        out.append(t)
    return out


async def get_player_transfers(player_id: int) -> list:
    """Lịch sử chuyển nhượng (danh sách {date, type, teams:{in,out}}). [] nếu không có."""
    if settings.use_mock:
        return []
    data = await _request("/transfers", {"player": player_id}, ttl=STATIC_TTL)
    resp = data.get("response", [])
    return resp[0].get("transfers", []) if resp else []


async def get_player_sidelined(player_id: int) -> list:
    """Lịch sử chấn thương / treo giò (danh sách {type, start, end}). [] nếu không có."""
    if settings.use_mock:
        return []
    data = await _request("/sidelined", {"player": player_id}, ttl=STATIC_TTL)
    return data.get("response", [])


async def get_player_season_stats(player_id: int, limit: int = 10) -> list:
    """Bảng thống kê theo TỪNG MÙA (gộp mọi giải trong mùa): số trận / bàn / kiến tạo + đội chính.
    Lấy tối đa `limit` mùa gần nhất, gọi SONG SONG cho nhanh; mỗi mùa cache 6h."""
    if settings.use_mock:
        return []
    seasons_resp = await _request("/players/seasons", {"player": player_id}, ttl=STATIC_TTL)
    seasons = sorted([s for s in (seasons_resp.get("response") or []) if isinstance(s, int)], reverse=True)[:limit]

    async def one(season):
        try:
            data = await _request("/players", {"id": player_id, "season": season}, ttl=STATIC_TTL)
            resp = data.get("response", [])
        except Exception:
            return None
        stats = resp[0].get("statistics", []) if resp else []
        if not stats:
            return None
        apps = goals = assists = 0
        team_apps = {}  # tên đội -> số trận, để chọn đội chơi nhiều nhất làm nhãn
        seen = set()    # (đội|giải) đã cộng -> tránh API trả trùng mục gây cộng dư
        for st in stats:
            # Bỏ giao hữu + đội trẻ/Olympic (giống cách tính bàn official) -> số liệu sạch, nhất quán.
            if not _is_official_goal_entry(st):
                continue
            tname = (st.get("team") or {}).get("name")
            lname = (st.get("league") or {}).get("name")
            dkey = f"{tname}|{lname}"
            if dkey in seen:
                continue
            seen.add(dkey)
            g = st.get("games") or {}
            a = g.get("appearences") or 0
            apps += a
            goals += (st.get("goals") or {}).get("total") or 0
            assists += (st.get("goals") or {}).get("assists") or 0
            if tname:
                team_apps[tname] = team_apps.get(tname, 0) + a
        if not team_apps:
            return None  # mùa chỉ có giao hữu/đội trẻ -> bỏ, không hiện dòng rỗng
        team = max(team_apps, key=team_apps.get)
        return {"season": season, "team": team, "apps": apps, "goals": goals, "assists": assists}

    rows = await asyncio.gather(*[one(s) for s in seasons])
    return [r for r in rows if r]


async def get_player_history(player_id: int) -> dict:
    """Gộp 4 phần lịch sử của cầu thủ trong 1 lần gọi (tải song song):
    danh hiệu + chuyển nhượng + chấn thương + thống kê theo mùa."""
    if settings.use_mock:
        return {"trophies": [], "transfers": [], "sidelined": [], "seasons": []}
    trophies, transfers, sidelined, seasons = await asyncio.gather(
        get_player_trophies(player_id),
        get_player_transfers(player_id),
        get_player_sidelined(player_id),
        get_player_season_stats(player_id),
    )
    return {"trophies": trophies, "transfers": transfers, "sidelined": sidelined, "seasons": seasons}


# NEO THỦ CÔNG cho 'Cầu thủ hay nhất trận'.
# API-Football KHÔNG có giải "Man of the Match" chính thức, nên cách tự tính (rating cao
# nhất trận) có thể thấp hơn số MOTM chính thức thực tế (vd Ronaldo mùa 2025/26 có 8 MOTM
# chính thức của Saudi Pro League nhưng tính theo rating ra 0).
# Neo tay theo (player_id, season): {"base": số MOTM tính tới ngày "since", "since": ngày neo}.
# Hiển thị = base + số MOTM ở các trận đá SAU ngày "since" (tính theo rating như bình thường).
# -> Số neo là "sàn", và TỰ ĐỘNG cộng thêm khi có trận mới được MOTM.
MOTM_ANCHORS = {
    (874, 2025): {"base": 8, "since": "2026-06-07"},  # Cristiano Ronaldo
    (154, 2025): {"base": 4, "since": "2026-06-07"},  # Lionel Messi
}

# Cầu thủ tính MOTM theo "ĐỘI NHÀ" (rating cao nhất TRONG đội của cầu thủ ở trận đó).
# MẶC ĐỊNH mọi người khác tính theo "CẢ 2 ĐỘI" (phải cao nhất trong tất cả cầu thủ trên
# sân). Lý do: ở đội yếu/giải nhẹ (vd Messi ở MLS) cách "đội nhà" cho số cao bất thường.
MOTM_TEAM_SCOPED = {
    (583, 2025),   # João Félix — Al-Nassr
    (278, 2025),   # Kylian Mbappé — Real Madrid
}


async def get_player_motm(player_id: int, season: int) -> dict:
    """Đếm số trận cầu thủ là 'hay nhất trận' trong MÙA đang xem.

    MẶC ĐỊNH: so rating với CẢ 2 ĐỘI (phải cao nhất trong toàn bộ cầu thủ trên sân).
    Trường hợp trong MOTM_TEAM_SCOPED: chỉ so trong ĐỘI NHÀ của cầu thủ.
    Trường hợp trong MOTM_ANCHORS: kết quả = base + số MOTM ở các trận đá SAU ngày 'since'
      (số neo là sàn, TỰ ĐỘNG cộng thêm khi có trận mới được MOTM).

    API-Football KHÔNG có field POTM sẵn -> tự tính:
      1. Lấy các đội cầu thủ khoác áo mùa này (từ /players statistics).
      2. Lấy fixtures đã kết thúc của từng đội (/fixtures?team&season) + ngày trận.
      3. Mỗi trận (chỉ trận cần đếm): gọi /fixtures/players; tìm rating cao nhất
         (cả 2 đội hoặc chỉ đội nhà). Nếu là cầu thủ này -> +1. (Chỉ tính trận có ra sân.)
    Tốn nhiều request (1/trận) nên cache STATIC_TTL (6h) và tải lazy ở frontend.
    """
    anchor = MOTM_ANCHORS.get((player_id, season))
    base = anchor["base"] if anchor else 0
    since = anchor["since"] if anchor else None  # chỉ đếm trận có NGÀY > since

    if settings.use_mock:
        return {"motm": base, "computed": 0, "anchor": base, "scanned": base or 0,
                "season": season, "source": "mock"}

    # 1) Các đội cầu thủ khoác áo mùa này.
    pdata = await _request("/players", {"id": player_id, "season": season}, ttl=STATIC_TTL)
    resp = pdata.get("response", [])
    stats = resp[0].get("statistics", []) if resp else []
    team_ids = {
        (s.get("team") or {}).get("id")
        for s in stats
        if (s.get("team") or {}).get("id")
    }

    # 2) Gom fixture đã kết thúc + NGÀY trận (để lọc theo 'since').
    finished = {"FT", "AET", "PEN"}
    fixture_dates: dict = {}   # fid -> ngày trận (ISO)
    for tid in team_ids:
        try:
            fx = await _request(
                "/fixtures", {"team": tid, "season": season}, ttl=STATIC_TTL
            )
        except Exception:
            continue
        for f in fx.get("response", []):
            fx_obj = f.get("fixture") or {}
            status = ((fx_obj.get("status")) or {}).get("short")
            if status in finished and fx_obj.get("id"):
                fixture_dates[fx_obj["id"]] = fx_obj.get("date") or ""

    team_scoped = (player_id, season) in MOTM_TEAM_SCOPED

    # Chỉ quét những trận CẦN ĐẾM: nếu có neo -> chỉ trận đá SAU 'since'
    # (phần trước 'since' đã nằm trong base). Không neo -> quét hết.
    fids = [fid for fid, d in fixture_dates.items() if (not since) or (d[:10] > since)]

    # 3) Tải SONG SONG (có giới hạn) cho nhanh; quét tuần tự ~50 trận dễ vượt timeout.
    sem = asyncio.Semaphore(6)   # giới hạn để không vượt rate-limit API-Football

    async def _fetch_fixture_players(fid):
        async with sem:
            try:
                return await _request("/fixtures/players", {"fixture": fid}, ttl=STATIC_TTL)
            except Exception:
                return None

    results = await asyncio.gather(*(_fetch_fixture_players(fid) for fid in fids))

    motm = 0
    scanned = 0
    for pl in results:
        if pl is None:
            continue
        teams = pl.get("response", [])
        # Tìm đội của cầu thủ; bỏ qua nếu cầu thủ không ra sân trận này.
        my_players = None
        for team in teams:
            if any((p.get("player") or {}).get("id") == player_id for p in team.get("players", [])):
                my_players = team.get("players", [])
                break
        if my_players is None:
            continue
        scanned += 1
        # Phạm vi so sánh: chỉ đội nhà, hoặc cả 2 đội (mặc định).
        if team_scoped:
            candidates = my_players
        else:
            candidates = [p for team in teams for p in team.get("players", [])]
        best_id, best_rating = None, -1.0
        for p in candidates:
            raw = (((p.get("statistics") or [{}])[0].get("games")) or {}).get("rating")
            try:
                r = float(raw)
            except (TypeError, ValueError):
                continue
            if r > best_rating:
                best_rating, best_id = r, (p.get("player") or {}).get("id")
        if best_id == player_id:
            motm += 1

    # Có neo: total = base + MOTM trận mới (sau 'since'). Không neo: total = motm.
    total = base + motm
    return {
        "motm": total,
        "computed": motm,                 # MOTM ở các trận sau 'since' (phần "mới")
        "anchor": base,
        "scanned": max(scanned, base),    # > 0 để frontend luôn hiện thẻ POTM
        "season": season,
        "scope": "team" if team_scoped else "both",
        "source": "anchor+api" if anchor else "api",
    }


async def get_lineups(fixture_id: int) -> list:
    if settings.use_mock:
        return mock_data.lineups_for(fixture_id)
    # Đội hình đổi rất ít sau khi công bố (chỉ vài lần thay người) -> cache vừa phải.
    data = await _request("/fixtures/lineups", {"fixture": fixture_id}, ttl=UPCOMING_TTL)
    return data.get("response", [])


async def get_events(fixture_id: int) -> list:
    if settings.use_mock:
        return mock_data.events_for(fixture_id)
    # Sự kiện (bàn thắng/thẻ) thay đổi liên tục khi live -> cache ngắn.
    data = await _request("/fixtures/events", {"fixture": fixture_id}, ttl=LIVE_TTL)
    return data.get("response", [])


def _has_match_detail(entry: dict) -> bool:
    """True nếu dòng thống kê có dữ liệu CẤP TRẬN (phút thi đấu hoặc điểm số).
    Scorer thật của VCK có phút/điểm; số liệu vòng loại bị gộp nhầm thì null hết."""
    try:
        g = entry["statistics"][0]["games"]
    except (KeyError, IndexError, TypeError):
        return False
    return g.get("minutes") is not None or g.get("rating") is not None


def _drop_qualifier_leak(resp: list) -> list:
    """API-Football đôi khi GỘP số liệu VÒNG LOẠI vào vua phá lưới của giải đấu cúp.
    Ví dụ World Cup 2018: Immobile (Ý) đứng đầu với 6 bàn dù Ý không dự VCK — đó là
    bàn ở vòng loại. Các dòng "lọt" này không có dữ liệu cấp trận (phút/điểm = null).

    Quy tắc AN TOÀN: chỉ bỏ dòng rỗng KHI danh sách có CẢ dòng chi tiết lẫn dòng rỗng
    (đặc trưng của giải đấu cúp). Nếu TẤT CẢ đều rỗng (giải ít dữ liệu như V-League)
    thì giữ nguyên để không xoá trắng bảng."""
    if not resp:
        return resp
    detailed = [p for p in resp if _has_match_detail(p)]
    if detailed and len(detailed) < len(resp):
        return detailed
    return resp


async def get_topscorers(league: int, season: int = 2025) -> list:
    if settings.use_mock:
        return mock_data.topscorers_for(league)
    data = await _request("/players/topscorers", {"league": league, "season": season}, ttl=STATIC_TTL)
    return _drop_qualifier_leak(data.get("response", []))


async def get_topassists(league: int, season: int = 2025) -> list:
    """Vua kiến tạo của 1 giải. Cùng dạng dữ liệu như topscorers (statistics[].goals.assists)."""
    if settings.use_mock:
        return mock_data.topscorers_for(league)
    data = await _request("/players/topassists", {"league": league, "season": season}, ttl=STATIC_TTL)
    return _drop_qualifier_leak(data.get("response", []))


async def get_topyellowcards(league: int, season: int = 2025) -> list:
    """Cầu thủ nhiều thẻ vàng nhất (statistics[].cards.yellow)."""
    if settings.use_mock:
        return mock_data.topscorers_for(league)
    data = await _request("/players/topyellowcards", {"league": league, "season": season}, ttl=STATIC_TTL)
    return _drop_qualifier_leak(data.get("response", []))


async def get_topredcards(league: int, season: int = 2025) -> list:
    """Cầu thủ nhiều thẻ đỏ nhất (statistics[].cards.red)."""
    if settings.use_mock:
        return mock_data.topscorers_for(league)
    data = await _request("/players/topredcards", {"league": league, "season": season}, ttl=STATIC_TTL)
    return _drop_qualifier_leak(data.get("response", []))


async def get_statistics(fixture_id: int) -> list:
    if settings.use_mock:
        return mock_data.statistics_for(fixture_id)
    # Thống kê (sút, kiểm soát bóng) cập nhật khi live -> cache ngắn.
    data = await _request("/fixtures/statistics", {"fixture": fixture_id}, ttl=LIVE_TTL)
    return data.get("response", [])


async def get_predictions(fixture_id: int) -> dict:
    """Dự đoán trận: xác suất thắng/hòa/thua, lời khuyên, so sánh phong độ 2 đội.
    API-Football /predictions. Trả {} nếu không có dữ liệu (trận quá cũ / chưa hỗ trợ)."""
    if settings.use_mock:
        return {}
    data = await _request("/predictions", {"fixture": fixture_id}, ttl=STATIC_TTL)
    resp = data.get("response", [])
    return resp[0] if resp else {}


async def get_fixture_players(fixture_id: int) -> list:
    if settings.use_mock:
        return mock_data.players_ratings_for(fixture_id)
    data = await _request("/fixtures/players", {"fixture": fixture_id}, ttl=LIVE_TTL)
    return data.get("response", [])


async def get_h2h(fixture_id: int, home: int, away: int) -> list:
    if settings.use_mock:
        return mock_data.h2h_for(fixture_id)
    data = await _request("/fixtures/headtohead", {"h2h": f"{home}-{away}", "last": 10}, ttl=STATIC_TTL)
    return data.get("response", [])


async def get_team_fixtures(team_id: int, last: int = 5) -> list:
    if settings.use_mock:
        return mock_data.team_recent(team_id)
    data = await _request("/fixtures", {"team": team_id, "last": last}, ttl=STATIC_TTL)
    return data.get("response", [])


async def get_team_upcoming(team_id: int, nxt: int = 5) -> list:
    """Các trận sắp đá của đội (lịch tương lai). Mock chưa có -> trả rỗng."""
    if settings.use_mock:
        return []
    data = await _request("/fixtures", {"team": team_id, "next": nxt}, ttl=UPCOMING_TTL)
    return data.get("response", [])


# ===== Tìm kiếm GIẢI + QUỐC GIA (cho ô search cạnh thanh ngày) =====

# Quốc gia (mock) cho vài giải tiêu biểu, để chế độ mock vẫn có dữ liệu search.
_MOCK_LEAGUE_COUNTRY = {
    39: "England", 45: "England", 2: "World", 3: "World", 848: "World", 1: "World",
    10: "World", 15: "World", 140: "Spain", 143: "Spain", 135: "Italy",
    78: "Germany", 61: "France", 307: "Saudi Arabia", 253: "USA", 340: "Vietnam",
}


async def get_all_leagues() -> list:
    """Danh sách MỌI giải (đã rút gọn) để đổ vào ô tìm kiếm phía client.
    Cache 24h vì gần như không đổi -> dù bao nhiêu user cũng chỉ tốn 1 request/ngày.
    Trả [{id, name, type, logo, country, country_code, flag}]."""
    if settings.use_mock:
        out = []
        for l in mock_data.CURATED_LEAGUES:
            out.append({
                "id": l["id"], "name": l["name"], "type": "League",
                "logo": f"https://media.api-sports.io/football/leagues/{l['id']}.png",
                "country": _MOCK_LEAGUE_COUNTRY.get(l["id"], "World"),
                "country_code": None, "flag": None,
            })
        return out
    data = await _request("/leagues", {}, ttl=LEAGUES_TTL)
    out = []
    for it in data.get("response", []):
        lg = it.get("league") or {}
        co = it.get("country") or {}
        if not lg.get("id"):
            continue
        out.append({
            "id": lg.get("id"), "name": lg.get("name"), "type": lg.get("type"),
            "logo": lg.get("logo"), "country": co.get("name"),
            "country_code": co.get("code"), "flag": co.get("flag"),
        })
    return out


async def get_league_fixtures(league_id: int, last: int = 12, nxt: int = 12,
                              season: Optional[int] = None) -> dict:
    """Trận GẦN ĐÂY (kết quả) + SẮP TỚI của 1 giải. Dùng cho tab 'Lịch đấu' của trang giải.
    season: nếu truyền -> lấy theo MÙA đó (đã đá xếp mới->cũ, sắp đá xếp cũ->mới) để khớp
    với mùa đang chọn. Không truyền -> kiểu 'live' (last/next, trận mới nhất bất kể mùa)."""
    if settings.use_mock:
        return {"recent": mock_data.fixtures_for(None, league_id), "upcoming": []}
    if season:
        fx = (await _request("/fixtures", {"league": league_id, "season": season},
                             ttl=STATIC_TTL)).get("response", [])
        done = {"FT", "AET", "PEN", "WO", "AWD"}
        def _d(f):
            return (f.get("fixture") or {}).get("date") or ""
        def _st(f):
            return ((f.get("fixture") or {}).get("status") or {}).get("short")
        recent = sorted([f for f in fx if _st(f) in done], key=_d, reverse=True)
        upcoming = sorted([f for f in fx if _st(f) in ("NS", "TBD")], key=_d)
        return {"recent": recent[:20], "upcoming": upcoming[:20]}
    recent = (await _request("/fixtures", {"league": league_id, "last": last},
                             ttl=STATIC_TTL)).get("response", [])
    upcoming = (await _request("/fixtures", {"league": league_id, "next": nxt},
                               ttl=UPCOMING_TTL)).get("response", [])
    return {"recent": recent, "upcoming": upcoming}


async def get_league_seasons(league_id: int) -> list:
    """Danh sách MÙA mà giải có dữ liệu (để client đổ vào ô chọn mùa). Trả [{year, current}]
    sắp xếp mùa mới -> cũ. Cache 24h. [] nếu mock."""
    if settings.use_mock:
        return []
    data = await _request("/leagues", {"id": league_id}, ttl=LEAGUES_TTL)
    resp = data.get("response", [])
    seasons = resp[0].get("seasons", []) if resp else []
    out = [{"year": s.get("year"), "current": bool(s.get("current"))}
           for s in seasons if isinstance(s.get("year"), int)]
    out.sort(key=lambda x: x["year"], reverse=True)
    return out


async def get_bracket(league_id: int, season: Optional[int] = None) -> list:
    """Các trận VÒNG LOẠI TRỰC TIẾP (knockout) của giải -> client dựng SƠ ĐỒ NHÁNH ĐẤU.
    Trả [] nếu giải không có vòng knockout (vd VĐQG) -> client ẩn tab.
    season: mùa muốn xem; không truyền -> mùa mặc định theo giải.
    1 request /fixtures?league&season (cache 6h) rồi lọc theo tên vòng."""
    if settings.use_mock:
        return []
    season = season or config.season_for(league_id)
    data = await _request("/fixtures", {"league": league_id, "season": season}, ttl=STATIC_TTL)
    out = []
    for f in data.get("response", []):
        rnd = ((f.get("league") or {}).get("round") or "")
        # Vòng knockout (R16/QF/SF/Final/play-off...), BỎ vòng bảng / VĐQG / lượt league-stage.
        if re.search(r"round of|quarter|semi|\bfinal\b|play-?off|1/\d|last \d+", rnd, re.IGNORECASE) \
                and not re.search(r"group|regular season|league stage|qualif", rnd, re.IGNORECASE):
            out.append(f)
    return out


async def get_national_team(country: str) -> Optional[dict]:
    """Tìm ĐỘI TUYỂN QUỐC GIA theo tên nước (chấp nhận tên tiếng Việt). Ưu tiên national=true."""
    name = _vi_translate((country or "").strip())  # 'tây ban nha' -> 'Spain'
    if len(name) < 2 or settings.use_mock:
        return None
    resp = []
    for params in ({"name": name}, {"search": name}):
        try:
            resp = (await _request("/teams", params, ttl=STATIC_TTL)).get("response", [])
        except Exception:
            resp = []
        if resp:
            break
    best = next((it.get("team") for it in resp if (it.get("team") or {}).get("national")), None)
    if not best and resp:
        best = resp[0].get("team")
    if not best:
        return None
    return {"id": best.get("id"), "name": best.get("name"),
            "logo": best.get("logo"), "country": best.get("country")}


async def get_country_fixtures(country: str) -> dict:
    """Trận GẦN ĐÂY + SẮP TỚI của ĐỘI TUYỂN nước này. Trả {team, recent, upcoming}."""
    team = await get_national_team(country)
    if not team:
        return {"team": None, "recent": [], "upcoming": []}
    recent = (await _request("/fixtures", {"team": team["id"], "last": 10},
                             ttl=STATIC_TTL)).get("response", [])
    upcoming = (await _request("/fixtures", {"team": team["id"], "next": 10},
                               ttl=UPCOMING_TTL)).get("response", [])
    return {"team": team, "recent": recent, "upcoming": upcoming}


# ===== Tìm trận đấu (match search) =====
# Cho phép gõ "Real Madrid vs Barcelona" -> ra trận gần đây + sắp đá giữa 2 đội,
# hoặc gõ 1 đội -> lịch đấu của đội đó.
import re
import unicodedata

# Các từ ngăn cách 2 đội: "vs", "v", "x", "-", "–", "đấu với", "gặp".
_VS_RE = re.compile(r"\s+(?:vs|versus|v|x|-|–|đấu với|gặp)\s+", re.IGNORECASE)


def _norm_key(s: str) -> str:
    """Chuẩn hoá để tra cứu: bỏ dấu tiếng Việt, thường hoá, gộp khoảng trắng.
    Nhờ vậy gõ có dấu ('bồ đào nha') hay không dấu ('bo dao nha') đều khớp."""
    s = (s or "").lower().strip().replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


# Tên tiếng Việt -> tên tiếng Anh mà API-Football hiểu (đội tuyển quốc gia).
# Khoá đã ở dạng không dấu (_norm_key). Bỏ qua Thổ Nhĩ Kỳ / Ireland vì API không
# trả về đúng đội tuyển nam cho các tên đó.
_VI_COUNTRIES = {
    "bo dao nha": "Portugal",
    "tay ban nha": "Spain",
    "duc": "Germany",
    "anh": "England",
    "phap": "France",
    "brazil": "Brazil", "bra xin": "Brazil",
    "argentina": "Argentina", "ac hen ti na": "Argentina",
    "y": "Italy", "italia": "Italy", "italy": "Italy",
    "ha lan": "Netherlands",
    "bi": "Belgium",
    "croatia": "Croatia",
    "uruguay": "Uruguay",
    "mexico": "Mexico", "me hi co": "Mexico",
    "my": "USA", "hoa ky": "USA", "usa": "USA",
    "nhat ban": "Japan", "nhat": "Japan",
    "han quoc": "South Korea", "han": "South Korea",
    "uc": "Australia", "australia": "Australia",
    "a rap xe ut": "Saudi Arabia", "saudi": "Saudi Arabia", "saudi arabia": "Saudi Arabia",
    "ma roc": "Morocco", "maroc": "Morocco", "morocco": "Morocco",
    "senegal": "Senegal",
    "ghana": "Ghana",
    "nigeria": "Nigeria",
    "cameroon": "Cameroon",
    "ai cap": "Egypt", "egypt": "Egypt",
    "ba lan": "Poland",
    "dan mach": "Denmark",
    "thuy si": "Switzerland",
    "thuy dien": "Sweden",
    "na uy": "Norway",
    "nga": "Russia",
    "ao": "Austria",
    "scotland": "Scotland",
    "wales": "Wales", "xu wales": "Wales",
    "colombia": "Colombia",
    "chile": "Chile",
    "peru": "Peru",
    "ecuador": "Ecuador",
    "paraguay": "Paraguay",
    "serbia": "Serbia",
    "iran": "Iran",
    "iraq": "Iraq", "i rac": "Iraq",
    "qatar": "Qatar", "ca ta": "Qatar",
    "canada": "Canada",
    "viet nam": "Vietnam", "vietnam": "Vietnam",
    "thai lan": "Thailand", "thailand": "Thailand",
    "trung quoc": "China",
    "hy lap": "Greece",
    "ukraine": "Ukraine", "u krai na": "Ukraine",
    "cong hoa sec": "Czech Republic", "sec": "Czech Republic", "czech": "Czech Republic",
}


def _vi_translate(name: str) -> str:
    """Nếu là tên nước bằng tiếng Việt -> đổi sang tên tiếng Anh; nếu không, giữ nguyên."""
    return _VI_COUNTRIES.get(_norm_key(name), name)


def _split_vs(q: str):
    """Tách 'A vs B' -> ['A', 'B']. Nếu không có dấu ngăn cách -> [q]."""
    parts = [p.strip() for p in _VS_RE.split((q or "").strip(), maxsplit=1)]
    return [p for p in parts if p]


# Đội nữ / trẻ / dự bị -> hạ điểm để không bị nhầm với đội 1 nam.
_DEPRIORITIZE = re.compile(r"(\bw\b|\bwomen\b|\bu\d{2}\b|\bii\b|\bb\b|reserves?|youth|academy)", re.IGNORECASE)


def _team_variants(name: str):
    """Các cách tìm để bắt cả tên có gạch nối ('Al-Nassr') lẫn có dấu cách,
    và token dài nhất ('al nassr' -> 'nassr') vì API đôi khi chỉ khớp theo từ."""
    name = (name or "").strip()
    out = [name]
    for v in (name.replace(" ", "-"), name.replace("-", " ")):
        if v and v not in out:
            out.append(v)
    tokens = [w for w in re.split(r"[\s-]+", name) if len(w) >= 4]
    if tokens:
        longest = max(tokens, key=len)
        if longest.lower() not in [o.lower() for o in out]:
            out.append(longest)
    return out


def _score_team(query: str, team_name: str) -> float:
    """Điểm mức độ khớp: khớp tuyệt đối > bắt đầu bằng > chứa; phạt đội nữ/trẻ và tên dài."""
    qn = (query or "").lower().strip().replace("-", " ")
    nn = (team_name or "").lower().replace("-", " ")
    s = 0.0
    if nn == qn:
        s += 100
    elif nn.startswith(qn + " "):
        s += 60
    elif nn.startswith(qn):
        s += 55
    elif qn in nn:
        s += 30
    if _DEPRIORITIZE.search(team_name or ""):
        s -= 50
    s -= max(0, len(nn) - len(qn)) * 0.6  # càng sát query càng tốt
    return s


# Một số CLB nổi bật mà tìm theo tên của API-Football hay sót (vd 'Al-Hilal Saudi FC'
# không ra khi gõ 'al hilal' — API trả về Al Hilal của Libya/Sudan thay vì Ả Rập Xê Út).
# Map: từ khoá đã chuẩn hoá -> (id, tên hiển thị, quốc gia). Dễ bổ sung thêm khi cần.
_FEATURED = {
    "al hilal": (2932, "Al-Hilal Saudi FC", "Saudi-Arabia"),
    "al hilal saudi": (2932, "Al-Hilal Saudi FC", "Saudi-Arabia"),
    "al nassr": (2939, "Al-Nassr", "Saudi-Arabia"),
    "al ittihad": (2929, "Al-Ittihad FC", "Saudi-Arabia"),
    "al ahli": (2926, "Al-Ahli Saudi FC", "Saudi-Arabia"),
}


def _featured_match(name: str):
    """Nếu từ khoá trùng 1 CLB nổi bật -> trả thẳng đội đó (không phụ thuộc search API)."""
    hit = _FEATURED.get((name or "").lower().strip().replace("-", " "))
    if not hit:
        return None
    tid, tname, country = hit
    return {"id": tid, "name": tname,
            "logo": f"https://media.api-sports.io/football/teams/{tid}.png", "country": country}


async def _search_teams(name: str, limit: int = 8, deep: bool = False):
    """Tìm đội theo tên, gộp nhiều biến thể rồi xếp theo độ khớp. Trả [{id,name,logo,country}].
    deep=True: tìm hết mọi biến thể (cho match-search, để có đủ ứng viên trùng tên ở nhiều nước)."""
    name = _vi_translate((name or "").strip())  # 'bồ đào nha' -> 'Portugal'
    if len(name) < 2:
        return []
    qn = name.lower().replace("-", " ")
    seen = {}
    for v in _team_variants(name):
        try:
            resp = (await _request("/teams", {"search": v}, ttl=STATIC_TTL)).get("response", [])
        except Exception:
            resp = []
        for it in resp:
            t = it.get("team") or {}
            if t.get("id") and t["id"] not in seen:
                seen[t["id"]] = {"id": t["id"], "name": t.get("name"),
                                 "logo": t.get("logo"), "country": t.get("country")}
        # Tìm nhanh (dropdown): có khớp tuyệt đối là đủ. Tìm sâu (match-search): quét hết.
        if not deep and any((t["name"] or "").lower().replace("-", " ") == qn for t in seen.values()):
            break
    ranked = sorted(seen.values(), key=lambda t: _score_team(name, t["name"] or ""), reverse=True)
    # CLB nổi bật bị API sót -> chèn lên đầu để luôn ưu tiên.
    feat = _featured_match(name)
    if feat:
        ranked = [feat] + [t for t in ranked if t["id"] != feat["id"]]
    return ranked[:limit]


def _best_pair(ca: list, cb: list):
    """Chọn cặp đội cho 'A vs B'. Ưu tiên 2 đội CÙNG QUỐC GIA (bắt đúng derby khi tên trùng,
    vd 'Al Hilal' có ở nhiều nước), đồng thời ưu tiên đội khớp tên cao ở mỗi bên."""
    if not ca or not cb:
        return (ca[0] if ca else None, cb[0] if cb else None)
    best, best_score = None, -1e9
    for i, a in enumerate(ca):
        for j, b in enumerate(cb):
            s = -(i + j)  # đội xếp hạng càng cao mỗi bên càng tốt
            if a.get("country") and a.get("country") == b.get("country"):
                s += 10   # cùng nước -> nhiều khả năng là cặp đối đầu thật
            if s > best_score:
                best_score, best = s, (a, b)
    return best


async def _resolve_team(name: str) -> Optional[dict]:
    """Phân giải tên đội -> {id, name, logo} khớp nhất (ưu tiên đội 1 nam)."""
    cands = await _search_teams(name, limit=1, deep=True)
    return cands[0] if cands else None


async def match_search(q: str) -> dict:
    """Trả {mode, teamA/teamB hoặc team, recent: [...], upcoming: [...]}.
    mode = 'h2h' khi gõ 'A vs B', 'team' khi gõ 1 đội."""
    parts = _split_vs(q)

    # ---- 2 đội: đối đầu (head-to-head) ----
    if len(parts) >= 2:
        ca = await _search_teams(parts[0], deep=True)
        cb = await _search_teams(parts[1], deep=True)
        a, b = _best_pair(ca, cb)
        if not a or not b:
            return {"mode": "h2h", "teamA": a, "teamB": b, "recent": [], "upcoming": [],
                    "notFound": [p for p, t in ((parts[0], a), (parts[1], b)) if not t]}
        if settings.use_mock:
            recent, upcoming = mock_data.team_recent(a["id"]), []
        else:
            h2h = f"{a['id']}-{b['id']}"
            recent = (await _request("/fixtures/headtohead", {"h2h": h2h, "last": 10}, ttl=STATIC_TTL)).get("response", [])
            upcoming = (await _request("/fixtures/headtohead", {"h2h": h2h, "next": 5}, ttl=UPCOMING_TTL)).get("response", [])
        return {"mode": "h2h", "teamA": a, "teamB": b, "recent": recent, "upcoming": upcoming}

    # ---- 1 đội: lịch đấu của đội ----
    team = await _resolve_team(parts[0] if parts else q)
    if not team:
        return {"mode": "team", "team": None, "recent": [], "upcoming": [], "notFound": [q]}
    if settings.use_mock:
        recent, upcoming = mock_data.team_recent(team["id"]), []
    else:
        recent = (await _request("/fixtures", {"team": team["id"], "last": 10}, ttl=STATIC_TTL)).get("response", [])
        upcoming = (await _request("/fixtures", {"team": team["id"], "next": 5}, ttl=UPCOMING_TTL)).get("response", [])
    return {"mode": "team", "team": team, "recent": recent, "upcoming": upcoming}


async def raw_request(path: str, params: dict) -> dict:
    """Debug: trả nguyên văn JSON từ API-Football (gồm errors/results)."""
    return await _request(path, params)


# ===== Cầu thủ nổi bật (chèn thẳng lên đầu kết quả tìm) =====
# Vì sao cần làm thế này:
#  1) API-Football KHÔNG có chỉ số độ nổi tiếng.
#  2) Họ chính thức của nhiều sao có thêm chữ ('Cristiano Ronaldo' họ 'dos Santos
#     Aveiro', 'L. Messi' họ 'Messi Cuccittini') -> thuật toán khớp theo HỌ đẩy họ
#     chìm dưới người vô danh ('Ronaldo Teixiera', 'Messina').
#  3) Endpoint /players/profiles (plan hiện tại) cắt kết quả ~250 và NHIỀU KHI KHÔNG
#     trả về sao lớn (vd Harry Kane, Vinícius...) -> boost thôi cũng vô dụng.
# => Giải pháp chắc nhất: tự giữ danh sách (id, tên đẹp, alias) đã XÁC MINH ID, và
#    CHÈN THẲNG vào kết quả khi từ khoá khớp alias. Ảnh dựng từ id theo mẫu chuẩn của
#    API-Football nên không cần gọi thêm API.
# Muốn thêm sao: tra ID đúng qua /api/_debug/players?search=<tên đầy đủ> rồi thêm 1 dòng.
_PLAYER_PHOTO = "https://media.api-sports.io/football/players/{}.png"

FAMOUS_PLAYERS = [
    (874, "Cristiano Ronaldo", ("ronaldo", "cristiano", "cr7")),
    (154, "Lionel Messi", ("messi", "lionel")),
    (276, "Neymar Jr", ("neymar",)),
    (278, "Kylian Mbappé", ("mbappe", "mbappé", "kylian")),
    (1100, "Erling Haaland", ("haaland", "erling")),
    (762, "Vinícius Júnior", ("vinicius", "vinícius", "vini")),
    (129718, "Jude Bellingham", ("bellingham", "jude")),
    (759, "Karim Benzema", ("benzema", "karim")),
    (629, "Kevin De Bruyne", ("de bruyne", "bruyne", "kdb")),
    (754, "Luka Modrić", ("modric", "modrić")),
    (306, "Mohamed Salah", ("salah",)),
    (521, "Robert Lewandowski", ("lewandowski", "lewa")),
    (56, "Antoine Griezmann", ("griezmann",)),
    (1485, "Bruno Fernandes", ("bruno fernandes", "bruno")),
    (2780, "Victor Osimhen", ("osimhen",)),
    (217, "Lautaro Martínez", ("lautaro",)),
    (184, "Harry Kane", ("kane", "harry kane")),
    (1460, "Bukayo Saka", ("saka", "bukayo")),
    (44, "Rodri", ("rodri",)),
    (631, "Phil Foden", ("foden",)),
    (186, "Son Heung-min", ("son", "heung", "son heung")),
]

# Tra cứu nhanh: id -> tên đẹp (để ghi đè tên ngắn 'L. Messi' nếu API có trả về).
_FAMOUS_NAME = {pid: name for pid, name, _ in FAMOUS_PLAYERS}


def _famous_matches(query: str) -> list:
    """Sao lớn khớp từ khoá -> chèn thẳng vào kết quả (id, name, photo)."""
    nq = _norm_key(query)
    if not nq:
        return []
    hits = []
    for pid, name, aliases in FAMOUS_PLAYERS:
        for a in aliases:
            na = _norm_key(a)
            # Khớp khi gõ một phần ('ronald' ~ 'ronaldo') hoặc gõ cả cụm ('lionel messi').
            if na.startswith(nq) or nq.startswith(na):
                hits.append({"id": pid, "name": name, "photo": _PLAYER_PHOTO.format(pid)})
                break
    return hits


def _score_player(query: str, profile: dict) -> float:
    """Điểm khớp tên cầu thủ. Xét cả CỤM ('lionel messi') lẫn TOKEN HỌ ('messi')
    để: (1) 'Messi' xịn không bị chìm dưới 'Messina/Messías', và (2) gõ 'Lionel Messi'
    vẫn ưu tiên Messi xịn hơn 'Lionel Messi Nyamsi'."""
    qn = _norm_key(query)
    qtokens = [t for t in qn.split() if len(t) >= 2]
    qlast = qtokens[-1] if qtokens else qn   # token "họ" hay gặp ở cuối, vd 'messi'
    p = profile.get("player") or {}
    last = _norm_key(p.get("lastname") or "")
    name = _norm_key(p.get("name") or "")
    s = 0.0
    if qn and (last == qn or name == qn):
        s += 100          # khớp tuyệt đối cả cụm
    elif qlast and last == qlast:
        s += 85           # họ khớp đúng token họ ('Messi' == 'messi')
    elif qlast and last.startswith(qlast):
        s += 70           # họ bắt đầu bằng ('Messina' ~ 'messi')
    elif qn and name.startswith(qn):
        s += 55           # tên đầy đủ bắt đầu bằng cả cụm
    elif qlast and qlast in last:
        s += 40
    elif qn and qn in name:
        s += 30
    # Hồ sơ đầy đủ (có ảnh / vị trí) thường là cầu thủ nổi bật hơn -> nhỉnh điểm.
    if p.get("photo"):
        s += 2
    if p.get("position"):
        s += 1
    # Họ càng sát độ dài token họ càng tốt ('Messi' hơn 'Messina').
    s -= max(0, len(last) - len(qlast)) * 0.5
    # Nếu sao lớn cũng lọt vào kết quả của API -> đẩy hẳn lên đầu (phòng khi có).
    if p.get("id") in _FAMOUS_NAME:
        s += 1000
    return s


async def search(q: str) -> dict:
    """Tìm đội + cầu thủ theo tên. Trả {'teams': [...], 'players': [...]}.
    Bọc try/except từng phần để 1 endpoint lỗi (vd plan chặn) không làm hỏng cả search."""
    if settings.use_mock:
        return mock_data.search(q)
    qq = (q or "").strip()
    if len(qq) < 3:
        return {"teams": [], "players": []}

    async def find_teams():
        try:
            # Dùng cùng bộ tìm + xếp hạng với match-search: bắt cả tên có gạch nối
            # ('Al-Nassr' khi gõ 'al nassr') và ưu tiên đội 1 nam thay vì đội nữ/trẻ.
            return await _search_teams(qq, limit=8)
        except Exception:
            return []

    async def _profiles(term):
        try:
            return (await _request("/players/profiles", {"search": term}, ttl=STATIC_TTL)).get("response", [])
        except Exception:
            return []

    async def find_players():
        # API /players/profiles tìm theo HỌ. Gõ "Lionel Messi" chỉ khớp tên đầy đủ
        # ('Lionel Messi Nyamsi') mà SÓT Messi xịn -> phải tìm thêm bằng token họ.
        # Cũng bỏ initial 1 ký tự ('L.Messi' -> 'Messi').
        tokens = [t for t in re.split(r"[^0-9A-Za-zÀ-ÿ]+", qq) if len(t) >= 2]
        terms = []
        for t in ([qq] + ([max(tokens, key=len), tokens[-1]] if tokens else [])):
            t = t.strip()
            if t and t.lower() not in [x.lower() for x in terms]:
                terms.append(t)
        # Gọi SONG SONG (tối đa 3 từ khoá) rồi gộp, khử trùng theo id.
        batches = await asyncio.gather(*[_profiles(t) for t in terms[:3]])
        merged = {}
        for resp in batches:
            for p in resp:
                pid = (p.get("player") or {}).get("id")
                if pid and pid not in merged:
                    merged[pid] = p
        # Xếp theo độ khớp tên đối với TỪ KHOÁ GỐC (để 'Messi' xịn lên đầu).
        ranked = sorted(merged.values(), key=lambda p: _score_player(qq, p), reverse=True)
        api_players = []
        for p in ranked:
            pl = p.get("player") or {}
            pid = pl.get("id")
            api_players.append({
                "id": pid,
                # Sao lớn: dùng tên hiển thị đẹp (vd 'Lionel Messi' thay cho 'L. Messi').
                "name": _FAMOUS_NAME.get(pid) or pl.get("name"),
                "photo": pl.get("photo"),
            })
        # Chèn sao lớn khớp alias LÊN ĐẦU, khử trùng theo id (sao lớn có thể đã có
        # trong kết quả API -> chỉ giữ 1 bản, ưu tiên bản sao lớn).
        seen, result = set(), []
        for item in _famous_matches(qq) + api_players:
            pid = item.get("id")
            if pid and pid not in seen:
                seen.add(pid)
                result.append(item)
        return result[:8]

    # Chạy SONG SONG đội + cầu thủ để ô search phản hồi nhanh hơn (trước đây gọi tuần tự).
    teams, players = await asyncio.gather(find_teams(), find_players())
    return {"teams": teams, "players": players}
