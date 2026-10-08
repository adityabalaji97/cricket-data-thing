"""
"The deeper cut": in every post, one stat a scoreboard can't show, from data Hindsight has and the scoreboards don't
(ball-by-ball control, line and length, wagon zones, bowling styles, the game state, runs above average).

    candidates(db, role, name, scope)  ->  [Candidate, ...]  every probe that found something, most surprising first
    pick(cands, avoid)                 ->  the one to post (probes in `avoid` were used by the last few posts)
    to_card(c)                         ->  the story-card JSON (visual deep_compare, kicker "The deeper cut")

A probe is one query-builder call for the player and the same call for the field (every player in the same matches),
read into a sentence. Code writes every number and word; a candidate only exists when the player is clearly unlike the
field on a big enough sample, with enough tagged balls for tagged columns. Nothing is forced: no candidate, no slide.

Probes (role):
    slow-start      batter   strike rate by balls faced (1-9, 10-19, 20+)
    false-shots     batter   share of balls not controlled, against pace and spin
    zones           batter   share of runs through each wagon-wheel zone
    length          batter   strike rate by length
    style           batter   strike rate by bowling style
    phase-value     both     runs above average per over, by phase (T20 Primer, men's T20)
    hand            bowler   economy to left- and right-handers
    first-over      bowler   economy for the rest of the spell after a first over of 10+, against one of 0-6
    wicket-length   bowler   share of wickets by length
    conversion      bowler   balls per wicket among balls the batter didn't control (turning false shots into wickets)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from services.ig_posts.cards import ZONES, card, short

KICKER = "The deeper cut"
HELP = "From ball-by-ball tracking, not on any scorecard"
COVERAGE = 0.85  # tagged share needed for control, length and wagon-zone probes

LENGTHS = [("SHORT", "short"), ("SHORT_OF_A_GOOD_LENGTH", "back-of-a-length"), ("GOOD_LENGTH", "good-length"),
           ("FULL", "full"), ("YORKER", "yorker")]
BALLS = {"YORKER": "yorkers"}  # "against yorkers", not "against yorker balls"


def _balls(key: str, word: str) -> str:
    return BALLS.get(key, f"{word} balls")
STYLES = {
    "RF": "right-arm fast", "RFM": "right-arm fast-medium", "RMF": "right-arm medium-fast", "RM": "right-arm medium",
    "LF": "left-arm fast", "LFM": "left-arm fast-medium", "LMF": "left-arm medium-fast", "LM": "left-arm medium",
    "OB": "off-spin", "LB": "leg-spin", "LBG": "leg-spin", "SLA": "left-arm orthodox spin", "LWS": "left-arm wrist spin",
}
PHASES = [("powerplay", "In the powerplay", "Powerplay"), ("middle", "In the middle overs", "Middle overs"),
          ("death", "At the death", "Death")]


@dataclass
class Candidate:
    probe: str
    subject: str
    sentence: str
    surprise: float                 # how unlike the field, times confidence in the sample (0 = not at all)
    metric: Dict[str, str]          # {label, format} for the chart
    rows: List[Dict[str, Any]]      # [{label, subject, field, highlight?}]
    sample: str
    series: Tuple[str, str] = ("", "")
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Probe:
    id: str
    roles: Tuple[str, ...]
    group_by: Tuple[str, ...]
    read: Callable[..., Optional[Candidate]]
    dimension_filters: Tuple[str, ...] = ()
    t20_only: bool = False
    needs_field: bool = True  # runs above average are already measured against the field


# ---------------------------------------------------------------- helpers

def _sum(rows: Iterable[Dict[str, Any]], key: str) -> float:
    return float(sum((r.get(key) or 0) for r in rows))


def _sr(rows: List[Dict[str, Any]]) -> Optional[float]:
    balls = _sum(rows, "balls")
    return 100 * _sum(rows, "runs") / balls if balls else None


def _econ(rows: List[Dict[str, Any]]) -> Optional[float]:
    balls = _sum(rows, "balls")
    return 6 * _sum(rows, "runs") / balls if balls else None


def _conf(n: float, need: float) -> float:
    """Confidence in a sample: 0.5 at the minimum, 1 at four times it."""
    return min(1.0, 0.5 * math.sqrt(n / need)) if need else 1.0


def _rel(a: float, b: float) -> float:
    return abs(a / b - 1) if b else 0.0


def _who(role: str) -> str:
    return "the average batter" if role == "batter" else "the average bowler"


def _by(rows: List[Dict[str, Any]], key: str) -> Dict[Any, List[Dict[str, Any]]]:
    out: Dict[Any, List[Dict[str, Any]]] = {}
    for r in rows:
        out.setdefault(r.get(key), []).append(r)
    return out


def _lower(bucket: Any) -> Optional[int]:
    try:
        return int(str(bucket).split("-")[0].rstrip("+"))
    except ValueError:
        return None


# ---------------------------------------------------------------- probes

def slow_start(name, role, rows, field_rows, scope_label):
    def split(rs):
        early = [r for r in rs if _lower(r.get("batter_balls_faced_bucket")) == 1]
        mid = [r for r in rs if _lower(r.get("batter_balls_faced_bucket")) == 10]
        late = [r for r in rs if (_lower(r.get("batter_balls_faced_bucket")) or 0) >= 20]
        return early, mid, late
    e, m, l = split(rows)
    fe, fm, fl = split(field_rows)
    if _sum(e, "balls") < 40 or _sum(l, "balls") < 80 or not _sr(fe) or not _sr(fl):
        return None
    s_ratio, f_ratio = _sr(l) / _sr(e), _sr(fl) / _sr(fe)
    surprise = _rel(s_ratio, f_ratio) * _conf(_sum(e, "balls"), 40)
    if _rel(s_ratio, f_ratio) < 0.2:
        return None
    nm = name  # in full: "Patel" could be Axar or Harshal
    sentence = (f"{nm} strikes at {_sr(e):.0f} in the first 10 balls of an innings and {_sr(l):.0f} after 20. "
                f"The average batter: {_sr(fe):.0f}, then {_sr(fl):.0f}.")
    out_rows = [{"label": lab, "subject": _sr(s), "field": _sr(f)} for lab, s, f in
                (("Balls 1-9", e, fe), ("Balls 10-19", m, fm), ("Balls 20+", l, fl)) if _sum(s, "balls")]
    return Candidate("slow-start", name, sentence, surprise, {"label": "strike rate", "format": "int"}, out_rows,
                     f"{nm} · {scope_label} · {int(_sum(rows, 'balls')):,} balls", (nm, "Average batter"))


def false_shots(name, role, rows, field_rows, scope_label):
    def rate(rs):
        tagged = [r for r in rs if r.get("control") is not None]
        t = _sum(tagged, "balls")
        return (_sum([r for r in tagged if r.get("control") == 0], "balls") / t if t else None), t, _sum(rs, "balls")
    best = None
    for kind, word in (("pace bowler", "pace"), ("spin bowler", "spin")):
        s, t, total = rate([r for r in rows if r.get("bowl_kind") == kind])
        f, _ft, _ = rate([r for r in field_rows if r.get("bowl_kind") == kind])
        if s is None or not f or t < 80 or t < COVERAGE * total:
            continue
        dev = _rel(s, f)
        if dev >= 0.3 and (best is None or dev > best[0]):
            best = (dev, kind, word, s, f, t)
    if not best:
        return None
    dev, kind, word, s, f, t = best
    nm = name  # in full: "Patel" could be Axar or Harshal
    if s > f:
        sentence = (f"{nm} is beaten or mistimes {s:.0%} of balls against {word}. "
                    f"The average batter: {f:.0%}.")
    else:
        sentence = f"{nm} is in control of {1 - s:.0%} of balls against {word}. The average batter: {1 - f:.0%}."
    # The chart says what the sentence says: "beaten or mistimes" shows the miss rate, "in control" the control rate.
    worse = s > f
    out_rows = []
    for k, w in (("pace bowler", "v pace"), ("spin bowler", "v spin")):
        sk, _t, _ = rate([r for r in rows if r.get("bowl_kind") == k])
        fk, _t2, _ = rate([r for r in field_rows if r.get("bowl_kind") == k])
        if sk is not None and fk is not None:
            out_rows.append({"label": w, "subject": 100 * (sk if worse else 1 - sk), "field": 100 * (fk if worse else 1 - fk),
                             "highlight": k == kind})
    label = "% of balls beaten or mistimed" if worse else "% of balls in control"
    return Candidate("false-shots", name, sentence, dev * _conf(t, 80), {"label": label, "format": "pct0"},
                     out_rows, f"{nm} · {scope_label} · {int(t):,} tracked balls against {word}", (nm, "Average batter"))


def zones(name, role, rows, field_rows, scope_label):
    def shares(rs):
        hit = [r for r in rs if r.get("wagon_zone") in ZONES]
        runs = _sum(hit, "runs")
        return ({z: _sum(g, "runs") / runs for z, g in _by(hit, "wagon_zone").items()} if runs else {}), runs, hit
    s, runs, hit = shares(rows)
    f, _fr, _ = shares(field_rows)
    tagged = _sum([r for r in rows if r.get("wagon_zone") is not None], "balls")
    if runs < 200 or not f or tagged < COVERAGE * _sum(rows, "balls"):
        return None
    zone = max(s, key=lambda z: (s[z] / f.get(z, 1)) if s[z] >= 0.2 else 0)
    if s[zone] < 0.2 or not f.get(zone) or s[zone] / f[zone] < 1.35:
        return None
    nm = name  # in full: "Patel" could be Axar or Harshal
    where = ZONES[zone].lower()
    sentence = f"{s[zone]:.0%} of {nm}'s runs come through {where}. The average batter: {f[zone]:.0%}."
    top = sorted(s, key=lambda z: -s[z])[:4]
    out_rows = [{"label": ZONES[z], "subject": 100 * s[z], "field": 100 * f.get(z, 0), "highlight": z == zone} for z in top]
    return Candidate("zones", name, sentence, (s[zone] / f[zone] - 1) * _conf(runs, 200),
                     {"label": "% of runs", "format": "pct0"}, out_rows,
                     f"{nm} · {scope_label} · {int(runs):,} runs off the bat", (nm, "Average batter"))


def length(name, role, rows, field_rows, scope_label):
    by, fby = _by(rows, "length"), _by(field_rows, "length")
    tagged = _sum([r for r in rows if r.get("length") is not None], "balls")
    if tagged < COVERAGE * _sum(rows, "balls"):
        return None
    best = None
    for key, word in LENGTHS:
        b = _sum(by.get(key, []), "balls")
        if b < 40 or not _sr(fby.get(key, [])):
            continue
        s, f = _sr(by[key]), _sr(fby[key])
        dev = _rel(s, f) * _conf(b, 40)
        if _rel(s, f) >= 0.2 and (best is None or dev > best[0]):
            best = (dev, key, word, s, f)
    if not best:
        return None
    dev, key, word, s, f = best
    nm = name  # in full: "Patel" could be Axar or Harshal
    sentence = f"{nm} strikes at {s:.0f} against {_balls(key, word)}. The average batter: {f:.0f}."
    out_rows = [{"label": w.capitalize().replace("-", " "), "subject": _sr(by[k]), "field": _sr(fby.get(k, [])) or 0, "highlight": k == key}
                for k, w in LENGTHS if _sum(by.get(k, []), "balls") >= 15]
    return Candidate("length", name, sentence, dev, {"label": "strike rate", "format": "int"}, out_rows,
                     f"{nm} · {scope_label} · {int(tagged):,} tracked balls", (nm, "Average batter"))


def style(name, role, rows, field_rows, scope_label):
    by, fby = _by(rows, "bowl_style"), _by(field_rows, "bowl_style")
    best = None
    for key, word in STYLES.items():
        b = _sum(by.get(key, []), "balls")
        if b < 40 or not _sr(fby.get(key, [])):
            continue
        s, f = _sr(by[key]), _sr(fby[key])
        dev = _rel(s, f) * _conf(b, 40)
        if _rel(s, f) >= 0.25 and (best is None or dev > best[0]):
            best = (dev, key, word, s, f, b)
    if not best:
        return None
    dev, key, word, s, f, b = best
    nm = name  # in full: "Patel" could be Axar or Harshal
    sentence = f"{nm} strikes at {s:.0f} against {word}. The average batter: {f:.0f}."
    top = sorted((k for k in by if k in STYLES and _sum(by[k], "balls") >= 25), key=lambda k: -_sum(by[k], "balls"))[:4]
    if key not in top:
        top = top[:3] + [key]
    out_rows = [{"label": STYLES[k].replace("right-arm ", "RA ").replace("left-arm ", "LA ").capitalize(), "subject": _sr(by[k]),
                 "field": _sr(fby.get(k, [])) or 0, "highlight": k == key} for k in top]
    return Candidate("style", name, sentence, dev, {"label": "strike rate", "format": "int"}, out_rows,
                     f"{nm} · {scope_label} · {int(b):,} balls against {word}", (nm, "Average batter"))


def phase_value(name, role, rows, field_rows, scope_label):
    by = _by(rows, "phase")
    need = 120 if role == "bowler" else 100
    best = None
    for key, word, _label in PHASES:
        rs = by.get(key, [])
        b = _sum(rs, "balls")
        raa = _sum(rs, "raa")
        if b < need or not any(r.get("raa") is not None for r in rs):
            continue
        per_over = 6 * raa / b
        if abs(per_over) >= 0.8 and (best is None or abs(per_over) > abs(best[2])):
            best = (key, word, per_over, b)
    if not best:
        return None
    key, word, per_over, b = best
    nm = name  # in full: "Patel" could be Axar or Harshal
    if role == "bowler":
        verb = "saves" if per_over > 0 else "costs"
        sentence = f"{word}, {nm} {verb} {abs(per_over):.1f} runs an over against an average bowler in the same situations."
    else:
        verb = "adds" if per_over > 0 else "costs"
        sentence = f"{word}, {nm} {verb} {abs(per_over):.1f} runs an over against an average batter in the same situations."
    out_rows = [{"label": lab, "subject": 6 * _sum(by.get(k, []), "raa") / _sum(by.get(k, []), "balls"),
                 "field": 0.0, "highlight": k == key} for k, _w, lab in PHASES if _sum(by.get(k, []), "balls") >= 30]
    # Every player has a phase; damped so it doesn't win every post on availability alone.
    return Candidate("phase-value", name, sentence, (abs(per_over) / 4) * _conf(b, need),
                     {"label": "runs above average per over", "format": "signed1"}, out_rows,
                     f"{nm} · {scope_label} · {int(b):,} balls {word[0].lower() + word[1:]}",
                     (nm, "Average"), {"signed": True})


def hand(name, role, rows, field_rows, scope_label):
    by, fby = _by(rows, "bat_hand"), _by(field_rows, "bat_hand")
    l, r = by.get("LHB", []), by.get("RHB", [])
    if _sum(l, "balls") < 60 or _sum(r, "balls") < 60 or not _econ(fby.get("LHB", [])) or not _econ(fby.get("RHB", [])):
        return None
    s_ratio = _econ(l) / _econ(r)
    f_ratio = _econ(fby["LHB"]) / _econ(fby["RHB"])
    if _rel(s_ratio, f_ratio) < 0.2:
        return None
    nm = name  # in full: "Patel" could be Axar or Harshal
    sentence = (f"{nm} goes for {_econ(l):.1f} an over to left-handers and {_econ(r):.1f} to right-handers. "
                f"The average bowler: {_econ(fby['LHB']):.1f} and {_econ(fby['RHB']):.1f}.")
    out_rows = [{"label": "v left-handers", "subject": _econ(l), "field": _econ(fby["LHB"]), "highlight": s_ratio > f_ratio},
                {"label": "v right-handers", "subject": _econ(r), "field": _econ(fby["RHB"]), "highlight": s_ratio < f_ratio}]
    return Candidate("hand", name, sentence, _rel(s_ratio, f_ratio) * _conf(min(_sum(l, "balls"), _sum(r, "balls")), 60),
                     {"label": "runs an over", "format": "dec1"}, out_rows,
                     f"{nm} · {scope_label} · {int(_sum(rows, 'balls')):,} balls", (nm, "Average bowler"))


def first_over(name, role, rows, field_rows, scope_label):
    by, fby = _by(rows, "bowler_first_over_runs_bucket"), _by(field_rows, "bowler_first_over_runs_bucket")
    bad, good = by.get("10+", []), by.get("0-6", [])
    if _sum(bad, "balls") < 36 or _sum(good, "balls") < 36 or not _econ(fby.get("10+", [])) or not _econ(fby.get("0-6", [])):
        return None
    s_diff = _econ(bad) - _econ(good)
    f_diff = _econ(fby["10+"]) - _econ(fby["0-6"])
    # Only a clear story: they recover (no worse after a bad first over) or they unravel (much worse than most).
    recovers = s_diff <= 0 and f_diff - s_diff >= 1.5
    unravels = s_diff - f_diff >= 1.5
    if not (recovers or unravels):
        return None
    nm = name  # in full: "Patel" could be Axar or Harshal
    sentence = (f"After a first over of 10 or more, {nm}'s other overs go for {_econ(bad):.1f}, against "
                f"{_econ(good):.1f} after a tidy one. The average bowler: {_econ(fby['10+']):.1f} against {_econ(fby['0-6']):.1f}.")
    out_rows = [{"label": "After a 10+ first over", "subject": _econ(bad), "field": _econ(fby["10+"]), "highlight": True},
                {"label": "After a 0-6 first over", "subject": _econ(good), "field": _econ(fby["0-6"])}]
    return Candidate("first-over", name, sentence, (abs(s_diff - f_diff) / 2) * _conf(_sum(bad, "balls"), 36),
                     {"label": "runs an over, overs 2 onwards", "format": "dec1"}, out_rows,
                     f"{nm} · {scope_label} · {int(_sum(bad, 'balls')):,} balls after an expensive first over",
                     (nm, "Average bowler"))


def wicket_length(name, role, rows, field_rows, scope_label):
    def shares(rs):
        w = _sum([r for r in rs if r.get("length") is not None], "wickets")
        return ({k: _sum(g, "wickets") / w for k, g in _by(rs, "length").items() if k is not None} if w else {}), w
    s, w = shares(rows)
    f, _ = shares(field_rows)
    if w < 15 or not f:
        return None
    key = max((k for k, _ in LENGTHS if k in s and f.get(k)), key=lambda k: s[k] / f[k], default=None)
    if key is None or s[key] < 0.3 or s[key] / f[key] < 1.3:
        return None
    word = dict(LENGTHS)[key]
    nm = name  # in full: "Patel" could be Axar or Harshal
    sentence = f"{s[key]:.0%} of {nm}'s wickets come from {_balls(key, word)}. The average bowler: {f[key]:.0%}."
    out_rows = [{"label": wd.capitalize().replace("-", " "), "subject": 100 * s.get(k, 0), "field": 100 * f.get(k, 0), "highlight": k == key}
                for k, wd in LENGTHS if s.get(k) or f.get(k, 0) >= 0.1]
    return Candidate("wicket-length", name, sentence, (s[key] / f[key] - 1) * _conf(w, 15),
                     {"label": "% of wickets", "format": "pct0"}, out_rows,
                     f"{nm} · {scope_label} · {int(w):,} wickets", (nm, "Average bowler"))


def conversion(name, role, rows, field_rows, scope_label):
    """How often a false shot becomes a wicket: balls per wicket among balls the batter didn't control."""
    def read(rs):
        beaten = [r for r in rs if r.get("control") == 0]
        tagged = _sum([r for r in rs if r.get("control") is not None], "balls")
        b, w = _sum(beaten, "balls"), _sum(beaten, "wickets")
        return b, w, tagged, _sum(rs, "balls")
    b, w, tagged, total = read(rows)
    fb, fw, _ft, _ = read(field_rows)
    if w < 12 or b < 60 or not fw or tagged < COVERAGE * total:
        return None
    s_bpw, f_bpw = b / w, fb / fw
    if _rel(f_bpw, s_bpw) < 0.2:  # at least a fifth fewer (or more) balls per wicket than the field
        return None
    nm = name
    if s_bpw < f_bpw:
        sentence = (f"When {nm} beats the bat, a wicket follows every {s_bpw:.1f} balls. "
                    f"The average bowler: every {f_bpw:.1f}.")
    else:
        sentence = (f"{nm} beats the bat, but needs {s_bpw:.1f} of those balls for a wicket. "
                    f"The average bowler: {f_bpw:.1f}.")
    out_rows = [{"label": "Balls per wicket, batter beaten", "subject": s_bpw, "field": f_bpw, "highlight": True},
                {"label": "Share of balls beating the bat", "subject": 100 * b / tagged if tagged else 0,
                 "field": 100 * fb / _ft if _ft else 0}]
    return Candidate("conversion", name, sentence, _rel(f_bpw, s_bpw) * _conf(w, 12),
                     {"label": "lower balls per wicket is better", "format": "dec1"}, out_rows,
                     f"{nm} · {scope_label} · {int(w)} wickets from {int(b):,} balls the batter didn't control",
                     (nm, "Average bowler"))


PROBES: Tuple[Probe, ...] = (
    Probe("slow-start", ("batter",), ("batter_balls_faced_bucket",), slow_start),
    Probe("false-shots", ("batter",), ("control", "bowl_kind"), false_shots),
    Probe("zones", ("batter",), ("wagon_zone",), zones),
    Probe("length", ("batter",), ("length",), length),
    Probe("style", ("batter",), ("bowl_style",), style),
    Probe("phase-value", ("batter", "bowler"), ("phase",), phase_value, t20_only=True, needs_field=False),
    Probe("hand", ("bowler",), ("bat_hand",), hand),
    Probe("first-over", ("bowler",), ("bowler_first_over_runs_bucket",), first_over, ("bowler_over_number:gte:2",)),
    Probe("wicket-length", ("bowler",), ("length",), wicket_length),
    Probe("conversion", ("bowler",), ("control",), conversion),
)


# ---------------------------------------------------------------- running them

_FIELD: Dict[Tuple, List[Dict[str, Any]]] = {}  # field rows by (probe, role, scope): the same for every player


def _query(db, probe: Probe, role: str, scope: Dict[str, Any], name: Optional[str]) -> List[Dict[str, Any]]:
    from services.query_builder_v2 import run_deliveries_query

    args = {**scope, "group_by": list(probe.group_by), "limit": 500}
    if probe.dimension_filters:
        args["dimension_filters"] = list(probe.dimension_filters)
    if role == "bowler":
        args["metrics_perspective"] = "bowling"
    if name:
        args["batters" if role == "batter" else "bowlers"] = [name]
        return run_deliveries_query(db, **args).get("data") or []
    # The field is the same for every player in the scope, and scans every match in it: cached per data load.
    from services.query_cache import cached_run

    return cached_run(db, {"endpoint": "deep_cut_field", "role": role, **args},
                      lambda: run_deliveries_query(db, **args).get("data") or [])


def candidates(db, role: str, name: str, scope: Dict[str, Any], scope_label: str,
               probes: Iterable[Probe] = PROBES, display: Optional[str] = None) -> List[Candidate]:
    """Every probe's finding for this player in this scope, most surprising first. `name` is the data's name (for the
    queries), `display` the one people know (for the sentences)."""
    found = []
    for probe in probes:
        if role not in probe.roles or (probe.t20_only and scope.get("fmt", "T20") != "T20"):
            continue
        try:
            rows = _query(db, probe, role, scope, name)
            if not rows:
                continue
            key = (probe.id, role, repr(sorted(scope.items())))
            if key not in _FIELD:
                _FIELD[key] = _query(db, probe, role, scope, None) if probe.needs_field else []
            c = probe.read(display or name, role, rows, _FIELD[key], scope_label)
        except Exception:  # pragma: no cover - one probe never stops the others
            import logging

            logging.getLogger(__name__).exception("deep cut probe %s for %s failed", probe.id, name)
            continue
        if c:
            found.append(c)
    return sorted(found, key=lambda c: -c.surprise)


def pick(cands: List[Candidate], avoid: Iterable[str] = (), used: Iterable[Tuple[str, str]] = ()) -> Optional[Candidate]:
    """The best candidate whose probe the last few posts didn't use (any probe, if all were). A player's stat of one
    kind already in the queue nearby (`used`: (subject, probe)) is never repeated: no candidate then, no slide."""
    avoid, used = set(avoid), set(used)
    unused = [c for c in cands if (c.subject, c.probe) not in used]
    fresh = [c for c in unused if c.probe not in avoid]
    return (fresh or unused or [None])[0]


#: A debate's own subject, by words in its question: its deeper cut should be about the same thing.
TOPICS = (
    (("finisher", "death"), ("phase-value", "length", "wicket-length")),
    (("spin", "spinner"), ("false-shots", "style", "wicket-length", "first-over")),
    (("pace", "quick", "seam", "new ball", "powerplay"), ("false-shots", "style", "length", "wicket-length", "hand")),
    (("opener", "anchor", "complete"), ("slow-start", "false-shots", "length")),
)
ON_TOPIC = 1.6  # a candidate on the question's subject counts this much more


def on_topic(fact: Dict[str, Any], cands: List[Candidate]) -> None:
    """Weigh candidates towards the post's own question (a finisher debate gets a death-overs stat, not zones)."""
    text = f"{fact.get('title') or ''} {fact.get('noun') or ''}".lower()
    wanted = {p for words, probes in TOPICS if any(w in text for w in words) for p in probes}
    for c in cands:
        if c.probe in wanted:
            c.surprise *= ON_TOPIC


MAX_ROWS = 4  # what fits a 4:5 slide under a three-line title


def to_card(c: Candidate) -> Dict[str, Any]:
    rows = list(c.rows)
    while len(rows) > MAX_ROWS:  # drop from the end, never the split the sentence is about
        i = max(i for i, r in enumerate(rows) if not r.get("highlight"))
        rows.pop(i)
    payload = {"metric": {**c.metric, "signed": bool(c.extra.get("signed"))}, "series": list(c.series), "rows": rows}
    out = card(f"deep-{c.probe}", "deep_compare", c.sentence, payload, c.sample, HELP)
    out["kicker"] = KICKER
    return out


# ---------------------------------------------------------------- choosing one for a post

#: What Jev reads each candidate sentence for (0..4).
DEPTH_CRITERIA = [
    "Obvious: any scorecard or match report already says this",
    "Known: regular followers of this player would know it",
    "Interesting: true, but would not stop a fan scrolling",
    "Striking: a fan would stop, and might share it",
    "Revelation: changes how a fan sees this player, and only ball-by-ball data could show it",
]
LEAGUES = ("IPL", "BBL", "PSL", "CPL", "SA20", "The Hundred", "T20 Blast", "ILT20", "MLC")
YEARS_BACK = 3


def scope_for(fmt: str = "T20", since: Optional[int] = None, league: Optional[str] = None) -> Tuple[Dict[str, Any], str]:
    """A probe scope and its label. Without a league, every match of the format: leagues=[] with
    include_international=True would be internationals only."""
    from datetime import date

    year = since or date.today().year - YEARS_BACK
    scope = {"fmt": fmt, "gender": "male", "start_date": date(year, 1, 1), "leagues": [league] if league else [],
             "include_international": False}
    what = league or ("ODIs" if fmt == "ODI" else "T20s")
    return scope, f"{what} since {year}"


def resolve(db, name: str) -> Optional[Tuple[str, str]]:
    """(name in the data, name people know) for a player, or None."""
    from services.search import search_entities

    for item in search_entities(name, db, limit=5):
        if item.get("type") == "player" and name.lower() in {str(item.get("name")).lower(), str(item.get("display_name")).lower()}:
            return item["name"], item.get("display_name") or item["name"]
    return None


def name_in(db, text: str) -> Optional[Tuple[str, str]]:
    """The first player named in a sentence ("Does one bad over break Varun Chakravarthy?")."""
    import re

    words = re.findall(r"[A-Z][\w'.-]+(?:\s+[A-Z][\w'.-]+){1,2}", text or "")
    for span in words:
        for cut in (span, " ".join(span.split()[:2]), " ".join(span.split()[-2:])):
            hit = resolve(db, re.sub(r"'s?$", "", cut))
            if hit:
                return hit
    return None


def subjects_for(db, fact: Dict[str, Any]) -> Tuple[List[Tuple[Optional[str], str, str]], Dict[str, Any], str]:
    """[(role or None for either, data name, display name)] in the order to try, with the scope to probe them in."""
    import re

    kind = fact.get("kind")
    title = fact.get("title") or ""
    fmt = "ODI" if re.search(r"\bODIs?\b", f"{title} {fact.get('kicker') or ''}") else "T20"
    people: List[Tuple[Optional[str], str]] = []
    scope, label = scope_for(fmt)
    if fact.get("subject_role") and fact.get("subject"):  # a spotlight (services/ig_posts/spotlight.py): one player
        people = [(fact["subject_role"], fact["subject"])]
    elif kind == "debate":
        role = {"batters": "batter", "bowlers": "bowler"}.get((re.search(r"\d+ (batters|bowlers|partnerships)",
                                                                       fact.get("method") or "") or [None, None])[1])
        if role:
            people = [(role, n) for n in [fact.get("subject"), *(fact.get("leaders") or [])] if n]
        since = re.search(r"since (\d{4})", f"{fact.get('method') or ''} {title}")
        league = fact.get("kicker") if fact.get("kicker") in LEAGUES else None
        scope, label = scope_for(fmt, int(since.group(1)) if since else None, league)
    elif kind == "idea" and fact.get("subject"):
        numbers = fact.get("numbers") or {}
        people = [("bowler" if {"economy", "wickets"} & set(numbers) else "batter", fact["subject"])]
    elif kind == "play" and fact.get("answer"):
        people = [("batter", fact["answer"])]
    elif kind == "preview":
        from services.preview_cards import cached_story, context_from_params

        try:
            story = cached_story(db, context_from_params(db, fact.get("fixture") or {}))
            battle = next((c for ch in story["chapters"] for c in ch["cards"] if c["id"] == "key-battles"), None)
            rows = (battle or {}).get("payload", {}).get("rows") or []
            if rows:
                people = [("batter", rows[0]["batter"]), ("bowler", rows[0]["bowler"])]
        except Exception:  # pragma: no cover - a preview without a story gets no deeper cut
            people = []
        scope, label = scope_for((fact.get("fixture") or {}).get("format") or "T20")
    elif kind == "recap" and fact.get("match_id"):
        from services.ig_posts.match import _players

        from sqlalchemy import text

        f = db.execute(text("SELECT format FROM matches WHERE id = :i"), {"i": fact["match_id"]}).scalar() or "T20"
        ranked = sorted((p for r in ("batter", "bowler") for p in _players(db, fact["match_id"], f, r) if p.get("wpa") is not None),
                        key=lambda p: -abs(p["wpa"]))
        people = [(p["role"], p["name"]) for p in ranked[:2]]
        scope, label = scope_for(f)
    elif kind in ("record", "note"):
        hit = name_in(db, title)
        if hit:
            people = [("bowler" if "wicket" in title.lower() else ("batter" if kind == "record" else None), hit[0])]
    custom = fact.get("deep_cut_scope")  # a spotlight's own window, e.g. this season's powerplays
    if custom:
        scope, label = scope_for(fmt, custom.get("since"))
        if custom.get("over_max") is not None:
            scope["over_max"] = custom["over_max"]
        label = custom.get("label") or label
    out = []
    for role, n in people:
        hit = resolve(db, n) or (n, n)
        if hit[0] not in [o[1] for o in out]:
            out.append((role, hit[0], hit[1]))
    return out, scope, label


def rank(cands: List[Candidate], top: int = 6) -> Tuple[List[Candidate], str]:
    """Jev's 0..4 per sentence (the top few by surprise), best first; ties and a missing Jev fall back to surprise."""
    from services import jev_client

    head = sorted(cands, key=lambda c: -c.surprise)[:top]
    if not head or not jev_client.enabled():
        return head, "surprise"
    answers = jev_client.ask(
        {"audience": "cricket fans on Instagram and X who already follow the scorecards",
         "facts": {f"c{i}": c.sentence for i, c in enumerate(head)}},
        {f"c{i}": {"type": "score", "criteria": DEPTH_CRITERIA,
                   "instructions": f"How much does this stat go beyond what scoreboard apps show? \"{c.sentence}\""}
         for i, c in enumerate(head)},
        timeout=10.0,
    ) or {}
    for i, c in enumerate(head):
        s = (answers.get(f"c{i}") or {}).get("score")
        if isinstance(s, (int, float)):
            c.extra["jev"] = float(s)
    by = "jev" if any("jev" in c.extra for c in head) else "surprise"
    return sorted(head, key=lambda c: (-c.extra.get("jev", -1), -c.surprise)), by


def choose(db, fact: Dict[str, Any], avoid: Iterable[str] = (), used: Iterable[Tuple[str, str]] = ()) -> Optional[Dict[str, Any]]:
    """{card, deep_cut} for a post, or None when nothing clears the gates."""
    people, scope, label = subjects_for(db, fact)

    def found(group):
        out: List[Candidate] = []
        for role, name, display in group:
            for r in ([role] if role else ["batter", "bowler"]):
                out += candidates(db, r, name, scope, label, display=display)
        return out

    # A post about one player (a trend, a record, a myth) is about them: the others only if they have nothing.
    cands = found(people[:1]) if fact.get("subject") or fact.get("kind") in ("record", "note", "play", "idea") else []
    cands = cands or found(people[:3])
    used = set(used)
    cands = [c for c in cands if (c.subject, c.probe) not in used]
    if not cands:
        return None
    on_topic(fact, cands)
    ranked, by = rank(cands)
    c = pick(ranked, avoid, used)
    if c is None:
        return None
    return {"card": to_card(c), "deep_cut": {"probe": c.probe, "subject": c.subject, "sentence": c.sentence, "by": by,
                                             "jev": c.extra.get("jev"), "surprise": round(c.surprise, 3)}}
