"""
What people opened this week, for the search page: the most-visited player, team and venue pages over the last few
days, counted by people (services/usage_report's rule: an anonymous id with 2+ events, or arriving from another site),
so crawlers rendering the sitemap don't count.
"""
from __future__ import annotations

from typing import Any, Dict, List
from urllib.parse import parse_qs, unquote_plus, urlparse

from sqlalchemy import text

from services.usage_report import _PEOPLE_7D

LIMIT = 6


def popular(db, days: int = 7, limit: int = LIMIT) -> Dict[str, List[Dict[str, Any]]]:
    rows = db.execute(text(f"""
        SELECT path, anon_id FROM app_events
        WHERE event = 'page_view' AND ts >= now() - (:days || ' days')::interval AND {_PEOPLE_7D}
          AND (path LIKE '/player?%' OR path LIKE '/team?%' OR path LIKE '/venue?%')
    """), {"days": str(days), "own": "hindsightcricket.com"}).all()
    from services.team_page import canonical_team

    seen: Dict[str, Dict[str, set]] = {"players": {}, "teams": {}, "venues": {}}
    for path, anon in rows:
        u = urlparse(path)
        q = parse_qs(u.query)
        if u.path == "/player" and q.get("name"):
            kind, name = "players", unquote_plus(q["name"][0]).strip()
        elif u.path == "/team" and q.get("team"):
            kind, name = "teams", canonical_team(unquote_plus(q["team"][0]).strip())
        elif u.path == "/venue" and q.get("venue") and not q.get("team1"):
            kind, name = "venues", unquote_plus(q["venue"][0]).strip()
        else:
            continue
        if name:
            seen[kind].setdefault(name, set()).add(anon)
    return {kind: [{"name": n, "people": len(p)} for n, p in sorted(names.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:limit]]
            for kind, names in seen.items()}
