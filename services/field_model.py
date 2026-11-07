"""
A suggested field from where a batter hits the ball (FIELD_COVERAGE_PLAN.md, F1; the F0 findings shape it).

Inputs, per cut (phase x pace/spin, all men's T20s in the window), each ball with a position:
  direction: the angle from the batter in his view (0 behind, 90 square on the leg side, 180 straight, 270 square off);
  outcome:   a four, a six, runs 1-3 (ran), or caught at a distance.
Distance mostly records where fielders stood (F0), so it's used only for catches (in the ring or in the deep).

A batter's profile in a cut is his own balls plus K balls of the average batter of his hand in the same cut, so a thin
cut stays the standard field and only a deep, distinctive one moves away from it.

The field: nine fielders (keeper and bowler fixed), each in the ring (covers ground balls and catches in the ring within
+/-REACH_IN degrees) or on the rope (covers fours, and catches in the deep, within +/-REACH_OUT degrees along it); at most
MAX_OUT[phase] on the rope. What covering a ball is worth: a four 3 runs saved, a ran ball half its runs, a catch a
wicket (WICKET[phase] runs), a six a small catching chance. Fielders are placed greedily, then moved one at a time while
any move helps. The reaches and values are assumptions (we have no ball speed or fielder data), stated on every output.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional, Tuple

BIN = 5                        # degrees per direction bin
NBINS = 360 // BIN
REACH_IN, REACH_OUT = 15, 15   # degrees either side a fielder covers
MIN_GAP = 15                   # degrees between two fielders in the same ring
MAX_OUT = {"powerplay": 2, "middle": 5, "death": 5}
WICKET = {"powerplay": 9.0, "middle": 8.0, "death": 5.0}   # runs a wicket is worth, by phase
FOUR_SAVED, RAN_SAVED, SIX_CHANCE = 3.0, 0.5, 0.6
K_PRIOR = 200                  # balls of the average batter added to a batter's own
KEEPER_ARC = (355, 5)          # the keeper covers directly behind (in the ring)
FIELDERS = 9

INNER_NAMES = [(10, 35, "short fine leg"), (35, 70, "backward square leg"), (70, 100, "square leg"), (100, 135, "midwicket"),
               (135, 170, "mid on"), (170, 190, "straight"), (190, 225, "mid off"), (225, 260, "cover"), (260, 290, "point"),
               (290, 325, "backward point"), (325, 350, "slip / gully")]
OUTER_NAMES = [(10, 35, "fine leg"), (35, 70, "deep backward square"), (70, 100, "deep square leg"), (100, 135, "deep midwicket"),
               (135, 170, "long on"), (170, 190, "straight hit"), (190, 225, "long off"), (225, 260, "deep cover"),
               (260, 290, "deep point"), (290, 325, "deep backward point"), (325, 350, "third man")]


def position_name(angle: float, ring: str) -> str:
    for lo, hi, name in (INNER_NAMES if ring == "in" else OUTER_NAMES):
        if lo <= angle % 360 < hi:
            return name
    return "keeper" if ring == "in" else "fine (behind)"


def angle_of(x: float, y: float, hand: str) -> Tuple[float, float]:
    """The batter's-view angle and the distance (1 = the rope) of a ball's position on the feed's 0-363 grid (a fixed view
    of the ground, a right-hander's leg side on the right: a left-hander is mirrored)."""
    dx, dy = x - 181.0, y - 181.0
    if hand == "LHB":
        dx = -dx
    return math.degrees(math.atan2(dx, -dy)) % 360, math.hypot(dx, dy) / 181.0


def empty_profile() -> Dict[str, List[float]]:
    """Per direction bin: fours, sixes, ran balls' runs, catches in the ring, catches in the deep, and balls."""
    return {k: [0.0] * NBINS for k in ("four", "six", "ran", "catch_in", "catch_out", "balls")}


def add_profile(a: Dict[str, List[float]], b: Dict[str, List[float]], scale: float = 1.0) -> Dict[str, List[float]]:
    return {k: [x + scale * y for x, y in zip(a[k], b[k])] for k in a}


def shrink(own: Dict[str, List[float]], average: Dict[str, List[float]], k: float = K_PRIOR) -> Dict[str, List[float]]:
    """His profile plus k balls of the average batter's (scaled to k balls)."""
    n = sum(average["balls"]) or 1
    return add_profile(own, average, k / n)


def _covers(field_angle: float, ball_angle: float, reach: float) -> bool:
    d = abs((ball_angle - field_angle + 180) % 360 - 180)
    return d <= reach


def ball_values(p: Dict[str, List[float]], phase: str) -> List[Tuple[float, float]]:
    """Per bin: (value of covering it from the ring, value of covering it from the rope)."""
    w = WICKET.get(phase, 7.0)
    return [(RAN_SAVED * p["ran"][i] + w * p["catch_in"][i],
             FOUR_SAVED * p["four"][i] + SIX_CHANCE * p["six"][i] + w * p["catch_out"][i]) for i in range(NBINS)]


def field_value(field: Iterable[Tuple[float, str]], vals: List[Tuple[float, float]]) -> float:
    """Value covered by a field: each bin counted once per ring (two fielders on one area don't double it)."""
    field = list(field) + [(0.0, "keeper")]
    total = 0.0
    for i, (vin, vout) in enumerate(vals):
        a = i * BIN + BIN / 2
        if any((ring in ("in", "keeper")) and _covers(fa, a, REACH_IN if ring == "in" else 5) for fa, ring in field):
            total += vin
        if any(ring == "out" and _covers(fa, a, REACH_OUT) for fa, ring in field):
            total += vout
    return total


def _legal(field: List[Tuple[float, str]], phase: str) -> bool:
    if sum(1 for _, r in field if r == "out") > MAX_OUT.get(phase, 5):
        return False
    for i, (a, r) in enumerate(field):
        if r == "in" and _covers(0.0, a, KEEPER_ARC[1] + MIN_GAP / 2):
            return False  # don't stand on the keeper
        for b, s in field[i + 1:]:
            if r == s and _covers(a, b, MIN_GAP - 0.01):
                return False
    return True


def solve(p: Dict[str, List[float]], phase: str, n: int = FIELDERS) -> List[Tuple[float, str]]:
    """Nine fielders: greedy by marginal value, then one-at-a-time moves while any helps."""
    vals = ball_values(p, phase)
    cands = [(i * BIN + BIN / 2, ring) for i in range(NBINS) for ring in ("in", "out")]
    field: List[Tuple[float, str]] = []
    while len(field) < n:
        base = field_value(field, vals)
        best, gain = None, -1.0
        for c in cands:
            trial = field + [c]
            if not _legal(trial, phase):
                continue
            g = field_value(trial, vals) - base
            if g > gain:
                best, gain = c, g
        if best is None:
            break
        field.append(best)
    improved = True
    while improved:
        improved = False
        cur = field_value(field, vals)
        for i in range(len(field)):
            for c in cands:
                trial = field[:i] + [c] + field[i + 1:]
                if _legal(trial, phase) and field_value(trial, vals) > cur + 1e-9:
                    field, cur, improved = trial, field_value(trial, vals), True
    return sorted(field, key=lambda f: (f[1], f[0]))


def suggest(own: Dict[str, List[float]], average: Dict[str, List[float]], phase: str) -> Dict[str, Any]:
    """His field and the standard one for the cut, both scored on his (shrunk) profile; the fielders that moved."""
    mine = shrink(own, average)
    standard = solve(average, phase)
    his = solve(mine, phase)
    vals = ball_values(mine, phase)
    total = sum(a + b for a, b in vals) or 1
    v_std, v_his = field_value(standard, vals), field_value(his, vals)

    def named(f):
        return [{"angle": a, "ring": r, "name": position_name(a, r)} for a, r in f]

    moved_in = [f for f in his if not any(f[1] == s[1] and _covers(f[0], s[0], 10) for s in standard)]
    moved_out = [s for s in standard if not any(s[1] == f[1] and _covers(f[0], s[0], 10) for f in his)]
    return {"field": named(his), "standard": named(standard), "covered": round(v_his / total, 3),
            "covered_by_standard": round(v_std / total, 3), "gain": round((v_his - v_std) / total, 3),
            "moved": {"to": named(moved_in), "from": named(moved_out)}, "own_balls": int(sum(own["balls"])),
            "assumptions": {"reach_in": REACH_IN, "reach_out": REACH_OUT, "wicket_runs": WICKET.get(phase), "k_prior": K_PRIOR}}
