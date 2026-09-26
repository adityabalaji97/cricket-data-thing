#!/usr/bin/env python3
"""
Weekly adoption check-in (growth plan G0): prints the same numbers as GET /admin/usage.

    python scripts/usage_report.py            # last 8 weeks
    python scripts/usage_report.py --weeks 12 --json

Reads the production database via DATABASE_URL (.env), read-only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Rolling targets from the growth plan; the report flags the current stage's gap.
TARGETS = [
    ("Next 4 weeks", {"users": 100}),
    ("BBL / SA20 / ILT20 (Dec-Jan)", {"users": 500, "distinct_callers": 10}),
    ("IPL 2027 (Mar-May)", {"users": 3000}),
]

COLUMNS = [
    ("users", "WAU"), ("returning_users", "return"), ("sessions", "sess"), ("page_views", "views"),
    ("query_runs", "queries"), ("nl_searches", "NL"), ("game_players", "gamers"), ("shares", "shares"),
    ("calls", "MCP calls"), ("distinct_callers", "MCP users"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--weeks", type=int, default=8)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    from sqlalchemy.sql import text

    from database import get_session
    from services.usage_report import build_usage_report

    db = next(get_session())
    db.execute(text("SET TRANSACTION READ ONLY"))
    report = build_usage_report(db, args.weeks)
    if args.json:
        print(json.dumps(report, indent=2, default=str))
        return

    header = f"{'week':<11}" + "".join(f"{label:>10}" for _, label in COLUMNS)
    print(header)
    print("-" * len(header))
    for week in report["weeks"]:
        print(f"{week['week']:<11}" + "".join(f"{week.get(key, 0) or 0:>10}" for key, _ in COLUMNS))

    latest = report["weeks"][0] if report["weeks"] else {}
    stage, goals = TARGETS[0]
    gaps = ", ".join(f"{k} {latest.get(k, 0) or 0}/{v}" for k, v in goals.items())
    print(f"\nTarget ({stage}): {gaps}")

    last7 = report["last_7_days"]
    for title, key, label in (("Top pages", "top_pages", "path"), ("Sources", "referrers", "source"),
                              ("Countries", "countries", "country")):
        items = ", ".join(f"{row[label]} ({row.get('users') or row.get('views')})" for row in last7[key][:8])
        print(f"{title} (7d): {items or '-'}")


if __name__ == "__main__":
    main()
