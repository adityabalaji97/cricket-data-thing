"""
Landing page router - featured innings endpoint
Surfaces recent standout batting performances with wagon wheel data.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
import logging
import time

from database import get_session

router = APIRouter(prefix="/landing", tags=["landing"])
logger = logging.getLogger(__name__)

# Simple in-memory cache with 1-hour TTL
_featured_cache = {"data": None, "timestamp": 0}
CACHE_TTL = 3600


@router.get("/featured-innings")
def get_featured_innings(db: Session = Depends(get_session)):
    """
    Return up to 6 standout recent batting innings with wagon wheel data.
    Used on the landing page to showcase impressive performances.
    """
    global _featured_cache

    now = time.time()
    if _featured_cache["data"] is not None and (now - _featured_cache["timestamp"]) < CACHE_TTL:
        return _featured_cache["data"]

    try:
        result = _fetch_featured_innings(db, days=30, min_runs=40, min_sr=130)

        # Fallback: expand window if too few results
        if len(result) < 3:
            result = _fetch_featured_innings(db, days=60, min_runs=30, min_sr=120)

        _featured_cache["data"] = result
        _featured_cache["timestamp"] = now

        return result

    except Exception as e:
        logger.error(f"Error fetching featured innings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _fetch_featured_innings(db: Session, days: int, min_runs: int, min_sr: float):
    """Fetch standout innings and their wagon wheel data."""

    # Step 1: Find standout innings from batting_stats
    innings_query = text(f"""
        SELECT bs.match_id, bs.striker, bs.innings, bs.runs, bs.balls_faced,
               bs.strike_rate, bs.fours, bs.sixes, bs.batting_team,
               m.date, m.venue, m.competition, m.team1, m.team2
        FROM batting_stats bs
        JOIN matches m ON bs.match_id = m.id
        WHERE m.date >= CURRENT_DATE - INTERVAL '{days} days'
          AND bs.runs >= :min_runs
          AND bs.strike_rate >= :min_sr
          AND bs.balls_faced >= 15
        ORDER BY bs.runs DESC, bs.strike_rate DESC
        LIMIT 6
    """)

    innings_rows = db.execute(innings_query, {
        "min_runs": min_runs,
        "min_sr": min_sr
    }).fetchall()

    results = []

    for row in innings_rows:
        # Step 2: Look up player alias for delivery_details name
        alias_query = text("""
            SELECT alias_name FROM player_aliases
            WHERE player_name = :player_name
            LIMIT 1
        """)
        alias_row = db.execute(alias_query, {"player_name": row.striker}).fetchone()
        batter_name_dd = alias_row.alias_name if alias_row else row.striker

        # Step 3: Fetch wagon wheel deliveries from delivery_details
        deliveries_query = text("""
            SELECT wagon_x, wagon_y, score
            FROM delivery_details
            WHERE match_id = :match_id
              AND batter = :batter_name
              AND innings = :innings
              AND wagon_x IS NOT NULL
            ORDER BY over, ball
        """)

        deliveries = db.execute(deliveries_query, {
            "match_id": row.match_id,
            "batter_name": batter_name_dd,
            "innings": row.innings
        }).fetchall()

        # Determine opponent team
        opponent = row.team2 if row.batting_team == row.team1 else row.team1

        results.append({
            "batter": row.striker,
            "runs": row.runs,
            "balls": row.balls_faced,
            "strike_rate": round(row.strike_rate, 2) if row.strike_rate else 0,
            "fours": row.fours or 0,
            "sixes": row.sixes or 0,
            "team": row.batting_team,
            "opponent": opponent,
            "venue": row.venue,
            "date": str(row.date),
            "competition": row.competition,
            "match_id": row.match_id,
            "deliveries": [
                {"wagon_x": d.wagon_x, "wagon_y": d.wagon_y, "runs": d.score}
                for d in deliveries
            ]
        })

    return results
