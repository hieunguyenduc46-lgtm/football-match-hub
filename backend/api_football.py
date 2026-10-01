"""
Client for calling API-Football.
- Hides the API key (the key only lives in the backend; the frontend never sees it).
- Caches every response with a TTL to save quota.
- If USE_MOCK = true -> return sample data without any network calls.

Every function returns the list inside API-Football's "response" field,
so the frontend handles mock and real data the same way.
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

# ===== Tiered TTLs (seconds) =====
# Goal: keep live data fresh (~30s) and cache static data for a long time to minimise API calls.
# The cache is SHARED by all users, so 100 people watching still cost only 1 request / TTL / cache key.
# API-Football refreshes live data every 15s -> 15s is the lowest useful delay;
# polling faster than 15s gets NO newer data and just wastes requests.
LIVE_TTL = 15          # today's / live fixtures, live events and statistics
UPCOMING_TTL = 1800    # upcoming fixtures (30 minutes): kick-off time and expected line-ups rarely change
STATIC_TTL = 21600     # standings, players, teams, history, h2h, top scorers (6 hours): almost never change
LEAGUES_TTL = 86400    # league list (for the search box): almost never changes -> cache for 24 hours


def _today_in_tz(tz: Optional[str]) -> str:
    """'Today' (YYYY-MM-DD) in timezone tz. On error or missing tz -> use the server's local time."""
    if tz:
        try:
            from zoneinfo import ZoneInfo
            return datetime.now(ZoneInfo(tz)).strftime("%Y-%m-%d")
        except Exception:
            pass
    return datetime.now().strftime("%Y-%m-%d")


def _fixtures_ttl(date: Optional[str], timezone: Optional[str]) -> int:
    """Pick the TTL for a date's fixture list: today = short (live), future = medium, past = long."""
    if not date:
        return LIVE_TTL
    today = _today_in_tz(timezone)
    if date == today:
        return LIVE_TTL
    if date > today:
        return UPCOMING_TTL
    return STATIC_TTL  # past date -> results are final

# Switch URL and headers depending on the subscription type (direct dashboard or via RapidAPI).
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

    # API-Football returns HTTP 200 with an `errors` field when rate-limited (e.g. too many requests
    # per minute) -> empty response. NEVER cache an error response, otherwise the empty data
    # would be 'frozen' for 6h and break statistics (e.g. missing MOTM matches). errors = [] when OK.
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
        params["timezone"] = timezone  # The API returns fixtures and kick-off times in the viewer's timezone
    data = await _request("/fixtures", params, ttl=_fixtures_ttl(date, timezone))
    return data.get("response", [])


async def get_fixture(fixture_id: int) -> list:
    if settings.use_mock:
        return mock_data.fixture_by_id(fixture_id)
    # Single fixture: may be live -> short cache so the frontend (polling 30s while live) sees new scores.
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
    # Fetch the squad from a separate endpoint so the team page has a player list.
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
    """Find the team's MAIN league (domestic league) for a given season -> (league_id, name, logo).
    Prefer type='League'; otherwise take the first league. (None, None, None) if empty."""
    data = await _request("/leagues", {"team": team_id, "season": season}, ttl=STATIC_TTL)
    leagues = data.get("response", [])
    pick = None
    is_league = False  # True if a real domestic league was found (club); False = national team (cups only)
    for lg in leagues:
        if ((lg.get("league") or {}).get("type") or "").lower() == "league":
            pick = lg["league"]
            is_league = True
            break
    if not pick and leagues:
        pick = leagues[0].get("league")
    if not pick:
        return (None, None, None, False)
    return (pick.get("id"), pick.get("name"), pick.get("logo"), is_league)


async def get_team_statistics(team_id: int) -> dict:
    """Team season statistics in the domestic league: form, wins/draws/losses, average goals, clean sheets, streaks...
    Auto-detect league + season (try the previous season if the new one has no data yet). {} if no data."""
    if settings.use_mock:
        return {}
    season = config.default_season()
    lid, lname, llogo, is_league = await _team_primary_league(team_id, season)
    if not lid:
        season -= 1
        lid, lname, llogo, is_league = await _team_primary_league(team_id, season)
    if not lid:
        return {}
    # NATIONAL TEAM (no domestic league) playing at the World Cup: prefer statistics from the CURRENT World Cup
    # instead of last season's tournament (Euro/Nations League) that the heuristic may pick. Clubs (is_league=True)
    # skip this branch, so there are NO extra requests and the old behaviour is unchanged.
    if not is_league:
        wc_season = config.LEAGUE_SEASON.get(1)
        if wc_season:
            wc = await _request(
                "/teams/statistics", {"team": team_id, "league": 1, "season": wc_season}, ttl=STATIC_TTL
            )
            wcr = wc.get("response") or {}
            played = ((wcr.get("fixtures") or {}).get("played") or {}).get("total") or 0
            if played > 0:
                wcr["_league"] = {"id": 1, "name": "World Cup",
                                  "logo": "https://media.api-sports.io/football/leagues/1.png",
                                  "season": wc_season}
                return wcr
    data = await _request(
        "/teams/statistics", {"team": team_id, "league": lid, "season": season}, ttl=STATIC_TTL
    )
    resp = data.get("response") or {}
    if not resp or not resp.get("fixtures"):
        return {}
    resp["_league"] = {"id": lid, "name": lname, "logo": llogo, "season": season}
    return resp


async def get_team_injuries(team_id: int) -> list:
    """Team's injured/suspended players (current season), grouped by player
    (keep the latest record). [] if none."""
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
    """Combine team season stats + injury list in one call (fetched in parallel)."""
    if settings.use_mock:
        return {"statistics": {}, "injuries": []}
    statistics, injuries = await asyncio.gather(
        get_team_statistics(team_id),
        get_team_injuries(team_id),
    )
    return {"statistics": statistics, "injuries": injuries}


# ========================= MANUAL STATISTICS OVERRIDES =========================
# API-Football sometimes returns WRONG or MISSING league rows (e.g. the Saudi King's Cup returns
# CUMULATIVE numbers across seasons: Ronaldo 16 apps/14 goals, and league.id = null so the logo is lost).
# This table manually fixes those rows using official sources.
# Key = (player_id, season). Each rule matches a league by `match` (league name, lowercase,
# 'contains' match) and OVERWRITES the given fields (dicts are merged, other values replaced).
# Set None for fields that cannot be verified -> the frontend shows a dash instead of a made-up number.
# Source for King's Cup 2025/26: Al-Nassr were knocked out in the round of 32 -> Ronaldo played 1 match, 0 goals
# (Wikipedia "2025–26 Al-Nassr FC season", appearances by competition table).
_MEDIA = "https://media.api-sports.io/football"

# Each entry = {(player_id, season): {"patch": [...], "add": [...]}}
#  - patch: FIX an existing league row (league name, lowercase, 'contains' match); dicts are merged,
#           other values replaced. Set None for unverifiable fields -> the frontend shows a dash.
#  - add:   INSERT a league row that the API is missing (with league id + logo for the icon).
# Data source: official 2025/26 statistics (Pro League 30/28/3, ACL Two 4/1/1,
# Super Cup 2/1/1, King's Cup 1/0/0). API issues: Pro League assists missing, ACL Two missing
# apps + goals, King's Cup wrongly cumulative + missing id/logo, and Super Cup COMPLETELY missing.
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
            {  # Saudi Super Cup (id 826): the API has no row for the 2025 season
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
    """PATCH existing league rows + ADD rows the API is missing (based on STAT_OVERRIDES)."""
    rule = STAT_OVERRIDES.get((player_id, season))
    if not resp or not rule:
        return resp
    # IMPORTANT: deep-copy before editing. resp is an object STORED IN THE CACHE and shared with
    # _sum_official_goals (career goals) and get_player_motm. Editing it in place would
    # corrupt those numbers (e.g. career goals dropping). Only edit a copy returned by get_player.
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

    # ADD (skip if the league is already present -> avoids duplicates when called again on cached data)
    have_ids = {(s.get("league") or {}).get("id") for s in stats}
    have_names = {((s.get("league") or {}).get("name") or "").lower() for s in stats}
    for entry in rule.get("add", []):
        lid = (entry.get("league") or {}).get("id")
        lname = ((entry.get("league") or {}).get("name") or "").lower()
        if lid in have_ids or lname in have_names:
            continue
        stats.append(copy.deepcopy(entry))
    return resp


async def _merge_world_cup_stats(player_id: int, resp: list) -> list:
    """Merge WORLD CUP statistics (national team, 2026 season) into the player profile. The World Cup is in CALENDAR season
    2026, NOT in the European club season (default 2025) -> without merging, the national team section
    would be missing (e.g. Mbappé scores at the World Cup but it is not shown). Teams NOT at the World Cup -> no rows -> unchanged.
    The frontend places the World Cup entry in the national team group (splitStats)."""
    wc_season = config.LEAGUE_SEASON.get(1)
    if not resp or not wc_season:
        return resp
    try:
        wc = await _request("/players", {"id": player_id, "season": wc_season}, ttl=STATIC_TTL)
        wc_resp = wc.get("response") or []
    except Exception:
        return resp
    wc_stats = (wc_resp[0].get("statistics") if wc_resp else None) or []
    wc_entries = [s for s in wc_stats if ((s.get("league") or {}).get("id")) == 1]
    if not wc_entries:
        return resp
    resp = copy.deepcopy(resp)  # Do NOT modify the cached object (shared with career/motm)
    stats = resp[0].setdefault("statistics", [])
    have = {((s.get("team") or {}).get("id"), (s.get("league") or {}).get("id")) for s in stats}
    for e in wc_entries:
        key = ((e.get("team") or {}).get("id"), (e.get("league") or {}).get("id"))
        if key not in have:  # avoid inserting a duplicate if it already exists
            stats.append(e)
    return resp


async def get_player(player_id: int, season: int = 2025) -> list:
    # Only return data for the season being viewed. The frontend splits club vs national team;
    # if that season has no national team matches, the national team section stays empty (no other season is used).
    if settings.use_mock:
        return mock_data.player_by_id(player_id)
    data = await _request("/players", {"id": player_id, "season": season}, ttl=STATIC_TTL)
    resp = data.get("response", [])

    # ===== Leagues that run on the CALENDAR YEAR (MLS...) =====
    # The default `season` (e.g. 2025) is the EUROPEAN season (25/26). But MLS runs January to December,
    # so the 'current season' for an Inter Miami player is THIS YEAR (2026), not 2025.
    # If the player plays in a calendar-year league in the default season -> reload all data for season = this year.
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
                # Only switch if this year's season actually has data (avoid returning empty results early in the year).
                if cy_resp and cy_resp[0].get("statistics"):
                    return _apply_stat_overrides(player_id, cur_year, cy_resp)
            except Exception:
                pass
    # European clubs (default season 2025): also merge 2026 World Cup stats to show the national team section.
    resp = await _merge_world_cup_stats(player_id, resp)
    return _apply_stat_overrides(player_id, season, resp)


# Youth / Olympic teams -> NOT counted as 'official' (official totals only count senior national team + club).
_YOUTH_KEYWORDS = ("u15", "u16", "u17", "u18", "u19", "u20", "u21", "u23", "olympic", "youth")


def _is_official_goal_entry(stat: dict) -> bool:
    """Entries counted in the official total: NOT friendlies and NOT youth/Olympic teams."""
    team = ((stat.get("team") or {}).get("name") or "").lower()
    league = ((stat.get("league") or {}).get("name") or "").lower()
    if "friendl" in league:
        return False
    return not any(k in team or k in league for k in _YOUTH_KEYWORDS)


async def _sum_official_goals(player_id: int, seasons: list) -> int:
    """Sum official goals (club + senior national team, excluding friendlies/youth) across the given seasons.
    APPLY STAT_OVERRIDES before summing so the career total MATCHES the per-league table shown.
    Why: some API rows are wrong (e.g. Ronaldo's King's Cup is cumulative with ~14 phantom goals,
    the override fixes it to 0) or MISSING (e.g. Super Cup, the override ADDS 1 goal). Read raw, the career total would be
    inflated or inconsistent with the table. Overrides only apply when a (player_id, season) rule exists -> other
    players are not affected."""
    total = 0
    for s in seasons:
        try:
            data = await _request("/players", {"id": player_id, "season": s}, ttl=STATIC_TTL)
            resp = data.get("response", [])
        except Exception:
            continue
        resp = _apply_stat_overrides(player_id, s, resp)   # fix/add league rows exactly like the displayed table
        for st in (resp[0].get("statistics", []) if resp else []):
            if _is_official_goal_entry(st):
                total += (st.get("goals") or {}).get("total") or 0
    return total


async def get_player_career(player_id: int) -> dict:
    """Total official career goals.
    - If a manual BASELINE exists (config.CAREER_BASELINE): use the official baseline + add goals from seasons AFTER it.
    - Otherwise: sum all seasons from the API (may differ from the 'official' number)."""
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


# Pre-season FRIENDLY / EXHIBITION cups + YOUTH tournaments -> NOT counted as real trophies.
# (e.g. Messi's "Trofeo Joan Gamper", "Copa Catalunya"; Mbappé's "UEFA U19".)
# Note: "Trophée des Champions" (French Super Cup) is DIFFERENT from "Trofeo ..." (Spanish friendlies),
# so matching "trofeo" is safe and does not affect the French cup. KEEP the Olympics because it is a real trophy.
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
    """Career trophies. API-Football /trophies.
    Clean-up: DROP records without a season (empty season -> API error entry that causes double counting,
    e.g. Ronaldo getting a phantom +1 'UEFA Champions League') and REMOVE DUPLICATES by
    (country|league|season|place). [] if none."""
    if settings.use_mock:
        return []
    data = await _request("/trophies", {"player": player_id}, ttl=STATIC_TTL)
    resp = data.get("response", [])
    seen = set()
    out = []
    for t in resp:
        season = str(t.get("season") or "").strip()  # force str: in case the API returns season as a number
        if not season:
            continue  # record without a season -> junk data, drop it
        if _is_exhibition_trophy(t.get("league")):
            continue  # friendly/exhibition cup or youth tournament -> NOT counted as a trophy
        key = (t.get("country") or "", t.get("league") or "", season, t.get("place") or "")
        if key in seen:
            continue  # duplicate -> drop
        seen.add(key)
        out.append(t)
    return out


async def get_player_transfers(player_id: int) -> list:
    """Transfer history (list of {date, type, teams:{in,out}}). [] if none."""
    if settings.use_mock:
        return []
    data = await _request("/transfers", {"player": player_id}, ttl=STATIC_TTL)
    resp = data.get("response", [])
    return resp[0].get("transfers", []) if resp else []


async def get_player_sidelined(player_id: int) -> list:
    """Injury / suspension history (list of {type, start, end}). [] if none."""
    if settings.use_mock:
        return []
    data = await _request("/sidelined", {"player": player_id}, ttl=STATIC_TTL)
    return data.get("response", [])


async def get_player_season_stats(player_id: int, limit: int = 10) -> list:
    """Statistics PER SEASON (all competitions combined): apps / goals / assists + main team.
    Fetch at most `limit` recent seasons IN PARALLEL for speed; each season is cached for 6h."""
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
        team_apps = {}  # team name -> apps, to pick the most-played team as the label
        seen = set()    # (team|league) already counted -> avoids double counting when the API returns duplicates
        for st in stats:
            # Exclude friendlies + youth/Olympic teams (same as the official goals logic) -> clean, consistent numbers.
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
            return None  # season with only friendlies/youth -> skip, do not show an empty row
        team = max(team_apps, key=team_apps.get)
        return {"season": season, "team": team, "apps": apps, "goals": goals, "assists": assists}

    rows = await asyncio.gather(*[one(s) for s in seasons])
    return [r for r in rows if r]


async def get_player_history(player_id: int) -> dict:
    """Combine 4 parts of a player's history in one call (fetched in parallel):
    trophies + transfers + injuries + per-season statistics."""
    if settings.use_mock:
        return {"trophies": [], "transfers": [], "sidelined": [], "seasons": []}
    trophies, transfers, sidelined, seasons = await asyncio.gather(
        get_player_trophies(player_id),
        get_player_transfers(player_id),
        get_player_sidelined(player_id),
        get_player_season_stats(player_id),
    )
    return {"trophies": trophies, "transfers": transfers, "sidelined": sidelined, "seasons": seasons}


# MANUAL ANCHORS for 'Player of the Match'.
# API-Football has NO official 'Man of the Match' award, so our own calculation (highest
# rating in the match) can be lower than the real official MOTM count (e.g. Ronaldo had 8 official MOTM
# awards in the 2025/26 Saudi Pro League, but the rating-based count gives 0).
# Manual anchor per (player_id, season): {"base": MOTM count up to the "since" date, "since": anchor date}.
# Displayed = base + MOTM awards in matches played AFTER "since" (calculated by rating as usual).
# -> The anchor is a 'floor' and AUTOMATICALLY increases when a new MOTM is earned.
MOTM_ANCHORS = {
    # Season 2026/27: NO base anchor -> POTM is calculated for the WHOLE season from 0 (since=None: scan all
    # 2026 matches) and increases with each new MOTM. The old anchors (Ronaldo base 8 / Messi base 4) were for 2025/26,
    # which is FINISHED -> removed; keeping them with the key changed to 2026 would add an extra 8/4 to the new season.
    # To anchor again later: add {(player_id, 2026): {"base": N, "since": "YYYY-MM-DD"}}.
}

# Players whose MOTM is calculated within their OWN TEAM (highest rating IN the player's team in that match).
# By DEFAULT everyone else is calculated across BOTH TEAMS (must be the highest of all players on the
# pitch). Reason: in weaker teams/leagues (e.g. Messi in MLS) the 'own team' method gives unusually high numbers.
MOTM_TEAM_SCOPED = {
    (583, 2026),   # João Félix
    (278, 2026),   # Kylian Mbappé
}


async def get_player_motm(player_id: int, season: int) -> dict:
    """Count the matches where the player was 'player of the match' in the season being viewed.

    DEFAULT: compare ratings across BOTH TEAMS (must be the highest of all players on the pitch).
    Players in MOTM_TEAM_SCOPED: only compare within the player's OWN TEAM.
    Players in MOTM_ANCHORS: result = base + MOTM in matches played AFTER the 'since' date'
      (the anchor is a floor and AUTOMATICALLY increases when a new MOTM is earned).

    API-Football has NO built-in POTM field -> calculate it ourselves:
      1. Get the teams the player played for this season (from /players statistics).
      2. Get each team's finished fixtures (/fixtures?team&season) + match dates.
      3. For each match (only the ones that need counting): call /fixtures/players and find the highest rating
         (both teams or own team only). If it is this player -> +1. (Only matches the player played in.)
    Uses many requests (1 per match), so it is cached with STATIC_TTL (6h) and lazy-loaded in the frontend.
    """
    anchor = MOTM_ANCHORS.get((player_id, season))
    base = anchor["base"] if anchor else 0
    since = anchor["since"] if anchor else None  # only count matches with DATE > since

    if settings.use_mock:
        return {"motm": base, "computed": 0, "anchor": base, "scanned": base or 0,
                "season": season, "source": "mock"}

    # 1) Teams the player played for this season.
    pdata = await _request("/players", {"id": player_id, "season": season}, ttl=STATIC_TTL)
    resp = pdata.get("response", [])
    stats = resp[0].get("statistics", []) if resp else []
    team_ids = {
        (s.get("team") or {}).get("id")
        for s in stats
        if (s.get("team") or {}).get("id")
    }

    # 2) Collect finished fixtures + match DATES (to filter by 'since').
    finished = {"FT", "AET", "PEN"}
    fixture_dates: dict = {}   # fid -> match date (ISO)
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

    # Only scan matches that NEED COUNTING: if anchored -> only matches played AFTER 'since'
    # (matches before 'since' are already in base). Not anchored -> scan all.
    fids = [fid for fid, d in fixture_dates.items() if (not since) or (d[:10] > since)]

    # 3) Fetch IN PARALLEL (with a limit) for speed; scanning ~50 matches sequentially can time out.
    sem = asyncio.Semaphore(6)   # limit to avoid exceeding API-Football's rate limit

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
        # Find the player's team; skip if the player did not play in this match.
        my_players = None
        for team in teams:
            if any((p.get("player") or {}).get("id") == player_id for p in team.get("players", [])):
                my_players = team.get("players", [])
                break
        if my_players is None:
            continue
        scanned += 1
        # Comparison scope: own team only, or both teams (default).
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

    # Anchored: total = base + MOTM in new matches (after 'since'). Not anchored: total = motm.
    total = base + motm
    return {
        "motm": total,
        "computed": motm,                 # MOTM in matches after 'since' (the 'new' part)
        "anchor": base,
        "scanned": max(scanned, base),    # > 0 so the frontend always shows the POTM card
        "season": season,
        "scope": "team" if team_scoped else "both",
        "source": "anchor+api" if anchor else "api",
    }


async def get_lineups(fixture_id: int) -> list:
    if settings.use_mock:
        return mock_data.lineups_for(fixture_id)
    # Line-ups change very little after being announced (only a few substitutions) -> medium cache.
    data = await _request("/fixtures/lineups", {"fixture": fixture_id}, ttl=UPCOMING_TTL)
    return data.get("response", [])


async def get_events(fixture_id: int) -> list:
    if settings.use_mock:
        return mock_data.events_for(fixture_id)
    # Events (goals/cards) change constantly while live -> short cache.
    data = await _request("/fixtures/events", {"fixture": fixture_id}, ttl=LIVE_TTL)
    return data.get("response", [])


# NATIONAL TEAM cup competitions where API-Football often MERGES QUALIFIER data into the top scorers table
# (e.g. World Cup 2018: Immobile/Italy ranked first even though Italy did not qualify; those were qualifier goals).
_QUALIFIER_LEAK_LEAGUES = {
    1,   # World Cup
    4,   # Euro
    9,   # Copa America
    6,   # Africa Cup of Nations
    7,   # Asian Cup
}


async def _finalist_team_ids(league: int, season: int) -> set:
    """Set of team ids that ACTUALLY played in the finals. Prefer the STANDINGS; if the API has no standings (old seasons),
    fall back to the competition's FIXTURES (teams that played in the finals). {} if it cannot be determined."""
    try:
        st = await get_standings(league, season)
    except Exception:
        st = []
    ids = set()
    for entry in st:
        for group in ((entry.get("league") or {}).get("standings") or []):
            for row in group:
                tid = (row.get("team") or {}).get("id")
                if tid is not None:
                    ids.add(tid)
    if ids:
        return ids
    # Fallback: teams that appear in the finals FIXTURES (league=finals, so qualifiers are not mixed in).
    try:
        data = await _request("/fixtures", {"league": league, "season": season}, ttl=STATIC_TTL)
    except Exception:
        return set()
    for f in data.get("response", []):
        for side in ("home", "away"):
            tid = (((f.get("teams") or {}).get(side)) or {}).get("id")
            if tid is not None:
                ids.add(tid)
    return ids


def _has_match_detail(p: dict) -> bool:
    """True if the row has MATCH-LEVEL DATA (minutes or rating) -> played in the finals. Qualifier data
    that was wrongly merged usually leaves both empty."""
    g = (p.get("statistics") or [{}])[0].get("games") or {}
    return g.get("minutes") is not None or g.get("rating") is not None


async def _filter_to_finalists(league: int, season: int, resp: list) -> list:
    """Top scorers/assists/cards for NATIONAL TEAM tournaments: remove QUALIFIER data wrongly merged by the API.
    Filter by TEAMS IN THE FINALS (from standings or fixtures). Does NOT rely on minutes, so real scorers are not removed.
    Other competitions -> unchanged."""
    if not resp or league not in _QUALIFIER_LEAK_LEAGUES:
        return resp
    ongoing = (season == config.LEAGUE_SEASON.get(league))
    ids = await _finalist_team_ids(league, season)
    if not ids:
        return resp  # cannot determine the finals teams -> leave unchanged to avoid removing valid rows
    in_finals = [p for p in resp if ((p.get("statistics") or [{}])[0].get("team") or {}).get("id") in ids]
    if not in_finals:
        return resp
    if ongoing:
        return in_finals  # in progress: filter by team only, not by minutes (avoids the Balogun bug)
    # FINISHED: also drop rows with NO minutes (qualifier data wrongly merged even if the team qualified, e.g. Morata/Spain
    # 2018 scored in qualifiers but did not play in the finals), BUT only when the minutes data is GOOD ENOUGH (>= half
    # of the rows have details). For very old seasons the API lacks minutes even for real scorers (e.g. Villa at Euro 2008), so
    # keep in_finals unchanged to avoid wrongly removing them.
    detailed = [p for p in in_finals if _has_match_detail(p)]
    if detailed and len(detailed) >= len(in_finals) * 0.5:
        return detailed
    return in_finals


async def get_topscorers(league: int, season: int = 2025) -> list:
    if settings.use_mock:
        return mock_data.topscorers_for(league)
    data = await _request("/players/topscorers", {"league": league, "season": season}, ttl=STATIC_TTL)
    return await _filter_to_finalists(league, season, data.get("response", []))


async def get_topassists(league: int, season: int = 2025) -> list:
    """Top assists for a competition. Same data shape as topscorers (statistics[].goals.assists)."""
    if settings.use_mock:
        return mock_data.topscorers_for(league)
    data = await _request("/players/topassists", {"league": league, "season": season}, ttl=STATIC_TTL)
    return await _filter_to_finalists(league, season, data.get("response", []))


async def get_topyellowcards(league: int, season: int = 2025) -> list:
    """Players with the most yellow cards (statistics[].cards.yellow)."""
    if settings.use_mock:
        return mock_data.topscorers_for(league)
    data = await _request("/players/topyellowcards", {"league": league, "season": season}, ttl=STATIC_TTL)
    return await _filter_to_finalists(league, season, data.get("response", []))


async def get_topredcards(league: int, season: int = 2025) -> list:
    """Players with the most red cards (statistics[].cards.red)."""
    if settings.use_mock:
        return mock_data.topscorers_for(league)
    data = await _request("/players/topredcards", {"league": league, "season": season}, ttl=STATIC_TTL)
    return await _filter_to_finalists(league, season, data.get("response", []))


async def get_statistics(fixture_id: int) -> list:
    if settings.use_mock:
        return mock_data.statistics_for(fixture_id)
    # Statistics (shots, possession) update while live -> short cache.
    data = await _request("/fixtures/statistics", {"fixture": fixture_id}, ttl=LIVE_TTL)
    return data.get("response", [])


async def get_predictions(fixture_id: int) -> dict:
    """Match prediction: win/draw/loss probabilities, advice, form comparison of the two teams.
    API-Football /predictions. Returns {} if there is no data (match too old / not supported)."""
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
    resp = data.get("response", [])
    # Exclude the CURRENT match from H2H; H2H only counts PREVIOUS meetings. Otherwise the current
    # match (live / not yet final, e.g. stuck at 1H 1-0) would be wrongly counted in wins/draws/losses.
    return [m for m in resp if ((m.get("fixture") or {}).get("id")) != fixture_id]


async def get_team_fixtures(team_id: int, last: int = 5) -> list:
    if settings.use_mock:
        return mock_data.team_recent(team_id)
    data = await _request("/fixtures", {"team": team_id, "last": last}, ttl=STATIC_TTL)
    return data.get("response", [])


async def get_team_upcoming(team_id: int, nxt: int = 5) -> list:
    """The team's upcoming fixtures (future schedule). Not in mock yet -> returns empty."""
    if settings.use_mock:
        return []
    data = await _request("/fixtures", {"team": team_id, "next": nxt}, ttl=UPCOMING_TTL)
    return data.get("response", [])


# ===== LEAGUE + COUNTRY search (for the search box next to the date bar) =====

# Countries (mock) for a few well-known leagues, so mock mode still has search data.
_MOCK_LEAGUE_COUNTRY = {
    39: "England", 45: "England", 2: "World", 3: "World", 848: "World", 1: "World",
    10: "World", 15: "World", 140: "Spain", 143: "Spain", 135: "Italy",
    78: "Germany", 61: "France", 307: "Saudi Arabia", 253: "USA", 340: "Vietnam",
}


async def get_all_leagues() -> list:
    """List of ALL leagues (trimmed) to load into the client-side search box.
    Cached for 24h because it almost never changes -> 1 request/day no matter how many users.
    Returns [{id, name, type, logo, country, country_code, flag}]."""
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
    """RECENT (results) + UPCOMING fixtures of a league. Used by the 'Fixtures' tab on the league page.
    season: if given -> fetch that SEASON (played: newest -> oldest, upcoming: oldest -> newest) to match
    the selected season. If not given -> 'live' style (last/next, latest matches regardless of season)."""
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
    """SEASONS for which the league has data (for the client's season dropdown). Returns [{year, current}]
    sorted newest -> oldest. Cached 24h. [] in mock mode."""
    if settings.use_mock:
        return []
    data = await _request("/leagues", {"id": league_id}, ttl=LEAGUES_TTL)
    resp = data.get("response", [])
    seasons = resp[0].get("seasons", []) if resp else []
    out = [{"year": s.get("year"), "current": bool(s.get("current"))}
           for s in seasons if isinstance(s.get("year"), int)]
    out.sort(key=lambda x: x["year"], reverse=True)
    return out


# UEFA club cups (UCL/UEL/UECL): a round named just "Play-offs" is a QUALIFYING round (before the league stage),
# not part of the main bracket -> drop it. ("Knockout Round Play-offs" = the new round-of-16 play-off, so KEEP it.)
_UEFA_CLUB_CUPS = {2, 3, 848}


async def get_bracket(league_id: int, season: Optional[int] = None) -> list:
    """KNOCKOUT matches of a competition -> the client builds the BRACKET diagram.
    Returns [] if the competition has no knockout rounds (e.g. a domestic league) -> the client hides the tab.
    season: the season to view; if not given -> the league's default season.
    1 request /fixtures?league&season (cached 6h), then filter by round name."""
    if settings.use_mock:
        return []
    season = season or config.season_for(league_id)
    data = await _request("/fixtures", {"league": league_id, "season": season}, ttl=STATIC_TTL)
    out = []
    for f in data.get("response", []):
        rnd = ((f.get("league") or {}).get("round") or "")
        # UEFA: a round named just "Play-offs" = qualifying round before the league stage -> removed from the bracket.
        if league_id in _UEFA_CLUB_CUPS and re.fullmatch(r"\s*play-?offs?\s*", rnd, re.IGNORECASE):
            continue
        # Knockout rounds (R16/R32/QF/SF/Final/play-off/"8th|16th Finals"...), EXCLUDING group stage / league / qualifiers.
        if re.search(r"round of|quarter|semi|\bfinal\b|\d+(?:st|nd|rd|th)\s+finals?|play-?off|1/\d|last \d+", rnd, re.IGNORECASE) \
                and not re.search(r"group|regular season|league stage|qualif", rnd, re.IGNORECASE):
            out.append(f)
    return out


async def get_national_team(country: str) -> Optional[dict]:
    """Find a NATIONAL TEAM by country name (Vietnamese names accepted). Prefer national=true."""
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
    """RECENT + UPCOMING matches of this country's NATIONAL TEAM. Returns {team, recent, upcoming}."""
    team = await get_national_team(country)
    if not team:
        return {"team": None, "recent": [], "upcoming": []}
    recent = (await _request("/fixtures", {"team": team["id"], "last": 10},
                             ttl=STATIC_TTL)).get("response", [])
    upcoming = (await _request("/fixtures", {"team": team["id"], "next": 10},
                               ttl=UPCOMING_TTL)).get("response", [])
    return {"team": team, "recent": recent, "upcoming": upcoming}


# ===== Match search =====
# Lets users type "Real Madrid vs Barcelona" -> recent + upcoming matches between the two teams,
# or type one team -> that team's fixtures.
import re
import unicodedata

# Separators between the two teams: "vs", "v", "x", "-", "–", "đấu với", "gặp" (Vietnamese for 'vs').
_VS_RE = re.compile(r"\s+(?:vs|versus|v|x|-|–|đấu với|gặp)\s+", re.IGNORECASE)


def _norm_key(s: str) -> str:
    """Normalise for lookup: remove Vietnamese accents, lowercase, collapse whitespace.
    So typing with accents ('bồ đào nha') or without ('bo dao nha') both match."""
    s = (s or "").lower().strip().replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


# Vietnamese name -> English name that API-Football understands (national teams).
# Keys are already accent-free (_norm_key). Turkey / Ireland are skipped because the API does not
# return the correct men's national team for those names.
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
    """If it is a country name in Vietnamese -> convert to English; otherwise keep it unchanged."""
    return _VI_COUNTRIES.get(_norm_key(name), name)


def _split_vs(q: str):
    """Split 'A vs B' -> ['A', 'B']. If there is no separator -> [q]."""
    parts = [p.strip() for p in _VS_RE.split((q or "").strip(), maxsplit=1)]
    return [p for p in parts if p]


# Women's / youth / reserve teams -> lower score so they are not confused with the senior men's team.
_DEPRIORITIZE = re.compile(r"(\bw\b|\bwomen\b|\bu\d{2}\b|\bii\b|\bb\b|reserves?|youth|academy)", re.IGNORECASE)


def _team_variants(name: str):
    """Search variants to catch both hyphenated names ('Al-Nassr') and names with spaces,
    plus the longest token ('al nassr' -> 'nassr') because the API sometimes only matches single words."""
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
    """Match score: exact match > starts with > contains; penalise women's/youth teams and long names."""
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
    s -= max(0, len(nn) - len(qn)) * 0.6  # the closer to the query the better
    return s


# Some well-known clubs that API-Football's name search often misses (e.g. 'Al-Hilal Saudi FC'
# does not appear when typing 'al hilal'; the API returns Al Hilal from Libya/Sudan instead of Saudi Arabia).
# Map: normalised keyword -> (id, display name, country). Easy to extend when needed.
_FEATURED = {
    "al hilal": (2932, "Al-Hilal Saudi FC", "Saudi-Arabia"),
    "al hilal saudi": (2932, "Al-Hilal Saudi FC", "Saudi-Arabia"),
    "al nassr": (2939, "Al-Nassr", "Saudi-Arabia"),
    "al ittihad": (2929, "Al-Ittihad FC", "Saudi-Arabia"),
    "al ahli": (2926, "Al-Ahli Saudi FC", "Saudi-Arabia"),
}


def _featured_match(name: str):
    """If the keyword matches a well-known club -> return that team directly (independent of the search API)."""
    hit = _FEATURED.get((name or "").lower().strip().replace("-", " "))
    if not hit:
        return None
    tid, tname, country = hit
    return {"id": tid, "name": tname,
            "logo": f"https://media.api-sports.io/football/teams/{tid}.png", "country": country}


async def _search_teams(name: str, limit: int = 8, deep: bool = False):
    """Search teams by name, combine several variants, then rank by match quality. Returns [{id,name,logo,country}].
    deep=True: search every variant (for match-search, to get all same-name candidates across countries)."""
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
        # Quick search (dropdown): an exact match is enough. Deep search (match-search): scan everything.
        if not deep and any((t["name"] or "").lower().replace("-", " ") == qn for t in seen.values()):
            break
    ranked = sorted(seen.values(), key=lambda t: _score_team(name, t["name"] or ""), reverse=True)
    # Well-known clubs missed by the API -> insert at the top so they always come first.
    feat = _featured_match(name)
    if feat:
        ranked = [feat] + [t for t in ranked if t["id"] != feat["id"]]
    return ranked[:limit]


def _best_pair(ca: list, cb: list):
    """Choose the team pair for 'A vs B'. Prefer 2 teams from the SAME COUNTRY (finds the right derby when names clash,
    e.g. 'Al Hilal' exists in several countries), while preferring the best name match on each side."""
    if not ca or not cb:
        return (ca[0] if ca else None, cb[0] if cb else None)
    best, best_score = None, -1e9
    for i, a in enumerate(ca):
        for j, b in enumerate(cb):
            s = -(i + j)  # the higher each side's ranking, the better
            if a.get("country") and a.get("country") == b.get("country"):
                s += 10   # same country -> more likely to be a real fixture pairing
            if s > best_score:
                best_score, best = s, (a, b)
    return best


async def _resolve_team(name: str) -> Optional[dict]:
    """Resolve a team name -> best matching {id, name, logo} (prefer the senior men's team)."""
    cands = await _search_teams(name, limit=1, deep=True)
    return cands[0] if cands else None


async def match_search(q: str) -> dict:
    """Returns {mode, teamA/teamB or team, recent: [...], upcoming: [...]}.
    mode = 'h2h' when typing 'A vs B', 'team' when typing one team."""
    parts = _split_vs(q)

    # ---- 2 teams: head-to-head ----
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

    # ---- 1 team: the team's fixtures ----
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
    """Debug: return the raw JSON from API-Football (including errors/results)."""
    return await _request(path, params)


# ===== Featured players (inserted at the top of search results) =====
# Why this is needed:
#  1) API-Football has NO popularity metric.
#  2) Many stars have longer official surnames ('Cristiano Ronaldo' surname 'dos Santos
#     Aveiro', 'L. Messi' surname 'Messi Cuccittini') -> surname-based matching pushes them
#     below unknown players ('Ronaldo Teixiera', 'Messina').
#  3) The /players/profiles endpoint (current plan) cuts results at ~250 and OFTEN DOES NOT
#     return big stars (e.g. Harry Kane, Vinícius...) -> boosting alone does not help.
# => Most reliable solution: keep our own list of (id, display name, aliases) with VERIFIED IDs, and
#    INSERT them directly into the results when the keyword matches an alias. Photos are built from the id using
#    API-Football's standard URL pattern, so no extra API call is needed.
# To add a star: look up the correct ID via /api/_debug/players?search=<full name>, then add one line.
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

# Quick lookup: id -> display name (to override short names like 'L. Messi' if the API returns them).
_FAMOUS_NAME = {pid: name for pid, name, _ in FAMOUS_PLAYERS}


def _famous_matches(query: str) -> list:
    """Stars matching the keyword -> inserted directly into the results (id, name, photo)."""
    nq = _norm_key(query)
    if not nq:
        return []
    hits = []
    for pid, name, aliases in FAMOUS_PLAYERS:
        for a in aliases:
            na = _norm_key(a)
            # Matches partial input ('ronald' ~ 'ronaldo') or the full phrase ('lionel messi').
            if na.startswith(nq) or nq.startswith(na):
                hits.append({"id": pid, "name": name, "photo": _PLAYER_PHOTO.format(pid)})
                break
    return hits


def _score_player(query: str, profile: dict) -> float:
    """Player name match score. Considers both the full PHRASE ('lionel messi') and the SURNAME token ('messi')
    so that: (1) the real 'Messi' is not buried under 'Messina/Messías', and (2) typing 'Lionel Messi''
    still ranks the real Messi above 'Lionel Messi Nyamsi'."""
    qn = _norm_key(query)
    qtokens = [t for t in qn.split() if len(t) >= 2]
    qlast = qtokens[-1] if qtokens else qn   # the 'surname' token is usually last, e.g. 'messi'
    p = profile.get("player") or {}
    last = _norm_key(p.get("lastname") or "")
    name = _norm_key(p.get("name") or "")
    s = 0.0
    if qn and (last == qn or name == qn):
        s += 100          # exact match of the whole phrase
    elif qlast and last == qlast:
        s += 85           # surname exactly matches the surname token ('Messi' == 'messi')
    elif qlast and last.startswith(qlast):
        s += 70           # surname starts with it ('Messina' ~ 'messi')
    elif qn and name.startswith(qn):
        s += 55           # full name starts with the whole phrase
    elif qlast and qlast in last:
        s += 40
    elif qn and qn in name:
        s += 30
    # A complete profile (with photo / position) is usually a more notable player -> small bonus.
    if p.get("photo"):
        s += 2
    if p.get("position"):
        s += 1
    # The closer the surname length is to the surname token, the better ('Messi' beats 'Messina').
    s -= max(0, len(last) - len(qlast)) * 0.5
    # If a star also appears in the API results -> push it to the top (just in case).
    if p.get("id") in _FAMOUS_NAME:
        s += 1000
    return s


async def search(q: str) -> dict:
    """Search teams + players by name. Returns {'teams': [...], 'players': [...]}.
    Each part is wrapped in try/except so one failing endpoint (e.g. blocked by the plan) does not break the whole search."""
    if settings.use_mock:
        return mock_data.search(q)
    qq = (q or "").strip()
    if len(qq) < 3:
        return {"teams": [], "players": []}

    async def find_teams():
        try:
            # Uses the same search + ranking as match-search: catches hyphenated names
            # ('Al-Nassr' when typing 'al nassr') and prefers the senior men's team over women's/youth teams.
            return await _search_teams(qq, limit=8)
        except Exception:
            return []

    async def _profiles(term):
        try:
            return (await _request("/players/profiles", {"search": term}, ttl=STATIC_TTL)).get("response", [])
        except Exception:
            return []

    async def find_players():
        # The /players/profiles API searches by SURNAME. Typing "Lionel Messi" only matches the full name
        # ('Lionel Messi Nyamsi') and MISSES the real Messi -> also search by the surname token.
        # Also drop 1-character initials ('L.Messi' -> 'Messi').
        tokens = [t for t in re.split(r"[^0-9A-Za-zÀ-ÿ]+", qq) if len(t) >= 2]
        terms = []
        for t in ([qq] + ([max(tokens, key=len), tokens[-1]] if tokens else [])):
            t = t.strip()
            if t and t.lower() not in [x.lower() for x in terms]:
                terms.append(t)
        # Call IN PARALLEL (up to 3 keywords), then merge and de-duplicate by id.
        batches = await asyncio.gather(*[_profiles(t) for t in terms[:3]])
        merged = {}
        for resp in batches:
            for p in resp:
                pid = (p.get("player") or {}).get("id")
                if pid and pid not in merged:
                    merged[pid] = p
        # Rank by name match against the ORIGINAL keyword (so the real 'Messi' comes first).
        ranked = sorted(merged.values(), key=lambda p: _score_player(qq, p), reverse=True)
        api_players = []
        for p in ranked:
            pl = p.get("player") or {}
            pid = pl.get("id")
            api_players.append({
                "id": pid,
                # Stars: use the nicer display name (e.g. 'Lionel Messi' instead of 'L. Messi').
                "name": _FAMOUS_NAME.get(pid) or pl.get("name"),
                "photo": pl.get("photo"),
            })
        # Insert stars matching an alias AT THE TOP and de-duplicate by id (the star may already be
        # in the API results -> keep only one copy, preferring the star entry).
        seen, result = set(), []
        for item in _famous_matches(qq) + api_players:
            pid = item.get("id")
            if pid and pid not in seen:
                seen.add(pid)
                result.append(item)
        return result[:8]

    # Run teams + players IN PARALLEL so the search box responds faster (previously sequential).
    teams, players = await asyncio.gather(find_teams(), find_players())
    return {"teams": teams, "players": players}
