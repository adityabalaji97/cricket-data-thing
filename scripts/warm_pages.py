"""
Pre-build the venue and team pages (TEAM_VENUE_PLAN.md) after the nightly load.

A cold page is 15-30 seconds, so a page request builds in the background and the visitor waits on a skeleton. This
builds, for the default window (recent, T20), the pages most likely to be opened:

* venues: every ground with a men's T20 in the last --days, the IPL's grounds, and the grounds of fixtures in the
  next --hours (under the fixture's own spelling too, as the preview's "next here" link and the venue list differ);
* teams: every side with a men's T20 in the last --days, the IPL sides, and the sides in the next --hours' fixtures.

One page at a time (services/page_builds.py), stopping at --max-minutes so the nightly run stays bounded.

Usage: python scripts/warm_pages.py [--days 30] [--hours 48] [--max-minutes 40] [--dry-run]
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("USAGE_LOGGING", "0")
logging.basicConfig(level=logging.WARNING, format="%(message)s")
log = logging.getLogger("warm_pages")
log.setLevel(logging.INFO)


def recent(db, days: int):
    from sqlalchemy import text

    since = (date.today() - timedelta(days=days)).isoformat()
    grounds = db.execute(text("""
        SELECT ground, COUNT(DISTINCT p_match) n FROM delivery_details
        WHERE format = 'T20' AND gender = 'male' AND match_date >= :s AND ground IS NOT NULL
        GROUP BY ground ORDER BY n DESC"""), {"s": since}).scalars().all()
    sides = db.execute(text("""
        SELECT team_bat, COUNT(DISTINCT p_match) n FROM delivery_details
        WHERE format = 'T20' AND gender = 'male' AND match_date >= :s AND team_bat IS NOT NULL
        GROUP BY team_bat ORDER BY n DESC"""), {"s": since}).scalars().all()
    ipl_since = date(date.today().year - 2, 1, 1).isoformat()
    ipl_grounds = db.execute(text("""
        SELECT ground FROM delivery_details WHERE competition = 'IPL' AND match_date >= :s AND ground IS NOT NULL
        GROUP BY ground HAVING COUNT(DISTINCT p_match) >= 5 ORDER BY COUNT(DISTINCT p_match) DESC"""), {"s": ipl_since}).scalars().all()
    ipl_sides = db.execute(text("""
        SELECT team_bat FROM delivery_details WHERE competition = 'IPL' AND match_date >= :s AND team_bat IS NOT NULL
        GROUP BY team_bat ORDER BY MAX(match_date) DESC"""), {"s": ipl_since}).scalars().all()
    return list(grounds), list(sides), list(ipl_grounds), list(ipl_sides)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--hours", type=int, default=48)
    parser.add_argument("--max-minutes", type=int, default=40)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    import main as app  # noqa: F401  (registers the models and settings the services expect)
    from database import get_session
    from services.fixture_scraper import fetch_upcoming_fixtures
    from services.team_page import canonical_team, get_page as team_page
    from services.venue_page import get_page as venue_page

    db = next(get_session())
    grounds, sides, ipl_grounds, ipl_sides = recent(db, args.days)
    venues, teams = [], []
    now = datetime.now(timezone.utc)
    try:
        for f in fetch_upcoming_fixtures(30):
            start = f.get("start_utc")
            if not start or f.get("format") != "T20":
                continue
            if now < datetime.fromisoformat(start) <= now + timedelta(hours=args.hours):
                venues.append(f.get("venue"))
                teams += [f.get("team1"), f.get("team2")]
    except Exception as exc:  # fixtures are a nice-to-have here
        log.info("fixtures unavailable: %r", exc)
    # Fixtures first, then the IPL, then everything recent (busiest first): the time cap drops the tail.
    venues += ipl_grounds + grounds
    teams += ipl_sides + sides
    venues = list(dict.fromkeys(v for v in venues if v))
    teams = list(dict.fromkeys(canonical_team(t) for t in teams if t))
    log.info("%d venues, %d teams to warm", len(venues), len(teams))
    if args.dry_run:
        log.info("venues: %s", venues)
        log.info("teams: %s", teams)
        return 0

    t0 = time.time()
    built = failed = 0
    # Interleaved, so a bounded run warms some of each.
    from itertools import zip_longest

    pairs = zip_longest([("venue", v) for v in venues], [("team", t) for t in teams])
    queue = [x for pair in pairs for x in pair if x]
    for kind, name in queue:
        if time.time() - t0 > args.max_minutes * 60:
            log.info("stopping at %d minutes", args.max_minutes)
            break
        t = time.time()
        try:
            (venue_page if kind == "venue" else team_page)(db, name, wait=True)
            built += 1
            log.info("%s %s: %.0fs", kind, name, time.time() - t)
        except Exception as exc:
            failed += 1
            db.rollback()
            log.info("%s %s failed: %r", kind, name, exc)
    log.info("warmed %d pages (%d failed) in %.0fs", built, failed, time.time() - t0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
