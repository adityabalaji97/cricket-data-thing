"""The XI engine's scorer agrees with the grade (services/squad_grade.py), and the limits rule (XI_BUILDER_PLAN.md)."""
from services import xi_engine as X
from services.squad_grade import grade

BENCH = {k: {"values": [float(i) for i in range(1, 41)], "playoff": p, "rest": r}
         for k, p, r in (("openers", 30, 25), ("top", 150, 140), ("finishers", 155, 145), ("pp_pace", 1.1, 1.0),
                         ("mid_spin", 1.2, 1.0), ("death_pace", 9.8, 10.6), ("depth", 6, 5))}


def _p(name, bat=None, bowl=None, best=0):
    b = {pos: {"balls": balls, "runs": runs, "wickets": outs, "dots": 0, "boundaries": 0} for pos, balls, runs, outs in (bat or [])}
    w = {slot: {"balls": balls, "runs": runs, "wickets": wk, "dots": 0, "boundaries": 0} for slot, balls, runs, wk in (bowl or [])}
    return {"name": name, "bat": b, "bowl": w, "best_season_balls": best}


def test_score_matches_the_grade():
    players = [
        _p("A", bat=[(1, 400, 520, 12)]), _p("B", bat=[(2, 300, 360, 10)]), _p("C", bat=[(3, 250, 390, 8)]),
        _p("D", bat=[(6, 150, 240, 6)]), _p("E", bowl=[("powerplay|pace", 200, 260, 9), ("death|pace", 120, 190, 5)], best=180),
        _p("F", bowl=[("middle|spin", 300, 380, 14)], best=200),
    ]
    g = grade(players, BENCH, {})
    s = X.score([{"name": p["name"], "roles": X._roles_of(p), "best_season_balls": p["best_season_balls"]} for p in players], BENCH)
    assert [(r["key"], r["status"], r["holders"]) for r in g["roles"]] == [(r["key"], r["status"], r["holders"]) for r in s["roles"]]


def test_over_the_purse_scores_but_cannot_save():
    squad = [{"price": 30.0, "overseas": i < 2} for i in range(5)]
    st = X.limits_state(squad, {**X.LIMITS, "squad_min": 1})
    assert st["spent"] == 150.0 and not st["can_save"] and "over the purse" in st["problems"][0]
