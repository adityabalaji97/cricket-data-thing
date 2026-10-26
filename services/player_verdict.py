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

SUMMARY_VERSION = "v1"

STRONG_T20_LEAGUES = [
    "IPL", "BBL", "PSL", "CPL", "SA20", "T20 Blast", "ILT20", "MLC", "BPL", "LPL", "Super Smash",
]
TOP_TEAMS = 12

# Years of data the first screen covers when no dates are given (from 1 January).
DEFAULT_YEARS = {"T20": 2, "ODI": 3}
# A player needs this many balls in the window to be ranked among the peers.
MIN_BALLS = {"T20": {"bowl": 600, "bat": 300}, "ODI": {"bowl": 500, "bat": 400}}
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


def _peer_strips(db, fmt: str, role: str, window: Dict[str, Any], scope: Dict[str, Any],
                 me: Dict[str, Any]) -> Dict[str, Any]:
    r = ROLES[role]
    peers = [_with_economy(row) for row in _query(
        db, fmt, group_by=[r["group"]], metrics_perspective=r["perspective"],
        min_balls=MIN_BALLS[fmt][role], **window, **scope,
    )]
    name = me.get(r["group"])
    qualified = any(p.get(r["group"]) == name for p in peers)
    strips = []
    for key, label, lower in STRIPS[fmt][role]:
        value = _num(me.get(key))
        values = [v for v in (_num(p.get(key)) for p in peers) if v is not None]
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
    return {"qualified": qualified, "min_balls": MIN_BALLS[fmt][role], "pool": len(peers), "metrics": strips}


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
    return {
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


def get_summary(db, player: str, fmt: str = "T20", scope: str = "strong",
                start_date: Optional[date] = None, end_date: Optional[date] = None) -> Dict[str, Any]:
    """build_summary through the persistent result cache (fresh after every data load)."""
    key = {"kind": "player_verdict", "v": SUMMARY_VERSION, "player": player.strip().lower(),
           "fmt": fmt, "scope": scope, "start_date": start_date, "end_date": end_date}
    if end_date is None:
        # A default window ends today; key it by day so it rolls over.
        key["day"] = date.today()
    return cached_run(db, key, lambda: build_summary(db, player, fmt, scope, start_date, end_date))
