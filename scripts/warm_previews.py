"""
Pre-build the match-preview stories for the next day's fixtures, after the nightly load.

The nightly refresh bumps the data version, so every cached story (query_cache) is stale and the
first person to open a fixture waited for ~30 queries (up to ~7s on production). This builds each
upcoming fixture's story through the same endpoint the site calls, so it lands in the cache under
the exact key the page will ask for.

The page asks with different filters depending on how it was opened, so each fixture is built
twice: as the home page's fixture links open it (internationals on, top 20 sides) and as a direct
visit does (the page defaults: no internationals, top 10). Both use the format's preview window
(4 years for T20, 8 for ODI) and "up to now" (routers/match_preview.py treats today as now).

Usage: python scripts/warm_previews.py [--hours 36] [--dry-run]
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
log = logging.getLogger("warm_previews")

# (include_international, top_teams): LandingPage.routePreview, then App.js's own defaults.
VARIANTS = ((True, 20), (False, 10))


def site_team(name: str, teams):
    """The team the page resolves a fixture's name or abbreviation to (App.resolveTeamFromParam)."""
    want = (name or "").strip().lower()
    for t in teams:
        if want in ((t.get("full_name") or "").lower(), (t.get("abbreviated_name") or "").lower()):
            return t
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=int, default=36)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    import main as app
    from database import get_session
    from mcp_server.server import _default_window
    from routers.match_preview import get_match_preview_cards
    from services.fixture_scraper import fetch_upcoming_fixtures

    db = next(get_session())
    teams = app.get_teams(db=db)
    now = datetime.now(timezone.utc)
    built = skipped = 0
    for f in fetch_upcoming_fixtures(30):
        start = f.get("start_utc")
        if not start or f.get("format") not in ("T20", "ODI") or not f.get("venue"):
            continue
        if not now < datetime.fromisoformat(start) <= now + timedelta(hours=args.hours):
            continue
        t1 = site_team(f.get("team1_abbr") or f.get("team1"), teams) or site_team(f.get("team1"), teams)
        t2 = site_team(f.get("team2_abbr") or f.get("team2"), teams) or site_team(f.get("team2"), teams)
        if not t1 or not t2:
            log.info("skip %s v %s: team not on the site", f.get("team1"), f.get("team2"))
            skipped += 1
            continue
        window_start, _ = _default_window(f["format"])
        for intl, top in VARIANTS:
            label = f"{t1['abbreviated_name']} v {t2['abbreviated_name']} at {f['venue']} ({f['format']}, intl={intl}, top={top})"
            if args.dry_run:
                log.info("would build %s", label)
                continue
            t0 = time.time()
            try:
                story = get_match_preview_cards(
                    venue=f["venue"], team1_id=t1["full_name"] or t1["abbreviated_name"],
                    team2_id=t2["full_name"] or t2["abbreviated_name"], start_date=window_start, end_date=None,
                    include_international=intl, top_teams=top, day_or_night=None, format=f["format"],
                    team1_short=t1["abbreviated_name"], team2_short=t2["abbreviated_name"], db=db,
                )
                cards = sum(len(c["cards"]) for c in story.get("chapters", []))
                log.info("built %s: %s cards, %.1fs", label, cards, time.time() - t0)
                built += 1
            except Exception as exc:  # one fixture never stops the rest
                db.rollback()
                log.warning("failed %s: %r", label, exc)
    log.info("done: %s stories built, %s fixtures skipped", built, skipped)
    return 0


if __name__ == "__main__":
    sys.exit(main())
