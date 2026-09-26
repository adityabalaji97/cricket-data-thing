"""
Weekly adoption report (growth plan G0). Shared by GET /admin/usage and scripts/usage_report.py.
"""

from collections import defaultdict
from typing import Any, Dict, List

from sqlalchemy.orm import Session
from sqlalchemy.sql import text


def build_usage_report(db: Session, weeks: int = 8) -> Dict[str, Any]:
    """Week-by-week adoption: web users and actions, games, NL searches, connector usage."""
    weeks = max(1, min(int(weeks), 52))
    # Whole weeks: from the Monday (weeks - 1) weeks back, so the oldest row is never a partial week.
    params = {"since": f"{weeks - 1} weeks"}

    def rows(sql: str) -> List[Dict[str, Any]]:
        return [dict(r) for r in db.execute(text(sql), params).mappings().all()]

    web = rows("""
        SELECT date_trunc('week', ts)::date AS week,
               COUNT(DISTINCT anon_id) AS users,
               COUNT(DISTINCT session_id) AS sessions,
               COUNT(*) FILTER (WHERE event = 'page_view') AS page_views,
               COUNT(*) FILTER (WHERE event = 'query_run') AS query_runs,
               COUNT(*) FILTER (WHERE event = 'share') AS shares,
               COUNT(DISTINCT anon_id) FILTER (WHERE event = 'game_finish') AS game_players,
               COUNT(*) FILTER (WHERE event = 'game_finish') AS games_finished
        FROM app_events WHERE ts >= date_trunc('week', now()) - (:since)::interval
        GROUP BY 1 ORDER BY 1 DESC
    """)
    returning = rows("""
        WITH firsts AS (SELECT anon_id, min(ts) AS first_seen FROM app_events GROUP BY anon_id)
        SELECT date_trunc('week', e.ts)::date AS week,
               COUNT(DISTINCT e.anon_id) FILTER (WHERE f.first_seen < date_trunc('week', e.ts)) AS returning_users
        FROM app_events e JOIN firsts f USING (anon_id)
        WHERE e.ts >= date_trunc('week', now()) - (:since)::interval
        GROUP BY 1 ORDER BY 1 DESC
    """)
    mcp = rows("""
        SELECT date_trunc('week', ts)::date AS week, COUNT(*) AS calls,
               COUNT(DISTINCT caller_hash) AS distinct_callers,
               COUNT(*) FILTER (WHERE outcome <> 'ok') AS failed_calls,
               jsonb_object_agg(COALESCE(client, '?'), 1) AS clients
        FROM mcp_call_log WHERE ts >= date_trunc('week', now()) - (:since)::interval
        GROUP BY 1 ORDER BY 1 DESC
    """)
    nl = rows("""
        SELECT date_trunc('week', created_at)::date AS week, COUNT(*) AS nl_searches
        FROM nl_query_log WHERE created_at >= date_trunc('week', now()) - (:since)::interval
        GROUP BY 1 ORDER BY 1 DESC
    """)
    top_pages = rows("""
        SELECT path, COUNT(*) AS views, COUNT(DISTINCT anon_id) AS users
        FROM app_events WHERE event = 'page_view' AND ts >= now() - interval '7 days'
        GROUP BY 1 ORDER BY 2 DESC LIMIT 15
    """)
    referrers = rows("""
        SELECT COALESCE(NULLIF(split_part(split_part(referrer, '://', 2), '/', 1), ''), '(direct)') AS source,
               COUNT(DISTINCT anon_id) AS users
        FROM app_events WHERE ts >= now() - interval '7 days'
        GROUP BY 1 ORDER BY 2 DESC LIMIT 10
    """)
    countries = rows("""
        SELECT COALESCE(country, '?') AS country, COUNT(DISTINCT anon_id) AS users
        FROM app_events WHERE ts >= now() - interval '7 days'
        GROUP BY 1 ORDER BY 2 DESC LIMIT 10
    """)

    by_week: Dict[str, Dict[str, Any]] = defaultdict(dict)
    for group in (web, returning, mcp, nl):
        for row in group:
            week = str(row.pop("week"))
            if "clients" in row:
                row["clients"] = sorted((row["clients"] or {}).keys())
            by_week[week].update(row)
    return {
        "weeks": [{"week": week, **values} for week, values in sorted(by_week.items(), reverse=True)],
        "last_7_days": {"top_pages": top_pages, "referrers": referrers, "countries": countries},
    }
