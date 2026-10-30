"""
Pre-build the player profile's first screen (GET /player/{name}/summary) after the nightly load.

The load bumps the data version, so the shared peer pools (one per format and role) and every cached summary go
stale; the first profile opened afterwards rebuilt the pools (~15 s on production). This builds the pools for T20
and ODI, then the summaries of everyone who played in the last 3 matches of each side with a fixture in the next
--hours (VERDICT_SCREEN_PLAN.md V9), so match-day links open from the cache.

Usage: python scripts/warm_verdict.py [--hours 36] [--dry-run]
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("USAGE_LOGGING", "0")
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("warm_verdict")

RECENT_MATCHES = 3


def squad(db, team: str, fmt: str) -> list:
    """Everyone who batted or bowled for the side in its last RECENT_MATCHES matches of the format."""
    from sqlalchemy import text

    rows = db.execute(text("""
        WITH last AS (
            SELECT id::text AS id FROM matches
            WHERE format = :fmt AND gender = 'male' AND (team1 = :t OR team2 = :t)
            ORDER BY date DESC LIMIT :n
        )
        SELECT DISTINCT bat AS name FROM delivery_details WHERE p_match IN (SELECT id FROM last) AND team_bat = :t
        UNION
        SELECT DISTINCT bowl FROM delivery_details WHERE p_match IN (SELECT id FROM last) AND team_bowl = :t
    """), {"fmt": fmt, "t": team, "n": RECENT_MATCHES}).scalars().all()
    return sorted(n for n in rows if n)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=int, default=36)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    import main as app
    from database import get_session
    from services.fixture_scraper import fetch_upcoming_fixtures
    from services.player_verdict import _peer_pool, default_window, get_summary, scope_params
    from scripts.warm_previews import site_team

    db = next(get_session())
    t0 = time.time()
    if not args.dry_run:
        # Career pools (since 2015) are only ever built here: a profile request never builds one (PoolsCold).
        for fmt, period in (("T20", "recent"), ("ODI", "recent"), ("T20", "career"), ("ODI", "career")):
            start, end = default_window(fmt, period=period)
            for role in ("bowl", "bat"):
                t = time.time()
                pool = _peer_pool(db, fmt, role, {"start_date": start, "end_date": end}, scope_params(fmt, "strong"))
                log.info("pool %s %s %s: %d players (%s), %.1fs", fmt, period, role, len(pool["players"]),
                         pool["floor_label"], time.time() - t)

    teams = app.get_teams(db=db)
    now = datetime.now(timezone.utc)
    wanted = {}
    for f in fetch_upcoming_fixtures(30):
        start = f.get("start_utc")
        if not start or f.get("format") not in ("T20", "ODI"):
            continue
        if not now < datetime.fromisoformat(start) <= now + timedelta(hours=args.hours):
            continue
        for side in ("team1", "team2"):
            t = site_team(f.get(f"{side}_abbr") or f.get(side), teams) or site_team(f.get(side), teams)
            if t:
                for name in squad(db, t["full_name"], f["format"]):
                    wanted.setdefault((name, f["format"]), t["full_name"])

    built = failed = 0
    for (name, fmt), team in sorted(wanted.items()):
        if args.dry_run:
            log.info("would warm %s (%s, %s)", name, team, fmt)
            continue
        try:
            get_summary(db, name, fmt)
            built += 1
        except Exception as exc:  # one player's failure never blocks the rest
            db.rollback()
            failed += 1
            log.warning("failed %s (%s): %r", name, fmt, exc)
    log.info("warmed %d summaries (%d failed) for %d players in %.0fs", built, failed, len(wanted), time.time() - t0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
