#!/usr/bin/env python3
"""
The IPL 2027 trade window's moves (squad_moves, migration 040), as known on 11 Nov 2026. Re-runnable: replaces the
season's trades. Retained / released lists (17 Nov) and auction buys (16 Dec) get their own loaders.

    DATABASE_URL=... python scripts/seed_squad_moves.py
"""
import logging
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
logging.disable(logging.INFO)

# deal, player (our display name), from, to, price (lakh: the salary he moves on), state, source, announced
TRADES = [
    ("csk-srh-1", "Liam Livingstone", "SRH", "CSK", 600, "confirmed", "Chennai Super Kings' announcement", date(2026, 11, 5)),
    ("csk-srh-1", "Jack Edwards", "SRH", "CSK", 300, "confirmed", "Chennai Super Kings' announcement", date(2026, 11, 5)),
    ("csk-srh-1", "Khaleel Ahmed", "CSK", "SRH", 480, "confirmed", "Chennai Super Kings' announcement", date(2026, 11, 5)),
    ("csk-srh-1", "Nathan Ellis", "CSK", "SRH", 200, "confirmed", "Chennai Super Kings' announcement", date(2026, 11, 5)),
    ("dc-srh-1", "T Natarajan", "DC", "SRH", 500, "confirmed", "IPL trade tracker", None),
    ("dc-srh-1", "Zeeshan Ansari", "SRH", "DC", 40, "confirmed", "IPL trade tracker", None),
    ("lsg-dc-1", "Rishabh Pant", "LSG", "DC", 1500, "confirmed", "IPL trade tracker", None),
    ("lsg-dc-1", "Kuldeep Yadav", "DC", "LSG", 1350, "confirmed", "IPL trade tracker", None),
    ("pbks-mi-1", "Hardik Pandya", "MI", "PBKS", 1635, "reported", "agreed and reported, awaiting BCCI ratification",
     date(2026, 11, 7)),
    ("pbks-mi-1", "Arshdeep Singh", "PBKS", "MI", 1800, "reported", "agreed and reported, awaiting BCCI ratification",
     date(2026, 11, 7)),
]


def main() -> int:
    from sqlalchemy import text

    from database import get_session

    db = next(get_session())
    db.execute(text("DELETE FROM squad_moves WHERE league = 'ipl' AND season = 2027 AND kind = 'trade'"))
    for deal, name, frm, to, price, state, source, when in TRADES:
        pid = db.execute(text("SELECT pid FROM player_identity WHERE display_name = :n"), {"n": name}).scalar()
        assert pid, f"{name}: not one of our players"
        db.execute(text("""INSERT INTO squad_moves (season, deal, player_name, pid, from_team, to_team, price_lakh, kind,
                                                    state, source, announced)
                           VALUES (2027, :d, :n, :p, :f, :t, :pr, 'trade', :st, :src, :a)"""),
                   {"d": deal, "n": name, "p": pid, "f": frm, "t": to, "pr": price, "st": state, "src": source, "a": when})
    db.commit()
    print(f"{len(TRADES)} trade moves for 2027")
    return 0


if __name__ == "__main__":
    sys.exit(main())
