"""Statistics and verdict rules shared by analysis/hypotheses (preregistration/README.md)."""
import numpy as np
import pytest

from analysis.hypotheses import common as c


def _effect(lo, hi, direction="negative", meaningful=-0.5, est=None):
    return c.Effect("x", est if est is not None else (lo + hi) / 2, [lo, hi], 0.1, "t", "u", direction, meaningful)


@pytest.mark.parametrize("ci_, expected", [
    ((-1.2, -0.1), c.SUPPORTED),        # excludes zero in the claimed (negative) direction
    ((0.1, 0.9), c.NOT_SUPPORTED),      # excludes zero the other way
    ((-0.3, 0.2), c.NOT_SUPPORTED),     # includes zero but rules out -0.5
    ((-0.9, 0.2), c.INCONCLUSIVE),      # includes zero and -0.5
])
def test_directional_verdicts(ci_, expected):
    assert c.verdict_directional(_effect(*ci_)) == expected


def test_directional_positive_claim_and_minimum():
    assert c.verdict_directional(_effect(0.2, 1.0, "positive", 0.5)) == c.SUPPORTED
    assert c.verdict_directional(_effect(0.2, 1.0, "positive", 0.5), minimum_met=False) == c.INCONCLUSIVE


@pytest.mark.parametrize("ci_, expected", [((-2, 3), c.SUPPORTED), ((1, 6), c.NOT_SUPPORTED), ((-4, 7), c.INCONCLUSIVE)])
def test_equivalence_verdicts(ci_, expected):
    assert c.verdict_equivalence(_effect(*ci_, direction="none", meaningful=5), band=5) == expected


def test_mean_diff_effect_recovers_a_known_shift():
    g = np.random.default_rng(1)
    a, b = list(g.normal(-1.0, 1.0, 400)), list(g.normal(0.0, 1.0, 400))
    eff = c.mean_diff_effect("x", a, b, unit="u", direction="negative", meaningful=-0.5, label_a="a", label_b="b")
    assert eff.ci[0] < -1.0 < eff.ci[1] or abs(eff.estimate + 1.0) < 0.2
    assert eff.ci[1] < 0 and eff.p_value < 1e-6
    assert c.verdict_directional(eff) == c.SUPPORTED


def test_null_difference_is_not_significant():
    g = np.random.default_rng(2)
    a, b = list(g.normal(0, 1, 300)), list(g.normal(0, 1, 300))
    eff = c.mean_diff_effect("x", a, b, unit="u", direction="negative", meaningful=-0.5, label_a="a", label_b="b")
    assert eff.ci[0] < 0 < eff.ci[1]


def test_bootstrap_is_reproducible():
    xs = list(range(50))
    r1 = c.bootstrap(lambda g: float(np.mean(c.resample(g, xs))), n=200)
    r2 = c.bootstrap(lambda g: float(np.mean(c.resample(g, xs))), n=200)
    assert np.array_equal(r1, r2)


def test_boot_p_and_wilson():
    assert c.boot_p(np.array([1.0, 2.0, 3.0])) == 0.0
    assert c.boot_p(np.array([-1.0, 1.0])) == 1.0
    lo, hi = c.wilson(50, 100)
    assert lo < 0.5 < hi and round(lo, 3) == 0.404


def test_per_over_uses_metric_balls():
    assert c.per_over({"raa": 3.0, "metric_balls": 12}) == 1.5
    assert c.per_over({"raa": 3.0, "metric_balls": 0}) is None


def test_did_on_synthetic_cells():
    from analysis.hypotheses import h1_impact_player as h1

    def match(comp, year, runs):
        return [{"match_id": f"{comp}{year}{runs}", "innings": i, "competition": comp, "season_start_year": year,
                 "runs": runs, "balls": 120, "avg_total": runs} for i in (1, 2)]

    rows = []
    for k in range(40):
        rows += match("IPL", 2021, 160 + k % 5) + match("IPL", 2024, 190 + k % 5)
        rows += match("BBL", 2021, 160 + k % 5) + match("BBL", 2024, 166 + k % 5)
    cells = h1._cells(rows)
    eff = h1._did(cells, h1.OUTCOMES["runs per over"][0], "runs per over", 0.3)
    # IPL +30 runs per innings, BBL +6: DiD = 24 runs / 20 overs = 1.2 runs per over.
    assert eff.estimate == pytest.approx(1.2)
    assert eff.ci[0] > 0
