"""
Match-context dimensions for the query builder: computed per ball, usable as group_by columns and
as `dimension_filters` ('name:op:value').

    bowler_over_number             that bowler's 1st, 2nd, 3rd... over in the innings
    bowler_entry_over              the over (0-indexed, like `over`) in which the bowler first bowled
    spell_number                   1, 2, ...: a new spell starts when two of the bowler's consecutive
                                   overs are not exactly two apart
    bowler_first_over_runs(_bucket) runs the bowler conceded in his first over of the innings
    prev_over_runs(_bucket)        runs (all of them, extras included) off the previous over of the
                                   innings -- bowled from the other end
    prev_over_raa(_bucket)         the previous over's RAA from the batting side (+ = the batters did
                                   better than average for the game state), men's T20 only
    batter_balls_faced(_bucket)    balls the batter faced in that innings (wides excluded)
    impact_player_era              'pre-2023' / '2023+' (the IPL's Impact Player rule began in 2023)
    season                         the year, or 'YYYY/YY' for leagues whose season straddles New Year

Each comes from a CTE over every ball of the matches the query touches (scope_matches), not just
the filtered balls: a bowler's over number or the previous over must count overs the filters drop.
All are delivery_details only (2015+ for men's T20), like line/length.

Bucket labels are ASCII so they survive URLs: '0-6', '7-9', '10+'.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from services.metrics import sql_defs


class DimensionFilterError(ValueError):
    pass


# Competitions whose season runs across New Year (canonical names): a January match belongs to
# the season that began the previous July or later, labelled 'YYYY/YY'.
CROSS_YEAR_COMPETITIONS = ("BBL", "Super Smash", "ILT20", "SA20", "BPL")

RUNS_BUCKETS = (("0-6", None, 6), ("7-9", 7, 9), ("10+", 10, None))
RAA_BUCKETS = (("below -2", None, -2), ("-2 to +2", -2, 2), ("above +2", 2, None))
BALLS_FACED_BUCKETS = (("1-9", None, 9), ("10-19", 10, 19), ("20-29", 20, 29), ("30-39", 30, 39),
                       ("40-49", 40, 49), ("50+", 50, None))


def _int_bucket_sql(expr: str, buckets: Sequence[Tuple[str, Optional[int], Optional[int]]]) -> str:
    whens = []
    for label, _lo, hi in buckets[:-1]:
        whens.append(f"WHEN {expr} <= {hi} THEN '{label}'")
    return f"(CASE WHEN {expr} IS NULL THEN NULL {' '.join(whens)} ELSE '{buckets[-1][0]}' END)"


def _float_bucket_sql(expr: str) -> str:
    # RAA is continuous: strictly below -2, strictly above +2, the rest in the middle.
    return (f"(CASE WHEN {expr} IS NULL THEN NULL WHEN {expr} < -2 THEN 'below -2' "
            f"WHEN {expr} > 2 THEN 'above +2' ELSE '-2 to +2' END)")


def season_sql(competition_expr: str, date_expr: str = "dd.match_date", year_expr: str = "dd.year") -> str:
    """'2024' for most leagues; '2024/25' for a cross-year league's season (match_date is ISO text)."""
    comps = ", ".join(f"'{c}'" for c in CROSS_YEAR_COMPETITIONS)
    month = f"CAST(SUBSTRING({date_expr} FROM 6 FOR 2) AS integer)"
    start = f"(CASE WHEN {month} >= 7 THEN {year_expr} ELSE {year_expr} - 1 END)"
    return (f"(CASE WHEN {competition_expr} IN ({comps}) THEN "
            f"{start}::text || '/' || LPAD(((({start}) + 1) % 100)::text, 2, '0') "
            f"ELSE {year_expr}::text END)")


ERA_SQL = "(CASE WHEN dd.year >= 2023 THEN '2023+' ELSE 'pre-2023' END)"


@dataclass(frozen=True)
class Dimension:
    expr: str                     # group-by expression
    needs: Optional[str]          # CTE family: 'bowler_ctx' | 'prev_over' | 'batter_inns' | None
    numeric: bool                 # filter values are numbers
    filter_expr: Optional[str] = None  # filter on this instead of expr (e.g. unrounded RAA)
    order: Tuple[str, ...] = ()   # natural order of bucket labels


def dimensions(competition_expr: str) -> Dict[str, Dimension]:
    """The dimension table; season needs the query's canonical competition expression."""
    return {
        "bowler_over_number": Dimension("bo.bowler_over_number", "bowler_ctx", True),
        "bowler_entry_over": Dimension("bo.bowler_entry_over", "bowler_ctx", True),
        "spell_number": Dimension("bo.spell_number", "bowler_ctx", True),
        "bowler_first_over_runs": Dimension("bo.first_over_runs", "bowler_ctx", True),
        "bowler_first_over_runs_bucket": Dimension(
            _int_bucket_sql("bo.first_over_runs", RUNS_BUCKETS), "bowler_ctx", False,
            order=tuple(b[0] for b in RUNS_BUCKETS)),
        "prev_over_runs": Dimension("po.runs", "prev_over", True),
        "prev_over_runs_bucket": Dimension(
            _int_bucket_sql("po.runs", RUNS_BUCKETS), "prev_over", False, order=tuple(b[0] for b in RUNS_BUCKETS)),
        # Grouped as whole runs (a raw float would make one group per over); filtered unrounded.
        "prev_over_raa": Dimension("ROUND(po.raa::numeric)::int", "prev_over", True, filter_expr="po.raa"),
        "prev_over_raa_bucket": Dimension(_float_bucket_sql("po.raa"), "prev_over", False,
                                          order=tuple(b[0] for b in RAA_BUCKETS)),
        "batter_balls_faced": Dimension("bi.balls_faced", "batter_inns", True),
        "batter_balls_faced_bucket": Dimension(
            _int_bucket_sql("bi.balls_faced", BALLS_FACED_BUCKETS), "batter_inns", False,
            order=tuple(b[0] for b in BALLS_FACED_BUCKETS)),
        "impact_player_era": Dimension(ERA_SQL, None, False, order=("pre-2023", "2023+")),
        "season": Dimension(season_sql(competition_expr), None, False),
    }


#: Names, in a stable order, for GROUP_BY_COLUMNS and the connector's enum.
DIMENSION_NAMES = (
    "bowler_over_number", "bowler_entry_over", "spell_number", "bowler_first_over_runs",
    "bowler_first_over_runs_bucket", "prev_over_runs", "prev_over_runs_bucket", "prev_over_raa",
    "prev_over_raa_bucket", "batter_balls_faced", "batter_balls_faced_bucket", "impact_player_era", "season",
)


# ----------------------------------------------------------------------------------------------
# dimension_filters: 'name:op:value'
# ----------------------------------------------------------------------------------------------

_OPS = {"eq": "=", "ne": "<>", "gt": ">", "gte": ">=", "lt": "<", "lte": "<=", "in": "IN"}
_FILTER = re.compile(r"^\s*([a-z_]+)\s*:\s*(eq|ne|gt|gte|lt|lte|in)\s*:\s*(.+?)\s*$")


def parse_filters(raw: Optional[Sequence[str]], allowed: Sequence[str]) -> List[Tuple[str, str, List[str]]]:
    """'bowler_over_number:gte:2', 'prev_over_runs_bucket:in:7-9|10+' -> (name, op, [values])."""
    out = []
    for item in raw or []:
        match = _FILTER.match(str(item))
        if not match:
            raise DimensionFilterError(
                f"Bad dimension filter {item!r}: use 'name:op:value' with op eq/ne/gt/gte/lt/lte/in "
                "(values for 'in' separated by '|').")
        name, op, value = match.groups()
        if name not in allowed:
            raise DimensionFilterError(f"Unknown dimension {name!r} in {item!r}. Known: {', '.join(allowed)}.")
        values = [v.strip() for v in value.split("|")] if op == "in" else [value.strip()]
        out.append((name, op, values))
    return out


def filter_sql(filters, dims: Dict[str, Dimension], params: Dict, prefix: str = "dimf") -> List[str]:
    """SQL predicates for parsed filters, binding values into params."""
    conditions = []
    for i, (name, op, values) in enumerate(filters):
        dim = dims[name]
        expr = dim.filter_expr or dim.expr
        cast = []
        for v in values:
            if dim.numeric:
                try:
                    cast.append(float(v) if "." in v else int(v))
                except ValueError:
                    raise DimensionFilterError(f"{name} takes numbers, got {v!r}.")
            else:
                cast.append(v)
        key = f"{prefix}_{i}"
        if op == "in":
            params[key] = cast
            conditions.append(f"{expr} = ANY(:{key})")
        else:
            params[key] = cast[0]
            conditions.append(f"{expr} {_OPS[op]} :{key}")
    return conditions


def needed_families(names: Sequence[str], dims: Dict[str, Dimension]) -> List[str]:
    fams = []
    for n in names:
        d = dims.get(n)
        if d and d.needs and d.needs not in fams:
            fams.append(d.needs)
    return fams


def build_ctes(families: Sequence[str], scope_from_where: str, metrics_enabled: bool) -> Tuple[List[str], List[str]]:
    """CTEs and joins for the requested families. scope_from_where = 'FROM delivery_details dd ... WHERE ...'."""
    if not families:
        return [], []
    bowler_runs = sql_defs.delivery_details_defs(sql_defs.BOWLER, "d").runs
    ctes = [f"scope_matches AS MATERIALIZED (SELECT DISTINCT dd.p_match {scope_from_where})"]
    joins = []
    in_scope = "d.p_match IN (SELECT p_match FROM scope_matches)"
    if "bowler_ctx" in families:
        ctes.append(f"""bowler_over_runs AS (
            SELECT d.p_match, d.inns, d.bowl, d.over, SUM({bowler_runs}) AS runs
            FROM delivery_details d
            WHERE {in_scope}
            GROUP BY d.p_match, d.inns, d.bowl, d.over
        )""")
        ctes.append("""bowler_over_ctx AS (
            SELECT p_match, inns, bowl, over,
                   ROW_NUMBER() OVER w AS bowler_over_number,
                   MIN(over) OVER (PARTITION BY p_match, inns, bowl) AS bowler_entry_over,
                   SUM(new_spell) OVER (w ROWS UNBOUNDED PRECEDING) AS spell_number,
                   FIRST_VALUE(runs) OVER w AS first_over_runs
            FROM (
                SELECT r.*,
                       CASE WHEN LAG(over) OVER (PARTITION BY p_match, inns, bowl ORDER BY over) IS NULL
                              OR over - LAG(over) OVER (PARTITION BY p_match, inns, bowl ORDER BY over) <> 2
                            THEN 1 ELSE 0 END AS new_spell
                FROM bowler_over_runs r
            ) marked
            WINDOW w AS (PARTITION BY p_match, inns, bowl ORDER BY over)
        )""")
        joins.append("LEFT JOIN bowler_over_ctx bo ON bo.p_match = dd.p_match AND bo.inns = dd.inns "
                     "AND bo.bowl = dd.bowl AND bo.over = dd.over")
    if "prev_over" in families:
        raa = ("SUM(CASE WHEN COALESCE(d.wide, 0) = 0 THEN pbm.raa::double precision END)"
               if metrics_enabled else "NULL::double precision")
        metrics_join = "LEFT JOIN ball_metrics pbm ON pbm.delivery_id = d.id" if metrics_enabled else ""
        ctes.append(f"""innings_over AS (
            SELECT d.p_match, d.inns, d.over, SUM(COALESCE(d.score, 0)) AS runs, {raa} AS raa
            FROM delivery_details d
            {metrics_join}
            WHERE {in_scope}
            GROUP BY d.p_match, d.inns, d.over
        )""")
        joins.append("LEFT JOIN innings_over po ON po.p_match = dd.p_match AND po.inns = dd.inns "
                     "AND po.over = dd.over - 1")
    if "batter_inns" in families:
        ctes.append(f"""batter_inns AS (
            SELECT d.p_match, d.inns, d.bat,
                   SUM(CASE WHEN COALESCE(d.wide, 0) = 0 THEN 1 ELSE 0 END) AS balls_faced
            FROM delivery_details d
            WHERE {in_scope}
            GROUP BY d.p_match, d.inns, d.bat
        )""")
        joins.append("LEFT JOIN batter_inns bi ON bi.p_match = dd.p_match AND bi.inns = dd.inns AND bi.bat = dd.bat")
    return ctes, joins
