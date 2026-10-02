"""Thresholds on computed metrics for grouped query-builder results ("50+ average, 100+ SR").

The query builder already filters groups on counts (min/max balls, runs, wickets). This adds
filters on the rate metrics it reports, written as `metric:op:value` strings, e.g.
`having=average:gte:50&having=strike_rate:gte:100&having=control_percentage:gte:80`.

They are applied where the count thresholds are: in the grouped query's first stage, before
ordering and LIMIT, so the result is "every group that clears the bar", not "the clearing rows of
one page". Every definition matches the reported column exactly (handle_grouped_query's final
SELECT and _primer_metric_fields):

    average              runs / wickets                    (no value when wickets = 0)
    strike_rate          runs * 100 / balls
    balls_per_dismissal  balls / wickets                   (no value when wickets = 0)
    dot_percentage       dots * 100 / balls
    boundary_percentage  boundaries * 100 / balls
    control_percentage   controlled / judged shots * 100   (no value without control data)
    impact, raa, waa, wpa                      signed totals over balls with metrics
    impact_per_100, raa_per_100, waa_per_100   total * 100 / metric balls
    impact_per_innings                         impact / innings
    avg_leverage                               mean leverage over metric balls

A group without a value does not pass (the table shows no value). The first three come from the
stage-1 counts; the rest need extra stage-1 aggregates, which handle_grouped_query adds only when
a threshold asks for them (see `needs`). The Primer metrics exist for men's T20 only.
"""
from typing import Any, Dict, List, Optional, Set, Tuple

OPS = {"gte": ">=", "lte": "<=", "gt": ">", "lt": "<"}


def _pct(num: str, den: str) -> str:
    return f"(CASE WHEN {den} > 0 THEN {num}::float * 100.0 / {den} END)"


def _get(key):
    return lambda r: r.get(key)


# metric -> (SQL over stage-1 aliases, python over a merged row, extra stage-1 aggregates needed)
SUPPORTED: Dict[str, Tuple[str, Any, Set[str]]] = {
    "average": ("(CASE WHEN wickets > 0 THEN runs::float / wickets END)",
                lambda r: (r.get("runs") or 0) / r["wickets"] if r.get("wickets") else None, set()),
    "strike_rate": (_pct("runs", "balls"),
                    lambda r: (r.get("runs") or 0) * 100.0 / r["balls"] if r.get("balls") else None, set()),
    "balls_per_dismissal": ("(CASE WHEN wickets > 0 THEN balls::float / wickets END)",
                            lambda r: (r.get("balls") or 0) / r["wickets"] if r.get("wickets") else None, set()),
    "dot_percentage": (_pct("t_dots", "balls"), _get("dot_percentage"), {"dots"}),
    "boundary_percentage": (_pct("t_boundaries", "balls"), _get("boundary_percentage"), {"boundaries"}),
    "control_percentage": (_pct("t_ctrl_num", "t_ctrl_den"), _get("control_percentage"), {"control"}),
    "impact": ("t_impact", _get("impact"), {"metrics"}),
    "raa": ("t_raa", _get("raa"), {"metrics"}),
    "waa": ("t_waa", _get("waa"), {"metrics"}),
    "wpa": ("t_wpa", _get("wpa"), {"metrics"}),
    "impact_per_100": (_pct("t_impact", "t_metric_balls"), _get("impact_per_100"), {"metrics"}),
    "raa_per_100": (_pct("t_raa", "t_metric_balls"), _get("raa_per_100"), {"metrics"}),
    "waa_per_100": (_pct("t_waa", "t_metric_balls"), _get("waa_per_100"), {"metrics"}),
    "impact_per_innings": ("(CASE WHEN innings_count > 0 THEN t_impact / innings_count END)",
                           _get("impact_per_innings"), {"metrics"}),
    "avg_leverage": ("(CASE WHEN t_lev_n > 0 THEN t_lev_sum / t_lev_n END)", _get("avg_leverage"), {"metrics"}),
}

# Reported elsewhere but not a delivery-mode column.
KNOWN_UNSUPPORTED = {"economy"}

METRIC_MODE_ONLY = {m for m, (_, _, need) in SUPPORTED.items() if need}
PRIMER = {m for m, (_, _, need) in SUPPORTED.items() if "metrics" in need}

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
            warnings.append(f"Filter on {metric} ({OPS[op]} {value}) is not available in this mode and was not applied.")
        else:
            raise ThresholdError(f"Unknown threshold metric '{metric}': use one of {', '.join(SUPPORTED)}")
    return thresholds, warnings


def applicable(thresholds: List[Threshold], *, primer_available: bool, cumulative: bool) -> Tuple[List[Threshold], List[str]]:
    """Drop thresholds this query cannot evaluate, with a warning for each."""
    kept, warnings = [], []
    for t in thresholds:
        metric, op, value = t
        label = f"{metric} ({OPS[op]} {value:g})"
        if cumulative and metric in METRIC_MODE_ONLY:
            warnings.append(f"Filter on {label} is not available with cumulative ball aggregation and was not applied.")
        elif metric in PRIMER and not primer_available:
            warnings.append(f"Filter on {label} needs the Impact/WPA metrics, which cover men's T20 only; not applied.")
        else:
            kept.append(t)
    return kept, warnings


def needs(thresholds: List[Threshold]) -> Set[str]:
    """Extra stage-1 aggregates the thresholds require: dots, boundaries, control, metrics."""
    out: Set[str] = set()
    for metric, _, _ in thresholds:
        out |= SUPPORTED[metric][2]
    return out


def sql_conditions(thresholds: List[Threshold], params: Dict[str, Any]) -> List[str]:
    """Predicates over the grouped CTE's aliases; binds values into params."""
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
        v = float(v)
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
