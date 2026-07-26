"""
Landing page router - featured innings endpoint
Surfaces recent standout batting performances with wagon wheel data.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.sql import text, bindparam
import logging
import time

from database import get_session
from format_config import get_format

router = APIRouter(prefix="/landing", tags=["landing"])
logger = logging.getLogger(__name__)

# Competitions eligible for the featured innings section (both full and abbreviated DB values)
FEATURED_COMPETITIONS = [
    'Indian Premier League', 'IPL',
    'Big Bash League', 'BBL',
    'Pakistan Super League', 'PSL',
    'Caribbean Premier League', 'CPL',
    'SA20',
    'International League T20', 'ILT20',
    'Bangladesh Premier League', 'BPL',
    'Lanka Premier League',
    'Vitality Blast', 'T20 Blast',
    'Super Smash',
    'The Hundred', "Men's Hundred", "Men's 100",
    'Major League Cricket',
    'Syed Mushtaq Ali Trophy', 'SMAT',
]

# ICC Full Member teams — T20Is only qualify if at least one team is a Full Member
_FULL_MEMBER_TEAMS = {
    'India', 'Australia', 'England', 'West Indies', 'New Zealand',
    'South Africa', 'Pakistan', 'Sri Lanka', 'Bangladesh', 'Afghanistan',
    'Ireland', 'Zimbabwe',
}

# Simple in-memory cache with 1-hour TTL
# Keyed by (format, gender): a single global entry would serve whichever format asked first to
# every other one. Same trap as the query-builder column cache.
_featured_cache: dict = {}
CACHE_TTL = 3600


@router.get("/featured-innings")
def get_featured_innings(
    format: str = Query("T20", description="Cricket format"),
    gender: str = Query("male", description="Men's or women's cricket"),
    db: Session = Depends(get_session),
):
    """
    Return up to 6 standout recent batting innings with wagon wheel data.
    Used on the landing page to showcase impressive performances.
    """
    cache_key = (format, gender)
    now = time.time()
    cached = _featured_cache.get(cache_key)
    if cached and (now - cached["timestamp"]) < CACHE_TTL:
        return cached["data"]

    try:
        spec = get_format(format, gender)
        good_sr = spec.sr_bands[0]
        result = _fetch_featured_innings(
            db, days=30, min_runs=40, min_sr=good_sr, fmt=format, gender=gender
        )

        # Fallback: expand window if too few results
        if len(result) < 3:
            result = _fetch_featured_innings(
                db, days=60, min_runs=30, min_sr=spec.sr_bands[1], fmt=format, gender=gender
            )

        _featured_cache[cache_key] = {"data": result, "timestamp": now}

        return result

    except Exception as e:
        logger.error(f"Error fetching featured innings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _fetch_featured_innings(db: Session, days: int, min_runs: int, min_sr: float,
                            fmt: str = 'T20', gender: str = 'male'):
    """Fetch standout innings and their wagon wheel data."""

    # Step 1: Find standout innings from batting_stats (used as candidate filter)
    # The league whitelist is a T20 concept. Every ODI or Test sits in its format's own bucket
    # or a named ICC event, so for those the format pin above is already the right filter and
    # only the Full Member check is worth keeping.
    if fmt == "T20" and gender == "male":
        competition_clause = (
            "m.competition IN :competitions"
            " OR (m.competition IN ('T20I', 'International Twenty20')"
            "     AND (m.team1 IN :full_members OR m.team2 IN :full_members))"
        )
    else:
        competition_clause = "m.team1 IN :full_members OR m.team2 IN :full_members"

    innings_query = text(f"""
        SELECT bs.match_id, bs.striker, bs.innings, bs.runs, bs.balls_faced,
               bs.strike_rate, bs.fours, bs.sixes, bs.batting_team,
               m.date, m.venue, m.competition, m.team1, m.team2
        FROM batting_stats bs
        JOIN matches m ON bs.match_id = m.id
        WHERE m.date >= CURRENT_DATE - INTERVAL '{days} days'
          AND bs.format = :fmt AND bs.gender = :gender
          AND bs.runs >= :min_runs
          AND bs.strike_rate >= :min_sr
          AND bs.balls_faced >= 15
          AND ({competition_clause})
        ORDER BY bs.runs DESC, bs.strike_rate DESC
        LIMIT 20
    """).bindparams(
        bindparam('competitions', expanding=True),
        bindparam('full_members', expanding=True),
    )

    innings_rows = db.execute(innings_query, {
        "min_runs": min_runs,
        "min_sr": min_sr,
        "fmt": fmt,
        "gender": gender,
        "competitions": FEATURED_COMPETITIONS,
        "full_members": list(_FULL_MEMBER_TEAMS),
    }).fetchall()

    results = []

    for row in innings_rows:
        if len(results) >= 6:
            break

        # Step 2: Fetch wagon wheel deliveries using correct column names
        # delivery_details uses: p_match (not match_id), bat (not batter), inns (not innings)
        deliveries_query = text("""
            SELECT wagon_x, wagon_y, score, cur_bat_runs, cur_bat_bf
            FROM delivery_details
            WHERE p_match = :match_id
              AND bat = :batter_name
              AND inns = :innings
              AND wagon_x IS NOT NULL
              AND wagon_y IS NOT NULL
            ORDER BY over, ball
        """)

        deliveries = db.execute(deliveries_query, {
            "match_id": row.match_id,
            "batter_name": row.striker,
            "innings": row.innings
        }).fetchall()

        # Skip innings with no wagon wheel data
        if not deliveries:
            continue

        # Skip innings where wagon wheel coverage is below 50%
        total_query = text("""
            SELECT COUNT(*) FROM delivery_details
            WHERE p_match = :match_id AND bat = :batter_name AND inns = :innings
        """)
        total = db.execute(total_query, {
            "match_id": row.match_id,
            "batter_name": row.striker,
            "innings": row.innings
        }).scalar()
        if total and len(deliveries) / total < 0.5:
            continue

        # Use accurate runs/balls from delivery_details (last delivery has cumulative stats)
        last = deliveries[-1]
        actual_runs = int(last.cur_bat_runs) if last.cur_bat_runs is not None else row.runs
        actual_balls = int(last.cur_bat_bf) if last.cur_bat_bf is not None else row.balls_faced
        actual_sr = round(actual_runs * 100.0 / actual_balls, 2) if actual_balls else 0

        # Count fours and sixes from delivery-level data for accuracy
        fours = sum(1 for d in deliveries if d.score == 4)
        sixes = sum(1 for d in deliveries if d.score == 6)

        # Determine opponent team
        opponent = row.team2 if row.batting_team == row.team1 else row.team1

        results.append({
            "batter": row.striker,
            "runs": actual_runs,
            "balls": actual_balls,
            "strike_rate": actual_sr,
            "fours": fours,
            "sixes": sixes,
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
