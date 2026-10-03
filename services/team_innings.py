"""
Query-builder mode `team_innings`: one record per team innings (total, wickets, run rate, runs by
phase, result), aggregated by the requested group_by.

"How often do teams pass 200 in the IPL, by season?" is one query:

    query_mode=team_innings, leagues=IPL, group_by=season  -> pct_200_plus per season

and group_by=['match_id', 'innings'] lists the innings themselves.

Built from delivery_details (2015+ for men's T20; every other format complete). Team totals count
every run, extras included. Innings 3+ (super overs) are left out for limited-overs formats.
`full_length` is 1 when the innings was scheduled for the format's full allocation (120 balls in
a T20): use dimension_filters=['full_length:eq:1'] to drop rain-reduced innings from rate
questions.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict

from fastapi import HTTPException
from sqlalchemy import text

from format_config import get_format
from services.analytics_common import phase_bounds, phase_case_sql
from services.competition_aliases import canonical_sql as competition_canonical_sql
from services.metrics import sql_defs
from services import query_dimensions

TOTAL_THRESHOLDS = (160, 180, 200, 220, 250)

#: group_by columns this mode accepts, with their expression over the per-innings CTE `i`.
GROUP_BY = {
    "match_id": "i.match_id", "innings": "i.innings", "competition": "i.competition", "year": "i.year",
    "season": "i.season", "impact_player_era": "i.impact_player_era", "venue": "i.venue",
    "country": "i.country", "batting_team": "i.batting_team", "bowling_team": "i.bowling_team",
    "match_outcome": "i.result", "toss_decision": "i.toss_decision", "format": "i.format",
    "full_length": "i.full_length", "total_bucket": "i.total_bucket",
    "batted_after_winning_toss": "i.batted_after_winning_toss",
}

#: dimension_filters this mode accepts: name -> (expression, numeric).
FILTERS = {
    "total": ("i.total", True), "wickets": ("i.wickets", True), "balls": ("i.balls", True),
    "full_length": ("i.full_length", True), "year": ("i.year", True), "season": ("i.season", False),
    "impact_player_era": ("i.impact_player_era", False), "match_outcome": ("i.result", False),
    "total_bucket": ("i.total_bucket", False), "country": ("i.country", False), "venue": ("i.venue", False),
    "innings": ("i.innings", True),
}

_TOTAL_BUCKETS = (("<140", 139), ("140-159", 159), ("160-179", 179), ("180-199", 199), ("200-219", 219),
                  ("220-249", 249))


_COUNT_COLUMNS = {"runs", "balls", "innings_count", "matches", "highest_total", "lowest_total", "wins", "losses",
                  *(f"count_{t}_plus" for t in TOTAL_THRESHOLDS)}


def _total_bucket_sql(expr: str) -> str:
    whens = " ".join(f"WHEN {expr} <= {hi} THEN '{label}'" for label, hi in _TOTAL_BUCKETS)
    return f"(CASE {whens} ELSE '250+' END)"


def query_team_innings(
    db, *, venue, start_date, end_date, leagues, teams, batting_teams, bowling_teams, innings,
    match_outcome, is_chase, toss_decision, day_or_night, group_by, include_international, top_teams,
    fmt, gender, match_ids, dimension_filters, limit, offset, ball_level: Dict[str, Any],
) -> Dict[str, Any]:
    from services.query_builder_v2 import (
        QueryValidationError, build_where_clause, get_match_outcome_sql,
    )

    used = sorted(k for k, v in (ball_level or {}).items() if v not in (None, [], "", False))
    if used:
        raise QueryValidationError(
            f"query_mode=team_innings aggregates whole innings, so ball-level filters do not apply: {used}. "
            "Use query_mode=delivery for those.")
    if not group_by:
        raise QueryValidationError("query_mode=team_innings needs a group_by, e.g. ['season'] or ['match_id', 'innings'].")
    bad = [g for g in group_by if g not in GROUP_BY]
    if bad:
        raise QueryValidationError(f"group_by {bad} is not available for team_innings. Use: {', '.join(GROUP_BY)}.")
    try:
        filters = query_dimensions.parse_filters(dimension_filters, list(FILTERS))
    except query_dimensions.DimensionFilterError as exc:
        raise QueryValidationError(str(exc))

    pin_fmt = "T20" if fmt == "ALL" else fmt
    spec = get_format(pin_fmt, gender)
    where, params = build_where_clause(
        venue=venue, start_date=start_date, end_date=end_date, leagues=leagues, teams=teams,
        batting_teams=batting_teams, bowling_teams=bowling_teams, players=[], batters=[], bowlers=[],
        bat_hand=None, bowl_style=[], bowl_kind=[], crease_combo=[], line=[], length=[], shot=[],
        control=None, wagon_zone=[], dismissal=[], innings=innings, over_min=None, over_max=None,
        match_outcome=match_outcome, is_chase=is_chase, chase_outcome=[], toss_decision=toss_decision,
        include_international=include_international, top_teams=top_teams, group_by=[], base_params={},
        db=db, day_or_night=day_or_night, fmt=fmt, gender=gender, match_ids=match_ids,
    )
    if spec.balls_per_innings:
        where += " AND dd.inns <= 2"

    team = sql_defs.delivery_details_defs(sql_defs.TEAM, "dd")
    phase_expr = phase_case_sql(pin_fmt, gender, over_column="dd.over")
    phases = [p.key for p in phase_bounds(pin_fmt, gender)]
    result_sql = get_match_outcome_sql("dd.team_bat", "dd.team_bowl", "m.winner", "m.outcome")
    phase_cols = []
    for key in phases:
        phase_cols.append(f"SUM(CASE WHEN {phase_expr} = '{key}' THEN {team.runs} ELSE 0 END) AS {key}_runs")
        phase_cols.append(f"SUM(CASE WHEN {phase_expr} = '{key}' AND {team.legal_ball} THEN 1 ELSE 0 END) AS {key}_balls")
    full_balls = spec.balls_per_innings or 0

    filter_conditions = []
    for i, (name, op, values) in enumerate(filters):
        expr, numeric = FILTERS[name]
        dim = query_dimensions.Dimension(expr, None, numeric)
        filter_conditions += query_dimensions.filter_sql([(name, op, values)], {name: dim}, params, prefix=f"tif{i}")
    filter_where = ("WHERE " + " AND ".join(filter_conditions)) if filter_conditions else ""

    group_exprs = [GROUP_BY[g] for g in group_by]
    select_groups = ", ".join(f"{e} AS {g}" for g, e in zip(group_by, group_exprs))
    group_clause = ", ".join(group_exprs)
    pct_cols = ",\n".join(
        f"ROUND(100.0 * AVG(CASE WHEN i.total >= {t} THEN 1 ELSE 0 END), 2) AS pct_{t}_plus,\n"
        f"SUM(CASE WHEN i.total >= {t} THEN 1 ELSE 0 END) AS count_{t}_plus"
        for t in TOTAL_THRESHOLDS
    )
    phase_rr = ",\n".join(
        f"ROUND(SUM(i.{k}_runs) * 6.0 / NULLIF(SUM(i.{k}_balls), 0), 2) AS {k}_run_rate" for k in phases
    )
    params.update({"limit": int(limit), "offset": int(offset)})

    sql = f"""
        WITH innings_rows AS (
            SELECT dd.p_match AS match_id, dd.inns AS innings,
                   MIN(dd.match_date) AS match_date, MIN(dd.year) AS year,
                   MIN({competition_canonical_sql('dd.competition')}) AS competition,
                   MIN(dd.ground) AS venue, MIN(dd.country) AS country,
                   MIN(dd.team_bat) AS batting_team, MIN(dd.team_bowl) AS bowling_team, MIN(dd.format) AS format,
                   {team.runs_sum} AS total, {team.wickets_sum} AS wickets, {team.balls_sum} AS balls,
                   SUM(CASE WHEN dd.batruns IN (4, 6) THEN 1 ELSE 0 END) AS boundaries,
                   {team.dots_sum} AS dots,
                   MAX(dd.max_balls) AS max_balls,
                   MIN({result_sql}) AS result,
                   MIN(LOWER(COALESCE(m.toss_decision, ''))) AS toss_decision,
                   -- 1 when the batting side won the toss, 0 when it lost it, NULL if unknown.
                   MIN(CASE WHEN COALESCE(m.toss_winner, '') = '' THEN NULL
                            WHEN LOWER(m.toss_winner) = LOWER(dd.team_bat) THEN 1 ELSE 0 END) AS batted_after_winning_toss,
                   -- 1 when the toss winner won the match, 0 when it lost; NULL for ties / no result.
                   MIN(CASE WHEN COALESCE(m.toss_winner, '') = '' OR COALESCE(m.winner, '') = '' THEN NULL
                            WHEN LOWER(m.toss_winner) = LOWER(m.winner) THEN 1 ELSE 0 END) AS toss_winner_won,
                   {', '.join(phase_cols)}
            FROM delivery_details dd
            LEFT JOIN matches m ON m.id = dd.p_match
            {where}
            GROUP BY dd.p_match, dd.inns
        ),
        i AS (
            SELECT r.*,
                   {query_dimensions.season_sql('r.competition', 'r.match_date', 'r.year')} AS season,
                   (CASE WHEN r.year >= 2023 THEN '2023+' ELSE 'pre-2023' END) AS impact_player_era,
                   (CASE WHEN {full_balls} > 0 AND COALESCE(r.max_balls, 0) >= {full_balls} THEN 1 ELSE 0 END) AS full_length,
                   {_total_bucket_sql('r.total')} AS total_bucket
            FROM innings_rows r
        ),
        grouped AS (
            SELECT {select_groups},
                   COUNT(*) AS innings_count,
                   COUNT(DISTINCT i.match_id) AS matches,
                   ROUND(AVG(i.total), 2) AS avg_total,
                   MAX(i.total) AS highest_total,
                   MIN(i.total) AS lowest_total,
                   ROUND(AVG(i.wickets), 2) AS avg_wickets,
                   SUM(i.total) AS runs,
                   SUM(i.balls) AS balls,
                   ROUND(SUM(i.total) * 6.0 / NULLIF(SUM(i.balls), 0), 2) AS run_rate,
                   {phase_rr},
                   ROUND(100.0 * SUM(i.boundaries) / NULLIF(SUM(i.balls), 0), 2) AS boundary_percentage,
                   ROUND(100.0 * SUM(i.dots) / NULLIF(SUM(i.balls), 0), 2) AS dot_percentage,
                   {pct_cols},
                   SUM(CASE WHEN i.result = 'win' THEN 1 ELSE 0 END) AS wins,
                   SUM(CASE WHEN i.result = 'loss' THEN 1 ELSE 0 END) AS losses,
                   ROUND(100.0 * SUM(CASE WHEN i.result = 'win' THEN 1 ELSE 0 END)
                         / NULLIF(SUM(CASE WHEN i.result IN ('win', 'loss') THEN 1 ELSE 0 END), 0), 2) AS win_percentage,
                   ROUND(100.0 * AVG(i.toss_winner_won), 2) AS toss_winner_win_percentage,
                   ROUND(100.0 * AVG(i.batted_after_winning_toss), 2) AS pct_batting_side_won_toss
            FROM i
            {filter_where}
            GROUP BY {group_clause}
        )
        SELECT g.*, COUNT(*) OVER () AS total_groups, SUM(g.innings_count) OVER () AS total_innings
        FROM grouped g
        ORDER BY g.innings_count DESC, {', '.join(f'g.{c}' for c in group_by)}
        LIMIT :limit OFFSET :offset
    """
    rows = [dict(r) for r in db.execute(text(sql), params).mappings().all()]
    total_groups = int(rows[0].pop("total_groups")) if rows else 0
    total_innings = int(rows[0].get("total_innings") or 0) if rows else 0
    for r in rows:
        r.pop("total_groups", None)
        r.pop("total_innings", None)
        for k, v in list(r.items()):
            if isinstance(v, Decimal):
                r[k] = int(v) if v == v.to_integral_value() and k in _COUNT_COLUMNS else float(v)
    warnings = []
    if (fmt in ("T20", "ALL")) and gender == "male" and (start_date is None or start_date.year < 2015):
        warnings.append("team_innings reads ball-by-ball data from 2015 onward for men's T20; earlier seasons are not included.")
    return {
        "data": rows,
        "summary_data": None,
        "percentages": None,
        "metadata": {
            "total_groups": total_groups,
            "total_innings_in_query": total_innings,
            "returned_groups": len(rows),
            "limit": limit,
            "offset": offset,
            "has_more": total_groups > offset + len(rows),
            "grouped_by": group_by,
            "query_mode_used": "team_innings",
            "data_sources": ["delivery_details"],
            "warnings": warnings,
            "phases": phases,
            "note": "One record per team innings (extras included in totals), aggregated by group_by.",
        },
    }
