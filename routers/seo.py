"""
Data for the site's sitemap.xml (growth plan G1), formatted into XML by api/sitemap.mjs on Vercel.

Lists the pages worth indexing: scorecards from the last year, the most-covered men's T20 players
(their pages carry Impact/WPA nobody else publishes), and the busiest venues. Cached for a day --
it changes with the nightly ingest at most.
"""

from __future__ import annotations

import time
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from database import get_session

router = APIRouter(prefix="/seo", tags=["seo"])

_CACHE: Dict[str, Any] = {"ts": 0.0, "data": None}
_TTL = 24 * 3600


@router.get("/sitemap-entries")
def sitemap_entries(db: Session = Depends(get_session)) -> Dict[str, Any]:
    if _CACHE["data"] is not None and time.time() - _CACHE["ts"] < _TTL:
        return _CACHE["data"]
    matches = db.execute(text("""
        SELECT id, date FROM matches
        WHERE date >= now() - interval '365 days' AND format IN ('T20', 'ODI')
        ORDER BY date DESC LIMIT 5000
    """)).fetchall()
    players = db.execute(text("""
        SELECT dd.bat AS name, COUNT(*) AS balls
        FROM delivery_details dd
        WHERE dd.format = 'T20' AND dd.gender = 'male' AND dd.year >= EXTRACT(YEAR FROM now())::int - 3
          AND dd.bat IS NOT NULL
        GROUP BY dd.bat ORDER BY balls DESC LIMIT 500
    """)).fetchall()
    venues = db.execute(text("""
        SELECT venue, COUNT(*) AS n FROM matches
        WHERE venue IS NOT NULL AND date >= now() - interval '4 years'
        GROUP BY venue ORDER BY n DESC LIMIT 200
    """)).fetchall()
    data = {
        "matches": [{"id": str(r.id), "date": r.date.isoformat() if r.date else None} for r in matches],
        "players": [r.name for r in players],
        "venues": [r.venue for r in venues],
    }
    _CACHE.update(ts=time.time(), data=data)
    return data
