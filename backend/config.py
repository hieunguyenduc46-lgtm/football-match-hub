"""
Read configuration from the .env file (or environment variables).
Logic: if there is no API key -> automatically enable mock mode so the app still runs.
"""
from datetime import datetime

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    api_football_key: str = ""
    api_football_host: str = "v3.football.api-sports.io"
    # "direct" = subscribed via the api-sports.io dashboard (header x-apisports-key)
    # "rapidapi" = subscribed via RapidAPI (header x-rapidapi-key)
    api_football_via: str = "direct"
    # 0 = INFER the season from the date (no yearly updates needed). Set >0 (e.g. 2025) to PIN a season.
    season: int = 0
    use_mock: bool = True
    # CORS: one or more origins, separated by commas (for deployment)
    frontend_origin: str = "http://localhost:5173"
    cache_ttl_seconds: int = 300
    # Enable the /_debug/* endpoints (show raw API output). DISABLED by default in production so
    # internal data is not exposed and no quota is wasted. Set DEBUG=true locally when debugging.
    debug: bool = False
    # Set by the deployment (docker compose): build version and environment name.
    app_version: str = "dev"
    app_env: str = "local"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

# Strip spaces/newlines from environment variables (e.g. a key pasted from the dashboard
# with a trailing '\n' -> httpx raises "Illegal header value" and EVERY API request fails).
settings.api_football_key = (settings.api_football_key or "").strip()
settings.api_football_host = (settings.api_football_host or "").strip()
settings.api_football_via = (settings.api_football_via or "").strip()

# Safety: without a key always use mock mode, to avoid API calls failing with 401.
if not settings.api_football_key:
    settings.use_mock = True


# ===== Infer the SEASON from the date (no yearly updates needed) =====
# European seasons span 2 years (August -> May). Rule: month >= 7 belongs to THAT YEAR's season,
# month < 7 belongs to the PREVIOUS YEAR's season. E.g. 06/2026 -> 2025 (2025/26 season just finished);
# 08/2026 -> 2026 (new 2026/27 season). Matches how the /fixtures endpoint infers the season.
def current_season(now=None):
    now = now or datetime.now()
    return now.year if now.month >= 7 else now.year - 1


def default_season():
    """Default season for standings / top scorers / player profiles.
    SEASON env > 0 -> PIN exactly that value (manual override to view an old season).
    SEASON = 0 (or unset) -> INFER from the date, no yearly edits needed."""
    return settings.season if settings.season and settings.season > 0 else current_season()


# Competitions with SPECIAL seasons that do not follow the usual season-year rule:
#  - World Cup (every 4 years) -> pin the tournament year; update for each new edition (2030...).
LEAGUE_SEASON = {
    1: 2026,   # World Cup 2026
}

# Competitions that run on the CALENDAR YEAR (January to December): season = the current year (e.g. MLS).
CALENDAR_YEAR_LEAGUES = {253}  # MLS


def season_for(league):
    """Return the correct season for a competition:
      - special competitions (World Cup...) -> from LEAGUE_SEASON,
      - calendar-year leagues (MLS) -> the current YEAR,
      - everything else -> the default season (inferred from the date, unless pinned by the SEASON env)."""
    try:
        lid = int(league)
    except (TypeError, ValueError):
        return default_season()
    if lid in LEAGUE_SEASON:
        return LEAGUE_SEASON[lid]
    if lid in CALENDAR_YEAR_LEAGUES:
        return datetime.now().year
    return default_season()


# ===== OFFICIAL goals baseline (entered manually) =====
# No free API returns the exact running official total, so we anchor an official number
# up to the END of season `through`, and the app AUTOMATICALLY adds official goals from later seasons (via the API).
# => Only one update per year after the season ends; goals in the current season are added automatically.
#
# player_id: taken from the player page URL (e.g. /player/874 -> 874).
# goals: total official goals up to the end of season `through` (check Wikipedia or another trusted source).
# through: the last season ALREADY included (e.g. 2024 = everything up to the end of 2024/25).
CAREER_BASELINE = {
    # Cristiano Ronaldo: manually adjusted so the CURRENT total = 977 (official, matches the real-world figure).
    # Mechanism: total = goals + official goals from seasons AFTER `through` (added automatically, WITH STAT_OVERRIDES applied
    # so it matches the table: phantom King's Cup goals set to 0, Super Cup included). Auto-adding is KEPT: new official goals -> increases automatically.
    # The simulated data currently gives added=31 (total 978) because of 1 extra Al-Nassr Pro League goal in 2026/27;
    # baseline lowered 947->946 to match the real figure of 977 (946 + 31 = 977). This only shifts the FLOOR down by 1; auto-adding stays on.
    874: {"goals": 946, "through": 2024},
    # Lionel Messi (id 154): anchored at 911 official goals, the current season UPDATES AUTOMATICALLY.
    # Mechanism: baseline = official goals up to the END of season 2025 = 889; the app AUTOMATICALLY adds official goals for
    # 2026 (API currently shows 22) -> 889 + 22 = 911 right now, and it increases as Messi scores more.
    # (Summing everything from the API is wrong because data for old seasons 2004–2015 is missing, so the old part must be anchored.)
    154: {"goals": 889, "through": 2025},
    # Neymar (id 276): official TOTAL ~491 (Santos/Barça/PSG/Al-Hilal + Brazil), as of ~06/2026.
    # through=2025 + baseline 483 -> 483 + (Santos 2026 season, API currently counts 8) = 491; new goals are ADDED AUTOMATICALLY.
    276: {"goals": 483, "through": 2025},
    # Karim Benzema (id 759): official TOTAL ~515 (Lyon/Real/Al-Ittihad + France), as of ~06/2026.
    # through=2025 -> the 2026 season (API currently 0) is added automatically when he scores. Sources: Wikipedia/StatMuse.
    759: {"goals": 515, "through": 2025},
    # Kylian Mbappé (id 278): official TOTAL 429 (manually adjusted to the real figure). baseline 425 +
    # goals the API counts for 2026 (currently 4 World Cup goals) = 429. through=2025 -> new goals at the World Cup/official
    # competitions are ADDED AUTOMATICALLY by the API, no manual edits needed.
    278: {"goals": 425, "through": 2025},
    # Erling Haaland (id 1100): official TOTAL ~372 (clubs Bryne/Molde/Salzburg/Dortmund/Man City +
    # Norway), as of ~06/2026. The API is missing early seasons (Bryne/Molde 2016–2019), so the old part is anchored manually.
    # through=2025 + baseline 370 -> 370 + (2026 season, API currently 2) = 372; new goals are ADDED AUTOMATICALLY.
    1100: {"goals": 370, "through": 2025},
}
