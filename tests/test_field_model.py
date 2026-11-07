"""The field model's rules and behaviour (services/field_model.py)."""
from services import field_model as F


def _profile(spots):
    """spots: [(angle, kind, amount)] -> a profile."""
    p = F.empty_profile()
    for a, k, v in spots:
        i = int(a // F.BIN) % F.NBINS
        p[k][i] += v
        p["balls"][i] += v
    return p


def test_angles_are_the_batters_view():
    assert round(F.angle_of(181, 20, "RHB")[0]) == 0        # behind
    assert round(F.angle_of(340, 181, "RHB")[0]) == 90      # a right-hander's leg side, square
    assert round(F.angle_of(22, 181, "LHB")[0]) == 90       # a left-hander's leg side is on the grid's left
    assert round(F.angle_of(181, 340, "RHB")[0]) == 180     # straight


def test_never_breaks_the_rules():
    p = _profile([(a, "four", 5) for a in range(0, 360, 10)])
    for phase in ("powerplay", "middle", "death"):
        f = F.solve(p, phase)
        assert len(f) == F.FIELDERS
        assert sum(1 for _, r in f if r == "out") <= F.MAX_OUT[phase]
        assert F._legal(f, phase)


def test_a_square_hitter_gets_square_boundary_riders():
    p = _profile([(85, "four", 60), (95, "four", 60), (270, "ran", 5), (200, "ran", 5)])
    out = [a for a, r in F.solve(p, "middle") if r == "out"]
    assert any(70 <= a <= 110 for a in out)


def test_a_thin_cut_stays_the_standard_field():
    avg = _profile([(a, "four", 10) for a in range(0, 360, 15)] + [(a, "ran", 20) for a in range(0, 360, 15)])
    thin = _profile([(90, "four", 2)])
    s = F.suggest(thin, avg, "middle")
    assert s["gain"] < 0.02
