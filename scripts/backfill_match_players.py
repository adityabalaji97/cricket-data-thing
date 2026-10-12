#!/usr/bin/env python3
"""
Backfill match_players (migration 020) from Cricsheet's full archives: the playing XI of every men's T20 and ODI in
`matches`, whatever source loaded the match. Idempotent (upsert). The nightly Cricsheet step keeps it current after.

    python scripts/backfill_match_players.py                       # the archives below, against DATABASE_URL
    python scripts/backfill_match_players.py --zip path/or/url.zip --dry-run

Matches are read from the zip in batches (BATCH) so memory stays flat; names resolve as the loader does
(scripts/load_cricsheet.NameResolver: Cricsheet id -> ESPNcricinfo id -> the feed's name).
"""
from __future__ import annotations

import argparse
import io
import json
import logging
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

ARCHIVES = ("https://cricsheet.org/downloads/t20s_male_json.zip", "https://cricsheet.org/downloads/odis_male_json.zip",
            "https://cricsheet.org/downloads/ipl_male_json.zip", "https://cricsheet.org/downloads/bbl_male_json.zip",
            "https://cricsheet.org/downloads/psl_male_json.zip", "https://cricsheet.org/downloads/cpl_male_json.zip",
            "https://cricsheet.org/downloads/sat_male_json.zip", "https://cricsheet.org/downloads/ilt_male_json.zip",
            "https://cricsheet.org/downloads/bpl_male_json.zip", "https://cricsheet.org/downloads/lpl_male_json.zip",
            "https://cricsheet.org/downloads/ntb_male_json.zip", "https://cricsheet.org/downloads/mlc_male_json.zip",
            "https://cricsheet.org/downloads/ssm_male_json.zip", "https://cricsheet.org/downloads/sma_male_json.zip")
BATCH = 500


def batches(raw: bytes):
    from load_cricsheet import CricsheetMatch

    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = [n for n in zf.namelist() if n.endswith(".json")]
        for i in range(0, len(names), BATCH):
            yield [CricsheetMatch(os.path.basename(n)[:-5], json.loads(zf.read(n))) for n in names[i:i + BATCH]]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", action="append", help="a Cricsheet zip (path or URL); repeatable; default: ARCHIVES")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
    from sqlalchemy import text

    from database import get_database_connection
    from load_cricsheet import NameResolver, _fetch, read_people_register, write_playing_xis

    register = read_people_register()
    _, SessionLocal = get_database_connection()
    total = 0
    for source in args.zip or ARCHIVES:
        try:
            raw = _fetch(source)
        except Exception as e:  # an archive Cricsheet doesn't publish (or a typo): skip it
            logger.warning(f"{source}: {e}")
            continue
        for batch in batches(raw):
            session = SessionLocal()
            try:
                ids = [m.match_id for m in batch]
                known = {r[0] for r in session.execute(text("SELECT id FROM matches WHERE id = ANY(:ids)"), {"ids": ids})}
                batch = [m for m in batch if m.match_id in known]
                if not batch:
                    continue
                if args.dry_run:
                    total += sum(len(p) for m in batch for p in (m.info.get("players") or {}).values())
                    continue
                name_of = NameResolver.build(session, batch, register)
                total += write_playing_xis(session, batch, name_of)
                session.commit()
            finally:
                session.close()
        logger.info(f"{source}: {total} rows so far")
    logger.info(f"done: {total} rows{' (dry run)' if args.dry_run else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
