"""
All-grounds baselines for the boundary-zone (B6) and dismissal (B8) preview cards.

Both cards compare one ground with every men's T20 ground. That baseline takes ~11s to compute
from delivery_details and moves by tenths of a percent a year, so it is stored in
services/preview_cards/baselines.json instead of being recomputed per request. Re-run after a
large data load:

    python analysis/preview/build_baselines.py            # reads hindsight_analysis
"""
import json
import os
from datetime import date
from pathlib import Path

import psycopg2

DSN = os.getenv("BASELINE_DSN", "dbname=hindsight_analysis")
OUT = Path(__file__).resolve().parents[2] / "services" / "preview_cards" / "baselines.json"

con = psycopg2.connect(DSN)
cur = con.cursor()
cur.execute("""
    SELECT wagon_zone, COUNT(*) FROM delivery_details
    WHERE format = 'T20' AND gender = 'male' AND batruns IN (4, 6) AND wagon_zone BETWEEN 1 AND 8
    GROUP BY 1 ORDER BY 1
""")
zones = dict(cur.fetchall())
cur.execute("""
    SELECT CASE WHEN dismissal = 'caught' THEN 'caught' WHEN dismissal = 'bowled' THEN 'bowled'
                WHEN dismissal = 'leg before wicket' THEN 'lbw' ELSE 'other' END, COUNT(*)
    FROM delivery_details
    WHERE format = 'T20' AND gender = 'male'
      AND dismissal IN ('caught', 'bowled', 'leg before wicket', 'stumped', 'hit wicket', 'caught and bowled')
    GROUP BY 1
""")
kinds = dict(cur.fetchall())
zn, kn = sum(zones.values()), sum(kinds.values())
OUT.write_text(json.dumps({
    "built": date.today().isoformat(),
    "source": "men's T20, every ground, 2015+ (delivery_details)",
    "boundary_zones": {"n": zn, "share": {str(z): round(c / zn, 5) for z, c in sorted(zones.items())}},
    "dismissals": {"n": kn, "share": {k: round(c / kn, 5) for k, c in sorted(kinds.items())}},
}, indent=2) + "\n")
print(OUT.read_text())
