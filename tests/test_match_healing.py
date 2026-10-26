from services import match_healing as H


class _Match:
    match_id = "999"

    def __init__(self, innings, outcome=None):
        self.data = {"info": {"teams": ["New Zealand", "India"], "overs": 20, "outcome": outcome or {}},
                     "innings": innings}

    @property
    def info(self):
        return self.data["info"]

    def innings(self):
        return [(n, i) for n, i in enumerate(self.data["innings"], 1) if not i.get("super_over")]


def _ball(batter, runs, extras=None, wicket=None, total=None):
    b = {"batter": batter, "bowler": "Bowler", "non_striker": "Other",
         "runs": {"batter": runs, "total": total if total is not None else runs + sum((extras or {}).values())}}
    if extras:
        b["extras"] = extras
    if wicket:
        b["wickets"] = [wicket]
    return b


def test_rows_follow_the_feed_conventions():
    first = {"team": "New Zealand", "overs": [{"over": 0, "deliveries": [
        _ball("A", 4), _ball("A", 0, {"wides": 1}), _ball("A", 0, {"noballs": 1, "byes": 4}),
        _ball("A", 1), _ball("B", 0, wicket={"kind": "bowled", "player_out": "B"}), _ball("C", 6), _ball("C", 0)]}]}
    second = {"team": "India", "overs": [{"over": 0, "deliveries": [_ball("D", 2)]}]}
    rows = H.dd_rows(_Match([first, second], {"winner": "India"}), lambda n: n, lambda n: 7, {"ground": "Hagley Oval"}, {})
    one = [r for r in rows if r["inns"] == 1]
    assert [r["ball"] for r in one] == [1, 2, 3, 4, 5, 6, 7]                 # every delivery counts in the over
    assert one[2]["batruns"] == 0 and one[2]["score"] == 5                    # no-ball + 4 byes: nothing to the batter
    assert one[-1]["inns_balls"] == 5 and one[-1]["inns_balls_rem"] == 115  # legal balls only
    assert one[-1]["inns_runs"] == 4 + 1 + 5 + 1 + 0 + 6 + 0 and one[4]["inns_wkts"] == 1
    assert one[0]["cur_bat_runs"] == 4 and one[0]["ground"] == "Hagley Oval" and one[0]["p_bat"] == 7
    chase = [r for r in rows if r["inns"] == 2][0]
    assert chase["target"] == "18" and chase["inns_runs_rem"] == "16" and chase["winner"] == "India"


def test_the_feed_takes_a_match_back_only_when_it_has_it_whole():
    assert H.feed_caught_up(240, 240) and H.feed_caught_up(241, 240)
    assert not H.feed_caught_up(118, 240) and not H.feed_caught_up(0, 0)
