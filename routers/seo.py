"""
Data for the site's sitemap.xml (growth plan G1), formatted into XML by api/sitemap.mjs on Vercel.

Lists the pages worth indexing: every scorecard (one sitemap per year, /seo/scorecards), the most-covered men's T20
players
(their pages carry Impact/WPA nobody else publishes), the busiest venues, and every published note.
Cached for a day -- it changes with the nightly ingest at most -- except notes, which are read
fresh (one small query) so a note is in the sitemap the moment it is published.
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
    from services.notes import sitemap_entries as note_entries

    return {**_data_entries(db), "notes": note_entries(db)}


def _data_entries(db: Session) -> Dict[str, Any]:
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


_YEARS: Dict[str, Any] = {"ts": 0.0, "data": None}


@router.get("/scorecard-years")
def scorecard_years(db: Session = Depends(get_session)) -> Dict[str, Any]:
    """Years with T20 or ODI scorecards, newest first, with their latest match date (a sitemap's lastmod)."""
    if _YEARS["data"] is None or time.time() - _YEARS["ts"] > _TTL:
        rows = db.execute(text("""
            SELECT EXTRACT(YEAR FROM date)::int AS year, COUNT(*) AS n, MAX(date) AS latest FROM matches
            WHERE date IS NOT NULL AND format IN ('T20', 'ODI') GROUP BY 1 ORDER BY 1 DESC
        """)).fetchall()
        _YEARS.update(ts=time.time(), data=[{"year": r.year, "matches": r.n, "lastmod": r.latest.isoformat()}
                                            for r in rows])
    return {"years": _YEARS["data"]}


@router.get("/scorecards")
def scorecards(year: int, db: Session = Depends(get_session)) -> Dict[str, Any]:
    """Every T20 and ODI scorecard of one year (a sitemap holds 50,000 URLs; a year is a few thousand)."""
    rows = db.execute(text("""
        SELECT id, date FROM matches
        WHERE date >= make_date(:y, 1, 1) AND date < make_date(:y + 1, 1, 1) AND format IN ('T20', 'ODI')
        ORDER BY date DESC, id DESC
    """), {"y": year}).fetchall()
    return {"year": year, "matches": [{"id": str(r.id), "date": r.date.isoformat()} for r in rows]}
