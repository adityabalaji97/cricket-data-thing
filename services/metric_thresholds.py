"""Thresholds on computed metrics for grouped query-builder results ("50+ average, 100+ SR").

The query builder already filters groups on counts (min/max balls, runs, wickets). This adds
filters on the rate metrics it reports, written as `metric:op:value` strings, e.g.
`having=average:gte:50&having=strike_rate:gte:100`.

They are applied where the count thresholds are: in the grouped query's first stage, before
ordering and LIMIT, so the result is "every group that clears the bar", not "the clearing rows of
one page". Definitions match the reported columns exactly:

    average              runs / wickets        (no value when wickets = 0)
    strike_rate          runs * 100 / balls
    balls_per_dismissal  balls / wickets       (no value when wickets = 0)

A group without a value (0 dismissals) does not pass an average or balls-per-dismissal threshold,
matching the empty cell the table shows. Metrics only computed after the LIMIT (dot %, boundary %,
control %, Impact...) are not supported yet; asking for one returns a warning naming it instead of
silently ignoring it.
"""
from typing import Any, Dict, List, Optional, Tuple

OPS = {"gte": ">=", "lte": "<=", "gt": ">", "lt": "<"}

# metric -> (SQL over the stage-1 aliases balls/runs/wickets, python over a row dict)
SUPPORTED = {
    "average": (
        "(CASE WHEN wickets > 0 THEN runs::float / wickets END)",
        lambda r: (r.get("runs") or 0) / r["wickets"] if r.get("wickets") else None,
    ),
    "strike_rate": (
        "(CASE WHEN balls > 0 THEN runs::float * 100.0 / balls END)",
        lambda r: (r.get("runs") or 0) * 100.0 / r["balls"] if r.get("balls") else None,
    ),
    "balls_per_dismissal": (
        "(CASE WHEN wickets > 0 THEN balls::float / wickets END)",
        lambda r: (r.get("balls") or 0) / r["wickets"] if r.get("wickets") else None,
    ),
}

# Reported metrics we know about but cannot filter on yet (computed after the LIMIT).
KNOWN_UNSUPPORTED = {
    "dot_percentage", "boundary_percentage", "control_percentage", "impact", "impact_per_100",
    "raa", "raa_per_100", "waa", "waa_per_100", "wpa", "avg_leverage", "economy",
}

Threshold = Tuple[str, str, float]


class ThresholdError(ValueError):
    pass


def parse(having: Optional[List[str]]) -> Tuple[List[Threshold], List[str]]:
    """Parse `metric:op:value` strings. Returns (thresholds, warnings); raises on malformed input."""
    thresholds: List[Threshold] = []
    warnings: List[str] = []
    for raw in having or []:
        if not raw:
            continue
        parts = [p.strip() for p in str(raw).split(":")]
        if len(parts) != 3:
            raise ThresholdError(f"Invalid threshold '{raw}': use metric:op:value, e.g. average:gte:50")
        metric, op, value = parts[0].lower(), parts[1].lower(), parts[2]
        if op not in OPS:
            raise ThresholdError(f"Invalid threshold operator '{op}' in '{raw}': use one of {', '.join(OPS)}")
        try:
            number = float(value)
        except ValueError:
            raise ThresholdError(f"Invalid threshold value '{value}' in '{raw}': expected a number")
        if metric in SUPPORTED:
            thresholds.append((metric, op, number))
        elif metric in KNOWN_UNSUPPORTED:
            warnings.append(
                f"Filter on {metric} ({OPS[op]} {value}) is not supported yet and was not applied; "
                f"supported: {', '.join(SUPPORTED)}."
            )
        else:
            raise ThresholdError(f"Unknown threshold metric '{metric}': use one of {', '.join(SUPPORTED)}")
    return thresholds, warnings


def sql_conditions(thresholds: List[Threshold], params: Dict[str, Any]) -> List[str]:
    """Predicates over the grouped CTE's balls/runs/wickets aliases; binds values into params."""
    out = []
    for i, (metric, op, value) in enumerate(thresholds):
        key = f"thr_{i}"
        params[key] = value
        out.append(f"{SUPPORTED[metric][0]} {OPS[op]} :{key}")
    return out


def row_passes(row: Dict[str, Any], thresholds: List[Threshold]) -> bool:
    """The same test on a merged/aggregated row (legacy + modern merge path)."""
    for metric, op, value in thresholds:
        v = SUPPORTED[metric][1](row)
        if v is None:
            return False
        if op == "gte" and not v >= value:
            return False
        if op == "lte" and not v <= value:
            return False
        if op == "gt" and not v > value:
            return False
        if op == "lt" and not v < value:
            return False
    return True


def describe(thresholds: List[Threshold]) -> List[str]:
    """Human-readable chips: 'average >= 50'."""
    return [f"{m.replace('_', ' ')} {OPS[op]} {v:g}" for m, op, v in thresholds]
