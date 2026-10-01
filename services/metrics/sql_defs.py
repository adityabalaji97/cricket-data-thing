"""Canonical per-ball SQL for balls, runs, wickets and dots, by perspective.

Every live query that aggregates deliveries should take its definitions from here, so a batter's
strike rate or a bowler's economy is the same number on every page. The rules mirror the stored
stats tables (sync_stats_from_dd.py), which are the reference:

* **Batter** -- balls faced exclude wides (a no-ball is a ball faced); runs are off the bat; a
  wicket is the *striker's* dismissal (``out`` and ``bat_out``), so a non-striker run out on this
  batter's ball is not his; a dot is nothing off the bat on a non-wide.
* **Bowler** -- balls exclude wides and no-balls; runs are the ball's total less byes and
  leg-byes (wides and no-balls are the bowler's); wickets are only the dismissals credited to the
  bowler (no run outs, retirements or obstruction); a dot is nothing off the bat on a legal ball.
* **Team** -- what a side's innings scored and lost: legal balls, every run including extras,
  every dismissal (run outs included). Used when rows are not players (phase, venue, year...).

One deliberate difference from the stats tables: "retired not out (hurt)" / "retired hurt" and
the stray "not out" rows carry ``out = 'true'`` in the feed but are not dismissals, so they are
never counted as wickets here. (The sync still counts them for batters -- a separate fix.)

Expressions are per row (wrap them in SUM(CASE ...) / SUM(...)); ``alias`` is the table alias.
"""
from dataclasses import dataclass
from typing import Iterable, Optional

BATTER = "batter"
BOWLER = "bowler"
TEAM = "team"

# Dismissals credited to the bowler, in the spellings both tables use.
BOWLER_WICKET_TYPES = (
    "bowled", "caught", "caught and bowled", "lbw", "leg before wicket", "stumped", "hit wicket",
)
# Rows whose dismissal field is set but on which nobody is out.
NON_DISMISSALS = ("retired not out (hurt)", "retired hurt", "not out")


def _sql_list(values: Iterable[str]) -> str:
    return ", ".join("'" + v.replace("'", "''") + "'" for v in values)


@dataclass(frozen=True)
class BallDefs:
    """Per-row SQL expressions for one perspective on one table."""

    perspective: str
    legal_ball: str  # boolean: the ball counts towards this perspective's balls
    runs: str        # numeric: runs this perspective is credited / charged with on the ball
    wicket: str      # boolean: the ball is a wicket for this perspective
    dot: str         # boolean: a dot ball for this perspective

    # Aggregates, for direct use in a SELECT list.
    @property
    def balls_sum(self) -> str:
        return f"SUM(CASE WHEN {self.legal_ball} THEN 1 ELSE 0 END)"

    @property
    def runs_sum(self) -> str:
        return f"SUM({self.runs})"

    @property
    def wickets_sum(self) -> str:
        return f"SUM(CASE WHEN {self.wicket} THEN 1 ELSE 0 END)"

    @property
    def dots_sum(self) -> str:
        return f"SUM(CASE WHEN {self.dot} THEN 1 ELSE 0 END)"


def perspective_for(group_by: Optional[Iterable[str]], has_batter_filters: bool = False) -> str:
    """Whose numbers a grouped row shows.

    Grouping by batter, or filtering to batters, reads as batting; grouping by bowler (without
    batter) reads as bowling; anything else is a team-level aggregate. Matches the metric sign
    the query builder already uses for Impact/RAA.
    """
    cols = set(group_by or ())
    if "batter" in cols or has_batter_filters:
        return BATTER
    if "bowler" in cols:
        return BOWLER
    return TEAM


def delivery_details_defs(perspective: str, alias: str = "dd") -> BallDefs:
    """Definitions over ``delivery_details`` (out/bat_out are 'true'/'false' varchar)."""
    a = alias
    not_wide = f"COALESCE({a}.wide, 0) = 0"
    legal = f"{not_wide} AND COALESCE({a}.noball, 0) = 0"
    out = f"LOWER({a}.out) = 'true'"
    real_dismissal = f"LOWER(COALESCE({a}.dismissal, '')) NOT IN ({_sql_list(NON_DISMISSALS)})"
    no_bat_runs = f"COALESCE({a}.batruns, 0) = 0"

    if perspective == BATTER:
        return BallDefs(
            perspective,
            legal_ball=not_wide,
            runs=f"COALESCE({a}.batruns, 0)",
            wicket=f"{out} AND LOWER({a}.bat_out) = 'true' AND {real_dismissal}",
            dot=f"{no_bat_runs} AND {not_wide}",
        )
    if perspective == BOWLER:
        return BallDefs(
            perspective,
            legal_ball=legal,
            runs=f"(COALESCE({a}.score, 0) - COALESCE({a}.byes, 0) - COALESCE({a}.legbyes, 0))",
            wicket=f"{out} AND LOWER({a}.dismissal) IN ({_sql_list(BOWLER_WICKET_TYPES)})",
            dot=f"{no_bat_runs} AND {legal}",
        )
    if perspective == TEAM:
        return BallDefs(
            perspective,
            legal_ball=legal,
            runs=f"COALESCE({a}.score, 0)",
            wicket=f"{out} AND {real_dismissal}",
            dot=f"{no_bat_runs} AND {legal}",
        )
    raise ValueError(f"unknown perspective {perspective!r}")


def legacy_defs(perspective: str, alias: str = "d") -> BallDefs:
    """Definitions over the legacy ``deliveries`` table (cricsheet-style columns)."""
    a = alias
    not_wide = f"COALESCE({a}.wides, 0) = 0"
    legal = f"{not_wide} AND COALESCE({a}.noballs, 0) = 0"
    wicket_type = f"LOWER(COALESCE({a}.wicket_type, ''))"
    real_dismissal = f"{wicket_type} <> '' AND {wicket_type} NOT IN ({_sql_list(NON_DISMISSALS)})"
    no_bat_runs = f"COALESCE({a}.runs_off_bat, 0) = 0"

    if perspective == BATTER:
        return BallDefs(
            perspective,
            legal_ball=not_wide,
            runs=f"COALESCE({a}.runs_off_bat, 0)",
            wicket=f"{real_dismissal} AND {a}.player_dismissed = {a}.batter",
            dot=f"{no_bat_runs} AND {not_wide}",
        )
    if perspective == BOWLER:
        return BallDefs(
            perspective,
            legal_ball=legal,
            # extras = wides + noballs + byes + legbyes + penalty; only the first two are the bowler's.
            runs=f"(COALESCE({a}.runs_off_bat, 0) + COALESCE({a}.wides, 0) + COALESCE({a}.noballs, 0))",
            wicket=f"{wicket_type} IN ({_sql_list(BOWLER_WICKET_TYPES)})",
            dot=f"{no_bat_runs} AND {legal}",
        )
    if perspective == TEAM:
        return BallDefs(
            perspective,
            legal_ball=legal,
            runs=f"(COALESCE({a}.runs_off_bat, 0) + COALESCE({a}.extras, 0))",
            wicket=real_dismissal,
            dot=f"{no_bat_runs} AND {legal}",
        )
    raise ValueError(f"unknown perspective {perspective!r}")
