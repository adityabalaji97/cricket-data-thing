"""
Shared helpers for analytics endpoints.
"""

from __future__ import annotations

from datetime import date
from typing import Dict, Iterable, List, Optional, Tuple

from utils.league_utils import expand_league_abbreviations


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

