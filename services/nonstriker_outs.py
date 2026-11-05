"""
A batter's dismissals at the non-striker's end, for the query builder's batting rows.

The per-ball definitions (services/metrics/sql_defs.py) give a batter the dismissals on the balls he faced: his own
wickets as striker. A batter run out backing up (or retired out, or obstructing) at the non-striker's end is dismissed
on someone else's ball, so a ball-grouped query never saw it, and every batting average came out high: Virat Kohli's
ODI average read 59.7 against the official 58.8 (12 run-outs, 6 of them as non-striker), 5 Nov 2026.

This counts those dismissals under the same filters and grouping as the main query, keyed on the dismissed player, and
adds them to each row's `wickets` (then `average` and `balls_per_dismissal`). Only where the grouping and the filters
describe the innings, not the ball: a run-out at the other end isn't "against spin" or "on a good length", so a query
filtered or grouped by a ball's line, length, shot, bowler, hand, zone and so on keeps the striker-only count, which is
the right one there (and says so in its metadata).

The dismissed player: `p_out` on delivery_details (set on every non-striker dismissal in both feeds, measured
5 Nov 2026: T20 4,815 of 4,815, ODI 1,752 of 1,754), the canonical non_striker name as the fallback;
`player_dismissed` on the legacy table.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy import text

# Group-bys that describe the match, innings or over rather than the ball, in both tables. A non-striker's dismissal
# belongs to these rows as much as a striker's does.
CONTEXT_DIMS = {
    "batter", "venue", "country", "match_id", "match_date", "competition", "year", "batting_team", "bowling_team",
    "innings", "phase", "over", "format", "gender", "match_outcome", "chase_outcome", "toss_decision",
    "toss_match_outcome",
}
# Group-bys that need the matches join on delivery_details.
_MATCH_DIMS = {"match_outcome", "chase_outcome", "toss_decision", "toss_match_outcome"}
NON_DISMISSALS = ("retired not out (hurt)", "retired hurt", "not out")

#: The dismissed non-striker's name on delivery_details, spelled as the main query spells a batter.
NEW_OUT_NAME = "COALESCE(pi_out.display_name, pa_out.alias_name, dd.non_striker)"
NEW_OUT_JOINS = (
    "LEFT JOIN player_identity pi_out ON pi_out.pid = dd.p_out "
    "LEFT JOIN player_alias_unambiguous pa_out ON pa_out.player_name = dd.non_striker "
)


def applies(group_by: Iterable[str], perspective: str, *, ball_filters: Dict[str, Any], dimension_filters,
            partnership: bool, cumulative: bool) -> bool:
    """Whether the rows are batters' (or batting) rows whose dismissals should include the non-striker's end."""
    from services.metrics import sql_defs

    group_by = list(group_by or [])
    if perspective != sql_defs.BATTER or not group_by or partnership or cumulative or dimension_filters:
        return False
    if any(g not in CONTEXT_DIMS for g in group_by):
        return False
    return not any(v not in (None, [], "", False) for v in ball_filters.values())


def _key(row: Dict[str, Any], group_by: List[str]) -> Tuple[str, ...]:
    return tuple(str(row.get(g)) for g in group_by)


def new_counts(db, where_clause: str, params: Dict[str, Any], group_by: List[str], grouping_columns: Dict[str, str],
               join_matches: bool, out_ids: Optional[List[int]], out_names: Optional[List[str]],
               exclude_names: Optional[List[str]]) -> Dict[Tuple[str, ...], int]:
    """Non-striker dismissals on delivery_details, by the query's groups (the batter is the dismissed player).
    where_clause/params: the main query's WHERE built without its batter filters."""
    p = {k: v for k, v in params.items() if k not in ("limit", "offset", "min_balls", "max_balls", "min_runs",
                                                      "max_runs", "min_wickets", "max_wickets")}
    cols = [NEW_OUT_NAME if g == "batter" else grouping_columns[g] for g in group_by]
    conds = ["LOWER(dd.out) = 'true'", "LOWER(COALESCE(dd.bat_out, '')) = 'false'",
             "LOWER(COALESCE(dd.dismissal, '')) NOT IN :ns_nd"]
    if out_ids or out_names:
        p["ns_ids"] = list(out_ids or [-1])
        p["ns_names"] = list(out_names or ["__none__"])
        conds.append("(dd.p_out = ANY(:ns_ids) OR (dd.p_out IS NULL AND dd.non_striker = ANY(:ns_names)))")
    if exclude_names:
        p["ns_exclude"] = list(exclude_names)
        conds.append(f"{NEW_OUT_NAME} <> ALL(:ns_exclude)")
    where = (where_clause + " AND " if where_clause.strip() else "WHERE ") + " AND ".join(conds)
    join = "JOIN matches m ON m.id = dd.p_match " if (join_matches or set(group_by) & _MATCH_DIMS) else ""
    sql = (f"SELECT {', '.join(f'{c} AS g{i}' for i, c in enumerate(cols))}, COUNT(*) AS n "
           f"FROM delivery_details dd {join}{NEW_OUT_JOINS}{where} "
           f"GROUP BY {', '.join(f'g{i}' for i in range(len(cols)))}")
    from sqlalchemy import bindparam
    rows = db.execute(text(sql).bindparams(bindparam("ns_nd", expanding=True)), {**p, "ns_nd": list(NON_DISMISSALS)}).fetchall()
    return {tuple(str(v) for v in r[:-1]): int(r[-1]) for r in rows}


def legacy_counts(db, where_clause: str, params: Dict[str, Any], group_by: List[str], grouping_columns: Dict[str, str],
                  out_names: Optional[List[str]], exclude_names: Optional[List[str]]) -> Dict[Tuple[str, ...], int]:
    """The same on the legacy table (deliveries): the dismissed player is player_dismissed, a raw name, as the legacy
    rows' batter is (the merge maps both to canonical names)."""
    p = {k: v for k, v in params.items() if k not in ("limit", "offset", "min_balls", "max_balls", "min_runs",
                                                      "max_runs", "min_wickets", "max_wickets")}
    cols = ["d.player_dismissed" if g == "batter" else grouping_columns[g] for g in group_by]
    conds = ["d.player_dismissed IS NOT NULL", "d.player_dismissed <> d.batter",
             "COALESCE(d.wicket_type, '') <> ''", "LOWER(d.wicket_type) NOT IN :ns_nd"]
    if out_names:
        p["ns_names"] = list(out_names)
        conds.append("d.player_dismissed = ANY(:ns_names)")
    if exclude_names:
        p["ns_exclude"] = list(exclude_names)
        conds.append("d.player_dismissed <> ALL(:ns_exclude)")
    where = (where_clause + " AND " if where_clause.strip() else "WHERE ") + " AND ".join(conds)
    sql = (f"SELECT {', '.join(f'{c} AS g{i}' for i, c in enumerate(cols))}, COUNT(*) AS n "
           f"FROM deliveries d JOIN matches m ON d.match_id = m.id LEFT JOIN players p ON p.name = d.bowler {where} "
           f"GROUP BY {', '.join(f'g{i}' for i in range(len(cols)))}")
    from sqlalchemy import bindparam
    rows = db.execute(text(sql).bindparams(bindparam("ns_nd", expanding=True)), {**p, "ns_nd": list(NON_DISMISSALS)}).fetchall()
    return {tuple(str(v) for v in r[:-1]): int(r[-1]) for r in rows}


def add_to_rows(rows: List[Dict[str, Any]], counts: Dict[Tuple[str, ...], int], group_by: List[str]) -> int:
    """Add the counts to the rows' wickets and recompute what depends on them. Returns how many were added. A batter
    run out without facing a ball in the scope has no row to add to (rare: a diamond duck), and is left out."""
    added = 0
    for row in rows:
        n = counts.get(_key(row, group_by))
        if not n:
            continue
        row["wickets"] = (row.get("wickets") or 0) + n
        w = row["wickets"]
        runs, balls = row.get("runs") or 0, row.get("balls") or 0
        row["average"] = round(runs / w, 2) if w > 0 else None
        row["balls_per_dismissal"] = round(balls / w, 2) if w > 0 else None
        added += n
    return added
