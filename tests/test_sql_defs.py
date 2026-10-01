from services.metrics import sql_defs as D


def test_perspective_follows_grouping_and_batter_filters():
    assert D.perspective_for(["batter", "year"]) == D.BATTER
    assert D.perspective_for(["bowler"], has_batter_filters=True) == D.BATTER
    assert D.perspective_for(["bowler", "phase"]) == D.BOWLER
    assert D.perspective_for(["phase"]) == D.TEAM
    assert D.perspective_for(None) == D.TEAM


def test_delivery_details_rules():
    bat, bowl, team = (D.delivery_details_defs(p) for p in (D.BATTER, D.BOWLER, D.TEAM))
    # A no-ball is a ball faced, never a ball bowled; wides are neither.
    assert "noball" not in bat.legal_ball and "wide" in bat.legal_ball
    assert "noball" in bowl.legal_ball and "noball" in team.legal_ball
    # Byes and leg-byes are never the bowler's; the batter only gets runs off the bat.
    assert "byes" in bowl.runs and "legbyes" in bowl.runs and bat.runs == "COALESCE(dd.batruns, 0)"
    # Striker's own dismissal for batters; credited dismissals only for bowlers.
    assert "bat_out" in bat.wicket and "run out" not in bowl.wicket and "leg before wicket" in bowl.wicket
    for defs in (bat, team):
        assert "retired not out (hurt)" in defs.wicket


def test_alias_is_applied_everywhere():
    s = D.delivery_details_defs(D.BOWLER, "s")
    assert "dd." not in s.dot and "s.batruns" in s.dot
    legacy = D.legacy_defs(D.BATTER, "x")
    assert "x.player_dismissed = x.batter" in legacy.wicket and " d." not in legacy.runs
