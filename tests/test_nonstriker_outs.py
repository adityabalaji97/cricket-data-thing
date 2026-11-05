"""A batter's dismissal at the non-striker's end counts in his average (services/nonstriker_outs.py, 5 Nov 2026)."""
from services import nonstriker_outs as N
from services.metrics import sql_defs as D

NO_BALL_FILTERS = dict(bowlers=[], bat_hand=None, bowl_style=[], bowl_kind=[], crease_combo=[], line=[], length=[],
                       shot=[], control=False, wagon_zone=[], dismissal=[], exclude_bowlers=[])


def _applies(group_by, perspective=D.BATTER, **filters):
    return N.applies(group_by, perspective, ball_filters={**NO_BALL_FILTERS, **filters}, dimension_filters=None,
                     partnership=False, cumulative=False)


def test_applies_to_batting_rows_by_innings_context():
    assert _applies(["batter"])
    assert _applies(["batter", "year"])
    assert _applies(["phase"])            # batting rows (a batter filter) by phase
    assert _applies(["batter", "venue", "innings"])


def test_not_by_the_ball_or_for_other_perspectives():
    # A run-out at the other end isn't "against spin" or "on a good length".
    assert not _applies(["batter"], bowl_kind=["spin bowler"])
    assert not _applies(["batter"], line=["OUTSIDE_OFFSTUMP"])
    assert not _applies(["batter"], control=True)        # control=0 is a filter too: passed as `is not None`
    assert not _applies(["batter"], bowlers=["Jasprit Bumrah"])
    assert not _applies(["batter", "length"])
    assert not _applies(["batter", "bowler"])
    # Bowlers' and teams' wickets are already their own rules.
    assert not _applies(["bowler"], perspective=D.BOWLER)
    assert not _applies(["phase"], perspective=D.TEAM)
    assert not _applies([])
    assert not N.applies(["batter"], D.BATTER, ball_filters=NO_BALL_FILTERS, dimension_filters=[("x", "eq", ["1"])],
                         partnership=False, cumulative=False)
    assert not N.applies(["batter"], D.BATTER, ball_filters=NO_BALL_FILTERS, dimension_filters=None,
                         partnership=True, cumulative=False)


def test_add_to_rows_recomputes_average():
    # Kohli's ODIs on 5 Nov 2026: 251 dismissals as striker, 6 more backing up; official 15,109 at 58.79.
    rows = [{"batter": "Virat Kohli", "runs": 15109, "balls": 16011, "wickets": 251, "average": 60.2},
            {"batter": "Rohit Sharma", "runs": 100, "balls": 90, "wickets": 2, "average": 50.0}]
    added = N.add_to_rows(rows, {("Virat Kohli",): 6}, ["batter"])
    assert added == 6
    assert rows[0]["wickets"] == 257 and rows[0]["average"] == 58.79 and rows[0]["balls_per_dismissal"] == 62.3
    assert rows[1]["wickets"] == 2 and rows[1]["average"] == 50.0      # untouched


def test_sync_counts_the_non_strikers_dismissal():
    from sync_stats_from_dd import StatsFromDeliveryDetails as S

    run_out_backing_up = {"out": "true", "bat_out": "false", "dismissal": "run out", "p_out": 253802}
    assert S._nonstriker_dismissed(run_out_backing_up, 253802)
    assert not S._nonstriker_dismissed(run_out_backing_up, 34102)                       # someone else was out
    assert not S._nonstriker_dismissed({**run_out_backing_up, "bat_out": "true"}, 253802)  # the striker's: counted already
    assert not S._nonstriker_dismissed({**run_out_backing_up, "dismissal": "retired hurt"}, 253802)
    assert not S._nonstriker_dismissed({**run_out_backing_up, "out": "false"}, 253802)
    assert not S._nonstriker_dismissed(run_out_backing_up, None)
