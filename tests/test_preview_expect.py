"""build_expect_block: the "What to expect" numbers come straight from the gathered context."""
from services.match_preview import build_expect_block


CONTEXT = {
    "team1": "Mumbai Indians",
    "team2": "Chennai Super Kings",
    "venue_stats": {
        "total_matches": 28, "batting_first_wins": 15, "batting_second_wins": 13,
        "average_first_innings": 197.04, "average_second_innings": 174.14,
        "average_winning_score": 215.0, "average_chasing_score": 176.31,
        "highest_total_chased": 243, "lowest_total_defended": 169,
    },
    "story_signals": {"venue_balance": {"toss_bias": "balanced"}},
    "recent_form": {"Mumbai Indians": {"record": "LLWLW"}, "Chennai Super Kings": {"record": "LLLWW"}},
    "elo": {"Mumbai Indians": 1456, "Chennai Super Kings": 1465, "delta_team1_minus_team2": -9},
    "screen_story": {
        "head_to_head_stats": {"overall_window_summary": {"sample_size": 5, "team1_wins": 1, "team2_wins": 4}},
        "phase_wise_strategy": {
            "batting_first_wins_template": {
                "powerplay": {"runs_per_innings": 63.27}, "middle1": {"runs_per_innings": 35.53},
                "middle2": {"runs_per_innings": 53.07}, "death": {"runs_per_innings": 62.0},
                "template_total_runs": 213.9,
            },
            "chasing_wins_template": {},
        },
        "expected_fantasy_points": {"fantasy_top": {
            "Mumbai Indians": [{"player": "Will Jacks", "expected_points": 65.9, "role": "all-rounder"}],
            "Chennai Super Kings": [{"player": "Matthew Short", "expected_points": 77.7, "role": "all-rounder"}],
        }},
    },
}


def test_expect_block_shapes_context():
    lean = {"label": "Slight lean Chennai Super Kings", "winner": "Chennai Super Kings",
            "top_reasons": [{"detail": "Recent H2H edge"}, {"detail": "Fantasy/matchup edge"}]}
    out = build_expect_block(CONTEXT, lean)

    assert out["venue"]["avg_winning_score"] == 215
    assert out["venue"]["avg_target_chased"] == 176
    assert out["venue"]["chasing_wins"] == 13
    assert out["winning_phases"]["batting_first"] == {"powerplay": 63, "middle": 89, "death": 62, "total": 214}
    assert out["winning_phases"]["chasing"] is None
    assert out["form"][0] == {"team": "Mumbai Indians", "record": "LLWLW"}
    assert out["head_to_head"] == {"sample_size": 5, "team1_wins": 1, "team2_wins": 4}
    assert out["lean"]["reasons"] == ["Recent H2H edge", "Fantasy/matchup edge"]
    assert [p["player"] for p in out["fantasy_top"]] == ["Matthew Short", "Will Jacks"]


def test_expect_block_empty_venue():
    out = build_expect_block({"team1": "A", "team2": "B"}, None)
    assert out["venue"] is None
    assert out["lean"] is None
    assert out["fantasy_top"] == []
