"""
Split questions: a player's most striking split as the post's question, instead of one template for everyone ("Is X the
most complete batter?"). Used by the trend radar (services/ig_posts/trends.py) for a player in the news.

    find(db, name, role, scope)        -> [Split, ...]  every split cell where the player stands out, best first
    build(db, name, role, scope, ...)  -> {question, hook, cards, title, verdict, leaders, players, method, split}

A split is one cell of one dimension: a phase ("at the death"), the bowling ("against spin", "against leg-spin"),
both ("against spin in the middle overs"), the length ("against good-length balls"); for bowlers the batter's hand
("to left-handers") and phase. In each cell the field is every player in the scope with enough balls there (one
query-builder call per dimension, grouped by player and the dimension), and the player's place in it is a percentile.
The best cell (a high percentile, clearly above the field, a field big enough to mean something) is the question;
the next best from another dimension is the third slide.

The headline metric is what fans read: strike rate for batters, economy for bowlers; average or balls per wicket in
each row's detail, so a fast scorer who gets out every over doesn't read as a superpower without that showing.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from services.ig_posts.cards import card, fmt

STYLES = {"OB": "off-spin", "LB": "leg-spin", "LBG": "leg-spin", "SLA": "left-arm orthodox spin",
          "LWS": "left-arm wrist spin", "RF": "right-arm fast", "RFM": "right-arm fast-medium",
          "LF": "left-arm fast", "LFM": "left-arm fast-medium", "LMF": "left-arm medium-fast",
          "RMF": "right-arm medium-fast", "RM": "right-arm medium", "LM": "left-arm medium"}
PHASES = {"powerplay": "in the powerplay", "middle": "in the middle overs", "death": "at the death"}
KINDS = {"pace bowler": "against pace", "spin bowler": "against spin"}
LENGTHS = {"YORKER": "against yorkers", "FULL": "against full balls", "GOOD_LENGTH": "against good-length balls",
           "SHORT_OF_A_GOOD_LENGTH": "against back-of-a-length balls", "SHORT": "against short balls"}
HANDS = {"LHB": "to left-handers", "RHB": "to right-handers"}

#: (key, group_by, phrase(row) or None to skip the row, cell minimum balls) per role
BATTER_DIMS = [
    ("phase", ["phase"], lambda r: PHASES.get(r.get("phase")), 120),
    ("kind", ["bowl_kind"], lambda r: KINDS.get(r.get("bowl_kind")), 150),
    ("phase-kind", ["phase", "bowl_kind"],
     lambda r: f"{KINDS[r['bowl_kind']]} {PHASES[r['phase']]}" if r.get("bowl_kind") in KINDS and r.get("phase") in PHASES else None, 80),
    ("style", ["bowl_style"], lambda r: f"against {STYLES[r['bowl_style']]}" if r.get("bowl_style") in STYLES else None, 60),
    ("length", ["length"], lambda r: LENGTHS.get(r.get("length")), 60),
]
BOWLER_DIMS = [
    ("phase", ["phase"], lambda r: PHASES.get(r.get("phase")), 90),
    ("hand", ["bat_hand"], lambda r: HANDS.get(r.get("bat_hand")), 120),
    ("phase-hand", ["phase", "bat_hand"],
     lambda r: f"{HANDS[r['bat_hand']]} {PHASES[r['phase']]}" if r.get("bat_hand") in HANDS and r.get("phase") in PHASES else None, 60),
]
MIN_FIELD = 12          # qualifiers in a cell before a rank means anything
MIN_PCT = 80            # the player's percentile in the cell, at least
MIN_GAP = 0.08          # and this far better than the cell's field as a whole (8% on strike rate or economy)
SPECIFIC = {"phase-kind": 3, "phase-hand": 3, "style": 2, "length": 2}  # a sharper cell is a better story, a little


#: Short row labels and cricket order for the profile slide.
SHORT = {"powerplay": "Powerplay", "middle": "Middle overs", "death": "Death", "pace bowler": "Pace",
         "spin bowler": "Spin", "LHB": "Left-handers", "RHB": "Right-handers",
         **{k: v[:1].upper() + v[1:] for k, v in STYLES.items()},
         "YORKER": "Yorkers", "FULL": "Full", "GOOD_LENGTH": "Good length", "SHORT_OF_A_GOOD_LENGTH": "Back of a length",
         "SHORT": "Short"}
ORDER = ["powerplay", "middle", "death", "pace bowler", "spin bowler", "RHB", "LHB", "YORKER", "FULL", "GOOD_LENGTH",
         "SHORT_OF_A_GOOD_LENGTH", "SHORT"]


def _label(key: Tuple[Any, ...]) -> str:
    """("death", "LHB") -> "Left-handers · Death": the bowling or batter first, then the phase."""
    parts = [SHORT.get(k, str(k)) for k in key]
    if len(parts) == 2:
        parts = [parts[1], parts[0].lower() if parts[0] != "Middle overs" else "middle overs"]
    return " · ".join(parts)


def _order(key: Tuple[Any, ...]) -> Tuple[int, ...]:
    return tuple(ORDER.index(k) if k in ORDER else 99 for k in reversed(key))


@dataclass
class Split:
    dim: str
    group_by: List[str]
    key: Tuple[Any, ...]       # the cell's values, in group_by order
    phrase: str                # "against spin in the middle overs"
    value: float               # the player's strike rate / economy there
    field_value: float         # the whole field's in that cell (all balls, not an average of players)
    rank: int
    of: int
    pct: float
    score: float
    rows: List[Dict[str, Any]]  # the cell's qualifiers, best first


def _metric(role: str) -> Tuple[str, bool, str, str]:
    """(row key, higher is better, format, label)"""
    return ("strike_rate", True, "int", "strike rate") if role == "batter" else ("economy", False, "dec2", "economy")


def _econ(r: Dict[str, Any]) -> Optional[float]:
    if r.get("economy") is not None:
        return r["economy"]
    return 6 * r["runs"] / r["balls"] if r.get("balls") else None


def _value(r: Dict[str, Any], role: str) -> Optional[float]:
    return r.get("strike_rate") if role == "batter" else _econ(r)


def _query(db, role: str, scope: Dict[str, Any], group_by: List[str]) -> List[Dict[str, Any]]:
    from services.ig_posts.context import QuestionContext

    ctx = QuestionContext(db=db, role=role, fmt=scope["fmt"], params=scope["params"], min_balls=1)
    return ctx.query(group_by=[role, *group_by], min_balls=1, limit=10000)


def find(db, name: str, role: str, scope: Dict[str, Any]) -> List[Split]:
    """Every cell where `name` stands out in `scope`, best first (one cell per dimension)."""
    dims = BATTER_DIMS if role == "batter" else BOWLER_DIMS
    metric, higher, _, _ = _metric(role)
    out: List[Split] = []
    for dim, group_by, phrase, min_balls in dims:
        if scope["fmt"] != "T20" and dim in ("phase-kind", "phase-hand"):
            min_balls = int(min_balls * 1.5)  # ODI phases are longer; ask more of a cell
        rows = _query(db, role, scope, group_by)
        cells: Dict[Tuple[Any, ...], List[Dict[str, Any]]] = {}
        for r in rows:
            if phrase(r):
                cells.setdefault(tuple(r.get(g) for g in group_by), []).append(r)
        best: Optional[Split] = None
        for key, cell in cells.items():
            balls = sum(r["balls"] for r in cell)
            runs = sum(r["runs"] for r in cell)
            field_value = 100 * runs / balls if role == "batter" else 6 * runs / balls if balls else None
            q = [r for r in cell if r["balls"] >= min_balls and _value(r, role) is not None]
            mine = next((r for r in q if r[role] == name), None)
            if not mine or len(q) < MIN_FIELD or not field_value:
                continue
            q.sort(key=lambda r: _value(r, role), reverse=higher)
            rank = q.index(mine) + 1
            pct = 100 * (len(q) - rank) / (len(q) - 1)
            v = _value(mine, role)
            gap = (v - field_value) / field_value if higher else (field_value - v) / field_value
            if pct < MIN_PCT or gap < MIN_GAP:
                continue
            score = pct + 40 * min(gap, 0.5) + SPECIFIC.get(dim, 0) + (5 if rank == 1 else 0)
            s = Split(dim, group_by, key, phrase(mine), v, field_value, rank, len(q), pct, score, q)
            if not best or s.score > best.score:
                best = s
        if best:
            out.append(best)
    return sorted(out, key=lambda s: -s.score)


def _detail(r: Dict[str, Any], role: str) -> str:
    if role == "batter":
        avg = r.get("average")
        return f"{r['runs']} off {r['balls']}" + (f" · avg {avg:.0f}" if avg else "")
    bpw = r.get("balls_per_dismissal") or (r["balls"] / r["wickets"] if r.get("wickets") else None)
    return f"{r['wickets']} wkts in {r['balls']} balls" + (f" · a wicket every {bpw:.0f}" if bpw else "")


def _ordinal(n: int) -> str:
    return f"{n}{'th' if 11 <= n % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def leaderboard(s: Split, name: str, role: str, sample: str, scope_hook: str, top: int = 7) -> Dict[str, Any]:
    metric, higher, f, label = _metric(role)
    shown = s.rows[:top] if s.rank <= top else s.rows[:top - 1] + [s.rows[s.rank - 1]]
    lead = s.rows[0]
    if s.rank == 1:
        title = (f"{name} {'scores fastest' if role == 'batter' else 'is the tightest'} {s.phrase} {scope_hook}: "
                 f"{fmt(s.value, f)}, the next best {fmt(_value(s.rows[1], role), f)}")
    else:
        title = (f"{name} is {_ordinal(s.rank)} of {s.of} {s.phrase}; {lead[role]} leads at "
                 f"{fmt(_value(lead, role), f)}")
    c = card(f"split-{s.dim}", "metric_bars", title, {
        "metric": {"label": label, "format": f, "signed": False}, "label_width": 150,
        "rows": [{"name": r[role], "value": round(_value(r, role), 2), "detail": _detail(r, role),
                  "highlight": r[role] == name} for r in shown],
    }, sample, f"{s.of} {role}s with enough balls {s.phrase}. The field as a whole: {fmt(s.field_value, f)}.")
    return c


def profile(db, s: Split, name: str, role: str, scope: Dict[str, Any], sample: str) -> Optional[Dict[str, Any]]:
    """The player against the field in every cell of the split's dimension, the split's own cell highlighted."""
    metric, higher, f, label = _metric(role)
    dims = {d[0]: d for d in (BATTER_DIMS if role == "batter" else BOWLER_DIMS)}
    _, group_by, phrase, min_balls = dims[s.dim]
    rows = _query(db, role, scope, group_by)
    cells: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
    for r in rows:
        ph = phrase(r)
        if not ph:
            continue
        k = tuple(r.get(g) for g in group_by)
        c = cells.setdefault(k, {"phrase": ph, "runs": 0, "balls": 0, "mine": None})
        c["runs"] += r["runs"]
        c["balls"] += r["balls"]
        if r[role] == name:
            c["mine"] = r
    out = []
    for k, c in cells.items():
        mine = c["mine"]
        if not mine or mine["balls"] < min_balls // 2 or not c["balls"]:
            continue
        fv = 100 * c["runs"] / c["balls"] if role == "batter" else 6 * c["runs"] / c["balls"]
        out.append({"label": _label(k), "subject": round(_value(mine, role), 2), "field": round(fv, 2),
                    "highlight": k == s.key, "_k": _order(k)})
    if len(out) < 2:
        return None
    out.sort(key=lambda r: r.pop("_k"))
    gap = abs(s.value - s.field_value) / s.field_value
    title = (f"{s.phrase[:1].upper() + s.phrase[1:]}, {name} {'strikes at' if role == 'batter' else 'goes at'} "
             f"{fmt(s.value, f)}{'' if role == 'batter' else ' an over'}: {round(100 * gap)}% "
             f"{'faster' if role == 'batter' else 'tighter'} than the field")
    return card(f"profile-{s.dim}", "deep_compare", title, {
        "metric": {"label": label, "format": f, "signed": False}, "series": [name, f"Every {role}"], "rows": out,
    }, sample, "Every ball in the scope, the player's against everyone's.")


def build(db, name: str, role: str, scope: Dict[str, Any], scope_hook: str, sample: str) -> Optional[Dict[str, Any]]:
    splits = find(db, name, role, scope)
    if not splits:
        return None
    s = splits[0]
    metric, higher, f, label = _metric(role)
    if role == "batter":
        hook = (f"{name} strikes at {fmt(s.value, f)} {s.phrase} {scope_hook}. "
                + ("Who comes closest?" if s.rank == 1 else "Who's faster?"))
    else:
        hook = (f"{name} goes at {fmt(s.value, f)} an over {s.phrase} {scope_hook}. "
                + ("Who comes closest?" if s.rank == 1 else "Who's tighter?"))
    cards = [leaderboard(s, name, role, sample, scope_hook)]
    prof = profile(db, s, name, role, scope, sample)
    if prof:
        cards.append(prof)
    if len(splits) > 1:
        cards.append(leaderboard(splits[1], name, role, sample, scope_hook))
    verdict = cards[0]["title"]
    leaders = sorted({sp.rows[0][role] for sp in splits[:2]})
    return {"hook": hook, "cards": cards, "title": hook, "verdict": verdict, "leaders": leaders,
            "players": [name, *[l for l in leaders if l != name]],
            "split": {"dim": s.dim, "phrase": s.phrase, "rank": s.rank, "of": s.of, "pct": round(s.pct, 1),
                      "value": round(s.value, 2), "field": round(s.field_value, 2),
                      "next": splits[1].phrase if len(splits) > 1 else None},
            "method": (f"{label.capitalize()} in each split for every {role} with enough balls there ({sample}); "
                       f"the field figure is every ball in the split, not an average of players.")}
