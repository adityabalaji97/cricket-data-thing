"""
A question's field: every qualifying player (or pair) in its scope, with every metric, from one query-builder call.

The post's cards, the planner's checks and the contestedness test all read the same rows, so a post never mixes
numbers from different queries. Derived metrics (economy, WPA per 100, wickets per innings, sixes per 100) are
computed here from the row's own fields, the way mcp_server's _with_economy does.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from functools import cached_property
from typing import Any, Dict, List, Optional

from services.ig_posts.angles import Angle

ROLE_KEY = {"batter": "batter", "bowler": "bowler", "partnership": "partnership"}
#: Rows whose control tags cover less than this share of balls don't get a control % (services/coverage.py floor).
CONTROL_FLOOR = 90.0


@dataclass
class QuestionContext:
    db: Any
    role: str                         # batter | bowler | partnership
    fmt: str                          # T20 | ODI
    params: Dict[str, Any]            # query-builder filters for the field (leagues, start_date, over_min, bowl_kind...)
    min_balls: int
    subject: Optional[str] = None     # highlighted entity, when the question names one
    gender: str = "male"
    extra: Dict[str, Any] = field(default_factory=dict)

    def query(self, **overrides) -> List[Dict[str, Any]]:
        from services.query_builder_v2 import run_deliveries_query

        args = {"fmt": self.fmt, "gender": self.gender, "group_by": [ROLE_KEY[self.role]], "min_balls": self.min_balls,
                "limit": 5000, **self.params, **overrides}
        for key in ("start_date", "end_date"):
            if isinstance(args.get(key), str):
                args[key] = date.fromisoformat(args[key])
        if self.role == "bowler":
            args.setdefault("metrics_perspective", "bowling")
        return run_deliveries_query(self.db, **args).get("data") or []

    @cached_property
    def rows(self) -> List[Dict[str, Any]]:
        out = []
        for r in self.query():
            name = r.get(ROLE_KEY[self.role])
            if not name:
                continue
            out.append({"name": name, **r, **derived(r, self.role)})
        return out

    @property
    def n(self) -> int:
        return len(self.rows)

    def values(self, angle: Angle) -> List[float]:
        return [r[angle.metric] for r in self.rows if usable(r, angle)]

    def percentile(self, row: Dict[str, Any], angle: Angle) -> Optional[float]:
        """0..100, 100 = best in the field (direction-aware)."""
        if not usable(row, angle):
            return None
        vals = self.values(angle)
        if len(vals) < 2:
            return None
        v = row[angle.metric]
        below = sum(1 for x in vals if (x < v if angle.higher_better else x > v))
        ties = sum(1 for x in vals if x == v) - 1
        return round(100.0 * (below + 0.5 * ties) / (len(vals) - 1), 1)

    def leader(self, angle: Angle) -> Optional[Dict[str, Any]]:
        rows = [r for r in self.rows if usable(r, angle)]
        if not rows:
            return None
        return (max if angle.higher_better else min)(rows, key=lambda r: r[angle.metric])

    def ranked(self, angle: Angle) -> List[Dict[str, Any]]:
        rows = [r for r in self.rows if usable(r, angle)]
        return sorted(rows, key=lambda r: r[angle.metric], reverse=angle.higher_better)

    def composite(self, angles: List[Angle]) -> List[Dict[str, Any]]:
        """Rows by mean percentile across the angles (only rows with every angle)."""
        scored = []
        for r in self.rows:
            pcts = [self.percentile(r, a) for a in angles]
            if any(p is None for p in pcts):
                continue
            scored.append({**r, "composite": round(sum(pcts) / len(pcts), 1), "pcts": dict(zip([a.id for a in angles], pcts))})
        return sorted(scored, key=lambda r: r["composite"], reverse=True)

    def find(self, name: str) -> Optional[Dict[str, Any]]:
        return next((r for r in self.rows if r["name"] == name), None)


def usable(row: Dict[str, Any], angle: Angle) -> bool:
    v = row.get(angle.metric)
    if v is None:
        return False
    if angle.min_coverage == "control" and (row.get("control_coverage_pct") or 0) < CONTROL_FLOOR:
        return False
    return True


def derived(r: Dict[str, Any], role: str) -> Dict[str, Any]:
    """Metrics the query builder doesn't return directly, from the row's own fields."""
    out: Dict[str, Any] = {}
    balls, mballs = r.get("balls") or 0, r.get("metric_balls") or 0
    if role == "bowler" and r.get("strike_rate") is not None:
        out["economy"] = round(r["strike_rate"] * 6 / 100, 2)  # bowler view: SR is runs conceded per 100 balls
    if r.get("wpa") is not None and mballs:
        out["wpa_per_100"] = round(r["wpa"] * 100 / mballs, 3)
    if r.get("innings_count"):
        out["wickets_per_innings"] = round((r.get("wickets") or 0) / r["innings_count"], 2)
    if balls:
        out["sixes_per_100"] = round(100 * (r.get("sixes") or 0) / balls, 2)
    return out
