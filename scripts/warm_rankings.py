#!/usr/bin/env python3
"""Precompute the global T20 rankings payloads the site asks for, right after the nightly load.

A rankings payload is a league-wide computation (1-2.5 s locally, several times that on
production), and a player's ranking card needs seven: the selected window plus six month-end
snapshots. Cold, /rankings/player took ~28 s and production returned 503s. Payloads are cached in
query_cache keyed by data_version (services/global_t20_rankings._build_rankings_payload), so the
nightly load invalidates them; this script refills the ones the pages request by default:

* the profile page's ranking card: 1 January PROFILE_WINDOW_YEARS back -> today, batting and bowling;
* the rankings page: today minus 2 years -> today, all / pace / spin;
* the trajectory snapshots: the last SNAPSHOTS month-ends (24-month windows), every mode and kind.

"Today" is the UTC date, as the frontend computes it (toISOString); the workflow runs at 23:30 UTC,
so tomorrow's date-dependent windows are warmed too. Keep the constants in step with
src/utils/dateDefaults.js (PROFILE_WINDOW_YEARS), GlobalT20Rankings.jsx (2-year preset, snapshots=6)
and UnifiedPlayerProfile.jsx (snapshots=6).

Usage: python scripts/warm_rankings.py [--dry-run]
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal  # noqa: E402
from services import global_t20_rankings as rankings  # noqa: E402

PROFILE_WINDOW_YEARS = 6
RANKINGS_PAGE_YEARS = 2
SNAPSHOTS = 6
MODES = ("batting", "bowling")
BOWL_KINDS = ("all", "pace", "spin")


def _years_back(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year - years)
    except ValueError:  # 29 February
        return d.replace(year=d.year - years, day=28)


def windows_for(today: date):
    """(mode, bowl_kind, start, end) for every payload the pages request by default on `today`."""
    out = set()
    profile_start = date(today.year - PROFILE_WINDOW_YEARS, 1, 1)
    for mode in MODES:
        out.add((mode, "all", profile_start, today))
        for kind in BOWL_KINDS:
            out.add((mode, kind, _years_back(today, RANKINGS_PAGE_YEARS), today))
    # Same arithmetic as global_t20_rankings._build_player_trajectory.
    anchor = rankings._month_end(today)
    for idx in range(SNAPSHOTS):
        month_end = rankings._month_end(rankings._add_months(anchor, -(SNAPSHOTS - 1 - idx)))
        start = rankings._add_months(month_end, -24) + timedelta(days=1)
        for mode in MODES:
            for kind in BOWL_KINDS:
                out.add((mode, kind, start, month_end))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="List the windows without computing")
    args = parser.parse_args()

    today = datetime.now(timezone.utc).date()
    work = sorted(windows_for(today) | windows_for(today + timedelta(days=1)),
                  key=lambda w: (w[3], w[2], w[0], w[1]))
    print(f"{len(work)} rankings payloads to warm (UTC today {today})")
    if args.dry_run:
        for w in work:
            print("  ", *w)
        return 0

    db = SessionLocal()
    failures = 0
    started = time.time()
    try:
        for mode, kind, start, end in work:
            t = time.time()
            try:
                payload = rankings._build_rankings_payload(db, mode, start, end, kind)
                print(f"  ok  {mode:8s} {kind:5s} {start} -> {end}  {payload.get('total', 0):4d} rows  {time.time() - t:5.1f}s")
            except Exception as exc:  # keep warming the rest; the endpoint will compute on demand
                failures += 1
                db.rollback()
                print(f"  ERR {mode:8s} {kind:5s} {start} -> {end}  {exc!r}")
    finally:
        db.close()
    print(f"done in {time.time() - started:.0f}s, {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
