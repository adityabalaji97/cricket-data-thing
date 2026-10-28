"""The data behind a player profile's first screen (VERDICT_SCREEN_PLAN.md, chunk V2).

One call returns both roles, built for a phone screenshot that answers "is the hype fair?":
season rows (wins added by season), phase rows, peer strips (the player's rank among comparable
players, with the peer distribution as quantiles), and the last 8 matches with runs above par.

Everything runs through run_deliveries_query, so each piece sits in the query result cache
(keyed by data_version). Peer pools are shared by every player in the same format, scope and
window, so the first profile after a data load warms them for all the others. The assembled
summary is cached the same way.

Decisions (VERDICT_SCREEN_PLAN.md):
* D1 peers: "strong" = major leagues + T20Is between top-12 sides (T20); ODIs between top-12
  sides. Against every side the ODI pool fills with associates (the cheapest ODI bowlers since
  2023 are from Namibia, Oman, Nepal and the USA).
* D2 the season metric is wins added (WPA); bowling Impact is too noisy to rank bowlers on.
* D3 form is the last 8 games in the format, whatever the scope, so the chips stay current.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from services.query_builder_v2 import run_deliveries_query
from services.query_cache import cached_run

SUMMARY_VERSION = "v2"  # v2: dynamic peer floors, identity, verdict line

STRONG_T20_LEAGUES = [
    "IPL", "BBL", "PSL", "CPL", "SA20", "T20 Blast", "ILT20", "MLC", "BPL", "LPL", "Super Smash",
]
TOP_TEAMS = 12

# Years of data the first screen covers when no dates are given (from 1 January).
DEFAULT_YEARS = {"T20": 2, "ODI": 3}
# The peer pool's floor follows the window (services/qualification.py): 40% of the median balls of the role's
# regulars, never below 120. Players under PREFILTER_BALLS can't move that median much and would make the pool
# query too big to cache, so they're dropped first.
PREFILTER_BALLS = 30
# A role counts from this many balls in the window.
ROLE_MIN_BALLS = 60
# The second role makes the player an all-rounder when he does it in this share of the innings he
# plays his main role in, with at least SECOND_ROLE_MIN_BALLS. Balls alone misjudge it: Jansen faced
# a quarter of the balls he bowled, but batted in 60% as many innings.
SECOND_ROLE_SHARE = 0.4
SECOND_ROLE_MIN_BALLS = 120
FORM_GAMES = 8
FORM_LOOKBACK_DAYS = 548
QUANTILES = 50

# (key, label, lower_is_better)
STRIPS = {
    "T20": {
        "bowl": [("wpa", "Wins added", False), ("dot_percentage", "Dot balls %", False),
                 ("economy", "Economy", True), ("balls_per_dismissal", "Balls per wicket", True)],
        "bat": [("wpa", "Wins added", False), ("strike_rate", "Strike rate", False),
                ("average", "Average", False)],
    },
    "ODI": {
        "bowl": [("balls_per_dismissal", "Balls per wicket", True), ("dot_percentage", "Dot balls %", False),
                 ("economy", "Economy", True)],
        "bat": [("strike_rate", "Strike rate", False), ("average", "Average", False)],
    },
}

ROW_FIELDS = [
    "balls", "runs", "wickets", "innings_count", "strike_rate", "average", "balls_per_dismissal",
    "dot_percentage", "economy", "wpa", "impact_per_innings", "raa", "raa_per_100",
]

ROLES = {
    "bowl": {"group": "bowler", "filter": "bowlers", "perspective": "bowling", "opponent": "batting_team", "own": "bowling_team"},
    "bat": {"group": "batter", "filter": "batters", "perspective": "batting", "opponent": "bowling_team", "own": "batting_team"},
}


def default_window(fmt: str, today: Optional[date] = None) -> tuple[date, date]:
    today = today or date.today()
    return date(today.year - DEFAULT_YEARS[fmt], 1, 1), today


def scope_params(fmt: str, scope: str) -> Dict[str, Any]:
    """Competition filters for the peer pool and the player's own numbers."""
    if fmt == "T20":
        if scope == "strong":
            return {"leagues": STRONG_T20_LEAGUES, "include_international": True, "top_teams": TOP_TEAMS}
        # Every men's T20: no leagues and include_international off (True with no leagues would be
        # internationals only).
        return {"leagues": [], "include_international": False}
    if scope == "strong":
        return {"include_international": True, "top_teams": TOP_TEAMS}
    return {"include_international": True}


def scope_label(fmt: str, scope: str) -> str:
    if scope != "strong":
        return "All T20s" if fmt == "T20" else "All ODIs"
    if fmt == "T20":
        return "Major leagues + T20Is between top-12 sides"
    return "ODIs between top-12 sides"


def _num(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _with_economy(row: Dict[str, Any]) -> Dict[str, Any]:
    balls, runs = _num(row.get("balls")), _num(row.get("runs"))
    if "economy" not in row or row.get("economy") is None:
        row["economy"] = round(runs * 6 / balls, 2) if balls and runs is not None else None
    return row


def _slim(row: Dict[str, Any], extra: List[str]) -> Dict[str, Any]:
    _with_economy(row)
    out = {k: row.get(k) for k in extra}
    for k in ROW_FIELDS:
        v = row.get(k)
        out[k] = round(v, 3) if isinstance(v, float) else v
    return out


def quantiles(values: List[float], n: int = QUANTILES) -> List[float]:
    """n+1 evenly spaced quantiles of the sorted values (nearest rank), for drawing the peer strip."""
    vals = sorted(values)
    if not vals:
        return []
    if len(vals) == 1:
        return [vals[0]]
    return [vals[round(i * (len(vals) - 1) / n)] for i in range(n + 1)]


def rank_among(values: List[float], value: float, lower_is_better: bool) -> int:
    """1 = best. Ties share the better rank."""
    better = sum(1 for v in values if (v < value if lower_is_better else v > value))
    return better + 1


def classify_roles(overall: Dict[str, Dict[str, Any]]) -> tuple[Optional[str], bool]:
    """(main role, all-rounder?) from each role's overall row: the main role is the one with more
    innings; the player is an all-rounder when the other role clears SECOND_ROLE_SHARE of those
    innings and SECOND_ROLE_MIN_BALLS."""
    if not overall:
        return None, False
    innings = {role: (row.get("innings_count") or 0) for role, row in overall.items()}
    primary = max(innings, key=lambda role: (innings[role], (overall[role].get("balls") or 0)))
    other = next((role for role in overall if role != primary), None)
    if other is None:
        return primary, False
    allrounder = (
        innings[other] >= SECOND_ROLE_SHARE * innings[primary]
        and (overall[other].get("balls") or 0) >= SECOND_ROLE_MIN_BALLS
    )
    return primary, allrounder


def _query(db, fmt: str, **params) -> List[Dict[str, Any]]:
    result = run_deliveries_query(db, fmt=fmt, limit=10000, **params)
    return list((result or {}).get("data") or [])


def _peer_pool(db, fmt: str, role: str, window: Dict[str, Any], scope: Dict[str, Any]) -> Dict[str, Any]:
    """The role's qualified players in the window, trimmed to the strip metrics, with the floor that qualified
    them. Cached on its own: every player in the same format, scope and window shares it."""
    from services.qualification import min_balls

    r = ROLES[role]
    keys = [k for k, _, _ in STRIPS[fmt][role]]

    def run() -> Dict[str, Any]:
        rows = [_with_economy(row) for row in _query(
            db, fmt, group_by=[r["group"]], metrics_perspective=r["perspective"], min_balls=PREFILTER_BALLS,
            **window, **scope,
        )]
        floor = min_balls(rows)
        keep = [{"name": row.get(r["group"]), **{k: _num(row.get(k)) for k in keys}}
                for row in rows if (row.get("balls") or 0) >= floor["min_balls"]]
        return {**floor, "players": keep}

    key = {"kind": "verdict_peer_pool", "v": SUMMARY_VERSION, "fmt": fmt, "role": role, **window, **scope}
    return cached_run(db, key, run)


def _peer_strips(db, fmt: str, role: str, window: Dict[str, Any], scope: Dict[str, Any],
                 me: Dict[str, Any]) -> Dict[str, Any]:
    r = ROLES[role]
    pool = _peer_pool(db, fmt, role, window, scope)
    peers = pool["players"]
    name = me.get(r["group"])
    qualified = any(p["name"] == name for p in peers)
    strips = []
    for key, label, lower in STRIPS[fmt][role]:
        value = _num(me.get(key))
        values = [p[key] for p in peers if p.get(key) is not None]
        if value is None or not values:
            continue
        others = values if qualified else values + [value]
        strips.append({
            "key": key,
            "label": label,
            "lower_is_better": lower,
            "value": round(value, 3),
            "rank": rank_among(others, value, lower),
            "n": len(others),
            "median": quantiles(values, 2)[1] if len(values) > 1 else values[0],
            "quantiles": [round(v, 3) for v in quantiles(values)],
        })
    return {"qualified": qualified, "min_balls": pool["min_balls"], "median_balls": pool["median_balls"],
            "pool": len(peers), "metrics": strips}


def _role_block(db, fmt: str, role: str, player: str, window: Dict[str, Any],
                scope: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    r = ROLES[role]
    base = {r["filter"]: [player], "metrics_perspective": r["perspective"], **window, **scope}
    overall_rows = _query(db, fmt, group_by=[r["group"]], **base)
    if not overall_rows:
        return None
    me = _with_economy(max(overall_rows, key=lambda row: row.get("balls") or 0))
    if (me.get("balls") or 0) < ROLE_MIN_BALLS:
        return None
    years = sorted(_query(db, fmt, group_by=["year"], **base), key=lambda row: row.get("year") or 0)
    phases = _query(db, fmt, group_by=["phase"], **base)
    return {
        "name": me.get(r["group"]),
        "overall": _slim(me, []),
        "seasons": [_slim(row, ["year"]) for row in years],
        "phases": [_slim(row, ["phase"]) for row in phases],
        "peers": _peer_strips(db, fmt, role, window, scope, me),
    }


def _form(db, fmt: str, player: str, end: date) -> Dict[str, Any]:
    """Last FORM_GAMES matches in the format, bat and ball joined, whatever the scope (D3)."""
    window = {"start_date": end - timedelta(days=FORM_LOOKBACK_DAYS), "end_date": end}
    every = scope_params(fmt, "all")
    games: Dict[str, Dict[str, Any]] = {}
    for role in ("bowl", "bat"):
        r = ROLES[role]
        rows = _query(
            db, fmt, group_by=["match_id", "match_date", "competition", "batting_team", "bowling_team"],
            **{r["filter"]: [player]}, metrics_perspective=r["perspective"], **window, **every,
        )
        for row in rows:
            game = games.setdefault(str(row.get("match_id")), {
                "match_id": row.get("match_id"),
                "date": str(row.get("match_date")),
                "competition": row.get("competition"),
                "team": row.get(r["own"]),
                "opponent": row.get(r["opponent"]),
            })
            game[role] = {
                "balls": row.get("balls"), "runs": row.get("runs"), "wickets": row.get("wickets"),
                "raa": row.get("raa"), "wpa": row.get("wpa"),
            }
    recent = sorted(games.values(), key=lambda g: g["date"])[-FORM_GAMES:]
    for game in recent:
        raas = [game[k]["raa"] for k in ("bowl", "bat") if k in game and game[k]["raa"] is not None]
        game["raa"] = round(sum(raas), 2) if raas else None
    return {"games": recent, "team": recent[-1]["team"] if recent else None}


STYLE_WORDS = {
    "RF": "right-arm fast", "RFM": "right-arm fast-medium", "RMF": "right-arm medium-fast", "RM": "right-arm medium",
    "LF": "left-arm fast", "LFM": "left-arm fast-medium", "LMF": "left-arm medium-fast", "LM": "left-arm medium",
    "OB": "off-spin", "LB": "leg-spin", "LBG": "leg-spin", "SLA": "left-arm orthodox", "LWS": "left-arm wrist spin",
}
METRIC_WORDS = {"wpa": "wins added", "dot_percentage": "dot balls", "economy": "economy",
                "balls_per_dismissal": "balls per wicket", "strike_rate": "strike rate", "average": "average"}


def _ordinal(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def _signed(v: float) -> str:
    return f"{v:+.1f}".replace("-", "\u2212")


def _identity(db, fmt: str, player: str, name: str, roles: Dict[str, Any], window: Dict[str, Any]) -> Dict[str, Any]:
    """National side (else main team), bowling style, batting hand and usual batting position."""
    from sqlalchemy import text

    out: Dict[str, Any] = {"side": None, "bowling_style": None, "bat_hand": None, "batting_position": None}
    try:
        out["side"] = db.execute(text(
            "SELECT main_side FROM player_identity WHERE name = :n ORDER BY balls DESC LIMIT 1"), {"n": name}).scalar()
    except Exception:
        db.rollback()
    if "bowl" in roles:
        rows = _query(db, fmt, group_by=["bowl_style"], bowlers=[player], metrics_perspective="bowling", **window)
        top = max(rows, key=lambda r: r.get("balls") or 0, default=None)
        if top and top.get("bowl_style"):
            out["bowling_style"] = STYLE_WORDS.get(top["bowl_style"], top["bowl_style"])
    if "bat" in roles:
        base = {"batters": [player], "metrics_perspective": "batting", **window}
        hand = max(_query(db, fmt, group_by=["bat_hand"], **base), key=lambda r: r.get("balls") or 0, default=None)
        pos = max(_query(db, fmt, group_by=["batting_position"], **base),
                  key=lambda r: r.get("innings_count") or 0, default=None)
        out["bat_hand"] = (hand or {}).get("bat_hand")
        out["batting_position"] = (pos or {}).get("batting_position")
    return out


def verdict_line(summary: Dict[str, Any]) -> Optional[str]:
    """One or two plain sentences from the ranks and the seasons (VERDICT_SCREEN_PLAN.md D4, first version).

    The claim is the player's best rank among his peers (a rank in the top 3, else the top 10% or 25%, else the
    rank itself). The second sentence is a swing of at least one win added between his last two seasons in his
    main role (T20 only, where wins added exist)."""
    roles = summary.get("roles") or {}
    cands = []
    for role, block in roles.items():
        if not block["peers"]["qualified"]:
            continue
        for m in block["peers"]["metrics"]:
            cands.append((m["rank"] / m["n"], m["rank"], role, m))
    if not cands:
        return None
    share, rank, role, m = min(cands, key=lambda c: (c[0], c[1]))
    words = METRIC_WORDS.get(m["key"], m["label"].lower())
    if rank <= 3:
        claim = f"{_ordinal(rank)} of {m['n']} for {words}"
    elif share <= 0.10:
        claim = f"Top 10% for {words}"
    elif share <= 0.25:
        claim = f"Top 25% for {words}"
    else:
        claim = f"{_ordinal(rank)} of {m['n']} for {words}"
    if summary.get("allrounder"):
        claim += " with the ball" if role == "bowl" else " with the bat"
    claim += "."  # the window and scope sit on the chip beside it
    primary = summary.get("primary_role")
    seasons = [r for r in (roles.get(primary) or {}).get("seasons", []) if r.get("wpa") is not None]
    if summary.get("has_wins_added") and len(seasons) >= 2:
        a, b = seasons[-2], seasons[-1]
        if abs(b["wpa"] - a["wpa"]) >= 1.0:
            claim += f" {_signed(a['wpa'])} wins added in {a['year']}, {_signed(b['wpa'])} in {b['year']}."
    return claim


def build_summary(db, player: str, fmt: str = "T20", scope: str = "strong",
                  start_date: Optional[date] = None, end_date: Optional[date] = None) -> Dict[str, Any]:
    default_start, default_end = default_window(fmt)
    start, end = start_date or default_start, end_date or default_end
    window = {"start_date": start, "end_date": end}
    params = scope_params(fmt, scope)

    roles = {role: _role_block(db, fmt, role, player, window, params) for role in ("bowl", "bat")}
    roles = {k: v for k, v in roles.items() if v}
    primary, allrounder = classify_roles(
        {role: block["overall"] for role, block in roles.items()}
    )

    name = next((block["name"] for block in roles.values() if block.get("name")), player)
    form = _form(db, fmt, player, end)
    summary = {
        "player": name,
        "format": fmt,
        "scope": scope,
        "scope_label": scope_label(fmt, scope),
        "window": {"start_date": start.isoformat(), "end_date": end.isoformat()},
        "primary_role": primary,
        "allrounder": allrounder,
        "latest_team": form["team"],
        "roles": roles,
        "form": form["games"],
        "has_wins_added": fmt == "T20",
        "version": SUMMARY_VERSION,
    }
    summary["identity"] = _identity(db, fmt, player, name, roles, window) if roles else {}
    summary["verdict"] = verdict_line(summary)
    return summary


def get_summary(db, player: str, fmt: str = "T20", scope: str = "strong",
                start_date: Optional[date] = None, end_date: Optional[date] = None) -> Dict[str, Any]:
    """build_summary through the persistent result cache (fresh after every data load)."""
    key = {"kind": "player_verdict", "v": SUMMARY_VERSION, "player": player.strip().lower(),
           "fmt": fmt, "scope": scope, "start_date": start_date, "end_date": end_date}
    if end_date is None:
        # A default window ends today; key it by day so it rolls over.
        key["day"] = date.today()
    return cached_run(db, key, lambda: build_summary(db, player, fmt, scope, start_date, end_date))
