"""
Player Line & Length Profile
============================
Returns line/length aggregated stats for a player compared against
global averages, optional similar-player averages, and (for bowlers)
same bowl_kind / bowl_style averages.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from typing import Optional, List
from datetime import date
import logging

from database import get_session
from utils.league_utils import expand_league_abbreviations

router = APIRouter(tags=["Player Line & Length"])
logger = logging.getLogger(__name__)

# Top international teams (matches games.py)
TOP_INTERNATIONAL_TEAMS = [
    'India', 'Australia', 'England', 'West Indies', 'New Zealand',
    'South Africa', 'Pakistan', 'Sri Lanka', 'Bangladesh', 'Afghanistan',
    'Ireland', 'Zimbabwe', 'Scotland', 'Netherlands', 'Namibia',
    'UAE', 'Nepal', 'USA', 'Oman', 'Papua New Guinea'
]

LENGTH_LABELS = {
    "FULL_TOSS": "Full Toss",
    "YORKER": "Yorker",
    "FULL": "Full",
    "GOOD_LENGTH": "Good Length",
    "SHORT_OF_LENGTH": "Short of Length",
    "SHORT": "Short",
}

LINE_LABELS = {
    "DOWN_LEG": "Down Leg",
    "LEG_STUMP": "Leg Stump",
    "MIDDLE": "Middle",
    "OFF_STUMP": "Off Stump",
    "OUTSIDE_OFF": "Outside Off",
    "WIDE_OUTSIDE_OFF": "Wide Outside Off",
}


def _build_match_filter(params: dict, leagues: Optional[List[str]],
                        include_international: bool,
                        top_teams: Optional[int]) -> str:
    """Build the competition / match-type filter clause."""
    expanded = expand_league_abbreviations(leagues) if leagues else []
    params["has_leagues"] = bool(expanded)
    params["leagues"] = expanded
    params["include_international"] = include_international
    params["top_teams"] = top_teams is not None
    params["top_team_list"] = TOP_INTERNATIONAL_TEAMS[:top_teams] if top_teams else []

    return """
        AND (
            (:has_leagues AND m.match_type = 'league' AND m.competition = ANY(:leagues))
            OR (:include_international AND m.match_type = 'international'
                AND (:top_teams IS NULL OR
                    (m.team1 = ANY(:top_team_list) AND m.team2 = ANY(:top_team_list))
                )
            )
        )
    """


def _aggregate_sql(group_col: str, player_filter: str, match_filter: str) -> str:
    """Return SQL that aggregates line/length metrics from delivery_details."""
    return f"""
        SELECT
            dd.{group_col}                                      AS bucket,
            COUNT(*)                                            AS balls,
            SUM(dd.batruns)                                     AS runs,
            SUM(CASE WHEN dd.out THEN 1 ELSE 0 END)            AS wickets,
            CAST(SUM(dd.batruns) * 100.0 AS FLOAT)
                / NULLIF(COUNT(*), 0)                           AS strike_rate,
            CAST(SUM(CASE WHEN dd.control = 1 THEN 1 ELSE 0 END) * 100.0 AS FLOAT)
                / NULLIF(COUNT(*), 0)                           AS control_pct,
            CAST(SUM(CASE WHEN dd.batruns >= 4 THEN 1 ELSE 0 END) * 100.0 AS FLOAT)
                / NULLIF(COUNT(*), 0)                           AS boundary_pct,
            CAST(SUM(CASE WHEN dd.batruns = 0 AND COALESCE(dd.wide, 0) = 0
                              AND COALESCE(dd.noball, 0) = 0 THEN 1 ELSE 0 END) * 100.0 AS FLOAT)
                / NULLIF(COUNT(*), 0)                           AS dot_pct
        FROM delivery_details dd
        JOIN matches m ON dd.match_id = m.id
        WHERE dd.{group_col} IS NOT NULL
        {player_filter}
        AND (:start_date IS NULL OR dd.date >= :start_date)
        AND (:end_date IS NULL OR dd.date <= :end_date)
        AND (:venue IS NULL OR m.venue = :venue)
        {match_filter}
        GROUP BY dd.{group_col}
    """


def _row_to_metrics(row) -> dict:
    """Extract rounded metrics from a SQL result row."""
    return {
        "strike_rate": round(row.strike_rate, 1) if row.strike_rate else 0,
        "control_pct": round(row.control_pct, 1) if row.control_pct else 0,
        "boundary_pct": round(row.boundary_pct, 1) if row.boundary_pct else 0,
        "dot_pct": round(row.dot_pct, 1) if row.dot_pct else 0,
    }


@router.get("/player/{player_name}/line-length-profile")
def get_player_line_length_profile(
    player_name: str,
    mode: str = Query(default="batting", regex="^(batting|bowling)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    leagues: List[str] = Query(default=[]),
    include_international: bool = Query(default=False),
    top_teams: Optional[int] = Query(default=None),
    venue: Optional[str] = None,
    similar_players: List[str] = Query(default=[], alias="similar_players"),
    db: Session = Depends(get_session),
):
    try:
        base_params: dict = {
            "player_name": player_name,
            "start_date": start_date,
            "end_date": end_date,
            "venue": venue,
        }
        match_filter = _build_match_filter(
            base_params, leagues, include_international, top_teams
        )

        player_col = "batter" if mode == "batting" else "bowler"
        player_filter = f"AND dd.{player_col} = :player_name"

        # Helper to run an aggregate query
        def _fetch(group_col, extra_filter, extra_params=None):
            p = {**base_params}
            if extra_params:
                p.update(extra_params)
            sql = _aggregate_sql(group_col, extra_filter, match_filter)
            rows = db.execute(text(sql), p).fetchall()
            return {r.bucket: r for r in rows}

        # 1. Player stats
        player_length = _fetch("length", player_filter)
        player_line = _fetch("line", player_filter)

        # 2. Global averages (no player filter)
        global_length = _fetch("length", "")
        global_line = _fetch("line", "")

        # 3. Similar players averages
        similar_length = {}
        similar_line = {}
        if similar_players:
            sim_filter = f"AND dd.{player_col} = ANY(:similar_list)"
            sim_extra = {"similar_list": similar_players}
            similar_length = _fetch("length", sim_filter, sim_extra)
            similar_line = _fetch("line", sim_filter, sim_extra)

        # 4. Bowl-kind / bowl-style averages (bowling mode only)
        bowler_info = None
        bk_length, bk_line = {}, {}
        bs_length, bs_line = {}, {}

        if mode == "bowling":
            detect_sql = text("""
                SELECT bowl_kind, bowl_style, COUNT(*) as cnt
                FROM delivery_details
                WHERE bowler = :player_name AND bowl_kind IS NOT NULL
                GROUP BY bowl_kind, bowl_style
                ORDER BY cnt DESC LIMIT 1
            """)
            detect_row = db.execute(detect_sql, {"player_name": player_name}).fetchone()
            if detect_row:
                bowler_info = {
                    "bowl_kind": detect_row.bowl_kind,
                    "bowl_style": detect_row.bowl_style,
                }
                bk_filter = "AND dd.bowl_kind = :bowl_kind"
                bk_extra = {"bowl_kind": detect_row.bowl_kind}
                bk_length = _fetch("length", bk_filter, bk_extra)
                bk_line = _fetch("line", bk_filter, bk_extra)

                if detect_row.bowl_style:
                    bs_filter = "AND dd.bowl_style = :bowl_style"
                    bs_extra = {"bowl_style": detect_row.bowl_style}
                    bs_length = _fetch("length", bs_filter, bs_extra)
                    bs_line = _fetch("line", bs_filter, bs_extra)

        # 5. Assemble response
        def _build_profile(player_data, global_data, similar_data, bk_data, bs_data, label_map):
            result = []
            for bucket, prow in player_data.items():
                entry = {
                    "bucket": bucket,
                    "label": label_map.get(bucket, bucket),
                    "player": {
                        "balls": prow.balls,
                        **_row_to_metrics(prow),
                    },
                    "global_avg": _row_to_metrics(global_data[bucket]) if bucket in global_data else None,
                    "similar_avg": _row_to_metrics(similar_data[bucket]) if bucket in similar_data else None,
                    "bowl_kind_avg": _row_to_metrics(bk_data[bucket]) if bucket in bk_data else None,
                    "bowl_style_avg": _row_to_metrics(bs_data[bucket]) if bucket in bs_data else None,
                }
                result.append(entry)
            result.sort(key=lambda x: x["player"]["balls"], reverse=True)
            return result

        length_profile = _build_profile(
            player_length, global_length, similar_length, bk_length, bs_length, LENGTH_LABELS
        )
        line_profile = _build_profile(
            player_line, global_line, similar_line, bk_line, bs_line, LINE_LABELS
        )

        # Data coverage
        coverage_sql = text(f"""
            SELECT COUNT(*) as total,
                   COUNT(CASE WHEN dd.length IS NOT NULL THEN 1 END) as with_length,
                   COUNT(CASE WHEN dd.line IS NOT NULL THEN 1 END) as with_line
            FROM delivery_details dd
            JOIN matches m ON dd.match_id = m.id
            WHERE dd.{player_col} = :player_name
            AND (:start_date IS NULL OR dd.date >= :start_date)
            AND (:end_date IS NULL OR dd.date <= :end_date)
            AND (:venue IS NULL OR m.venue = :venue)
            {match_filter}
        """)
        coverage = db.execute(coverage_sql, base_params).fetchone()

        return {
            "player_name": player_name,
            "mode": mode,
            "bowler_info": bowler_info,
            "length_profile": length_profile,
            "line_profile": line_profile,
            "data_coverage": {
                "player_balls": coverage.total if coverage else 0,
                "player_balls_with_length": coverage.with_length if coverage else 0,
                "player_balls_with_line": coverage.with_line if coverage else 0,
            },
        }

    except Exception as e:
        logger.error(f"Error in get_player_line_length_profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
