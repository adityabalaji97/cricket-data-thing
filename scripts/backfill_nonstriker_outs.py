"""
batting_stats: count a batter's dismissal at the non-striker's end (5 Nov 2026).

Both stats builders (sync_stats_from_dd.py, statsProcessor.py) used to count only the striker's own wicket, so a batter
run out backing up (or retired out) on someone else's ball had wickets = 0 for that innings: every average built on
batting_stats came out high (Virat Kohli's ODIs: 251 striker dismissals on record, 257 official). Both builders now
count it; this sets the rows already written.

For each such dismissal, the batter's row for that innings goes from wickets 0 to 1, with the wickets column of the
phase it fell in. Rows already at 1 are left alone, so it can run again safely. delivery_details matches go by the
dismissed player's id (p_out = batting_stats.pid); legacy matches (pre-2015 T20, none of them in delivery_details) by name (player_dismissed, or its canonical spelling, = striker).
A batter dismissed without facing a ball has no row (a diamond duck) and stays uncounted.

    python scripts/backfill_nonstriker_outs.py            # dry run: how many rows would change, by format
    python scripts/backfill_nonstriker_outs.py --apply    # write, then bump data_version (cached numbers refresh)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

NON_DISMISSALS = "('retired not out (hurt)', 'retired hurt', 'not out')"


def phase_case(fmt: str, gender: str, over: str) -> str:
    """The pp/middle/death prefix for an over, as sync_stats_from_dd._phase_ranges assigns it."""
    from services.analytics_common import phase_bounds

    phases = phase_bounds(fmt, gender)
    names = ["pp", "middle", "death"]
    parts = []
    for i, ph in enumerate(phases):
        if i == len(phases) - 1 or ph.end_over is None:
            parts.append(f"ELSE '{names[i]}'")
        else:
            parts.append(f"WHEN {over} <= {ph.end_over} THEN '{names[i]}'")
    return "CASE " + " ".join(parts) + " END"


def targets_sql() -> str:
    """One row per (batting_stats id, phase) to set: the innings rows still at 0 whose batter was out backing up."""
    cases = " ".join(
        f"WHEN o.format = '{f}' AND o.gender = '{g}' THEN {phase_case(f, g, 'o.over')}"
        for f, g in (("T20", "male"), ("T20", "female"), ("ODI", "male"), ("TEST", "male"))
    )
    return f"""
        WITH dd_outs AS (
            SELECT DISTINCT ON (o.p_match, o.inns, o.p_out)
                o.p_match::text AS match_id, o.inns AS innings, o.p_out AS pid, o.format,
                CASE {cases} ELSE NULL END AS phase
            FROM delivery_details o
            WHERE LOWER(o.out) = 'true' AND LOWER(COALESCE(o.bat_out, '')) = 'false' AND o.p_out IS NOT NULL
              AND LOWER(COALESCE(o.dismissal, '')) NOT IN {NON_DISMISSALS}
            ORDER BY o.p_match, o.inns, o.p_out, o.over, o.ball
        ),
        legacy_outs AS (
            SELECT DISTINCT ON (d.match_id, d.innings, d.player_dismissed)
                d.match_id, d.innings, d.player_dismissed AS striker, 'T20' AS format,
                CASE WHEN d.over < 6 THEN 'pp' WHEN d.over < 15 THEN 'middle' ELSE 'death' END AS phase
            FROM deliveries d
            WHERE d.player_dismissed IS NOT NULL AND d.player_dismissed <> '' AND d.player_dismissed <> d.batter
              AND COALESCE(d.wicket_type, '') <> '' AND LOWER(d.wicket_type) NOT IN {NON_DISMISSALS}
            ORDER BY d.match_id, d.innings, d.player_dismissed, d.over, d.ball
        )
        SELECT bs.id, x.phase, x.format FROM batting_stats bs
        JOIN dd_outs x ON bs.match_id = x.match_id AND bs.innings = x.innings AND bs.pid = x.pid
        WHERE COALESCE(bs.wickets, 0) = 0
        UNION
        SELECT bs.id, x.phase, x.format FROM legacy_outs x
        LEFT JOIN player_alias_map am ON am.name_key = LOWER(x.striker)
        JOIN batting_stats bs ON bs.match_id = x.match_id AND bs.innings = x.innings
         AND bs.striker IN (x.striker, am.canonical_name)
        WHERE COALESCE(bs.wickets, 0) = 0
    """


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    from sqlalchemy import text

    from database import get_session
    from services.query_cache import bump_data_version

    db = next(get_session())
    rows = db.execute(text(targets_sql())).fetchall()
    by_fmt = {}
    for _, _, fmt in rows:
        by_fmt[fmt] = by_fmt.get(fmt, 0) + 1
    print(f"{len(rows)} innings rows to set out at the non-striker's end: {by_fmt}")
    if not args.apply:
        print("dry run: --apply to write")
        return 0
    for phase in ("pp", "middle", "death"):
        ids = [r[0] for r in rows if r[1] == phase]
        if ids:
            db.execute(text(f"UPDATE batting_stats SET wickets = 1, {phase}_wickets = 1 "
                            "WHERE id = ANY(:ids) AND COALESCE(wickets, 0) = 0"), {"ids": ids})
    rest = [r[0] for r in rows if r[1] not in ("pp", "middle", "death")]
    if rest:
        db.execute(text("UPDATE batting_stats SET wickets = 1 WHERE id = ANY(:ids) AND COALESCE(wickets, 0) = 0"),
                   {"ids": rest})
    db.commit()
    print("written; data_version now", bump_data_version(db))
    db.commit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
