"""Unit tests for services/metrics (T20 Primer metrics). No database needed."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from services.metrics.ball_metrics import impact, prepare_states, win_prob_and_leverage, win_probability
from services.metrics.dl_curve import DLParams, r_pro, r_std, solve_lambda
from services.metrics.par_scores import compute_par_scores

PARAMS = DLParams.from_dict(json.loads((Path(__file__).resolve().parents[1] / "ml/models/primer/dl_params_v1.json").read_text()))


def test_pro_curve_reduces_to_standard_at_lambda_one():
    b = np.array([120, 84, 30, 6])
    w = np.array([0, 2, 5, 9])
    assert np.allclose(r_pro(b, w, 1.0, PARAMS), r_std(b, w, PARAMS))


def test_no_resources_means_no_runs_to_come():
    assert float(r_pro(0, 3, 1.1, PARAMS)) == 0.0
    assert float(r_pro(60, 10, 1.1, PARAMS)) == 0.0


def test_lambda_is_one_for_par_at_or_below_the_standard_curve():
    base = float(r_std(120, 0, PARAMS))
    assert solve_lambda(np.array([base - 20, base]), PARAMS).tolist() == [1.0, 1.0]


def test_lambda_inverts_the_full_innings_value():
    for par in (175.0, 200.0, 225.0):
        lam = float(solve_lambda(par, PARAMS))
        assert lam > 1
        assert float(r_pro(120, 0, lam, PARAMS)) == pytest.approx(par, abs=1e-6)


def test_primer_worked_example_magnitudes():
    # Primer sec. 5.2: 60/2 after 6 overs, par 180 -> a four is worth ~+3.08, a wicket ~-11.8.
    # Our curve is fit to a broader dataset, so the same shape with slightly different numbers.
    lam = float(solve_lambda(180, PARAMS))
    before = float(r_pro(84, 2, lam, PARAMS))
    four = 4 + float(r_pro(83, 2, lam, PARAMS)) - before
    wicket = float(r_pro(83, 3, lam, PARAMS)) - before
    assert 2.8 < four < 3.4
    assert -13.5 < wicket < -11.0


def _toy_innings():
    rows = []
    runs = wkts = balls = 0
    script = [(1, 0, 0), (4, 0, 0), (0, 1, 0), (1, 0, 1), (6, 0, 0), (0, 0, 0)]  # (runs, out, wide)
    for i, (r, out, wide) in enumerate(script):
        runs += r
        wkts += out
        balls += 0 if wide else 1
        rows.append(dict(id=i, p_match="m1", inns=1, over=0, ball=i + 1, score=r, out=bool(out), wide=wide, noball=0,
                         inns_runs=runs, inns_wkts=wkts, inns_balls=balls, target=np.nan, max_balls=120))
    return pd.DataFrame(rows)


def test_impact_telescopes_over_an_innings():
    df = _toy_innings()
    par = pd.DataFrame({"p_match": ["m1"], "par": [190.0], "lam": [float(solve_lambda(190, PARAMS))]})
    states = prepare_states(df, par, par)
    total_impact = impact(states, PARAMS).sum()
    lam = par["lam"].iloc[0]
    last = states.iloc[-1]
    expected = last.inns_runs + float(r_pro(last.balls_after, last.wkts_after, lam, PARAMS)) - float(r_pro(120, 0, lam, PARAMS))
    assert total_impact == pytest.approx(expected, abs=1e-9)


def test_a_wide_uses_no_ball_and_counts_its_run():
    df = _toy_innings()
    par = pd.DataFrame({"p_match": ["m1"], "par": [160.0], "lam": [1.0]})
    states = prepare_states(df, par, par)
    wide = states[states["wide"] == 1].iloc[0]
    assert wide.balls_before == wide.balls_after
    assert wide.team_runs == 1
    assert impact(states[states["wide"] == 1], PARAMS)[0] == pytest.approx(1.0)


def test_win_probability_is_continuous_across_the_innings_break():
    lam = float(solve_lambda(185, PARAMS))
    total = 185.0
    end_first = win_probability([1], [total], [0], [6], [lam], [120], [total + 1], PARAMS)[0]
    start_second = win_probability([2], [0.0], [120], [0], [lam], [120], [total + 1], PARAMS)[0]
    assert end_first == pytest.approx(1 - start_second, abs=1e-9)


def test_finished_chases_are_certain():
    p = win_probability([2, 2, 2], [180, 150, 179], [10, 0, 0], [3, 7, 9], [1.0] * 3, [120] * 3, [180, 180, 180], PARAMS)
    assert p.tolist() == [1.0, 0.0, 0.5]  # won, lost, tied


def test_leverage_is_non_negative():
    df = _toy_innings()
    par = pd.DataFrame({"p_match": ["m1"], "par": [170.0], "lam": [1.0]})
    states = prepare_states(df, par, par)
    out = win_prob_and_leverage(states, PARAMS)
    assert (out["leverage"] >= 0).all()


def test_small_buckets_shrink_toward_their_parent():
    # A league-year whose grounds differ by a few runs, innings-to-innings spread ~20, plus one
    # ground with two innings at 210.
    rng = np.random.default_rng(0)
    rows = []
    for g, mean in enumerate([152, 156, 158, 160, 162, 164, 168, 170]):
        rows += [dict(p_match=f"g{g}_{i}", competition="L", year=2025, ground=f"G{g}", country="X",
                      first_total=mean + rng.normal(0, 20)) for i in range(40)]
    rows += [dict(p_match=f"tiny{i}", competition="L", year=2025, ground="Tiny", country="X", first_total=210.0) for i in range(2)]
    par = compute_par_scores(pd.DataFrame(rows)).set_index("p_match")["par"]
    league_mean = np.mean([r["first_total"] for r in rows])
    # Pulled well toward the league (the Primer's eq. 4 counts the tiny bucket's own mean in
    # var_between, so the pull is real but not total), while 40 innings barely move.
    assert league_mean < par["tiny0"] < 210 - 15
    g7_raw = np.mean([r["first_total"] for r in rows if r["ground"] == "G7"])
    assert abs(par["g7_0"] - g7_raw) < 2
