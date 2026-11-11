#!/usr/bin/env python3
"""
Load the IPL retained and released lists (17 Nov 2026) and the auction's buys (16 Dec 2026) into squad_moves
(migration 040; XI_BUILDER_PLAN.md X8).

    python scripts/load_squad_lists.py lists.csv            # dry run: names matched, counts per team
    python scripts/load_squad_lists.py lists.csv --write    # replace the season's retained/released moves

CSV columns: team (IPL code: CSK, MI, ...), player (as published), status (retained | released | bought),
price_crore (the retention price, or the auction price for a buy: required for a buy), source (optional). A file of
buys replaces the season's buys; a file of retained / released replaces those. Names are matched to ours (services/name_match.py); an unmatched
name stops a --write, so nobody is silently dropped. After a write the team pages pick it up (team_squad's key
includes the latest move), and released players join the "who fits" auction pool.
"""
import argparse
import csv
import logging
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
logging.disable(logging.INFO)

SEASON = 2027


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--date", default=date.today().isoformat())
    args = ap.parse_args()
    from sqlalchemy import text

    from database import get_session
    from services.name_match import match_display_name
    from services.squad_view import TEAMS

    db = next(get_session())
    rows, missing = [], []
    for r in csv.DictReader(open(args.csv)):
        team, status = r["team"].strip().upper(), r["status"].strip().lower()
        assert team in TEAMS, f"unknown team {team!r}"
        assert status in ("retained", "released", "bought"), f"status must be retained, released or bought: {status!r}"
        assert status != "bought" or r.get("price_crore"), f"a buy needs its price: {r['player']}"
        name = match_display_name(db, r["player"])
        pid = db.execute(text("SELECT pid FROM player_identity WHERE display_name = :n"), {"n": name}).scalar() if name else None
        if not pid:
            missing.append((team, r["player"]))
            continue
        price = r.get("price_crore")
        rows.append({"n": name, "p": pid, "team": team, "kind": status,
                     "price": round(float(price) * 100, 2) if price not in (None, "") else None,
                     "src": (r.get("source") or "IPL retention lists").strip(), "a": args.date})
    for team in TEAMS:
        kept = sum(1 for x in rows if x["team"] == team and x["kind"] == "retained")
        gone = sum(1 for x in rows if x["team"] == team and x["kind"] == "released")
        bought = [x for x in rows if x["team"] == team and x["kind"] == "bought"]
        if kept or gone or bought:
            print(f"{team}: {kept} retained, {gone} released, {len(bought)} bought"
                  + (f" (₹{sum(x['price'] or 0 for x in bought) / 100:.2f} crore)" if bought else ""))
    if missing:
        print("UNMATCHED (fix the spelling or add an alias):", missing)
    if not args.write:
        return 1 if missing else 0
    assert not missing, "unmatched names: not writing"
    kinds = sorted({x["kind"] for x in rows})
    db.execute(text("DELETE FROM squad_moves WHERE league = 'ipl' AND season = :s AND kind = ANY(:k)"), {"s": SEASON, "k": kinds})
    db.execute(text("""
        INSERT INTO squad_moves (season, player_name, pid, from_team, to_team, price_lakh, kind, state, source, announced)
        VALUES (:s, :n, :p, CASE WHEN :kind = 'released' THEN :team END, CASE WHEN :kind IN ('retained', 'bought') THEN :team END,
                :price, :kind, 'confirmed', :src, CAST(:a AS date))"""), [{**x, "s": SEASON} for x in rows])
    db.commit()
    print(f"wrote {len(rows)} moves")
    return 0


if __name__ == "__main__":
    sys.exit(main())
