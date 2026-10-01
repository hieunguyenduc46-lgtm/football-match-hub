"""Unit tests for season logic in config.py."""
from datetime import datetime

import pytest

import config


@pytest.mark.parametrize("year, month, expected", [
    (2026, 8, 2026),   # August: new European season starts
    (2026, 7, 2026),   # July is the cut-over month
    (2026, 6, 2025),   # June: still the previous season
    (2027, 1, 2026),   # January belongs to the season that started last year
])
def test_current_season(year, month, expected):
    assert config.current_season(datetime(year, month, 15)) == expected


def test_world_cup_season_is_pinned():
    assert config.season_for(1) == 2026


def test_calendar_year_league_uses_current_year():
    assert config.season_for(253) == datetime.now().year  # MLS


def test_invalid_league_falls_back_to_default_season():
    assert config.season_for("abc") == config.default_season()


def test_season_env_value_pins_the_default(monkeypatch):
    monkeypatch.setattr(config.settings, "season", 2023)
    assert config.default_season() == 2023
