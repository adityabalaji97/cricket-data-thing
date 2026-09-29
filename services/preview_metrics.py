"""
T20 Primer metrics for the match preview: team and player Impact / RAA / WPA over the last year,
and the venue's par score. Men's T20 only (ball_metrics and match_par cover men's T20).

Impact is runs added to the batting side's projected total given the match state; from the
bowling side it is runs saved (sign flipped). RAA is runs above an average batter in the same
situations; WPA is win probability added. All from ball_metrics, joined on delivery_details.id.
"""
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from services.matchups import get_all_team_name_variations

logger = logging.getLogger(__name__)

MIN_PLAYER_BALLS = 60
MIN_TEAM_MATCHES = 5
MIN_PAR_MATCHES = 5


def _team_rows(db: Session, team: str, start: date, end: date) -> Dict[str, Any]:
    names = get_all_team_name_variations(team)
    params = {"teams": names, "start": start.isoformat(), "end": end.isoformat()}
    batting = db.execute(text("""
        SELECT dd.bat AS player,
               COUNT(*) AS balls,
               COUNT(DISTINCT dd.p_match) AS innings,
               SUM(bm.impact::double precision) AS impact,
               SUM(bm.raa::double precision) AS raa,
               SUM(bm.wpa::double precision) AS wpa
        FROM delivery_details dd
        JOIN ball_metrics bm ON bm.delivery_id = dd.id
        JOIN matches m ON m.id = dd.p_match
        WHERE dd.team_bat = ANY(:teams) AND COALESCE(dd.wide, 0) = 0
          AND m.format = 'T20' AND m.gender = 'male'
          AND dd.match_date BETWEEN :start AND :end
        GROUP BY dd.bat
    """), params).mappings().all()
    bowling = db.execute(text("""
        SELECT dd.bowl AS player,
               COUNT(*) AS balls,
               COUNT(DISTINCT dd.p_match) AS innings,
               -SUM(bm.impact::double precision) AS impact,
               -SUM(bm.raa::double precision) AS raa,
               -SUM(bm.wpa::double precision) AS wpa
        FROM delivery_details dd
        JOIN ball_metrics bm ON bm.delivery_id = dd.id
        JOIN matches m ON m.id = dd.p_match
        WHERE dd.team_bowl = ANY(:teams) AND COALESCE(dd.wide, 0) = 0
          AND m.format = 'T20' AND m.gender = 'male'
          AND dd.match_date BETWEEN :start AND :end
        GROUP BY dd.bowl
    """), params).mappings().all()
    matches = db.execute(text("""
        SELECT COUNT(DISTINCT dd.p_match)
        FROM delivery_details dd
        JOIN matches m ON m.id = dd.p_match
        WHERE (dd.team_bat = ANY(:teams) OR dd.team_bowl = ANY(:teams))
          AND m.format = 'T20' AND m.gender = 'male'
          AND dd.match_date BETWEEN :start AND :end
    """), params).scalar() or 0
    return {"batting": [dict(r) for r in batting], "bowling": [dict(r) for r in bowling], "matches": int(matches)}


def _leaders(rows: List[Dict[str, Any]], limit: int = 2) -> List[Dict[str, Any]]:
    eligible = [r for r in rows if (r["balls"] or 0) >= MIN_PLAYER_BALLS and r["impact"] is not None]
    eligible.sort(key=lambda r: r["impact"], reverse=True)
    return [
        {
            "player": r["player"],
            "balls": int(r["balls"]),
            "innings": int(r["innings"]),
            "impact": round(float(r["impact"]), 1),
            "raa": round(float(r["raa"] or 0), 1),
            "wpa": round(float(r["wpa"] or 0), 2),
        }
        for r in eligible[:limit]
    ]


def team_metrics(db: Session, team: str, end: Optional[date] = None, days: int = 365) -> Optional[Dict[str, Any]]:
    end = end or date.today()
    start = end - timedelta(days=days)
    rows = _team_rows(db, team, start, end)
    if rows["matches"] < MIN_TEAM_MATCHES:
        return None
    bat_total = sum(float(r["impact"] or 0) for r in rows["batting"])
    bowl_total = sum(float(r["impact"] or 0) for r in rows["bowling"])
    return {
        "team": team,
        "matches": rows["matches"],
        "window_days": days,
        "batting_impact_per_match": round(bat_total / rows["matches"], 1),
        "bowling_impact_per_match": round(bowl_total / rows["matches"], 1),
        "top_batters": _leaders(rows["batting"]),
        "top_bowlers": _leaders(rows["bowling"]),
    }


def venue_par(db: Session, venue: str, start: Optional[date], end: Optional[date]) -> Optional[Dict[str, Any]]:
    row = db.execute(text("""
        SELECT COUNT(*) AS n, AVG(mp.par) AS par
        FROM matches m
        JOIN match_par mp ON mp.p_match = m.id::text AND mp.format = 'T20' AND mp.gender = 'male'
        WHERE m.venue = :venue AND m.format = 'T20' AND m.gender = 'male'
          AND (CAST(:start AS date) IS NULL OR m.date >= :start)
          AND (CAST(:end AS date) IS NULL OR m.date <= :end)
    """), {"venue": venue, "start": start, "end": end}).mappings().first()
    if not row or (row["n"] or 0) < MIN_PAR_MATCHES or row["par"] is None:
        return None
    return {"par": round(float(row["par"])), "matches": int(row["n"])}


def preview_metrics(db: Session, venue: str, team1: str, team2: str,
                    start: Optional[date], end: Optional[date]) -> Dict[str, Any]:
    """Everything the typed preview needs; empty dict on any failure (the preview must not break)."""
    try:
        return {
            "teams": {team1: team_metrics(db, team1, end), team2: team_metrics(db, team2, end)},
            "venue_par": venue_par(db, venue, start, end),
        }
    except Exception as exc:
        logger.warning("preview metrics failed: %r", exc)
        try:
            db.rollback()
        except Exception:
            pass
        return {}
