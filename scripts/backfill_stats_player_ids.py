"""
Fill the player id (migration 027) on batting_stats, bowling_stats and match_players from delivery_details
(PLAYER_IDS_PLAN.md chunk 2): each row's player is the id on his balls in that match and innings (match_players: in
that match, for that side). Rows with no balls carrying an id stay NULL (pre-2015 legacy matches; XI players who
neither batted nor bowled). Idempotent: only rows whose id differs are written.

    python scripts/backfill_stats_player_ids.py --dry-run
    python scripts/backfill_stats_player_ids.py
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BAT = """
    SELECT p_match, inns, bat AS name, MODE() WITHIN GROUP (ORDER BY p_bat) AS pid
    FROM delivery_details WHERE p_bat IS NOT NULL AND bat IS NOT NULL GROUP BY 1, 2, 3
"""
BOWL = """
    SELECT p_match, inns, bowl AS name, MODE() WITHIN GROUP (ORDER BY p_bowl) AS pid
    FROM delivery_details WHERE p_bowl IS NOT NULL AND bowl IS NOT NULL GROUP BY 1, 2, 3
"""
XI = """
    SELECT p_match, team, name, MODE() WITHIN GROUP (ORDER BY pid) AS pid FROM (
        SELECT p_match, team_bat AS team, bat AS name, p_bat AS pid FROM delivery_details WHERE p_bat IS NOT NULL
        UNION ALL
        SELECT p_match, team_bowl, bowl, p_bowl FROM delivery_details WHERE p_bowl IS NOT NULL
    ) x GROUP BY 1, 2, 3
"""
UPDATES = {
    "batting_stats": f"""UPDATE batting_stats t SET pid = x.pid FROM ({BAT}) x
        WHERE t.match_id = x.p_match AND t.innings = x.inns AND t.striker = x.name AND t.pid IS DISTINCT FROM x.pid""",
    "bowling_stats": f"""UPDATE bowling_stats t SET pid = x.pid FROM ({BOWL}) x
        WHERE t.match_id = x.p_match AND t.innings = x.inns AND t.bowler = x.name AND t.pid IS DISTINCT FROM x.pid""",
    "match_players": f"""UPDATE match_players t SET pid = x.pid FROM ({XI}) x
        WHERE t.match_id = x.p_match AND t.team = x.team AND t.player = x.name AND t.pid IS DISTINCT FROM x.pid""",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    from sqlalchemy import text

    from database import engine

    for table, sql in UPDATES.items():
        with engine.begin() as conn:
            if args.dry_run:
                n = conn.execute(text(sql.replace(f"UPDATE {table} t SET pid = x.pid FROM", f"SELECT COUNT(*) FROM {table} t,"))).scalar()
                print(f"{table}: {n} rows would get an id")
                continue
            n = conn.execute(text(sql)).rowcount
            filled, total = conn.execute(text(f"SELECT COUNT(pid), COUNT(*) FROM {table}")).first()
            print(f"{table}: {n} updated · {filled:,} of {total:,} rows have an id")
    return 0


if __name__ == "__main__":
    sys.exit(main())
