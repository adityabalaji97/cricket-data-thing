"""
The fantasy chapter (chunk 8 of MATCH_PREVIEW_VIZ_PLAN.md): F1 projected points, F2 captain and
vice-captain, F3 value per credit and F4 differentials (F3 and F4 for IPL fixtures only, sign-off
decision 5).

Projections are the matchup model the classic preview and the fantasy planner use
(services/matchups.get_team_matchups_service): each player's batting and bowling record against
the other XI over the last two seasons, scaled to a typical match. Points are batting + bowling
fantasy points (no fielding), the same scoring as batting_stats / bowling_stats.fantasy_points, so
a player's usual haul (F4) compares like with like. The old "confidence" figure is gone: the audit
found it nearly uniform, so it told the reader nothing.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from services.preview_cards.spec import Card, CardSpec, Info, SampleRule

TOP_N = 6  # two lines per row (name + split): six rows and the legend fit the 4:5 card
VALUE_MIN_POINTS = 15  # a cheap player projected for nothing is not value


def _memo(ctx, key, build):
    store = ctx.__dict__.setdefault("_fantasy", {})
    if key not in store:
        store[key] = build()
    return store[key]


def _since(ctx) -> date:
    end = ctx.end or date.today()
    return date(end.year - 1, 1, 1)


def projections(ctx) -> List[Dict[str, Any]]:
    """Both XIs' projected points, best first, each tagged with its side label."""
    def build():
        from services.matchups import get_team_matchups_service

        xis = ctx.last_xis or {}
        if ctx.t1 not in xis or ctx.t2 not in xis:
            return []
        out = get_team_matchups_service(
            team1=ctx.team1, team2=ctx.team2, start_date=_since(ctx), end_date=ctx.end,
            team1_players=xis[ctx.t1]["players"], team2_players=xis[ctx.t2]["players"], db=ctx.db,
            fmt=ctx.fmt, gender=ctx.gender,
        )
        rows = (out.get("fantasy_analysis") or {}).get("all_fantasy_players") or []
        result = []
        for r in rows:
            side = ctx.t1 if r.get("team") in (ctx.team1, ctx.t1) else ctx.t2 if r.get("team") in (ctx.team2, ctx.t2) else None
            points = float(r.get("expected_points") or 0)
            if side is None or points <= 0:
                continue
            br = r.get("breakdown") or {}
            result.append({"name": r["player_name"], "side": side, "role": r.get("role"),
                           "points": round(points, 1), "batting": round(float(br.get("batting") or 0), 1),
                           "bowling": round(float(br.get("bowling") or 0), 1)})
        return sorted(result, key=lambda p: -p["points"])
    return _memo(ctx, "projections", build)


def _is_ipl(ctx) -> bool:
    return ctx.fmt == "T20" and ctx.gender == "male" and ctx.fixture_competition == "IPL"


def _sample(ctx) -> str:
    return f"Both XIs · records against this attack since {_since(ctx).year}"


def _split(p) -> str:
    """'41 batting · 12 bowling', leaving out a side the player won't score in."""
    parts = [f"{p['batting']:.0f} batting" if p["batting"] >= 1 else None,
             f"{p['bowling']:.0f} bowling" if p["bowling"] >= 1 else None]
    return " · ".join(x for x in parts if x)


_HOW = ("Each player's batting record against the other side's bowlers, and bowling record against its "
        "batters, scaled to a typical match. Batting and bowling points only; fielding isn't projected.")


# --------------------------------------------------------------------------------------------
# F1 and F2
# --------------------------------------------------------------------------------------------

def projected_points(ctx) -> Optional[Card]:
    rows = projections(ctx)[:TOP_N]
    if len(rows) < 4:
        return None
    top = rows[0]
    return Card(
        id="projected-points", chapter="fantasy", visual="player_bars",
        title=f"{top['name']} projects the most points: {top['points']:.0f}",
        help="Projected fantasy points; higher is better",
        sample=_sample(ctx), n=len(rows),
        payload={"rows": [{"name": r["name"], "side": r["side"], "value": round(r["points"]),
                           "detail": _split(r)} for r in rows],
                 "signed": False, "extra": "detail"},
        info=Info(what="The six players projected to score the most fantasy points in this match.",
                  how_to_read=_HOW, definitions=[("Points", "Batting: runs, boundaries, milestones and strike "
                                                            "rate; bowling: wickets, dots and economy.")]),
        relevance=1.5,
    )


def captaincy(ctx) -> Optional[Card]:
    rows = projections(ctx)
    if len(rows) < 2:
        return None
    c, vc = rows[0], rows[1]

    def reason(p):
        return f"{p['points']:.0f} projected points ({_split(p)})"
    return Card(
        id="captaincy", chapter="fantasy", visual="captaincy",
        title=f"{c['name']} for captain, {vc['name']} for vice-captain", help=None,
        sample=_sample(ctx), n=2,
        payload={"picks": [{"role": "Captain", "multiplier": "2×", "name": c["name"], "side": c["side"], "reason": reason(c)},
                           {"role": "Vice-captain", "multiplier": "1.5×", "name": vc["name"], "side": vc["side"],
                            "reason": reason(vc)}]},
        info=Info(what="The two highest projections. A captain's points count double and a vice-captain's 1.5×, "
                       "so the safest picks are the biggest projections.", how_to_read=_HOW),
        relevance=1.4,
    )


# --------------------------------------------------------------------------------------------
# F3 value (IPL only)
# --------------------------------------------------------------------------------------------

def _credit(name: str) -> Optional[float]:
    """The player's IPL credit price, or None when the price file doesn't know the player."""
    from services.fantasy_planner import _resolve_player_price_by_last_name, _resolve_player_price_entry

    entry = _resolve_player_price_entry(name) or _resolve_player_price_by_last_name(name)
    return float(entry["credits"]) if entry and entry.get("credits") else None


def value_picks(ctx) -> Optional[Card]:
    if not _is_ipl(ctx):
        return None
    rows = []
    for p in projections(ctx):
        credit = _credit(p["name"])
        if credit and p["points"] >= VALUE_MIN_POINTS:
            rows.append({"name": p["name"], "side": p["side"], "value": round(p["points"] / credit, 1),
                         "detail": f"{p['points']:.0f} pts · {credit:g} cr"})
    rows = sorted(rows, key=lambda r: -r["value"])[:TOP_N]
    if len(rows) < 4:
        return None
    top = rows[0]
    return Card(
        id="value-picks", chapter="fantasy", visual="player_bars",
        title=f"{top['name']} is the best value: {top['value']:.1f} points per credit",
        help="Projected points per credit; higher is better",
        sample=f"{_sample(ctx)} · IPL prices", n=len(rows),
        payload={"rows": rows, "signed": False, "extra": "detail", "decimals": 1},
        info=Info(what="Projected points divided by each player's IPL fantasy credit price.",
                  how_to_read=_HOW + f" Players projected under {VALUE_MIN_POINTS} points, or with no listed "
                                     "price, are left out."),
        relevance=1.2,
    )


# --------------------------------------------------------------------------------------------
# F4 differentials (IPL only)
# --------------------------------------------------------------------------------------------

def usual_points(ctx, names: List[str]) -> Dict[str, float]:
    """Average batting + bowling fantasy points per IPL match over the last two seasons."""
    from services.competition_aliases import variants_for
    from services.player_aliases import expand_name_group

    out = {}
    for name in names:
        spellings = expand_name_group([name], ctx.db) or [name]
        row = ctx.db.execute(text("""
            WITH appearances AS (
                SELECT b.match_id, COALESCE(b.fantasy_points, 0) AS pts FROM batting_stats b
                WHERE b.striker = ANY(:names)
                UNION ALL
                SELECT w.match_id, COALESCE(w.fantasy_points, 0) FROM bowling_stats w WHERE w.bowler = ANY(:names)
            )
            SELECT COUNT(DISTINCT a.match_id) AS matches, SUM(a.pts) AS pts
            FROM appearances a JOIN matches m ON m.id = a.match_id
            WHERE m.competition = ANY(:comps) AND m.date >= :start AND (CAST(:end AS date) IS NULL OR m.date <= :end)
        """), {"names": spellings, "comps": variants_for("IPL"), "start": _since(ctx), "end": ctx.end}).mappings().first()
        if row and row["matches"] and row["matches"] >= 5:
            out[name] = float(row["pts"] or 0) / row["matches"]
    return out


def _ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def differentials(ctx) -> Optional[Card]:
    """
    Players this match-up lifts up the order. Projections and real hauls sit on different scales
    (projections cap balls faced and skip some bonuses, so they run 10-20 points lower for almost
    everyone), so the comparison is by rank among both XIs: projected rank here against the rank
    of the player's usual IPL haul.
    """
    if not _is_ipl(ctx):
        return None
    proj = projections(ctx)
    usual = _memo(ctx, "usual", lambda: usual_points(ctx, [p["name"] for p in proj]))
    known = [p for p in proj if usual.get(p["name"])]
    if len(known) < 8:
        return None
    n = len(known)
    proj_rank = {p["name"]: i + 1 for i, p in enumerate(sorted(known, key=lambda p: -p["points"]))}
    usual_rank = {name: i + 1 for i, name in enumerate(sorted((p["name"] for p in known), key=lambda x: -usual[x]))}
    rows = []
    for p in known:
        jump = usual_rank[p["name"]] - proj_rank[p["name"]]
        if jump >= 3:
            rows.append({"name": p["name"], "side": p["side"], "value": jump,
                         "detail": f"{_ordinal(proj_rank[p['name']])} here · usually {_ordinal(usual_rank[p['name']])}"})
    rows = sorted(rows, key=lambda r: (-r["value"], r["name"]))[:6]
    if not rows:
        return None
    top = rows[0]
    return Card(
        id="differentials", chapter="fantasy", visual="player_bars",
        title=f"{top['name']} could surprise: projected {_ordinal(proj_rank[top['name']])} of {n} here, "
              f"usually {_ordinal(usual_rank[top['name']])}",
        help="Places climbed: projected rank here against the player's usual rank; higher is a bigger surprise",
        sample=f"{_sample(ctx)} · usual = IPL average since {_since(ctx).year}", n=len(rows),
        payload={"rows": rows, "signed": True, "unit": "", "extra": "detail"},
        info=Info(what="Players this match-up suits far better than their usual IPL outing: the picks rivals are "
                       "less likely to make.",
                  how_to_read=_HOW + f" Ranks are among the {n} players in both XIs with 5+ IPL matches in the "
                                     "last two seasons. Usual = their batting and bowling points per match. "
                                     "Projections run lower than real hauls for everyone, so ranks are compared, "
                                     "not points."),
        relevance=1.1,
    )


FANTASY = (
    CardSpec("projected-points", "fantasy", "Who will score the most fantasy points?", projected_points,
             sample=SampleRule(flag_below=0), scale_by_sample=False),
    CardSpec("captaincy", "fantasy", "Who should be captain and vice-captain?", captaincy,
             sample=SampleRule(flag_below=0), scale_by_sample=False),
    CardSpec("value-picks", "fantasy", "Who's the best value?", value_picks, formats=("T20",),
             sample=SampleRule(flag_below=0), scale_by_sample=False),
    CardSpec("differentials", "fantasy", "Who could surprise?", differentials, formats=("T20",),
             sample=SampleRule(flag_below=0), scale_by_sample=False),
)
