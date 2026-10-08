"""
Match-day Instagram posts, nightly (refresh-delivery-details.yml) or by hand:

    python scripts/ig_match_day.py --team India              # previews for fixtures in the next 2 days, recaps for
                                                             # matches played in the last 2 days (queued, rendered)
    python scripts/ig_match_day.py --team India --dry-run    # say what it would make, save nothing

Previews come from the fixture scraper (ESPN, a few days ahead) and the preview story; recaps from the loaded match.
Each post is made once (angle key preview-<teams>-<date> / recap-<match id>); --force remakes it. Slides render on the
live site (--base), so the code drawing them must be deployed.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, timedelta, timezone
from typing import Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


MIN_PREVIEW_CARDS = 4  # a top-N preview needs this many chapters with data (associates can be thin)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--team", action="append", default=None, help="only fixtures with this team (repeatable)")
    parser.add_argument("--days", type=int, default=2, help="look this many days ahead (previews) and back (recaps)")
    parser.add_argument("--base", default="https://hindsightcricket.com")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="remake posts that already exist")
    parser.add_argument("--no-previews", action="store_true")
    parser.add_argument("--no-recaps", action="store_true")
    parser.add_argument("--top-teams", type=int, default=0,
                        help="also preview internationals between two of the top N sides (recaps stay --team only)")
    args = parser.parse_args()

    from sqlalchemy import text

    from database import engine, get_session
    from services import ig_backlog, ig_slides
    from services.fixture_scraper import fetch_upcoming_fixtures
    from services.ig_posts.match import series_label

    db = next(get_session())
    teams = set(args.team or [])
    today = datetime.now(timezone.utc).date()

    def exists(key: str) -> bool:
        return bool(db.execute(text("SELECT 1 FROM content_packs WHERE angle_key = :k"), {"k": f"ig:{key}"}).first())

    made = []
    fixtures = fetch_upcoming_fixtures(20)
    from models import INTERNATIONAL_TEAMS_RANKED

    from services.fixture_scraper import _ESPN_TEAM_NAME_ALIASES

    rank = {t: i + 1 for i, t in enumerate(INTERNATIONAL_TEAMS_RANKED[: args.top_teams])}
    for espn, ours_name in _ESPN_TEAM_NAME_ALIASES.items():  # "United Arab Emirates" is "UAE" in the rankings
        if ours_name in rank:
            rank[espn] = rank[ours_name]
    ist = timezone(timedelta(hours=5, minutes=30))

    def ours(f) -> bool:  # a --team fixture: always a feed post, as before
        return bool(teams & {f["team1"], f["team2"]}) or not (teams or rank)

    def top(f) -> bool:
        return f["team1"] in rank and f["team2"] in rank
    # Of the other top-N games on a day, the biggest (lowest combined ranking) goes in the feed; the rest are optional.
    feed_pick: Dict[str, str] = {}
    for f in sorted((f for f in fixtures if top(f) and not ours(f)), key=lambda f: rank[f["team1"]] + rank[f["team2"]]):
        feed_pick.setdefault(f["date"], f.get("match_id") or f"{f['team1']}-{f['team2']}")
    if not args.no_previews:
        for f in fixtures:
            if f.get("format") not in ("T20", "ODI") or not (ours(f) or top(f)):
                continue
            day = date.fromisoformat(f["date"])
            if not today <= day <= today + timedelta(days=args.days):
                continue
            optional = not ours(f) and feed_pick.get(f["date"]) != (f.get("match_id") or f"{f['team1']}-{f['team2']}")
            key = f"preview-{f['team1']}-{f['team2']}-{day}".lower().replace(" ", "-")
            if exists(key) and not args.force:
                print(f"preview {key}: already queued")
                continue
            label = series_label(db, f["team1"], f["team2"], f["format"], day, f["venue"])
            # Out three hours before the start, or at 2 pm IST if that's earlier (an NZ evening start is 1:30 pm IST).
            post_time = None
            if f.get("start_utc"):
                start = datetime.fromisoformat(str(f["start_utc"]).replace("Z", "+00:00")).astimezone(ist)
                out_at = start - timedelta(hours=3)
                if out_at.hour < 14:
                    post_time = out_at.strftime("%-I:%M %p").lower().replace(":00", "")
            print(f"preview {f['team1']} v {f['team2']} on {day} at {f['venue']}: {label}"
                  + (" (optional)" if optional else "") + (f", out at {post_time}" if post_time else ""))
            if args.dry_run:
                continue
            post = ig_backlog.preview_post(db, f["venue"], f["team1"], f["team2"], None, day, label,
                                           f.get("team1_abbr"), f.get("team2_abbr"), f["format"])
            if post["status"] != "resolved":
                print(f"  not made: {post.get('note')}")
                continue
            if not ours(f) and len(post["fact"].get("card_titles") or []) < MIN_PREVIEW_CARDS:
                print(f"  not made: only {len(post['fact'].get('card_titles') or [])} chapters have data")
                continue
            if optional:
                post["fact"]["optional"] = True
            if post_time:
                post["fact"]["post_time"] = post_time
            made.append((post, day))

    if not args.no_recaps:
        rows = db.execute(text("""
            SELECT id, date, team1, team2 FROM matches
            WHERE gender = 'male' AND format IN ('T20', 'ODI') AND match_type = 'international' AND date >= :since
            ORDER BY date
        """), {"since": today - timedelta(days=args.days)}).mappings().all()
        for m in rows:
            if teams and not teams & {m["team1"], m["team2"]}:
                continue
            key = f"recap-{m['id']}"
            if exists(key) and not args.force:
                print(f"recap {key}: already queued")
                continue
            # Your rule: a recap is news until the sides meet again (or for RECAP_DAYS after a one-off / series end).
            post_by = ig_backlog.recap_post_by(m["date"], m["team1"], m["team2"], fixtures)
            if post_by <= datetime.now(timezone.utc):
                print(f"recap {key}: past its window ({post_by:%d %b %H:%M} UTC), not made")
                continue
            print(f"recap {m['team1']} v {m['team2']} on {m['date']} ({m['id']}), post by {post_by:%d %b %H:%M} UTC")
            if args.dry_run:
                continue
            post = ig_backlog.recap_pack(db, str(m["id"]))  # None until the match's ball-by-ball data is in
            if post:
                post["post_by"] = post_by
                made.append((post, post["day"]))
            else:
                print("  not made: no ball-by-ball data for this match yet")

    for post, day in made:
        ig_backlog.add_deep_cut(db, post, day)
        with engine.begin() as conn:
            ig_backlog.upsert_pack(conn, post, day, source="ig-match-day", post_by=post.get("post_by"))
        result = ig_slides.render(post["fact"]["carousel_id"], post["fact"]["slides"], args.base)
        print(f"queued {post['key']} for {day}; rendered {len(result['ok'])}/{post['fact']['slides']} slides"
              + (f", failed {result['failed']}" if result["failed"] else ""))
    if made:
        from services import ig_notes

        print(f"notes and YouTube copy: {ig_notes.extras_pending(db)}")
    print("dry run: nothing saved" if args.dry_run else f"{len(made)} posts queued")
    return 0


if __name__ == "__main__":
    sys.exit(main())
