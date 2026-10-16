"""
The licensed tracking columns (line, length, shot, shot family, wagon zone, control: Himanish Ganjoo & TechRadar's
ball-by-ball feed) are shared in aggregate only, by the website's API (routers/query_builder_v2.py) and the MCP
connector (mcp_server/server.py) alike:

  * a grouped query that groups or filters by a tracking column drops groups of fewer than MIN_GROUP_BALLS balls
    (grouping by match, over and ball would otherwise list the feed ball by ball);
  * individual balls (an ungrouped query) come back without the tracking columns, and can't be filtered by one
    (the list of balls matching length=GOOD_LENGTH would give the tags away).

Scorecard tabs, profiles and the other site views aggregate by player and match and aren't affected.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

TAGGED_COLUMNS = ("line", "length", "shot", "shot_family", "wagon_zone", "control")
MIN_GROUP_BALLS = int(os.getenv("MIN_TAGGED_GROUP_BALLS", os.getenv("MCP_MIN_TAGGED_GROUP_BALLS", "6")))
NOTE = ("Line, length, shot, wagon zone and control come from licensed ball-by-ball tracking (Himanish Ganjoo & "
        "TechRadar) and are shared in aggregate only")


def tag_filters_used(filters: Dict[str, Any]) -> bool:
    return any(filters.get(c) not in (None, [], "") for c in TAGGED_COLUMNS)


def uses_tags(group_by: Sequence[str], filters: Dict[str, Any]) -> bool:
    return bool(set(TAGGED_COLUMNS) & set(group_by or [])) or tag_filters_used(filters)


def ungrouped_tag_filter_error(filters: Dict[str, Any]) -> Optional[str]:
    if tag_filters_used(filters):
        return ("Individual balls can't be filtered by line, length, shot, wagon zone or control (licensed tracking "
                "data, shared in aggregate only). Add a group_by (for example batter, bowler or match) to use that filter.")
    return None


def floor_groups(rows: List[Dict[str, Any]], group_by: Sequence[str], filters: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], int]:
    """Rows of a grouped query with tracking-column groups under MIN_GROUP_BALLS balls left out, and how many were."""
    if not uses_tags(group_by, filters):
        return rows, 0
    kept = [r for r in rows if r.get("balls") is None or (r.get("balls") or 0) >= MIN_GROUP_BALLS]
    return kept, len(rows) - len(kept)


def strip_tags(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Individual balls without the tracking columns."""
    return [{k: (None if k in TAGGED_COLUMNS else v) for k, v in dict(r).items()} for r in rows]


def hidden_note(hidden: int) -> str:
    return f"{hidden} groups with fewer than {MIN_GROUP_BALLS} balls were left out. {NOTE}."
