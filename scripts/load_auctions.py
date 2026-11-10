#!/usr/bin/env python3
"""
Load the IPL auction lots and bids (migration 038) from data/auction_raw into the database DATABASE_URL points at.

    DATABASE_URL=postgresql://localhost:5432/hindsight_local python scripts/load_auctions.py [--raw data/auction_raw]

Prints how many lots matched one of our players and the ones that didn't (newest first), for a manual check.
"""
import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
logging.disable(logging.INFO)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=str(ROOT / "data/auction_raw"))
    ap.add_argument("--match-url", help="match players in this database (read-only) instead, e.g. production for a local load")
    args = ap.parse_args()
    from database import get_session
    from services.auctions import load

    match_db = None
    if args.match_url:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        url = args.match_url.replace("postgres://", "postgresql://", 1)  # Heroku URLs say postgres://
        match_db = Session(create_engine(url))
    out = load(next(get_session()), Path(args.raw), match_db=match_db)
    um = out["unmatched"]
    print(f"{out['lots']} lots, {out['bids']} bids, {out['players']} player-years; {len(um)} unmatched")
    for n, y in um[:60]:
        print(f"  {y} {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
