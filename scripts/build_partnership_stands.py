"""
Build partnership_stands (migration 016): every stand in delivery_details, from the striker sequence.

    python scripts/build_partnership_stands.py            # matches with no stands yet (nightly)
    python scripts/build_partnership_stands.py --full     # rebuild every stand
    python scripts/build_partnership_stands.py --match 1348645

Why not delivery_details.non_striker: the feed often names the wrong non-striker around a wicket (the
incoming batter on the dismissal ball, the dismissed one just after), so a stand's ending wicket was
credited to a pair that never batted together. Strikers are reliable: a stand is the balls between
two dismissals (any out = 'true', retirements included), its batters the distinct strikers in them,
and when only one of them faced, the partner is the most common non-striker in the run.
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("partnership_stands")

STANDS_SQL = """
WITH b AS (
    SELECT dd.p_match, dd.inns, dd.over, dd.ball,
           COALESCE(pb.alias_name, dd.bat) AS bat,
           COALESCE(pn.alias_name, dd.non_striker) AS ns,
           COALESCE(SUM(CASE WHEN LOWER(dd.out) = 'true' THEN 1 ELSE 0 END) OVER (
               PARTITION BY dd.p_match, dd.inns ORDER BY dd.over, dd.ball
               ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), 0) AS seq
    FROM delivery_details dd
    LEFT JOIN player_alias_unambiguous pb ON pb.player_name = dd.bat
    LEFT JOIN player_alias_unambiguous pn ON pn.player_name = dd.non_striker
    WHERE {scope}
), seg AS (
    SELECT p_match, inns, seq,
           MIN(bat) AS s1, MAX(bat) AS s2, COUNT(DISTINCT bat) AS strikers,
           MODE() WITHIN GROUP (ORDER BY ns) AS ns_mode,
           MIN(ARRAY[over, ball]) AS first_key, MAX(ARRAY[over, ball]) AS last_key
    FROM b GROUP BY p_match, inns, seq
)
INSERT INTO partnership_stands (p_match, inns, seq, batter_a, batter_b, first_over, first_ball,
                                last_over, last_ball, strikers)
SELECT p_match, inns, seq,
       CASE WHEN strikers = 2 THEN s1
            WHEN strikers = 1 AND ns_mode IS NOT NULL AND ns_mode <> s1 THEN LEAST(s1, ns_mode) END,
       CASE WHEN strikers = 2 THEN s2
            WHEN strikers = 1 AND ns_mode IS NOT NULL AND ns_mode <> s1 THEN GREATEST(s1, ns_mode) END,
       first_key[1], first_key[2], last_key[1], last_key[2], strikers
FROM seg
ON CONFLICT (p_match, inns, seq) DO UPDATE SET
    batter_a = EXCLUDED.batter_a, batter_b = EXCLUDED.batter_b,
    first_over = EXCLUDED.first_over, first_ball = EXCLUDED.first_ball,
    last_over = EXCLUDED.last_over, last_ball = EXCLUDED.last_ball, strikers = EXCLUDED.strikers
"""


def build(conn, full: bool = False, match_ids=None) -> int:
    """Insert or refresh stands; returns the number of stand rows written."""
    if match_ids:
        conn.execute(text("DELETE FROM partnership_stands WHERE p_match = ANY(:m)"), {"m": list(match_ids)})
        scope, params = "dd.p_match = ANY(:m)", {"m": list(match_ids)}
    elif full:
        conn.execute(text("TRUNCATE partnership_stands"))
        scope, params = "TRUE", {}
    else:
        # Matches loaded since the last build: no stand rows yet.
        scope = "dd.p_match IN (SELECT DISTINCT d2.p_match FROM delivery_details d2 " \
                "WHERE NOT EXISTS (SELECT 1 FROM partnership_stands s WHERE s.p_match = d2.p_match))"
        params = {}
    result = conn.execute(text(STANDS_SQL.format(scope=scope)), params)
    return result.rowcount


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="rebuild every stand")
    parser.add_argument("--match", action="append", help="rebuild these matches only")
    args = parser.parse_args()

    from database import engine

    t0 = time.time()
    with engine.begin() as conn:
        conn.execute(text("SET LOCAL statement_timeout = '1800s'"))
        written = build(conn, full=args.full, match_ids=args.match)
        total = conn.execute(text("SELECT COUNT(*) FROM partnership_stands")).scalar()
        unpaired = conn.execute(text("SELECT COUNT(*) FROM partnership_stands WHERE batter_a IS NULL")).scalar()
    # print, not log: importing database reconfigures logging.
    print(f"partnership_stands: {written} rows written, {total} in table ({unpaired} unpaired), "
          f"{time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
