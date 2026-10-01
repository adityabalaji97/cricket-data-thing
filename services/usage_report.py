"""
Weekly adoption report (growth plan G0). Shared by GET /admin/usage and scripts/usage_report.py.
"""

from collections import defaultdict
from typing import Any, Dict, List

from sqlalchemy.orm import Session
from sqlalchemy.sql import text


def build_usage_report(db: Session, weeks: int = 8) -> Dict[str, Any]:
    """Week-by-week adoption: web users and actions, games, NL searches, connector usage, and
    Notes reach (note views, embeds on other sites, packs posted and the visits they bring)."""
    weeks = max(1, min(int(weeks), 52))
    # Whole weeks: from the Monday (weeks - 1) weeks back, so the oldest row is never a partial week.
    params = {"since": f"{weeks - 1} weeks", "own": "hindsightcricket.com"}

    def rows(sql: str) -> List[Dict[str, Any]]:
        return [dict(r) for r in db.execute(text(sql), params).mappings().all()]

    web = rows("""
        SELECT date_trunc('week', ts)::date AS week,
               -- Embeds log each view under a throwaway "embed-..." id (api/embed.mjs): views, not people.
               COUNT(DISTINCT anon_id) FILTER (WHERE anon_id NOT LIKE 'embed-%') AS users,
               COUNT(DISTINCT session_id) AS sessions,
               COUNT(*) FILTER (WHERE event = 'page_view') AS page_views,
               COUNT(*) FILTER (WHERE event = 'query_run') AS query_runs,
               COUNT(*) FILTER (WHERE event = 'share') AS shares,
               COUNT(DISTINCT anon_id) FILTER (WHERE event = 'game_finish') AS game_players,
               COUNT(*) FILTER (WHERE event = 'game_finish') AS games_finished,
               COUNT(*) FILTER (WHERE event = 'note_view') AS note_views,
               -- Embeds on other people's sites; our own note pages iframe the same embeds.
               COUNT(*) FILTER (WHERE event = 'embed_view' AND COALESCE(props->>'host', '') NOT IN ('', :own)) AS embed_views,
               COUNT(DISTINCT props->>'host') FILTER (WHERE event = 'embed_view' AND COALESCE(props->>'host', '') NOT IN ('', :own)) AS embed_hosts,
               COUNT(DISTINCT anon_id) FILTER (WHERE event = 'page_view' AND path LIKE '%utm_source=embed%') AS embed_visitors,
               COUNT(DISTINCT anon_id) FILTER (WHERE event = 'page_view' AND path LIKE '%utm_campaign=pack-%') AS pack_visitors
        FROM app_events WHERE ts >= date_trunc('week', now()) - (:since)::interval
        GROUP BY 1 ORDER BY 1 DESC
    """)
    content = rows("""
        SELECT week, SUM(notes_published)::int AS notes_published, SUM(embeds_created)::int AS embeds_created,
               SUM(packs_posted)::int AS packs_posted
        FROM (
            SELECT date_trunc('week', published_at)::date AS week, COUNT(*) AS notes_published, 0 AS embeds_created, 0 AS packs_posted
            FROM notes WHERE status = 'published' AND published_at >= date_trunc('week', now()) - (:since)::interval GROUP BY 1
            UNION ALL
            -- Charts frozen by visitors with the "Image & embed" button (not the bot or the admin).
            SELECT date_trunc('week', created_at)::date, 0, COUNT(*), 0
            FROM chart_snapshots WHERE created_by = 'web' AND created_at >= date_trunc('week', now()) - (:since)::interval GROUP BY 1
            UNION ALL
            -- By the week the pack was made: packs carry no posted-at time.
            SELECT date_trunc('week', created_at)::date, 0, 0, COUNT(*)
            FROM content_packs WHERE status = 'posted' AND created_at >= date_trunc('week', now()) - (:since)::interval GROUP BY 1
        ) x GROUP BY week ORDER BY week DESC
    """)
    returning = rows("""
        WITH firsts AS (SELECT anon_id, min(ts) AS first_seen FROM app_events WHERE anon_id NOT LIKE 'embed-%' GROUP BY anon_id)
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
        FROM app_events WHERE ts >= now() - interval '7 days' AND anon_id NOT LIKE 'embed-%'
        GROUP BY 1 ORDER BY 2 DESC LIMIT 10
    """)
    countries = rows("""
        SELECT COALESCE(country, '?') AS country, COUNT(DISTINCT anon_id) AS users
        FROM app_events WHERE ts >= now() - interval '7 days' AND anon_id NOT LIKE 'embed-%'
        GROUP BY 1 ORDER BY 2 DESC LIMIT 10
    """)

    by_week: Dict[str, Dict[str, Any]] = defaultdict(dict)
    for group in (web, returning, mcp, nl, content):
        for row in group:
            week = str(row.pop("week"))
            if "clients" in row:
                row["clients"] = sorted((row["clients"] or {}).keys())
            by_week[week].update(row)
    return {
        "weeks": [{"week": week, **values} for week, values in sorted(by_week.items(), reverse=True)],
        "last_7_days": {"top_pages": top_pages, "referrers": referrers, "countries": countries},
    }
