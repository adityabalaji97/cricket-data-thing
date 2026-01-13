"""
Games Router - endpoints for interactive game modes.
"""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from database import get_session
from services.visualizations import expand_league_abbreviations

router = APIRouter(prefix="/games", tags=["games"])


@router.get("/guess-innings")
def get_guess_innings(
    leagues: List[str] = Query(default=["IPL", "BBL", "PSL", "CPL", "SA20", "T20 Blast", "T20I"]),
    competitions: List[str] = Query(default=[]),
    start_date: Optional[date] = Query(default=date(2015, 1, 1)),
    end_date: Optional[date] = Query(default=None),
    pool_limit: int = Query(default=1000, ge=1, le=5000),
    min_runs: int = Query(default=0, ge=0),
    min_balls: int = Query(default=0, ge=0),
    min_strike_rate: float = Query(default=0, ge=0),
    include_answer: bool = Query(default=False),
    db: Session = Depends(get_session),
):
    """
    Fetch a random innings (with wagon wheel data) for the Guess the Innings game.

    The innings pool is restricted to the top N by runs, balls faced, or strike rate,
    and is filtered by competition and date range.
    """

    if end_date and start_date and end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date cannot be earlier than start_date")

    expanded_leagues = expand_league_abbreviations(leagues) if leagues else []
    competition_filter = competitions or expanded_leagues
    if not competition_filter:
        raise HTTPException(status_code=400, detail="At least one competition or league must be provided")

    # Simplified query - no CTEs or window functions for speed
    innings_query = text(
        """
        SELECT
            dd.p_match AS match_id,
            dd.inns AS innings,
            dd.bat AS batter,
            dd.ground AS venue,
            dd.competition AS competition,
            dd.match_date AS match_date,
            COUNT(*) AS balls,
            SUM(dd.score) AS runs,
            ROUND(SUM(dd.score)::numeric * 100.0 / NULLIF(COUNT(*), 0), 2) AS strike_rate
        FROM delivery_details dd
        WHERE dd.bat IS NOT NULL
          AND dd.competition = ANY(:competitions)
          AND dd.match_date::date >= :start_date
          AND (:end_date IS NULL OR dd.match_date::date <= :end_date)
          AND dd.wagon_x IS NOT NULL
          AND dd.wagon_y IS NOT NULL
        GROUP BY dd.p_match, dd.inns, dd.bat, dd.ground, dd.competition, dd.match_date
        HAVING COUNT(*) >= :min_balls
          AND SUM(dd.score) >= :min_runs
          AND SUM(dd.score)::float * 100.0 / NULLIF(COUNT(*), 0) >= :min_strike_rate
          AND SUM(CASE WHEN dd.wagon_x != 0 OR dd.wagon_y != 0 THEN 1 ELSE 0 END) >= 5
        ORDER BY RANDOM()
        LIMIT 1
        """
    )

    result = db.execute(
        innings_query,
        {
            "competitions": competition_filter,
            "start_date": start_date,
            "end_date": end_date,
            "min_runs": min_runs,
            "min_balls": min_balls,
            "min_strike_rate": min_strike_rate,
        },
    ).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="No innings found for the specified filters")

    deliveries_query = text(
        """
        SELECT
            dd.over,
            dd.ball,
            dd.score AS runs,
            dd.shot,
            dd.bowl AS bowler,
            dd.wagon_x,
            dd.wagon_y,
            dd.wagon_zone,
            dd.bat_hand,
            dd.team_bat AS batting_team,
            dd.team_bowl AS bowling_team,
            dd.cur_bat_runs,
            dd.cur_bat_bf
        FROM delivery_details dd
        WHERE dd.p_match = :match_id
          AND dd.inns = :innings
          AND dd.bat = :batter
          AND dd.wagon_x IS NOT NULL
          AND dd.wagon_y IS NOT NULL
        ORDER BY dd.over, dd.ball
        """
    )

    deliveries = db.execute(
        deliveries_query,
        {
            "match_id": result.match_id,
            "innings": result.innings,
            "batter": result.batter,
        },
    ).fetchall()

    if not deliveries:
        raise HTTPException(status_code=404, detail="No wagon wheel deliveries found for this innings")

    # Extract bat_hand and teams from first delivery
    first_delivery = deliveries[0] if deliveries else None
    last_delivery = deliveries[-1] if deliveries else None
    bat_hand = first_delivery.bat_hand if first_delivery else None
    batting_team = first_delivery.batting_team if first_delivery else None
    bowling_team = first_delivery.bowling_team if first_delivery else None

    # Use cur_bat_runs and cur_bat_bf from last delivery for accurate batter stats
    batter_runs = int(last_delivery.cur_bat_runs) if last_delivery and last_delivery.cur_bat_runs is not None else int(result.runs) if result.runs else 0
    batter_balls = int(last_delivery.cur_bat_bf) if last_delivery and last_delivery.cur_bat_bf is not None else int(result.balls) if result.balls else 0
    batter_sr = round((batter_runs * 100.0 / batter_balls), 2) if batter_balls > 0 else 0.0

    payload = {
        "innings": {
            "match_id": result.match_id,
            "innings": result.innings,
            "venue": result.venue,
            "competition": result.competition,
            "match_date": str(result.match_date) if result.match_date else None,
            "runs": batter_runs,
            "balls": batter_balls,
            "strike_rate": batter_sr,
            "bat_hand": bat_hand,
            "batting_team": batting_team,
            "bowling_team": bowling_team,
        },
        "deliveries": [
            {
                "over": row.over,
                "ball": row.ball,
                "runs": row.runs,
                "shot": row.shot,
                "bowler": row.bowler,
                "wagon_x": row.wagon_x,
                "wagon_y": row.wagon_y,
                "wagon_zone": row.wagon_zone,
            }
            for row in deliveries
        ],
        "filters": {
            "competitions": competition_filter,
            "start_date": str(start_date) if start_date else None,
            "end_date": str(end_date) if end_date else None,
            "pool_limit": pool_limit,
            "min_runs": min_runs,
            "min_balls": min_balls,
            "min_strike_rate": min_strike_rate,
        },
    }

    if include_answer:
        payload["answer"] = {
            "batter": result.batter,
        }

    return payload
