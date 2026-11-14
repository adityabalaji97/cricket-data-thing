"""services/ig_posts/player_compare.py: two batters, each in his own window. Strike rate against the league in the
same seasons, and titles written from the numbers."""
from services.ig_posts import player_compare as P


def _d(runs_balls, league_sr, impact, rest=0.0, share=25.0):
    years = {y: {"runs": r, "balls": b, "impact_per_100": impact} for y, (r, b) in runs_balls.items()}
    return {"years": years, "league": {y: {"strike_rate": league_sr[y]} for y in years},
            "me": {"impact_per_100": impact, "wpa": 1.0, "control_percentage": 80.0, "control_coverage_pct": 95.0,
                   "balls": sum(b for _, b in runs_balls.values())},
            "team": {"rest_bat": rest, "bowl": 1.0, "win": 50.0, "share": share, "teams": ["X"]}}


def test_sr_index_is_runs_over_the_leagues_runs_from_the_same_balls():
    d = _d({"2015": (150, 100), "2016": (140, 100)}, {"2015": 125, "2016": 140}, 10)
    assert round(P.sr_index(d), 1) == round(100 * 290 / (125 + 140), 1)


def test_era_title_says_faster_and_slower():
    d = {"A": _d({"2024": (150, 100)}, {"2024": 160}, 8), "B": _d({"2016": (148, 100)}, {"2016": 140}, 27)}
    t = P.era_card({"players": [{"label": "A", "window": "x"}, {"label": "B", "window": "y"}], "scope": "IPL"}, d)["title"]
    assert t.startswith("A scored 6% slower than his league, B 6% faster") and len(t) <= 110


def test_team_title_names_the_side_that_leaned_on_him():
    d = {"A": _d({"2024": (150, 100)}, {"2024": 160}, 8, rest=5.3, share=24.6),
         "B": _d({"2016": (148, 100)}, {"2016": 140}, 27, rest=-8.0, share=28.7)}
    t = P.team_card({"players": [{"label": "A", "window": "x"}, {"label": "B", "window": "y"}], "scope": "IPL"}, d)["title"]
    assert t.startswith("B's batting-mates added −8.0 per 100 balls, A's +5.3. B made 29%")
