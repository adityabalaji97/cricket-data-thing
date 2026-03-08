"""
Player Line & Length Profile
============================
Returns line/length aggregated stats for a player compared against
global averages, optional similar-player averages, and (for bowlers)
same bowl_kind / bowl_style averages.

Uses the delivery_details table which has columns:
  bat/bowl (player names), p_match (match id), ground, competition,
  date, year, length, line, control, batruns, score, dismissal,
  wide, noball, bowl_kind, bowl_style, team_bat, team_bowl
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
    "SHORT_OF_A_GOOD_LENGTH": "Short of Good Length",
    "SHORT": "Short",
}

LINE_LABELS = {
    "DOWN_LEG": "Down Leg",
    "LEG_STUMP": "Leg Stump",
    "ON_THE_STUMPS": "On the Stumps",
    "MIDDLE": "Middle",
    "OFF_STUMP": "Off Stump",
    "OUTSIDE_OFFSTUMP": "Outside Off",
    "OUTSIDE_OFF": "Outside Off",
    "WIDE_OUTSIDE_OFF": "Wide Outside Off",
    "WIDE_OUTSIDE_OFFSTUMP": "Wide Outside Off",
}


def _build_comp_filter(params: dict, leagues: Optional[List[str]],
                       include_international: bool,
                       top_teams: Optional[int]) -> str:
    """Build competition filter for delivery_details (no matches join needed)."""
    expanded = expand_league_abbreviations(leagues) if leagues else []
    has_leagues = bool(expanded)

    if not has_leagues and not include_international:
        return ""

    conditions = []
    if has_leagues:
        conditions.append("dd.competition = ANY(:leagues)")
        params["leagues"] = expanded

    if include_international:
        top_team_list = TOP_INTERNATIONAL_TEAMS[:top_teams] if top_teams else TOP_INTERNATIONAL_TEAMS[:10]
        params["top_team_list"] = top_team_list
        conditions.append(
            "(dd.competition = 'T20I' AND dd.team_bat = ANY(:top_team_list) AND dd.team_bowl = ANY(:top_team_list))"
        )

    return "AND (" + " OR ".join(conditions) + ")"


def _aggregate_sql(group_col: str, player_filter: str, comp_filter: str) -> str:
    """Return SQL that aggregates line/length metrics from delivery_details."""
    return f"""
        SELECT
            dd.{group_col}                                      AS bucket,
            COUNT(*)                                            AS balls,
            SUM(dd.batruns)                                     AS runs,
            SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END) AS wickets,
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
        WHERE dd.{group_col} IS NOT NULL
        {player_filter}
        AND (:start_year IS NULL OR dd.year >= :start_year)
        AND (:end_year IS NULL OR dd.year <= :end_year)
        AND (:venue IS NULL OR dd.ground = :venue)
        {comp_filter}
        GROUP BY dd.{group_col}
    """


def _row_to_metrics(row) -> dict:
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
            "start_year": start_date.year if start_date else None,
            "end_year": end_date.year if end_date else None,
            "venue": venue,
        }
        comp_filter = _build_comp_filter(
            base_params, leagues, include_international, top_teams
        )

        # delivery_details uses 'bat' and 'bowl' columns for player names
        player_col = "bat" if mode == "batting" else "bowl"
        player_filter = f"AND dd.{player_col} = :player_name"

        def _fetch(group_col, extra_filter, extra_params=None):
            p = {**base_params}
            if extra_params:
                p.update(extra_params)
            sql = _aggregate_sql(group_col, extra_filter, comp_filter)
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
                WHERE bowl = :player_name AND bowl_kind IS NOT NULL
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
            WHERE dd.{player_col} = :player_name
            AND (:start_year IS NULL OR dd.year >= :start_year)
            AND (:end_year IS NULL OR dd.year <= :end_year)
            AND (:venue IS NULL OR dd.ground = :venue)
            {comp_filter}
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
