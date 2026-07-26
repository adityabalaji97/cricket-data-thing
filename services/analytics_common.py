"""
Shared helpers for analytics endpoints.
"""

from __future__ import annotations

from datetime import date
from typing import Dict, Iterable, List, Optional, Tuple

from format_config import FormatSpec, Phase, get_format
from utils.league_utils import expand_league_abbreviations


# =========================================================================================
# Format-aware helpers
# =========================================================================================
# The 6/15 over phase split used to be inline SQL in ~200 places. These helpers generate the
# same SQL from format_config, so a call site can be migrated without changing its output.
# Migrating a T20 call site must be a no-op -- the regression goldens enforce that.


#: Sentinel meaning "do not pin to a single format" -- a deliberate cross-format query, as
#: opposed to the accidental format leakage the pin exists to prevent.
ALL_FORMATS = "ALL"


def phase_bounds(
    fmt: Optional[str] = None,
    gender: Optional[str] = None,
    *,
    n_phases: int = 3,
) -> Tuple[Phase, ...]:
    """The ordered phases for a format: 3-way (default) or the finer 4-way preview split."""
    # Phase boundaries are format-specific, so a cross-format query has to pick one; T20 is
    # the sensible default since it is the dominant data set.
    if (fmt or "").upper() == ALL_FORMATS:
        fmt, gender = "T20", gender if gender and gender != ALL_FORMATS else "male"

    spec = get_format(fmt, gender)
    if n_phases == 3:
        return spec.phases
    if n_phases == 4:
        return spec.phases_4
    raise ValueError(f"n_phases must be 3 or 4, got {n_phases}")


def phase_case_sql(
    fmt: Optional[str] = None,
    gender: Optional[str] = None,
    *,
    over_column: str = "over",
    n_phases: int = 3,
) -> str:
    """Build the CASE expression that maps an over number to a phase key.

    ``over_column`` is the fully-qualified column, e.g. ``d.over`` or ``dd.over``.

    For men's T20 with the defaults this returns exactly the literal that was previously
    inlined in services/query_builder_v2.py, character for character:

        CASE WHEN d.over < 6 THEN 'powerplay' WHEN d.over < 15 THEN 'middle' ELSE 'death' END
    """
    phases = phase_bounds(fmt, gender, n_phases=n_phases)

    clauses = []
    for phase in phases[:-1]:
        # Phases are inclusive bounds, so the exclusive cut-off is end_over + 1.
        clauses.append(f"WHEN {over_column} < {phase.end_over + 1} THEN '{phase.key}'")

    return f"CASE {' '.join(clauses)} ELSE '{phases[-1].key}' END"


def table_routing(
    fmt: Optional[str] = None,
    gender: Optional[str] = None,
    *,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict[str, bool]:
    """Decide which ball-by-ball table(s) a query needs.

    The legacy `deliveries` table holds men's T20 only, from before 2015. Every other
    format lives entirely in `delivery_details` regardless of date -- which matters because
    ODI data goes back to 2005, and the old date-only check would have routed those matches
    to a table that has never contained them.

    Returns ``{"legacy": bool, "details": bool}``.
    """
    if (fmt or "").upper() == ALL_FORMATS:
        # Cross-format: delivery_details holds every format, and the legacy table adds the
        # pre-2015 men's T20 tail, so both are in play.
        return {"legacy": True, "details": True}

    spec = get_format(fmt, gender)
    cutoff = spec.legacy_table_before

    if cutoff is None:
        return {"legacy": False, "details": True}

    # Legacy data is only relevant if the requested window reaches back before the cutoff.
    needs_legacy = start_date is None or start_date < cutoff
    # delivery_details is needed unless the window ends entirely before the cutoff.
    needs_details = end_date is None or end_date >= cutoff

    # A window with no dates at all spans everything, so both are needed.
    return {"legacy": needs_legacy, "details": needs_details or not needs_legacy}


def format_filter_sql(
    alias: str,
    fmt: Optional[str] = None,
    gender: Optional[str] = None,
    *,
    params: Optional[Dict] = None,
) -> str:
    """WHERE fragment pinning a query to one format, for tables carrying format/gender.

    Pass ``params`` to bind values; otherwise the values are inlined (they come from a
    closed, validated set, so there is no injection surface either way).

    ``fmt=ALL_FORMATS`` returns a no-op predicate so a caller can query across formats on
    purpose -- comparing a batter's T20 and ODI records, say. Callers must opt in explicitly;
    the default remains a single pinned format.
    """
    if (fmt or "").upper() == ALL_FORMATS:
        return "1=1"

    spec = get_format(fmt, gender)
    if params is None:
        return f"{alias}.format = '{spec.format}' AND {alias}.gender = '{spec.gender}'"

    params["_format"] = spec.format
    params["_gender"] = spec.gender
    return f"{alias}.format = :_format AND {alias}.gender = :_gender"


def normalize_leagues(leagues: Optional[List[str]]) -> List[str]:
    """Expand user-provided league abbreviations to canonical competition names."""
    return expand_league_abbreviations(leagues or []) if leagues else []


def build_matches_filter_sql(
    *,
    alias: str,
    start_date: Optional[date],
    end_date: Optional[date],
    leagues: Optional[List[str]],
    include_international: bool,
    venue: Optional[str],
    params: Dict,
) -> str:
    """
    Build WHERE-clause fragments for queries that join against `matches`.

    Defaults:
    - No league filter + include_international=False => all league matches.
    - include_international=True adds internationals on top of leagues.
    """
    clauses: List[str] = []

    if start_date:
        clauses.append(f"{alias}.date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        clauses.append(f"{alias}.date <= :end_date")
        params["end_date"] = end_date
    if venue and venue != "All Venues":
        clauses.append(f"{alias}.venue = :venue")
        params["venue"] = venue

    competition_conditions: List[str] = []
    expanded = normalize_leagues(leagues)
    if expanded:
        competition_conditions.append(
            f"({alias}.match_type = 'league' AND {alias}.competition = ANY(:leagues))"
        )
        params["leagues"] = expanded
    else:
        competition_conditions.append(f"{alias}.match_type = 'league'")

    if include_international:
        competition_conditions.append(f"{alias}.match_type = 'international'")

    clauses.append("(" + " OR ".join(competition_conditions) + ")")
    return "".join(f" AND {clause}" for clause in clauses)


def overs_float_to_balls(overs: Optional[float]) -> int:
    """Convert cricket overs notation (e.g. 3.4) to balls."""
    if overs is None:
        return 0
    whole = int(overs)
    frac = int(round((float(overs) - whole) * 10))
    return whole * 6 + frac


def balls_to_overs(balls: int) -> str:
    """Convert balls to x.y overs notation string."""
    if balls <= 0:
        return "0.0"
    whole = balls // 6
    rem = balls % 6
    return f"{whole}.{rem}"


def mean(values: Iterable[Optional[float]]) -> Optional[float]:
    nums = [float(v) for v in values if v is not None]
    if not nums:
        return None
    return sum(nums) / len(nums)


def safe_rate(numerator: float, denominator: float, scale: float = 1.0) -> Optional[float]:
    if denominator <= 0:
        return None
    return (numerator * scale) / denominator


def percentile_rank(
    value: Optional[float],
    values: Iterable[Optional[float]],
    *,
    higher_is_better: bool = True,
) -> Optional[float]:
    """
    Mid-rank percentile in [0, 100].
    """
    if value is None:
        return None

    clean = sorted(float(v) for v in values if v is not None)
    if not clean:
        return None

    if higher_is_better:
        less = sum(v < value for v in clean)
        equal = sum(v == value for v in clean)
    else:
        less = sum(v > value for v in clean)
        equal = sum(v == value for v in clean)

    return round(((less + 0.5 * equal) / len(clean)) * 100.0, 1)


def rolling_mean(values: List[Optional[float]], window: int) -> List[Optional[float]]:
    """
    Rolling average over the trailing `window` observations (inclusive).
    """
    if window <= 0:
        raise ValueError("window must be > 0")

    out: List[Optional[float]] = []
    for idx in range(len(values)):
        chunk = [v for v in values[max(0, idx - window + 1) : idx + 1] if v is not None]
        out.append((sum(chunk) / len(chunk)) if chunk else None)
    return out


def split_spells_by_gap(overs: List[int], gap_threshold: int = 2) -> List[List[int]]:
    """
    Split sorted overs into spells where a new spell starts if gap > threshold.
    """
    if not overs:
        return []
    ordered = sorted(int(o) for o in overs)
    spells: List[List[int]] = [[ordered[0]]]
    for over in ordered[1:]:
        if over - spells[-1][-1] > gap_threshold:
            spells.append([over])
        else:
            spells[-1].append(over)
    return spells

