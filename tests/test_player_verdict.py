from services.player_verdict import classify_roles, quantiles, rank_among, scope_params


def test_quantiles_ends_and_count():
    q = quantiles(list(range(101)), 50)
    assert len(q) == 51
    assert q[0] == 0 and q[-1] == 100 and q[25] == 50


def test_rank_among_respects_direction():
    vals = [6.0, 7.0, 8.0, 9.0]
    assert rank_among(vals, 7.0, lower_is_better=True) == 2  # economy
    assert rank_among(vals, 7.0, lower_is_better=False) == 3  # dot %
    assert rank_among(vals + [7.0], 7.0, lower_is_better=True) == 2  # ties share the better rank


def test_jansen_is_an_allrounder_by_innings_not_balls():
    # Faced a quarter of the balls he bowled, but batted in 60% as many innings.
    primary, allrounder = classify_roles({
        "bowl": {"innings_count": 112, "balls": 2435},
        "bat": {"innings_count": 67, "balls": 602},
    })
    assert (primary, allrounder) == ("bowl", True)


def test_part_time_bowler_is_not_an_allrounder():
    primary, allrounder = classify_roles({
        "bat": {"innings_count": 116, "balls": 1905},
        "bowl": {"innings_count": 30, "balls": 290},
    })
    assert (primary, allrounder) == ("bat", False)


def test_all_t20_scope_is_not_internationals_only():
    assert scope_params("T20", "all") == {"leagues": [], "include_international": False}
    assert scope_params("T20", "strong")["top_teams"] == 12


def test_floor_follows_the_period():
    from services.qualification import min_balls

    busy = [{"balls": 1000, "innings_count": 30}] * 9 + [{"balls": 50, "innings_count": 3}]
    quiet = [{"balls": 400, "innings_count": 12}] * 9
    assert min_balls(busy)["min_balls"] == 400  # 40% of the regulars' median; the 3-innings player isn't a regular
    assert min_balls(quiet)["min_balls"] == 160
    assert min_balls([{"balls": 100, "innings_count": 6}])["min_balls"] == 120  # the noise floor


def _summary(metrics, seasons, allrounder=False):
    from services.player_verdict import verdict_line

    return verdict_line({
        "roles": {"bowl": {"peers": {"qualified": True, "metrics": metrics}, "seasons": seasons}},
        "primary_role": "bowl", "allrounder": allrounder, "has_wins_added": True,
        "window": {"start_date": "2024-01-01"},
    })


def test_verdict_claims_best_rank_and_swing():
    line = _summary(
        [{"key": "wpa", "label": "Wins added", "rank": 36, "n": 213}, {"key": "dot_percentage", "label": "Dot balls %", "rank": 21, "n": 213}],
        [{"year": 2025, "wpa": 1.99}, {"year": 2026, "wpa": -0.41}],
        allrounder=True,
    )
    assert line == "Top 10% for dot balls with the ball. +2.0 wins added in 2025, \u22120.4 in 2026."


def test_verdict_top_three_and_no_small_swing():
    line = _summary([{"key": "wpa", "label": "Wins added", "rank": 2, "n": 213}],
                    [{"year": 2025, "wpa": 1.4}, {"year": 2026, "wpa": 2.0}])
    assert line == "2nd of 213 for wins added."


def test_qualifying_needs_two_seasons_over_their_floors():
    from services.qualification import qualifying_players

    rows = []
    for year in (2024, 2025, 2026):
        rows += [{"name": f"reg{i}", "year": year, "balls": 400, "innings_count": 12} for i in range(9)]
    rows += [{"name": "parttimer", "year": 2025, "balls": 200, "innings_count": 8}]   # one season only
    rows += [{"name": "returning", "year": 2024, "balls": 170, "innings_count": 6},
             {"name": "returning", "year": 2026, "balls": 170, "innings_count": 6}]
    q = qualifying_players(rows, "name")
    assert q["floors"] == {"2024": 160, "2025": 160, "2026": 160}  # 40% of 400
    assert "parttimer" not in q["players"] and "returning" in q["players"] and "reg0" in q["players"]
    assert q["seasons_needed"] == 2
