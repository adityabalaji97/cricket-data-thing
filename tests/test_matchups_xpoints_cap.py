from fantasy_points_v2 import FantasyPointsCalculator
from services.matchups import calculate_fantasy_points_from_matchups


def test_expected_batting_points_caps_to_avg_balls_per_innings():
    calculator = FantasyPointsCalculator()

    result = calculator.calculate_expected_batting_points_from_matchup(
        {
            "runs": 60,
            "balls": 60,
            "wickets": 2,
            "boundaries": 20,
            "strike_rate": 100,
            "avg_balls_per_innings": 20,
        }
    )

    assert result["projected_balls"] == 20.0
    assert result["balls_cap"] == 20.0
    assert result["uncapped_balls"] == 60.0
    assert result["confidence"] == 0.67
    assert result["expected_batting_points"] == 50.67
    assert result["breakdown"]["balls_cap_source"] == "avg_balls_per_innings"


def test_expected_batting_points_uses_default_cap_when_avg_missing():
    calculator = FantasyPointsCalculator()

    result = calculator.calculate_expected_batting_points_from_matchup(
        {
            "runs": 80,
            "balls": 80,
            "wickets": 1,
            "boundaries": 20,
            "strike_rate": 180,
        }
    )

    assert result["projected_balls"] == 30.0
    assert result["balls_cap"] == 30.0
    assert result["uncapped_balls"] == 80.0
    assert result["breakdown"]["balls_cap_source"] == "default_30"


def test_strike_rate_bonus_requires_minimum_capped_balls():
    calculator = FantasyPointsCalculator()

    result = calculator.calculate_expected_batting_points_from_matchup(
        {
            "runs": 50,
            "balls": 50,
            "wickets": 1,
            "boundaries": 10,
            "strike_rate": 180,
            "avg_balls_per_innings": 8,
        }
    )

    assert result["projected_balls"] == 8.0
    assert result["breakdown"]["sr_points"] == 0
    assert "sr_category" not in result["breakdown"]


def test_matchups_fantasy_payload_includes_balls_cap_fields():
    fantasy = calculate_fantasy_points_from_matchups(
        team1_batting={
            "Batter A": {
                "Overall": {
                    "average": 60.0,
                    "strike_rate": 100.0,
                    "boundary_percentage": 40.0,
                    "balls": 100,
                    "avg_balls_per_innings": 20.0,
                }
            }
        },
        team2_batting={},
        team1_bowling_consolidated={},
        team2_bowling_consolidated={},
        team1_players=["Batter A"],
        team2_players=[],
        team1_name="CSK",
        team2_name="MI",
    )

    top_pick = fantasy["top_fantasy_picks"][0]
    assert top_pick["player_name"] == "Batter A"
    assert top_pick["projected_balls"] == 20.0
    assert top_pick["balls_cap"] == 20.0
    assert top_pick["uncapped_balls"] == 60.0
    assert top_pick["breakdown"]["projected_balls"] == 20.0
    assert top_pick["breakdown"]["balls_cap"] == 20.0
    assert top_pick["breakdown"]["uncapped_balls"] == 60.0
