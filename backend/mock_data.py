"""
Dữ liệu mẫu mô phỏng ĐÚNG shape của API-Football (key "response").
Nhờ giữ đúng shape, khi bạn cắm API key thật, frontend không phải sửa gì.
Logo đội & ảnh cầu thủ dùng CDN công khai của api-sports nên hiển thị được luôn.

Ngày các trận được tạo ĐỘNG quanh "hôm nay" để demo luôn có trận live/hôm nay/kết quả.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional


def _iso(days: int, hour: int) -> str:
    d = datetime.now(timezone.utc) + timedelta(days=days)
    return d.replace(hour=hour, minute=0, second=0, microsecond=0).isoformat()

# ---- Helpers tạo nhanh 1 trận ----
def _team(tid, name):
    return {"id": tid, "name": name, "logo": f"https://media.api-sports.io/football/teams/{tid}.png"}

def _league(lid, name, country):
    return {"id": lid, "name": name, "country": country,
            "logo": f"https://media.api-sports.io/football/leagues/{lid}.png", "season": 2025}

LEAGUE_PL = _league(39, "Premier League", "England")
LEAGUE_LALIGA = _league(140, "La Liga", "Spain")
LEAGUE_WC = _league(1, "World Cup", "World")
LEAGUE_SAUDI = _league(307, "Saudi Pro League", "Saudi-Arabia")


def _fixture(fid, date, status, elapsed, home, away, gh, ga, venue,
             league=None, ref="M. Oliver", round_="Regular Season - 38"):
    league = league or LEAGUE_PL
    return {
        "fixture": {
            "id": fid,
            "date": date,
            "status": {"short": status, "elapsed": elapsed},
            "venue": {"name": venue, "city": ""},
            "referee": ref,
        },
        "league": {**league, "round": round_},
        "teams": {
            "home": {**home, "winner": gh is not None and gh > (ga or 0)},
            "away": {**away, "winner": ga is not None and ga > (gh or 0)},
        },
        "goals": {"home": gh, "away": ga},
    }

MUN, LIV, MCI, ARS, CHE, TOT = (
    _team(33, "Manchester United"), _team(40, "Liverpool"), _team(50, "Manchester City"),
    _team(42, "Arsenal"), _team(49, "Chelsea"), _team(47, "Tottenham"),
)
RMA, BAR = _team(541, "Real Madrid"), _team(529, "Barcelona")
# Đội tuyển quốc gia (World Cup)
ARG, BRA, FRA, ENG, ESP, POR = (
    _team(26, "Argentina"), _team(6, "Brazil"), _team(2, "France"),
    _team(10, "England"), _team(9, "Spain"), _team(27, "Portugal"),
)
# CLB Saudi Pro League
ALNASSR, ALHILAL, ALITTIHAD, ALAHLI = (
    _team(2939, "Al-Nassr"), _team(2932, "Al-Hilal"),
    _team(2929, "Al-Ittihad"), _team(2926, "Al-Ahli"),
)

ALL_FIXTURES = [
    # ---- Premier League ----
    _fixture(1001, _iso(-1, 19), "FT", 90, MCI, CHE, 3, 1, "Etihad Stadium"),
    _fixture(1002, _iso(-1, 21), "FT", 90, ARS, TOT, 2, 2, "Emirates Stadium"),
    _fixture(1003, _iso(0, 14), "2H", 67, MUN, LIV, 1, 1, "Old Trafford"),
    _fixture(1004, _iso(0, 21), "NS", None, LIV, ARS, None, None, "Anfield"),
    _fixture(1005, _iso(1, 16), "NS", None, CHE, MUN, None, None, "Stamford Bridge"),
    _fixture(1006, _iso(2, 16), "NS", None, TOT, MCI, None, None, "Tottenham Hotspur Stadium"),
    # ---- La Liga ----
    _fixture(2001, _iso(0, 19), "1H", 30, RMA, BAR, 2, 1, "Santiago Bernabéu",
             league=LEAGUE_LALIGA, ref="A. Lahoz"),
    _fixture(2002, _iso(1, 20), "NS", None, BAR, RMA, None, None, "Spotify Camp Nou",
             league=LEAGUE_LALIGA, ref="A. Lahoz"),
    # ---- World Cup 2026 ----
    _fixture(3001, _iso(0, 22), "2H", 70, ARG, FRA, 1, 1, "MetLife Stadium",
             league=LEAGUE_WC, ref="Sl. Vinčić", round_="Group stage"),
    _fixture(3002, _iso(1, 22), "NS", None, BRA, ENG, None, None, "SoFi Stadium",
             league=LEAGUE_WC, ref="C. Ramos", round_="Group stage"),
    _fixture(3003, _iso(2, 19), "NS", None, ESP, POR, None, None, "AT&T Stadium",
             league=LEAGUE_WC, ref="D. Makkelie", round_="Group stage"),
    # ---- Saudi Pro League ----
    _fixture(4001, _iso(0, 17), "1H", 35, ALNASSR, ALHILAL, 1, 1, "Al-Awwal Park",
             league=LEAGUE_SAUDI, ref="M. Al-Hoaish"),
    _fixture(4002, _iso(1, 17), "NS", None, ALITTIHAD, ALAHLI, None, None, "King Abdullah Sports City",
             league=LEAGUE_SAUDI, ref="M. Al-Hoaish"),
]


def fixtures_for(date: Optional[str] = None, league: Optional[int] = None) -> list:
    out = ALL_FIXTURES
    if date:
        out = [f for f in out if f["fixture"]["date"].startswith(date)]
    if league:
        out = [f for f in out if f["league"]["id"] == int(league)]
    return out


def fixture_by_id(fixture_id: int) -> list:
    return [f for f in ALL_FIXTURES if f["fixture"]["id"] == fixture_id]


# ---- Bảng xếp hạng (standings) ----
def _standing(rank, team, played, win, draw, lose, gf, ga, pts):
    return {
        "rank": rank, "team": team, "points": pts, "goalsDiff": gf - ga,
        "all": {"played": played, "win": win, "draw": draw, "lose": lose,
                "goals": {"for": gf, "against": ga}},
        "form": "WWDLW",
    }

# Danh sách CLB / đội tuyển (id, tên) — logo lấy theo id từ CDN.
PL_CLUBS = [
    (50, "Manchester City"), (42, "Arsenal"), (40, "Liverpool"), (33, "Manchester United"),
    (49, "Chelsea"), (47, "Tottenham"), (34, "Newcastle"), (66, "Aston Villa"),
    (35, "Bournemouth"), (51, "Brighton"), (52, "Crystal Palace"), (36, "Fulham"),
    (55, "Brentford"), (45, "Everton"), (48, "West Ham"), (39, "Wolves"),
    (65, "Nottingham Forest"), (46, "Leicester"), (41, "Southampton"), (57, "Ipswich"),
]
LA_LIGA_CLUBS = [
    (541, "Real Madrid"), (529, "Barcelona"), (530, "Atlético Madrid"), (531, "Athletic Club"),
    (548, "Real Sociedad"), (533, "Villarreal"), (543, "Real Betis"), (536, "Sevilla"),
    (547, "Girona"), (532, "Valencia"), (538, "Celta Vigo"), (727, "Osasuna"),
    (728, "Rayo Vallecano"), (546, "Getafe"), (798, "Mallorca"), (534, "Las Palmas"),
    (542, "Alavés"), (540, "Espanyol"), (539, "Leganés"), (720, "Valladolid"),
]
SAUDI_CLUBS = [(2932, "Al-Hilal"), (2939, "Al-Nassr"), (2929, "Al-Ittihad"), (2926, "Al-Ahli")]

# 8 bảng World Cup, mỗi bảng 4 đội.
WC_GROUPS = {
    "A": [(26, "Argentina"), (16, "Mexico"), (24, "Poland"), (23, "Saudi Arabia")],
    "B": [(2, "France"), (21, "Denmark"), (20, "Australia"), (2382, "Canada")],
    "C": [(10, "England"), (2384, "USA"), (13, "Senegal"), (22, "Iran")],
    "D": [(9, "Spain"), (3, "Croatia"), (12, "Japan"), (31, "Morocco")],
    "E": [(6, "Brazil"), (15, "Switzerland"), (14, "Serbia"), (1530, "Cameroon")],
    "F": [(27, "Portugal"), (7, "Uruguay"), (17, "South Korea"), (1504, "Ghana")],
    "G": [(25, "Germany"), (1, "Belgium"), (2433, "Ecuador"), (1569, "Qatar")],
    "H": [(1118, "Netherlands"), (8, "Colombia"), (19, "Nigeria"), (768, "Italy")],
}


def _full_table(league, clubs):
    """BXH đầy đủ từ danh sách CLB (điểm giảm dần cho trông tự nhiên)."""
    rows = []
    for i, (tid, tname) in enumerate(clubs):
        w = max(3, 27 - i)
        l = min(30, 2 + i)
        d = max(0, 37 - w - l)
        gf = max(22, 88 - i * 3)
        ga = 24 + i * 2
        rows.append(_standing(i + 1, _team(tid, tname), w + d + l, w, d, l, gf, ga, w * 3 + d))
    return [{"league": {**league, "standings": [rows]}}]


def _wc_table():
    """BXH World Cup: 8 bảng riêng, mỗi hàng gắn tên Group."""
    rec = [(2, 2, 0, 0, 5, 1), (2, 1, 1, 0, 4, 2), (2, 0, 1, 1, 2, 3), (2, 0, 0, 2, 1, 6)]
    groups = []
    for gname, teams in WC_GROUPS.items():
        rows = []
        for i, (tid, tname) in enumerate(teams):
            p, w, d, l, gf, ga = rec[i]
            s = _standing(i + 1, _team(tid, tname), p, w, d, l, gf, ga, w * 3 + d)
            s["group"] = f"Group {gname}"
            rows.append(s)
        groups.append(rows)
    return [{"league": {**LEAGUE_WC, "standings": groups}}]


STANDINGS_BY_LEAGUE = {
    39: _full_table(LEAGUE_PL, PL_CLUBS),
    140: _full_table(LEAGUE_LALIGA, LA_LIGA_CLUBS),
    1: _wc_table(),
    307: _full_table(LEAGUE_SAUDI, SAUDI_CLUBS),
}


def standings_for(league: int) -> list:
    return STANDINGS_BY_LEAGUE.get(int(league), [])


# ---- Registry cầu thủ (dùng chung cho squad / trang cầu thủ / top scorers) ----
def _photo(pid):
    return f"https://media.api-sports.io/football/players/{pid}.png"

# pid: (tên, số áo, vị trí, tuổi, quốc tịch, bàn, kiến tạo, số trận, phút, rating, team, league)
PLAYER_DB = {
    # Liverpool
    306: ("Mohamed Salah", 11, "Attacker", 33, "Egypt", 21, 12, 36, 3100, "7.9", LIV, LEAGUE_PL),
    290: ("Virgil van Dijk", 4, "Defender", 34, "Netherlands", 3, 1, 36, 3200, "7.4", LIV, LEAGUE_PL),
    283: ("Alisson", 1, "Goalkeeper", 33, "Brazil", 0, 0, 33, 2970, "7.1", LIV, LEAGUE_PL),
    284: ("Darwin Núñez", 9, "Attacker", 26, "Uruguay", 13, 6, 35, 2400, "7.0", LIV, LEAGUE_PL),
    # Manchester United
    909: ("Bruno Fernandes", 8, "Midfielder", 31, "Portugal", 10, 9, 36, 3150, "7.5", MUN, LEAGUE_PL),
    2935: ("Marcus Rashford", 10, "Attacker", 28, "England", 15, 5, 35, 2900, "7.2", MUN, LEAGUE_PL),
    2934: ("Rasmus Højlund", 11, "Attacker", 23, "Denmark", 14, 2, 34, 2500, "6.9", MUN, LEAGUE_PL),
    905: ("Casemiro", 18, "Midfielder", 34, "Brazil", 4, 3, 30, 2400, "6.8", MUN, LEAGUE_PL),
    # Manchester City
    1100: ("Erling Haaland", 9, "Attacker", 25, "Norway", 27, 5, 35, 3000, "7.9", MCI, LEAGUE_PL),
    629: ("Kevin De Bruyne", 17, "Midfielder", 34, "Belgium", 6, 18, 30, 2400, "7.7", MCI, LEAGUE_PL),
    1500: ("Phil Foden", 47, "Midfielder", 25, "England", 17, 8, 35, 2900, "7.6", MCI, LEAGUE_PL),
    1501: ("Rodri", 16, "Midfielder", 29, "Spain", 8, 7, 34, 3000, "7.8", MCI, LEAGUE_PL),
    # Arsenal
    1465: ("Bukayo Saka", 7, "Attacker", 24, "England", 16, 13, 36, 3100, "7.7", ARS, LEAGUE_PL),
    1466: ("Martin Ødegaard", 8, "Midfielder", 27, "Norway", 11, 10, 35, 3000, "7.5", ARS, LEAGUE_PL),
    1467: ("Declan Rice", 41, "Midfielder", 27, "England", 7, 8, 36, 3200, "7.4", ARS, LEAGUE_PL),
    # Chelsea
    280: ("Cole Palmer", 20, "Midfielder", 23, "England", 22, 11, 34, 2950, "7.8", CHE, LEAGUE_PL),
    281: ("Nicolas Jackson", 15, "Attacker", 24, "Senegal", 14, 5, 33, 2600, "7.0", CHE, LEAGUE_PL),
    # Tottenham
    186: ("Son Heung-min", 7, "Attacker", 33, "South Korea", 17, 10, 35, 3000, "7.5", TOT, LEAGUE_PL),
    1505: ("James Maddison", 10, "Midfielder", 29, "England", 6, 9, 32, 2700, "7.2", TOT, LEAGUE_PL),
    # Real Madrid
    1102: ("Jude Bellingham", 5, "Midfielder", 22, "England", 19, 6, 35, 3050, "7.9", RMA, LEAGUE_LALIGA),
    762: ("Vinícius Júnior", 7, "Attacker", 25, "Brazil", 15, 9, 34, 2900, "7.7", RMA, LEAGUE_LALIGA),
    730: ("Thibaut Courtois", 1, "Goalkeeper", 33, "Belgium", 0, 0, 30, 2700, "7.2", RMA, LEAGUE_LALIGA),
    # Barcelona
    521: ("Robert Lewandowski", 9, "Attacker", 37, "Poland", 20, 3, 35, 2900, "7.5", BAR, LEAGUE_LALIGA),
    47431: ("Lamine Yamal", 19, "Attacker", 18, "Spain", 9, 12, 34, 2600, "7.6", BAR, LEAGUE_LALIGA),
    1503: ("Pedri", 8, "Midfielder", 23, "Spain", 5, 6, 33, 2800, "7.4", BAR, LEAGUE_LALIGA),
    # ===== World Cup (đội tuyển QG) =====
    154: ("Lionel Messi", 10, "Attacker", 38, "Argentina", 5, 4, 7, 600, "8.2", ARG, LEAGUE_WC),
    9301: ("Lautaro Martínez", 22, "Attacker", 28, "Argentina", 4, 1, 7, 540, "7.4", ARG, LEAGUE_WC),
    9302: ("Rodrygo", 10, "Attacker", 25, "Brazil", 3, 2, 6, 480, "7.3", BRA, LEAGUE_WC),
    9303: ("Raphinha", 11, "Attacker", 29, "Brazil", 4, 3, 6, 510, "7.5", BRA, LEAGUE_WC),
    278: ("Kylian Mbappé", 10, "Attacker", 27, "France", 6, 2, 7, 620, "8.0", FRA, LEAGUE_WC),
    9304: ("Antoine Griezmann", 7, "Midfielder", 35, "France", 2, 4, 7, 600, "7.4", FRA, LEAGUE_WC),
    9305: ("Harry Kane", 9, "Attacker", 32, "England", 5, 1, 7, 630, "7.6", ENG, LEAGUE_WC),
    9306: ("Jude Bellingham", 10, "Midfielder", 22, "England", 3, 3, 7, 600, "7.7", ENG, LEAGUE_WC),
    9307: ("Álvaro Morata", 7, "Attacker", 33, "Spain", 3, 1, 6, 470, "7.0", ESP, LEAGUE_WC),
    9308: ("Dani Olmo", 21, "Midfielder", 27, "Spain", 2, 3, 6, 450, "7.2", ESP, LEAGUE_WC),
    9309: ("Rafael Leão", 17, "Attacker", 26, "Portugal", 3, 2, 6, 480, "7.3", POR, LEAGUE_WC),
    9310: ("Bernardo Silva", 10, "Midfielder", 31, "Portugal", 2, 3, 6, 510, "7.4", POR, LEAGUE_WC),
    # ===== Saudi Pro League =====
    874: ("Cristiano Ronaldo", 7, "Attacker", 41, "Portugal", 30, 8, 32, 2850, "8.0", ALNASSR, LEAGUE_SAUDI),
    2294: ("Sadio Mané", 10, "Attacker", 33, "Senegal", 12, 9, 31, 2600, "7.4", ALNASSR, LEAGUE_SAUDI),
    276: ("Neymar", 10, "Attacker", 34, "Brazil", 8, 11, 20, 1500, "7.6", ALHILAL, LEAGUE_SAUDI),
    9201: ("Aleksandar Mitrović", 9, "Attacker", 31, "Serbia", 28, 4, 33, 2950, "7.8", ALHILAL, LEAGUE_SAUDI),
    759: ("Karim Benzema", 9, "Attacker", 38, "France", 18, 7, 30, 2600, "7.6", ALITTIHAD, LEAGUE_SAUDI),
    9202: ("Fabinho", 5, "Midfielder", 32, "Brazil", 3, 4, 31, 2700, "7.1", ALITTIHAD, LEAGUE_SAUDI),
    9203: ("Riyad Mahrez", 7, "Attacker", 35, "Algeria", 11, 13, 32, 2800, "7.5", ALAHLI, LEAGUE_SAUDI),
    9204: ("Roberto Firmino", 9, "Attacker", 34, "Brazil", 14, 6, 31, 2500, "7.3", ALAHLI, LEAGUE_SAUDI),
}


def _player_lite(pid):
    n = PLAYER_DB[pid]
    return {"id": pid, "name": n[0], "number": n[1], "pos": n[2], "photo": _photo(pid)}


def player_by_id(player_id: int) -> list:
    n = PLAYER_DB.get(player_id)
    if not n:
        return []
    name, number, pos, age, nat, g, a, apps, mins, rating, team, league = n
    return [{
        "player": {"id": player_id, "name": name, "age": age, "nationality": nat,
                   "height": "—", "weight": "—", "photo": _photo(player_id)},
        "statistics": [{
            "team": team,
            "league": {"id": league["id"], "name": league["name"],
                       "season": league["season"], "logo": league["logo"]},
            "games": {"appearences": apps, "minutes": mins, "position": pos, "rating": rating},
            "goals": {"total": g, "assists": a},
            "cards": {"yellow": 2, "red": 0},
        }],
    }]


# ---- Đội bóng + squad ----
# team_id -> (tên, sân, thành phố, sức chứa, năm thành lập)
TEAM_META = {
    40: ("Liverpool", "Anfield", "Liverpool", 61276, 1892),
    33: ("Manchester United", "Old Trafford", "Manchester", 74310, 1878),
    50: ("Manchester City", "Etihad Stadium", "Manchester", 53400, 1880),
    42: ("Arsenal", "Emirates Stadium", "London", 60704, 1886),
    49: ("Chelsea", "Stamford Bridge", "London", 40341, 1905),
    47: ("Tottenham", "Tottenham Hotspur Stadium", "London", 62850, 1882),
    541: ("Real Madrid", "Santiago Bernabéu", "Madrid", 81044, 1902),
    529: ("Barcelona", "Spotify Camp Nou", "Barcelona", 99354, 1899),
    # Đội tuyển quốc gia
    26: ("Argentina", "Estadio Monumental", "Buenos Aires", 83214, 1893),
    6: ("Brazil", "Maracanã", "Rio de Janeiro", 78838, 1914),
    2: ("France", "Stade de France", "Paris", 80698, 1919),
    10: ("England", "Wembley", "London", 90000, 1863),
    9: ("Spain", "Metropolitano", "Madrid", 70460, 1913),
    27: ("Portugal", "Estádio da Luz", "Lisbon", 64642, 1914),
    # CLB Saudi
    2939: ("Al-Nassr", "Al-Awwal Park", "Riyadh", 25000, 1955),
    2932: ("Al-Hilal", "Kingdom Arena", "Riyadh", 25000, 1957),
    2929: ("Al-Ittihad", "King Abdullah Sports City", "Jeddah", 62345, 1927),
    2926: ("Al-Ahli", "King Abdullah Sports City", "Jeddah", 62345, 1937),
}
# squad = các pid trong PLAYER_DB thuộc đội đó
SQUADS = {
    40: [306, 290, 283, 284],
    33: [909, 2935, 2934, 905],
    50: [1100, 629, 1500, 1501],
    42: [1465, 1466, 1467],
    49: [280, 281],
    47: [186, 1505],
    541: [1102, 762, 730],
    529: [521, 47431, 1503],
    # Đội tuyển
    26: [154, 9301],
    6: [9302, 9303],
    2: [278, 9304],
    10: [9305, 9306],
    9: [9307, 9308],
    27: [9309, 9310],
    # Saudi
    2939: [874, 2294],
    2932: [276, 9201],
    2929: [759, 9202],
    2926: [9203, 9204],
}


def team_by_id(team_id: int) -> list:
    meta = TEAM_META.get(team_id)
    if not meta:
        return []
    name, venue, city, cap, founded = meta
    return [{
        "team": {"id": team_id, "name": name, "country": "", "founded": founded,
                 "logo": f"https://media.api-sports.io/football/teams/{team_id}.png"},
        "venue": {"name": venue, "city": city, "capacity": cap},
        "squad": [_player_lite(pid) for pid in SQUADS.get(team_id, [])],
    }]


# ---- Line-up (đội hình ra sân) ----
# grid = "row:col": row 1 = thủ môn, tăng dần về phía tấn công; col = cột trong hàng.
def _xi(pid, name, number, pos, grid):
    return {"player": {
        "id": pid, "name": name, "number": number, "pos": pos, "grid": grid,
        "photo": f"https://media.api-sports.io/football/players/{pid}.png",
    }}

LINEUPS = {
    1003: [
        {
            "team": {"id": 33, "name": "Manchester United",
                     "logo": "https://media.api-sports.io/football/teams/33.png"},
            "formation": "4-2-3-1",
            "startXI": [
                _xi(2931, "A. Onana", 24, "G", "1:1"),
                _xi(18846, "D. Dalot", 20, "D", "2:1"),
                _xi(889, "R. Varane", 19, "D", "2:2"),
                _xi(1485, "L. Martínez", 6, "D", "2:3"),
                _xi(18845, "L. Shaw", 23, "D", "2:4"),
                _xi(905, "Casemiro", 18, "M", "3:1"),
                _xi(31170, "K. Mainoo", 37, "M", "3:2"),
                _xi(909, "B. Fernandes", 8, "M", "4:1"),
                _xi(18748, "M. Mount", 7, "M", "4:2"),
                _xi(2935, "M. Rashford", 10, "M", "4:3"),
                _xi(2934, "R. Højlund", 11, "F", "5:1"),
            ],
            "substitutes": [
                _xi(50132, "A. Bayındır", 1, "G", None),
                _xi(1478, "H. Maguire", 5, "D", None),
                _xi(18968, "S. McTominay", 39, "M", None),
            ],
            "coach": {"id": 19, "name": "E. ten Hag",
                      "photo": "https://media.api-sports.io/football/coachs/19.png"},
        },
        {
            "team": {"id": 40, "name": "Liverpool",
                     "logo": "https://media.api-sports.io/football/teams/40.png"},
            "formation": "4-3-3",
            "startXI": [
                _xi(283, "Alisson", 1, "G", "1:1"),
                _xi(304, "T. Alexander-Arnold", 66, "D", "2:1"),
                _xi(1602, "I. Konaté", 5, "D", "2:2"),
                _xi(290, "V. van Dijk", 4, "D", "2:3"),
                _xi(18839, "A. Robertson", 26, "D", "2:4"),
                _xi(1599, "A. Mac Allister", 10, "M", "3:1"),
                _xi(307, "Wataru Endo", 3, "M", "3:2"),
                _xi(1601, "D. Szoboszlai", 8, "M", "3:3"),
                _xi(306, "M. Salah", 11, "F", "4:1"),
                _xi(284, "D. Núñez", 9, "F", "4:2"),
                _xi(288, "L. Díaz", 7, "F", "4:3"),
            ],
            "substitutes": [
                _xi(285, "C. Kelleher", 62, "G", None),
                _xi(292, "J. Gomez", 2, "D", None),
                _xi(308, "H. Elliott", 19, "M", None),
            ],
            "coach": {"id": 8, "name": "J. Klopp",
                      "photo": "https://media.api-sports.io/football/coachs/8.png"},
        },
    ],
    2001: [
        {
            "team": {"id": 541, "name": "Real Madrid",
                     "logo": "https://media.api-sports.io/football/teams/541.png"},
            "formation": "4-3-3",
            "startXI": [
                _xi(730, "T. Courtois", 1, "G", "1:1"),
                _xi(9001, "D. Carvajal", 2, "D", "2:1"),
                _xi(9002, "A. Rüdiger", 22, "D", "2:2"),
                _xi(9003, "É. Militão", 3, "D", "2:3"),
                _xi(9004, "F. Mendy", 23, "D", "2:4"),
                _xi(9005, "F. Valverde", 15, "M", "3:1"),
                _xi(1102, "J. Bellingham", 5, "M", "3:2"),
                _xi(9006, "A. Tchouaméni", 18, "M", "3:3"),
                _xi(762, "Vinícius Jr", 7, "F", "4:1"),
                _xi(9007, "Rodrygo", 11, "F", "4:2"),
                _xi(9008, "Joselu", 14, "F", "4:3"),
            ],
            "substitutes": [
                _xi(9009, "A. Lunin", 13, "G", None),
                _xi(9010, "L. Modrić", 10, "M", None),
                _xi(9011, "E. Camavinga", 12, "M", None),
            ],
            "coach": {"id": 2407, "name": "C. Ancelotti",
                      "photo": "https://media.api-sports.io/football/coachs/2407.png"},
        },
        {
            "team": {"id": 529, "name": "Barcelona",
                     "logo": "https://media.api-sports.io/football/teams/529.png"},
            "formation": "4-3-3",
            "startXI": [
                _xi(9020, "M. ter Stegen", 1, "G", "1:1"),
                _xi(9021, "J. Cancelo", 2, "D", "2:1"),
                _xi(9022, "R. Araújo", 4, "D", "2:2"),
                _xi(9023, "A. Christensen", 15, "D", "2:3"),
                _xi(9024, "A. Balde", 28, "D", "2:4"),
                _xi(9025, "F. de Jong", 21, "M", "3:1"),
                _xi(1503, "Pedri", 8, "M", "3:2"),
                _xi(9026, "İ. Gündoğan", 22, "M", "3:3"),
                _xi(47431, "L. Yamal", 19, "F", "4:1"),
                _xi(521, "R. Lewandowski", 9, "F", "4:2"),
                _xi(9027, "Raphinha", 11, "F", "4:3"),
            ],
            "substitutes": [
                _xi(9028, "I. Peña", 13, "G", None),
                _xi(9029, "Gavi", 6, "M", None),
                _xi(9030, "Ferran Torres", 7, "F", None),
            ],
            "coach": {"id": 2402, "name": "X. Hernández",
                      "photo": "https://media.api-sports.io/football/coachs/2402.png"},
        },
    ],
    3001: [
        {
            "team": {"id": 26, "name": "Argentina",
                     "logo": "https://media.api-sports.io/football/teams/26.png"},
            "formation": "4-3-3",
            "startXI": [
                _xi(9501, "E. Martínez", 23, "G", "1:1"),
                _xi(9502, "N. Molina", 26, "D", "2:1"),
                _xi(9503, "C. Romero", 13, "D", "2:2"),
                _xi(9504, "N. Otamendi", 19, "D", "2:3"),
                _xi(9505, "N. Tagliafico", 3, "D", "2:4"),
                _xi(9506, "R. De Paul", 7, "M", "3:1"),
                _xi(9507, "E. Fernández", 24, "M", "3:2"),
                _xi(9508, "A. Mac Allister", 20, "M", "3:3"),
                _xi(154, "L. Messi", 10, "F", "4:1"),
                _xi(9301, "L. Martínez", 22, "F", "4:2"),
                _xi(9509, "J. Álvarez", 9, "F", "4:3"),
            ],
            "substitutes": [
                _xi(9510, "G. Rulli", 12, "G", None),
                _xi(9511, "L. Paredes", 5, "M", None),
                _xi(9512, "P. Dybala", 21, "F", None),
            ],
            "coach": {"id": 9600, "name": "L. Scaloni",
                      "photo": "https://media.api-sports.io/football/coachs/9600.png"},
        },
        {
            "team": {"id": 2, "name": "France",
                     "logo": "https://media.api-sports.io/football/teams/2.png"},
            "formation": "4-3-3",
            "startXI": [
                _xi(9520, "M. Maignan", 16, "G", "1:1"),
                _xi(9521, "J. Koundé", 5, "D", "2:1"),
                _xi(9522, "D. Upamecano", 4, "D", "2:2"),
                _xi(9523, "W. Saliba", 17, "D", "2:3"),
                _xi(9524, "T. Hernández", 22, "D", "2:4"),
                _xi(9525, "A. Tchouaméni", 8, "M", "3:1"),
                _xi(9526, "A. Rabiot", 14, "M", "3:2"),
                _xi(9304, "A. Griezmann", 7, "M", "3:3"),
                _xi(278, "K. Mbappé", 10, "F", "4:1"),
                _xi(9527, "M. Thuram", 26, "F", "4:2"),
                _xi(9528, "O. Dembélé", 11, "F", "4:3"),
            ],
            "substitutes": [
                _xi(9529, "B. Samba", 1, "G", None),
                _xi(9530, "E. Camavinga", 12, "M", None),
                _xi(9531, "K. Coman", 20, "F", None),
            ],
            "coach": {"id": 9601, "name": "D. Deschamps",
                      "photo": "https://media.api-sports.io/football/coachs/9601.png"},
        },
    ],
    4001: [
        {
            "team": {"id": 2939, "name": "Al-Nassr",
                     "logo": "https://media.api-sports.io/football/teams/2939.png"},
            "formation": "4-2-3-1",
            "startXI": [
                _xi(9620, "B. Al-Aqidi", 22, "G", "1:1"),
                _xi(9621, "S. Al-Ghannam", 25, "D", "2:1"),
                _xi(9622, "A. Laporte", 14, "D", "2:2"),
                _xi(9623, "M. Šimić", 3, "D", "2:3"),
                _xi(9624, "A. Al-Amri", 12, "D", "2:4"),
                _xi(9625, "M. Brozović", 23, "M", "3:1"),
                _xi(9626, "S. Al-Khaibari", 28, "M", "3:2"),
                _xi(2294, "S. Mané", 10, "M", "4:1"),
                _xi(9627, "A. Ghareeb", 18, "M", "4:2"),
                _xi(9628, "Otávio", 8, "M", "4:3"),
                _xi(874, "C. Ronaldo", 7, "F", "5:1"),
            ],
            "substitutes": [
                _xi(9629, "N. Al-Aqidi", 1, "G", None),
                _xi(9630, "A. Boushal", 30, "M", None),
                _xi(9631, "M. Marega", 9, "F", None),
            ],
            "coach": {"id": 9602, "name": "L. Castro",
                      "photo": "https://media.api-sports.io/football/coachs/9602.png"},
        },
        {
            "team": {"id": 2932, "name": "Al-Hilal",
                     "logo": "https://media.api-sports.io/football/teams/2932.png"},
            "formation": "4-2-3-1",
            "startXI": [
                _xi(9640, "Y. Bono", 1, "G", "1:1"),
                _xi(9641, "S. Abdulhamid", 66, "D", "2:1"),
                _xi(9642, "K. Koulibaly", 3, "D", "2:2"),
                _xi(9643, "Ali Al-Bulaihi", 4, "D", "2:3"),
                _xi(9644, "Y. Al-Shahrani", 13, "D", "2:4"),
                _xi(9645, "Rúben Neves", 8, "M", "3:1"),
                _xi(9646, "S. Milinković-Savić", 20, "M", "3:2"),
                _xi(276, "Neymar", 10, "M", "4:1"),
                _xi(9647, "Malcom", 77, "M", "4:2"),
                _xi(9648, "S. Al-Dawsari", 29, "M", "4:3"),
                _xi(9201, "A. Mitrović", 9, "F", "5:1"),
            ],
            "substitutes": [
                _xi(9649, "H. Al-Sahafi", 21, "G", None),
                _xi(9650, "N. Al-Dawsari", 14, "M", None),
                _xi(9651, "M. Marega", 19, "F", None),
            ],
            "coach": {"id": 9603, "name": "J. Jesus",
                      "photo": "https://media.api-sports.io/football/coachs/9603.png"},
        },
    ],
}


def lineups_for(fixture_id: int) -> list:
    return LINEUPS.get(fixture_id, [])


# ---- Sự kiện trận đấu (timeline) ----
def _event(elapsed, team, pid, pname, type_, detail, assist=None):
    return {
        "time": {"elapsed": elapsed},
        "team": {"id": team["id"], "name": team["name"], "logo": team["logo"]},
        "player": {"id": pid, "name": pname},
        "assist": {"id": assist[0], "name": assist[1]} if assist else {"id": None, "name": None},
        "type": type_, "detail": detail,
    }

EVENTS = {
    1003: [
        _event(23, MUN, 2935, "M. Rashford", "Goal", "Normal Goal", (909, "B. Fernandes")),
        _event(38, MUN, 905, "Casemiro", "Card", "Yellow Card"),
        _event(45, LIV, 1599, "A. Mac Allister", "Card", "Yellow Card"),
        _event(61, LIV, 306, "M. Salah", "Goal", "Normal Goal", (304, "T. Alexander-Arnold")),
        _event(65, MUN, 2934, "R. Højlund", "subst", "Substitution 1", (18968, "S. McTominay")),
    ],
    2001: [
        _event(12, RMA, 762, "Vinícius Jr", "Goal", "Normal Goal", (1102, "J. Bellingham")),
        _event(22, BAR, 521, "R. Lewandowski", "Goal", "Normal Goal", (47431, "L. Yamal")),
        _event(25, RMA, 1102, "J. Bellingham", "Goal", "Normal Goal", (762, "Vinícius Jr")),
        _event(28, BAR, 9022, "R. Araújo", "Card", "Yellow Card"),
    ],
    3001: [
        _event(30, ARG, 154, "L. Messi", "Goal", "Normal Goal", (9301, "L. Martínez")),
        _event(55, FRA, 278, "K. Mbappé", "Goal", "Normal Goal", (9304, "A. Griezmann")),
        _event(63, FRA, 9525, "A. Tchouaméni", "Card", "Yellow Card"),
    ],
    4001: [
        _event(15, ALNASSR, 874, "C. Ronaldo", "Goal", "Normal Goal", (2294, "S. Mané")),
        _event(32, ALHILAL, 9201, "A. Mitrović", "Goal", "Normal Goal", (276, "Neymar")),
    ],
}


def events_for(fixture_id: int) -> list:
    return EVENTS.get(fixture_id, [])


# ---- Top scorers (vua phá lưới) — tự tính từ PLAYER_DB theo giải, sắp theo số bàn ----
def topscorers_for(league: int) -> list:
    lid = int(league)
    rows = [(pid, n) for pid, n in PLAYER_DB.items() if n[11]["id"] == lid]
    rows.sort(key=lambda x: x[1][5], reverse=True)  # n[5] = số bàn thắng
    out = []
    for pid, n in rows[:10]:
        out.append({
            "player": {"id": pid, "name": n[0], "photo": _photo(pid)},
            "statistics": [{
                "team": n[10],
                "goals": {"total": n[5], "assists": n[6]},
                "games": {"appearences": n[7]},
            }],
        })
    return out


# ---- Danh sách giải cho bộ lọc ----
CURATED_LEAGUES = [
    {"id": 1, "name": "World Cup"},
    {"id": 10, "name": "Friendlies"},
    {"id": 39, "name": "Premier League"},
    {"id": 140, "name": "La Liga"},
    {"id": 307, "name": "Saudi Pro League"},
    {"id": 135, "name": "Serie A"},
    {"id": 78, "name": "Bundesliga"},
    {"id": 61, "name": "Ligue 1"},
    {"id": 253, "name": "MLS"},
    {"id": 340, "name": "V-League"},
    {"id": 2, "name": "Champions League"},
    {"id": 3, "name": "Europa League"},
    {"id": 848, "name": "UEFA Conference League"},
    {"id": 45, "name": "FA Cup"},
    {"id": 143, "name": "Copa del Rey"},
    {"id": 15, "name": "FIFA Club World Cup"},
]


# ---- Tìm kiếm (đội + cầu thủ) — lấy từ TEAM_META + PLAYER_DB ----
def search(q: str) -> dict:
    q = (q or "").strip().lower()
    if len(q) < 2:
        return {"teams": [], "players": []}
    teams = [{"id": tid, "name": meta[0],
              "logo": f"https://media.api-sports.io/football/teams/{tid}.png"}
             for tid, meta in TEAM_META.items() if q in meta[0].lower()]
    players = [{"id": pid, "name": n[0], "photo": _photo(pid)}
               for pid, n in PLAYER_DB.items() if q in n[0].lower()]
    return {"teams": teams[:8], "players": players[:8]}


# ---- Thống kê trận (statistics) ----
# fid: (home[poss, shots, sot, xg, corners, fouls, pass%], away[...])
_STATS_NUM = {
    1003: ((52, 12, 5, "1.4", 6, 11, 84), (48, 10, 4, "1.1", 5, 13, 81)),
    2001: ((58, 15, 7, "2.1", 8, 9, 88), (42, 9, 3, "0.9", 4, 12, 79)),
    3001: ((49, 11, 4, "1.2", 5, 14, 80), (51, 13, 6, "1.6", 7, 10, 83)),
    4001: ((55, 14, 6, "1.8", 7, 12, 82), (45, 8, 3, "0.7", 3, 15, 77)),
}
_STAT_KEYS = ["Ball Possession", "Total Shots", "Shots on Goal", "expected_goals",
              "Corner Kicks", "Fouls", "Passes %"]


def _stat_block(team, v):
    vals = [f"{v[0]}%", v[1], v[2], v[3], v[4], v[5], f"{v[6]}%"]
    return {
        "team": {"id": team["id"], "name": team["name"], "logo": team["logo"]},
        "statistics": [{"type": k, "value": val} for k, val in zip(_STAT_KEYS, vals)],
    }


def statistics_for(fixture_id: int) -> list:
    f = fixture_by_id(fixture_id)
    if not f or fixture_id not in _STATS_NUM:
        return []
    h, a = _STATS_NUM[fixture_id]
    return [_stat_block(f[0]["teams"]["home"], h), _stat_block(f[0]["teams"]["away"], a)]


# ---- Chấm điểm cầu thủ sau trận (/fixtures/players) ----
def players_ratings_for(fixture_id: int) -> list:
    lus = LINEUPS.get(fixture_id, [])
    if not lus:
        return []
    scorers = {e["player"]["id"] for e in EVENTS.get(fixture_id, []) if e["type"] == "Goal"}
    out = []
    for t in lus:
        players = []
        for x in t["startXI"]:
            p = x["player"]
            base = round(6.6 + (p["id"] % 12) / 10.0, 1)  # 6.6..7.7 ổn định
            rating = "8.4" if p["id"] in scorers else f"{base}"
            players.append({
                "player": {"id": p["id"], "name": p["name"]},
                "statistics": [{
                    "games": {"minutes": 90, "number": p["number"], "rating": rating},
                    "goals": {"total": 1 if p["id"] in scorers else 0, "assists": 0},
                }],
            })
        players.sort(key=lambda pp: float(pp["statistics"][0]["games"]["rating"]), reverse=True)
        out.append({"team": t["team"], "players": players})
    return out


# ---- Đối đầu (head-to-head) ----
def h2h_for(fixture_id: int) -> list:
    f = fixture_by_id(fixture_id)
    if not f:
        return []
    home, away, league = f[0]["teams"]["home"], f[0]["teams"]["away"], f[0]["league"]
    scores = [(2, 1), (1, 1), (0, 2), (3, 2), (1, 0)]  # cố định cho ổn định
    out = []
    for i, (gh, ga) in enumerate(scores):
        h, a = (home, away) if i % 2 == 0 else (away, home)
        out.append(_fixture(90000 + i, _iso(-30 * (i + 1), 20), "FT", 90,
                            {"id": h["id"], "name": h["name"], "logo": h["logo"]},
                            {"id": a["id"], "name": a["name"], "logo": a["logo"]},
                            gh, ga, "—", league=league))
    return out


# ---- Lịch/kết quả gần đây của 1 đội ----
_LEAGUE_TEAMS = {
    39: [40, 33, 50, 42, 49, 47],
    140: [541, 529],
    1: [26, 6, 2, 10, 9, 27],
    307: [2939, 2932, 2929, 2926],
}


def _league_of_team(tid):
    for lid, ids in _LEAGUE_TEAMS.items():
        if tid in ids:
            return lid
    return None


def team_recent(team_id: int) -> list:
    meta = TEAM_META.get(team_id)
    if not meta:
        return []
    me = {"id": team_id, "name": meta[0],
          "logo": f"https://media.api-sports.io/football/teams/{team_id}.png"}
    pool = [t for t in _LEAGUE_TEAMS.get(_league_of_team(team_id), []) if t != team_id]
    if not pool:
        return []
    scores = [(2, 0), (1, 1), (1, 2), (3, 1), (0, 0)]
    out = []
    for i in range(5):
        oid = pool[i % len(pool)]
        om = TEAM_META[oid]
        opp = {"id": oid, "name": om[0],
               "logo": f"https://media.api-sports.io/football/teams/{oid}.png"}
        gh, ga = scores[i]
        h, a = (me, opp) if i % 2 == 0 else (opp, me)
        out.append(_fixture(91000 + i, _iso(-7 * (i + 1), 18), "FT", 90, h, a, gh, ga, "—"))
    return out


# ---- Tự đăng ký mọi CLB/đội tuyển (chỉ-có-trong-BXH) để trang đội mở được ----
def _register(clubs, league_id):
    ids = []
    for tid, tname in clubs:
        TEAM_META.setdefault(tid, (tname, "—", "", 0, 1900))  # giữ nguyên đội đã có data chi tiết
        SQUADS.setdefault(tid, [])
        ids.append(tid)
    _LEAGUE_TEAMS[league_id] = ids


_register(PL_CLUBS, 39)
_register(LA_LIGA_CLUBS, 140)
_register(SAUDI_CLUBS, 307)

_wc_ids = []
for _grp in WC_GROUPS.values():
    for _tid, _tname in _grp:
        TEAM_META.setdefault(_tid, (_tname, "—", "", 0, 1900))
        SQUADS.setdefault(_tid, [])
        _wc_ids.append(_tid)
_LEAGUE_TEAMS[1] = _wc_ids
