"""
Coverage-aware ranking for tagged metrics (docs/query_builder_metrics.md).

Shot control, line, length, shot type and wagon zone are tagged ball by ball, and how many balls
carry a tag depends on the match, competition and era. A ranking by a tagged metric is only fair
between rows whose balls are mostly tagged: ranked by control %, ODI partnerships of 1000+ balls put
MacLeod & Berrington (34% of balls tagged) and Milind Kumar & Mukkamalla (58%) above Gill & Kohli
(99.9%), on the few balls that happened to be tagged.

So when the ranking metric is tagged, rows under the minimum coverage (default 90%) are kept --
with their values -- but ranked after every row that qualifies, marked `coverage_excluded`, and
left out of the denominator ("1st of 155 partnerships ... with 90%+ control data").
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

DEFAULT_MIN_COVERAGE = 90.0

#: ranking metric -> the tag it is built on
TAGGED_METRICS = {"control_percentage": "control"}

TAG_LABELS = {"control": "control", "shot": "shot", "line": "line", "length": "length", "wagon_zone": "wagon zone"}


def tag_for(metric: Optional[str]) -> Optional[str]:
    return TAGGED_METRICS.get(metric or "")


def rank_with_coverage(rows: List[Dict[str, Any]], metric: Optional[str],
                       min_coverage: Optional[float] = DEFAULT_MIN_COVERAGE) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Rows (already in ranking order) with those under the coverage floor moved after the rest, each
    marked `coverage_excluded`. Returns (rows, summary) -- summary is None when the metric is not
    tagged or no floor applies.
    """
    tag = tag_for(metric)
    if not tag or not min_coverage:
        return rows, None
    column = f"{tag}_coverage_pct"
    included, excluded = [], []
    for row in rows:
        pct = row.get(column)
        ok = pct is not None and float(pct) >= float(min_coverage)
        row["coverage_excluded"] = not ok
        (included if ok else excluded).append(row)
    summary = {"tag": tag, "label": TAG_LABELS[tag], "column": column, "min": float(min_coverage),
               "included": len(included), "excluded": len(excluded)}
    return included + excluded, summary


def describe_floor(summary: Dict[str, Any]) -> str:
    """'90%+ control data' for titles and footers."""
    return f"{summary['min']:g}%+ {summary['label']} data"
