"""
What's on: the format the Instagram queue leads with on a day.

    focus(day, majors)   'T20' / 'ODI' / None: an India series on (or starting within LEAD_DAYS), else another major series
    major_series(db, day) [(format, label)] from internationals between top-10 sides around the day (data + fixtures)
    post_format(fact, key) 'T20' / 'ODI' / None for a queued post

INDIA_SERIES is the one list to update when a series is announced: the fixture scraper only sees a few days ahead.
Both formats are always built; this only changes which goes first (services/ig_backlog.schedule / reorder).
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

#: (first day, last day, format, label). Tests aren't in the data, so they don't set a focus.
INDIA_SERIES: List[Tuple[date, date, str, str]] = [
    (date(2026, 10, 6), date(2026, 10, 17), "T20", "India v West Indies T20Is"),
    (date(2026, 10, 22), date(2026, 11, 1), "T20", "India in New Zealand T20Is"),
    (date(2026, 11, 4), date(2026, 11, 15), "ODI", "India in New Zealand ODIs"),
]
LEAD_DAYS = 3      # a series sets the focus from this many days before its first match
MAJOR_TOP = 10     # a major series: both sides in the top 10
LOOK_BACK = 3      # ... with a match in the last few days or the next few (fixtures)

_ODI = re.compile(r"\bODIs?\b")
_T20 = re.compile(r"\b(T20Is?|T20s?|IPL|BBL|PSL|CPL|SA20|ILT20|MLC|The Hundred|T20 Blast)\b")


def india_series(day: date) -> Optional[Tuple[str, str]]:
    for start, end, fmt, label in INDIA_SERIES:
        if start - timedelta(days=LEAD_DAYS) <= day <= end:
            return fmt, label
    return None


def focus(day: date, majors: Optional[List[Tuple[str, str]]] = None) -> Optional[Tuple[str, str]]:
    """(format, why) for the day, or None (no series on: the formats take turns)."""
    on = india_series(day)
    if on:
        return on
    for fmt, label in majors or []:
        return fmt, label
    return None


def major_series(db, day: date) -> List[Tuple[str, str]]:
    """Internationals between two top-10 sides within LOOK_BACK days of `day`, from loaded matches."""
    from sqlalchemy import text

    from models import INTERNATIONAL_TEAMS_RANKED

    top = list(INTERNATIONAL_TEAMS_RANKED[:MAJOR_TOP])
    rows = db.execute(text("""
        SELECT team1, team2, format, MAX(date) AS last FROM matches
        WHERE gender = 'male' AND match_type = 'international' AND format IN ('T20', 'ODI')
          AND team1 = ANY(:top) AND team2 = ANY(:top) AND date BETWEEN :a AND :b
        GROUP BY 1, 2, 3 ORDER BY last DESC
    """), {"top": top, "a": day - timedelta(days=LOOK_BACK), "b": day + timedelta(days=LOOK_BACK)}).mappings().all()
    word = {"T20": "T20Is", "ODI": "ODIs"}
    return [(r["format"], f"{r['team1']} v {r['team2']} {word[r['format']]}") for r in rows if "India" not in (r["team1"], r["team2"])]


def post_format(fact: Dict[str, Any], key: str = "") -> Optional[str]:
    """The format a post is about: from its key (odi- / ipl- / t20i-), else its kicker and title."""
    k = (key or "").removeprefix("ig:")
    if k.startswith(("odi-", "debate-odi")) or "-odiwc-" in k:
        return "ODI"
    if k.startswith(("ipl-", "t20i-", "debate-ipl", "debate-t20i")):
        return "T20"
    text = f"{fact.get('kicker') or ''} {fact.get('title') or ''} {fact.get('method') or ''}"
    if _ODI.search(text):
        return "ODI"
    if _T20.search(text):
        return "T20"
    return None
