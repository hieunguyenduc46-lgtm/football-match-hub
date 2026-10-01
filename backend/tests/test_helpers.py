"""Unit tests for pure helper functions in api_football.py (no network)."""
import api_football as af


def test_norm_key_removes_vietnamese_accents():
    assert af._norm_key("Bồ Đào Nha") == "bo dao nha"


def test_vi_translate_country_name():
    assert af._vi_translate("tây ban nha") == "Spain"


def test_vi_translate_keeps_unknown_names():
    assert af._vi_translate("Arsenal") == "Arsenal"


def test_split_vs_two_teams():
    assert af._split_vs("Arsenal vs Chelsea") == ["Arsenal", "Chelsea"]


def test_split_vs_single_team():
    assert af._split_vs("Arsenal") == ["Arsenal"]


def test_score_team_ranks_exact_match_first():
    exact = af._score_team("arsenal", "Arsenal")
    prefix = af._score_team("arsenal", "Arsenal Tula")
    contains = af._score_team("arsenal", "FC Arsenal Kyiv")
    assert exact > prefix > contains


def test_score_team_penalises_womens_team():
    assert af._score_team("arsenal", "Arsenal W") < af._score_team("arsenal", "Arsenal")


def test_official_goal_entry_rules():
    assert af._is_official_goal_entry({"team": {"name": "Inter Miami"}, "league": {"name": "Major League Soccer"}})
    assert not af._is_official_goal_entry({"team": {"name": "Argentina"}, "league": {"name": "Friendlies"}})
    assert not af._is_official_goal_entry({"team": {"name": "France U21"}, "league": {"name": "Euro U21"}})


def test_fixtures_ttl_by_date():
    today = af._today_in_tz(None)
    assert af._fixtures_ttl(None, None) == af.LIVE_TTL
    assert af._fixtures_ttl(today, None) == af.LIVE_TTL
    assert af._fixtures_ttl("2999-01-01", None) == af.UPCOMING_TTL
    assert af._fixtures_ttl("2000-01-01", None) == af.STATIC_TTL
