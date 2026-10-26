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
