from __future__ import annotations

from typing import Any, Dict, List

import services.fantasy_planner as fantasy_planner


def _fixture(match_num: int, team1: str, team2: str) -> Dict[str, Any]:
    return {
        "match_num": match_num,
        "date": f"2099-01-{match_num:02d}",
        "team1": team1,
        "team2": team2,
        "venue": "Test Venue",
    }


def _build_matchup_payload(team1: str, team2: str, team1_players: List[str], team2_players: List[str]) -> Dict[str, Any]:
    team1_batting = {
        player: {
            "Overall": {
                "average": 32.0,
                "strike_rate": 145.0,
                "boundary_percentage": 44.0,
                "balls": 60,
            }
        }
        for player in team1_players
    }
    team2_batting = {
        player: {
            "Overall": {
                "average": 29.0,
                "strike_rate": 138.0,
                "boundary_percentage": 40.0,
                "balls": 52,
            }
        }
        for player in team2_players
    }
    team1_bowling = {
        player: {"balls": 24, "runs": 28, "wickets": 1, "dot_percentage": 36.0}
        for player in team1_players
    }
    team2_bowling = {
        player: {"balls": 24, "runs": 30, "wickets": 1, "dot_percentage": 34.0}
        for player in team2_players
    }
    fantasy_top = []
    for player in team1_players:
        fantasy_top.append(
            {
                "team": "team1",
                "player_name": player,
                "expected_points": 1125.0,
                "confidence": 0.8,
                "role": "batter",
            }
        )
    for player in team2_players:
        fantasy_top.append(
            {
                "team": "team2",
                "player_name": player,
                "expected_points": 1090.0,
                "confidence": 0.78,
                "role": "batter",
            }
        )
    return {
        "team1": {
            "name": team1,
            "players": team1_players,
            "batting_matchups": team1_batting,
            "bowling_consolidated": team1_bowling,
        },
        "team2": {
            "name": team2,
            "players": team2_players,
            "batting_matchups": team2_batting,
            "bowling_consolidated": team2_bowling,
        },
        "lineup_sources": {"team1": "match_data", "team2": "match_data"},
        "fantasy_analysis": {"top_fantasy_picks": fantasy_top},
    }


def test_recommendations_include_points_model_and_normalized_match_points(monkeypatch):
    fantasy_planner._MATCHUP_CACHE.clear()
    fixtures = [
        _fixture(1, "CSK", "MI"),
        _fixture(2, "RCB", "RR"),
        _fixture(3, "GT", "LSG"),
        _fixture(4, "PBKS", "KKR"),
    ]
    monkeypatch.setattr(fantasy_planner, "_load_schedule", lambda: fixtures)
    monkeypatch.setattr(fantasy_planner, "get_player_credit", lambda _: 8.0)
    monkeypatch.setattr(fantasy_planner, "is_overseas", lambda _: False)

    def fake_team_players(team_abbrev: str, db, lookback_days: int = 30):
        return {
            "players": [
                {"name": f"{team_abbrev} Batter", "role": "batter"},
                {"name": f"{team_abbrev} Bowler", "role": "bowler"},
            ],
            "source": "match_data",
        }

    monkeypatch.setattr(fantasy_planner, "_get_team_players_for_projection", fake_team_players)

    def fake_matchups(team1, team2, start_date, end_date, team1_players, team2_players, db):
        return _build_matchup_payload(team1, team2, team1_players, team2_players)

    monkeypatch.setattr(fantasy_planner, "get_team_matchups_service", fake_matchups)

    result = fantasy_planner.get_fantasy_recommendations(
        db=object(),
        matches_ahead=3,
        from_date="2099-01-01",
    )

    assert result["points_model"] == "per_match_normalized_v1"
    assert len(result["match_details"]) == 3
    assert len(result["upcoming_matches"]) == 3

    sample_points = result["match_details"][0]["player_points"]
    assert sample_points
    assert any(row["expected_points_raw"] >= 1000 for row in sample_points)
    assert all(0 <= row["expected_points"] < 250 for row in sample_points)


def test_ipl_roster_lookup_uses_match_data_then_static_fallback(monkeypatch):
    fantasy_planner._MATCHUP_CACHE.clear()
    monkeypatch.setattr(
        fantasy_planner,
        "_get_upcoming_fixtures",
        lambda matches_ahead, from_date: [_fixture(1, "RCB", "CSK")],
    )
    monkeypatch.setattr(fantasy_planner, "get_player_credit", lambda _: 8.0)
    monkeypatch.setattr(fantasy_planner, "is_overseas", lambda _: False)
    monkeypatch.setattr(fantasy_planner, "get_team_abbrev_from_name", lambda team_name: team_name)

    static_rosters = {
        "RCB": {"players": [{"name": "RCB Static", "role": "batter"}]},
        "CSK": {"players": [{"name": "CSK Static", "role": "bowler"}]},
    }

    monkeypatch.setattr(
        fantasy_planner,
        "get_ipl_roster",
        lambda team_abbrev: static_rosters.get(team_abbrev),
    )

    def fake_team_roster(team_name: str, db, lookback_days: int = 30):
        if team_name == "RCB":
            return {
                "team": "RCB",
                "source": "match_data",
                "players": [{"name": "RCB Live", "role": "batter"}],
            }
        return {"team": "CSK", "source": "match_data", "players": []}

    monkeypatch.setattr(fantasy_planner, "get_team_roster_service", fake_team_roster)

    def fake_matchups(team1, team2, start_date, end_date, team1_players, team2_players, db):
        return _build_matchup_payload(team1, team2, team1_players, team2_players)

    monkeypatch.setattr(fantasy_planner, "get_team_matchups_service", fake_matchups)

    result = fantasy_planner.get_fantasy_recommendations(
        db=object(),
        matches_ahead=1,
        from_date="2099-01-01",
    )

    assert result["lineup_sources"]["RCB"] == "match_data"
    assert result["lineup_sources"]["CSK"] == "pre_season"
    csk_names = {p["name"] for p in result["match_details"][0]["player_points"] if p["team"] == "CSK"}
    assert "CSK Static" in csk_names
