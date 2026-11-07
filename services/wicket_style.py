"""
How a bowler takes wickets, against where he bowled (the profile's "How he takes wickets" card; analysis in
scripts/analysis/stumps_attack.py, 7 Nov 2026).

  split   his wickets bowled, LBW, caught (caught and bowled included) and stumped (hit wicket included)
  typical the same split for a bowler of his type (pace or spin) in the competitions and years he bowled in, weighted
          by his wickets in each: LBWs run from 4% of wickets (BBL, Super Smash) to 8.5% (T20Is, with associates), so
          a bare league-wide average would flatter some bowlers and not others
  attack  his share of line-tagged balls on the stumps and full, good length or yorker (the ball that hits), against
          the typical bowler of his type where he bowled, weighted by his tagged balls

A batter's version ("How he gets out", role="bat"): his dismissals by type against a typical batter dismissed in the
same competitions and years by the same kind of bowler. It repeats about as well (0.34 year to year) and is just as
unrelated to how well he bats (scripts/analysis/batter_bowled.py), so it gets a higher floor (batters have fewer
dismissals than bowlers have wickets) and no stumps line.

It's a style, not a rating: the bowled-and-LBW share repeats year to year (about 0.3-0.4) but doesn't predict economy
or balls per wicket. The card says how he takes wickets, never how well.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any, Dict, Optional, Tuple

MIN_WICKETS = 20        # the typical comparison needs this many wickets (a bowler's)
MIN_OUTS = 30           # ... or dismissals (a batter's: a typical 27% share swings about ±25% on 36)
MIN_TAGGED = 300        # the stumps line needs this many line-tagged balls
ATTACK_LENGTHS = {"FULL", "GOOD_LENGTH", "YORKER"}
HOW = {"bowled": "bowled", "leg before wicket": "lbw", "caught": "caught", "caught and bowled": "caught",
       "stumped": "stumped", "hit wicket": "stumped"}
KINDS = ("pace bowler", "spin bowler")


def _q(db, fmt, **kw):
    from services.player_cards import _q as q

    return q(db, fmt, **kw)


def _cell(r) -> Tuple[Any, Any, Any]:
    return r.get("competition"), r.get("year"), r.get("bowl_kind")


def _tables(db, fmt: str, who: Dict[str, Any], balls: bool = True) -> Dict[str, Dict]:
    """Wickets by type and tagged / attacking balls, per competition x year x bowler kind, for `who`'s balls."""
    wk = defaultdict(lambda: dict.fromkeys(("bowled", "lbw", "caught", "stumped"), 0))
    for r in _q(db, fmt, group_by=["competition", "year", "bowl_kind", "dismissal"], **who):
        k = HOW.get(r.get("dismissal"))
        if k and r.get("bowl_kind") in KINDS:
            wk[_cell(r)][k] += r.get("wickets") or 0
    tb = defaultdict(lambda: {"tagged": 0, "attack": 0})
    for r in (_q(db, fmt, group_by=["competition", "year", "bowl_kind", "line", "length"], **who) if balls else []):
        if r.get("line") and r.get("bowl_kind") in KINDS:
            b = tb[_cell(r)]
            b["tagged"] += r.get("balls") or 0
            if r["line"] == "ON_THE_STUMPS" and r.get("length") in ATTACK_LENGTHS:
                b["attack"] += r.get("balls") or 0
    return {"wickets": dict(wk), "balls": dict(tb)}


def typical_tables(db, fmt: str, base: Dict[str, Any], flt: Dict[str, Any], perspective: str = "bowling") -> Dict[str, Dict]:
    """Every ball's tables for the window, scope and the card's filter: cached once, shared by every profile."""
    from services.query_cache import cached_run

    key = {"kind": "wicket_style_typical", "v": 1, "fmt": fmt, "base": {k: str(v) for k, v in base.items()},
           "flt": {k: str(v) for k, v in flt.items()}}
    if perspective != "bowling":
        key["perspective"] = perspective
    if not base.get("end_date") or base["end_date"] >= date.today():
        key["day"] = date.today()

    def run():
        t = _tables(db, fmt, dict(metrics_perspective=perspective, **base, **flt), balls=perspective == "bowling")
        # JSON keys: "competition|year|kind".
        return {part: {"|".join(str(x) for x in c): v for c, v in t[part].items()} for part in t}
    return cached_run(db, key, run)


def wicket_style(db, fmt: str, player: str, base: Dict[str, Any], flt: Optional[Dict[str, Any]] = None,
                 role: str = "bowl") -> Optional[Dict[str, Any]]:
    """His split (and, for a bowler, stumps rate) against the typical player where he played; None with none."""
    flt = flt or {}
    bowling = role == "bowl"
    who = dict(bowlers=[player], metrics_perspective="bowling") if bowling else dict(batters=[player], metrics_perspective="batting")
    mine = _tables(db, fmt, dict(**who, **base, **flt), balls=bowling)
    typ = typical_tables(db, fmt, base, flt, "bowling" if bowling else "batting")
    split = dict.fromkeys(("bowled", "lbw", "caught", "stumped"), 0)
    expected = dict.fromkeys(split, 0.0)
    kinds = defaultdict(int)
    for c, w in mine["wickets"].items():
        n = sum(w.values())
        kinds[c[2]] += n
        for k in split:
            split[k] += w[k]
        t = typ["wickets"].get("|".join(str(x) for x in c))
        tn = sum(t.values()) if t else 0
        if tn:
            for k in split:
                expected[k] += n * t[k] / tn
    wickets = sum(split.values())
    if not wickets:
        return None
    tagged = attack = exp_attack = 0.0
    for c, b in mine["balls"].items():
        tagged += b["tagged"]
        attack += b["attack"]
        t = typ["balls"].get("|".join(str(x) for x in c))
        if t and t["tagged"]:
            exp_attack += b["tagged"] * t["attack"] / t["tagged"]
    exp_n = sum(expected.values())
    kind = (max(kinds, key=kinds.get).split()[0] if kinds else None) if bowling else None
    return {
        "kind": kind, "wickets": wickets, "split": split,
        "typical": ({k: round(100 * v / exp_n, 1) for k, v in expected.items()}
                    if wickets >= (MIN_WICKETS if bowling else MIN_OUTS) and exp_n else None),
        "attack": ({"share": round(100 * attack / tagged, 1), "typical": round(100 * exp_attack / tagged, 1), "tagged": int(tagged)}
                   if tagged >= MIN_TAGGED else None),
    }
