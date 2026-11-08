"""
"Recently asked" on the query builder's empty screen: what visitors actually asked, newest first (user, 8 Nov 2026).

From app_events: query_run events (a query that ran) whose page carries the question (q=), in the last 30 days.
The owner's own questions count (post work goes through the connector and the database, not this page; user, 8 Nov
2026). Left out: headless renders and test runs (no country), embeds, and questions that look like junk. One row per question (case-insensitive), the latest run's link.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List
from urllib.parse import parse_qs, urlparse

from sqlalchemy import text

LIMIT = 8
MAX_LEN = 100
CLIPPED = 200   # paths logged before 8 Nov 2026 were cut at 200 characters
WORDS = re.compile(r"[A-Za-z]{2,}")
JUNK = re.compile(r"https?://|www\.|@|<|>", re.I)


def _question(path: str) -> str:
    q = parse_qs(urlparse(path or "").query).get("q", [""])[0]
    return re.sub(r"\s+", " ", q).strip()


def recent_questions(db, limit: int = LIMIT) -> List[Dict[str, Any]]:
    rows = db.execute(text("""
        SELECT ts, path FROM app_events
        WHERE event = 'query_run' AND ts >= now() - interval '30 days' AND path LIKE '/query?%' AND path LIKE '%q=%'
          AND country IS NOT NULL AND anon_id NOT LIKE 'embed-%'
        ORDER BY ts DESC LIMIT 500""")).fetchall()
    out, seen = [], set()
    for ts, path in rows:
        if len(path) >= CLIPPED:  # the browser cut the path (src/utils/analytics.js): the link and question are partial
            continue
        q = _question(path)
        # A follow-up appends to the question ("Sanju Samson … vs pace heavy sides … Powerplay"): one row per chain,
        # its first question and latest step, linking to the latest run.
        steps = [x.strip() for x in q.split("…") if x.strip()]
        if not steps:
            continue
        key = steps[0].lower()
        shown = steps[0] if len(steps) == 1 else f"{steps[0]} … {steps[-1]}"
        if key in seen or JUNK.search(q) or len(WORDS.findall(shown)) < 2:
            continue
        seen.add(key)
        if len(shown) > MAX_LEN:
            shown = shown[: MAX_LEN - 1].rstrip() + "…"
        out.append({"q": shown, "search": "?" + urlparse(path).query, "at": ts.isoformat()})
        if len(out) >= limit:
            break
    return out
