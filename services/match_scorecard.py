"""Match scorecard service backed by delivery-level data."""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, Iterable, List, Optional

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from services.bowler_types import BOWL_STYLE_CATEGORY_SQL
from services.query_builder_v2 import get_legacy_bowler_style_sql, get_legacy_bowl_kind_sql


DETAILS_START_DATE = date(2015, 1, 1)
PHASE_ORDER = {"powerplay": 0, "middle": 1, "death": 2}
PHASE_META = {
    "powerplay": {"label": "Powerplay", "overs": "1-6"},
    "middle": {"label": "Middle", "overs": "7-15"},
    "death": {"label": "Death", "overs": "16-20"},
}
LINE_ORDER = [
    "WIDE_OUTSIDE_OFFSTUMP",
    "OUTSIDE_OFFSTUMP",
    "ON_THE_STUMPS",
    "DOWN_LEG",
    "WIDE_DOWN_LEG",
]
LENGTH_ORDER = [
    "SHORT",
    "SHORT_OF_A_GOOD_LENGTH",
    "GOOD_LENGTH",
    "FULL",
    "YORKER",
]
LINE_LABELS = {
    "WIDE_OUTSIDE_OFFSTUMP": "Wd Off",
    "OUTSIDE_OFFSTUMP": "Off",
    "ON_THE_STUMPS": "Stumps",
    "DOWN_LEG": "Leg",
    "WIDE_DOWN_LEG": "Wd Leg",
}
LENGTH_LABELS = {
    "SHORT": "Short",
    "SHORT_OF_A_GOOD_LENGTH": "Back",
    "GOOD_LENGTH": "Good",
    "FULL": "Full",
    "YORKER": "Yorker",
}
ZONE_LABELS = {
    1: "Fine Leg",
    2: "Square Leg",
    3: "Midwicket",
    4: "Long On",
    5: "Long Off",
    6: "Cover",
    7: "Point",
    8: "Behind",
}
ZONE_ANGLES = {
    1: 235,
    2: 185,
    3: 145,
    4: 105,
    5: 75,
    6: 45,
    7: 5,
    8: 270,
}
def get_match_scorecard_service(match_id: str, min_balls: int, db: Session) -> Dict[str, Any]:
    min_balls = max(1, int(min_balls or 1))
    match = _fetch_match(match_id, db)
    if not match:
        raise HTTPException(status_code=404, detail=f"Match not found: {match_id}")

    match_date = match.get("date")
    data_source = data_source_for_match_date(match_date)
    use_details = data_source == "delivery_details"

    if use_details:
        innings = _build_details_innings(match_id, min_balls, db)
    else:
        innings = _build_legacy_innings(match_id, min_balls, db)

    if not innings:
        raise HTTPException(status_code=404, detail=f"No delivery data found for match: {match_id}")

    capabilities = _capabilities_for_source(data_source, innings)
    warnings = []
    if data_source == "deliveries":
        warnings.append("Legacy deliveries data does not include wagon zone, line/length, shot, or control tracking.")

    return {
        "match": _format_match(match, innings),
        "summary": _build_summary(match, innings),
        "innings": innings,
        "meta": {
            "data_source": data_source,
            "min_balls": min_balls,
            "capabilities": capabilities,
            "warnings": warnings,
        },
    }


def _fetch_match(match_id: str, db: Session) -> Optional[Dict[str, Any]]:
    row = db.execute(
        text(
            """
            SELECT id, date, venue, city, event_name, event_match_number, team1, team2,
                   toss_winner, toss_decision, winner, outcome, player_of_match,
                   overs, balls_per_over, match_type, competition
            FROM matches
            WHERE id = :match_id
            """
        ),
        {"match_id": match_id},
    ).mappings().first()
    return dict(row) if row else None


def data_source_for_match_date(match_date: Optional[date]) -> str:
    return "delivery_details" if match_date and match_date >= DETAILS_START_DATE else "deliveries"


def _format_match(match: Dict[str, Any], innings: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "id": match.get("id"),
        "date": match.get("date").isoformat() if match.get("date") else None,
        "competition": match.get("competition"),
        "event_name": match.get("event_name"),
        "event_match_number": match.get("event_match_number"),
        "venue": match.get("venue"),
        "city": match.get("city"),
        "team1": match.get("team1"),
        "team2": match.get("team2"),
        "winner": match.get("winner"),
        "result_text": _result_text(match, innings),
        "chase_note": _chase_note(innings),
        "player_of_match": match.get("player_of_match"),
        "teams": _team_accents(innings),
        "toss": {
            "winner": match.get("toss_winner"),
            "decision": match.get("toss_decision"),
        },
    }


def _build_summary(match: Dict[str, Any], innings: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "innings_scores": [item["score"] for item in innings],
        "moment": _build_moment(innings),
        "worm": [_worm_payload(item) for item in innings],
        "top_performers": _top_performers(innings),
        "player_of_match": match.get("player_of_match"),
    }


def _build_details_innings(match_id: str, min_balls: int, db: Session) -> List[Dict[str, Any]]:
    innings_rows = db.execute(
        text(
            """
            SELECT
                dd.inns AS innings,
                MIN(dd.team_bat) AS batting_team,
                MIN(dd.team_bowl) AS bowling_team,
                MAX(COALESCE(dd.inns_runs, 0)) AS runs,
                MAX(COALESCE(dd.inns_wkts, 0)) AS wickets,
                MAX(COALESCE(dd.inns_balls, 0)) AS legal_balls,
                MAX(NULLIF(dd.target, '')::numeric) AS target,
                COUNT(*) AS balls
            FROM delivery_details dd
            WHERE dd.p_match = :match_id
            GROUP BY dd.inns
            ORDER BY dd.inns
            """
        ),
        {"match_id": match_id},
    ).mappings().all()

    batting = _details_batting_rows(match_id, db)
    bowling = _details_bowling_rows(match_id, db)
    batter_breakdowns = _details_batter_breakdowns(match_id, min_balls, db)
    bowler_breakdowns = _details_bowler_breakdowns(match_id, min_balls, db)
    worms = _details_worm(match_id, db)

    out = []
    for row in innings_rows:
        inns = int(row["innings"])
        batting_rows = batting.get(inns, [])
        bowling_rows = bowling.get(inns, [])
        batter_ids = {r["id"] for r in batting_rows}
        bowler_ids = {r["id"] for r in bowling_rows}
        for player in batting_rows:
            player["links"] = {"bowling_card_id": player["id"] if player["id"] in bowler_ids else None}
            player["breakdowns"] = batter_breakdowns.get((inns, player["name"]), _empty_batter_breakdowns(False))
        for player in bowling_rows:
            player["links"] = {"batting_card_id": player["id"] if player["id"] in batter_ids else None}
            player["breakdowns"] = bowler_breakdowns.get((inns, player["name"]), _empty_bowler_breakdowns(False, True))

        score = _score_payload(row, row["batting_team"], row["bowling_team"])
        out.append({
            "innings": inns,
            "batting_team": row["batting_team"],
            "bowling_team": row["bowling_team"],
            "score": score,
            "batting": batting_rows,
            "bowling": bowling_rows,
            "worm": worms.get(inns, []),
        })
    return out


def _build_legacy_innings(match_id: str, min_balls: int, db: Session) -> List[Dict[str, Any]]:
    innings_rows = db.execute(
        text(
            """
            SELECT
                d.innings,
                MIN(d.batting_team) AS batting_team,
                MIN(d.bowling_team) AS bowling_team,
                SUM(COALESCE(d.runs_off_bat, 0) + COALESCE(d.extras, 0)) AS runs,
                SUM(CASE WHEN d.wicket_type IS NOT NULL AND d.wicket_type != '' THEN 1 ELSE 0 END) AS wickets,
                SUM(CASE WHEN COALESCE(d.wides, 0) = 0 AND COALESCE(d.noballs, 0) = 0 THEN 1 ELSE 0 END) AS legal_balls,
                NULL::numeric AS target,
                COUNT(*) AS balls
            FROM deliveries d
            WHERE d.match_id = :match_id
            GROUP BY d.innings
            ORDER BY d.innings
            """
        ),
        {"match_id": match_id},
    ).mappings().all()

    batting = _legacy_batting_rows(match_id, db)
    bowling = _legacy_bowling_rows(match_id, db)
    batter_breakdowns = _legacy_batter_breakdowns(match_id, min_balls, db)
    bowler_breakdowns = _legacy_bowler_breakdowns(match_id, min_balls, db)
    worms = _legacy_worm(match_id, db)

    out = []
    for row in innings_rows:
        inns = int(row["innings"])
        batting_rows = batting.get(inns, [])
        bowling_rows = bowling.get(inns, [])
        batter_ids = {r["id"] for r in batting_rows}
        bowler_ids = {r["id"] for r in bowling_rows}
        for player in batting_rows:
            player["links"] = {"bowling_card_id": player["id"] if player["id"] in bowler_ids else None}
            player["breakdowns"] = batter_breakdowns.get((inns, player["name"]), _empty_batter_breakdowns(True))
        for player in bowling_rows:
            player["links"] = {"batting_card_id": player["id"] if player["id"] in batter_ids else None}
            player["breakdowns"] = bowler_breakdowns.get((inns, player["name"]), _empty_bowler_breakdowns(True, True))

        score = _score_payload(row, row["batting_team"], row["bowling_team"])
        out.append({
            "innings": inns,
            "batting_team": row["batting_team"],
            "bowling_team": row["bowling_team"],
            "score": score,
            "batting": batting_rows,
            "bowling": bowling_rows,
            "worm": worms.get(inns, []),
        })
    return out


def _details_batting_rows(match_id: str, db: Session) -> Dict[int, List[Dict[str, Any]]]:
    rows = db.execute(
        text(
            """
            WITH alias_map AS (
                SELECT DISTINCT ON (name_key) name_key, canonical_name
                FROM (
                    SELECT LOWER(player_name) AS name_key, alias_name AS canonical_name
                    FROM player_aliases WHERE player_name IS NOT NULL AND alias_name IS NOT NULL
                    UNION ALL
                    SELECT LOWER(alias_name) AS name_key, alias_name AS canonical_name
                    FROM player_aliases WHERE alias_name IS NOT NULL
                ) a
            ),
            base AS (
                SELECT dd.*, COALESCE(pa.canonical_name, dd.bat) AS batter_name
                FROM delivery_details dd
                LEFT JOIN alias_map pa ON LOWER(dd.bat) = pa.name_key
                WHERE dd.p_match = :match_id AND dd.bat IS NOT NULL
            ),
            player_map AS (
                SELECT DISTINCT ON (p_bat)
                    p_bat,
                    batter_name
                FROM base
                WHERE p_bat IS NOT NULL AND batter_name IS NOT NULL
                ORDER BY p_bat, inns, over, ball
            ),
            outs AS (
                SELECT DISTINCT ON (inns, dismissed_name)
                    inns,
                    dismissed_name AS batter_name,
                    dismissal
                FROM (
                    SELECT
                        b.inns,
                        COALESCE(pm.batter_name, CASE WHEN LOWER(COALESCE(b.bat_out, '')) = 'true' THEN b.batter_name ELSE NULL END) AS dismissed_name,
                        b.dismissal,
                        b.over,
                        b.ball
                    FROM base b
                    LEFT JOIN player_map pm ON pm.p_bat = b.p_out
                    WHERE LOWER(COALESCE(b.out, '')) = 'true'
                      AND b.dismissal IS NOT NULL
                      AND b.dismissal != ''
                ) wicket_rows
                WHERE dismissed_name IS NOT NULL
                ORDER BY inns, dismissed_name, over DESC, ball DESC
            )
            SELECT
                b.inns AS innings,
                b.batter_name AS name,
                MIN(b.team_bat) AS team,
                MIN(b.over * 100 + b.ball) AS order_key,
                SUM(COALESCE(b.batruns, 0)) AS runs,
                COUNT(*) AS balls,
                SUM(CASE WHEN b.batruns = 4 THEN 1 ELSE 0 END) AS fours,
                SUM(CASE WHEN b.batruns = 6 THEN 1 ELSE 0 END) AS sixes,
                SUM(CASE WHEN b.score = 0 AND COALESCE(b.wide, 0) = 0 AND COALESCE(b.noball, 0) = 0 THEN 1 ELSE 0 END) AS dots,
                MAX(o.dismissal) AS dismissal
            FROM base b
            LEFT JOIN outs o ON o.inns = b.inns AND o.batter_name = b.batter_name
            GROUP BY b.inns, b.batter_name
            ORDER BY b.inns, order_key
            """
        ),
        {"match_id": match_id},
    ).mappings().all()
    return _group_player_rows(rows, "batting")


def _legacy_batting_rows(match_id: str, db: Session) -> Dict[int, List[Dict[str, Any]]]:
    rows = db.execute(
        text(
            """
            WITH outs AS (
                SELECT DISTINCT ON (innings, batter)
                    innings, batter, wicket_type
                FROM deliveries
                WHERE match_id = :match_id
                  AND wicket_type IS NOT NULL AND wicket_type != ''
                  AND (player_dismissed IS NULL OR player_dismissed = '' OR player_dismissed = batter)
                ORDER BY innings, batter, over DESC, ball DESC
            )
            SELECT
                d.innings,
                COALESCE(pa.alias_name, d.batter) AS name,
                MIN(d.batting_team) AS team,
                MIN(d.over * 100 + d.ball) AS order_key,
                SUM(COALESCE(d.runs_off_bat, 0)) AS runs,
                COUNT(*) AS balls,
                SUM(CASE WHEN d.runs_off_bat = 4 THEN 1 ELSE 0 END) AS fours,
                SUM(CASE WHEN d.runs_off_bat = 6 THEN 1 ELSE 0 END) AS sixes,
                SUM(CASE WHEN COALESCE(d.runs_off_bat, 0) = 0 AND COALESCE(d.extras, 0) = 0 THEN 1 ELSE 0 END) AS dots,
                MAX(o.wicket_type) AS dismissal
            FROM deliveries d
            LEFT JOIN player_aliases pa ON pa.player_name = d.batter
            LEFT JOIN outs o ON o.innings = d.innings AND o.batter = d.batter
            WHERE d.match_id = :match_id AND d.batter IS NOT NULL
            GROUP BY d.innings, COALESCE(pa.alias_name, d.batter)
            ORDER BY d.innings, order_key
            """
        ),
        {"match_id": match_id},
    ).mappings().all()
    return _group_player_rows(rows, "batting")


def _details_bowling_rows(match_id: str, db: Session) -> Dict[int, List[Dict[str, Any]]]:
    rows = db.execute(
        text(
            """
            WITH alias_map AS (
                SELECT DISTINCT ON (name_key) name_key, canonical_name
                FROM (
                    SELECT LOWER(player_name) AS name_key, alias_name AS canonical_name
                    FROM player_aliases WHERE player_name IS NOT NULL AND alias_name IS NOT NULL
                    UNION ALL
                    SELECT LOWER(alias_name) AS name_key, alias_name AS canonical_name
                    FROM player_aliases WHERE alias_name IS NOT NULL
                ) a
            )
            SELECT
                dd.inns AS innings,
                COALESCE(pa.canonical_name, dd.bowl) AS name,
                MIN(dd.team_bowl) AS team,
                MIN(dd.bowl_style) AS style,
                SUM(COALESCE(dd.score, 0)) AS runs,
                COUNT(*) AS balls,
                SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != ''
                          AND LOWER(dd.dismissal) NOT LIKE '%run out%' THEN 1 ELSE 0 END) AS wickets,
                SUM(CASE WHEN dd.score = 0 AND COALESCE(dd.wide, 0) = 0 AND COALESCE(dd.noball, 0) = 0 THEN 1 ELSE 0 END) AS dots,
                SUM(CASE WHEN COALESCE(dd.wide, 0) = 0 AND COALESCE(dd.noball, 0) = 0 THEN 1 ELSE 0 END) AS legal_balls
            FROM delivery_details dd
            LEFT JOIN alias_map pa ON LOWER(dd.bowl) = pa.name_key
            WHERE dd.p_match = :match_id AND dd.bowl IS NOT NULL
            GROUP BY dd.inns, COALESCE(pa.canonical_name, dd.bowl)
            ORDER BY dd.inns, MIN(dd.over * 100 + dd.ball)
            """
        ),
        {"match_id": match_id},
    ).mappings().all()
    return _group_bowling_rows(rows)


def _legacy_bowling_rows(match_id: str, db: Session) -> Dict[int, List[Dict[str, Any]]]:
    rows = db.execute(
        text(
            """
            SELECT
                d.innings,
                COALESCE(pa.alias_name, d.bowler) AS name,
                MIN(d.bowling_team) AS team,
                MIN(COALESCE(d.bowler_type, p.bowler_type, p.bowling_type, p.bowl_type)) AS style,
                SUM(COALESCE(d.runs_off_bat, 0) + COALESCE(d.extras, 0)) AS runs,
                COUNT(*) AS balls,
                SUM(CASE WHEN d.wicket_type IS NOT NULL AND d.wicket_type != ''
                          AND LOWER(d.wicket_type) NOT LIKE '%run out%'
                          AND LOWER(d.wicket_type) NOT LIKE 'retired%' THEN 1 ELSE 0 END) AS wickets,
                SUM(CASE WHEN COALESCE(d.runs_off_bat, 0) = 0 AND COALESCE(d.extras, 0) = 0 THEN 1 ELSE 0 END) AS dots,
                SUM(CASE WHEN COALESCE(d.wides, 0) = 0 AND COALESCE(d.noballs, 0) = 0 THEN 1 ELSE 0 END) AS legal_balls
            FROM deliveries d
            LEFT JOIN players p ON p.name = d.bowler
            LEFT JOIN player_aliases pa ON pa.player_name = d.bowler
            WHERE d.match_id = :match_id AND d.bowler IS NOT NULL
            GROUP BY d.innings, COALESCE(pa.alias_name, d.bowler)
            ORDER BY d.innings, MIN(d.over * 100 + d.ball)
            """
        ),
        {"match_id": match_id},
    ).mappings().all()
    return _group_bowling_rows(rows)


def _details_batter_breakdowns(match_id: str, min_balls: int, db: Session) -> Dict[tuple, Dict[str, Any]]:
    base = _details_base_cte()
    result: Dict[tuple, Dict[str, Any]] = {}
    _seed_batters(result, _details_players(match_id, db), legacy=False)
    rows = db.execute(text(base + _bat_vs_bowler_sql("base")), {"match_id": match_id}).mappings().all()
    for row in rows:
        key = (int(row["innings"]), row["player"])
        item = result.setdefault(key, _empty_batter_breakdowns(False))
        item["vs_bowler"]["rows"].append(_bat_vs_row(row))

    rows = db.execute(text(base + _phase_sql("batter_name", batting=True)), {"match_id": match_id}).mappings().all()
    _attach_phase_rows(result, rows, batting=True, min_balls=min_balls)

    rows = db.execute(text(base + _pace_spin_sql("batter_name", batting=True, source="details")), {"match_id": match_id}).mappings().all()
    _attach_pace_spin_rows(result, rows, batting=True, min_balls=min_balls)

    rows = db.execute(text(base + _zones_sql("batter_name", batting=True)), {"match_id": match_id}).mappings().all()
    _attach_zone_rows(result, rows, min_balls=min_balls)

    rows = db.execute(text(base + _line_length_sql("batter_name", batting=True)), {"match_id": match_id}).mappings().all()
    _attach_line_length_rows(result, rows, batting=True, min_balls=min_balls)
    return result


def _legacy_batter_breakdowns(match_id: str, min_balls: int, db: Session) -> Dict[tuple, Dict[str, Any]]:
    base = _legacy_base_cte()
    result: Dict[tuple, Dict[str, Any]] = {}
    _seed_batters(result, _legacy_players(match_id, db), legacy=True)
    rows = db.execute(text(base + _bat_vs_bowler_sql("base")), {"match_id": match_id}).mappings().all()
    for row in rows:
        key = (int(row["innings"]), row["player"])
        item = result.setdefault(key, _empty_batter_breakdowns(True))
        item["vs_bowler"]["rows"].append(_bat_vs_row(row))

    rows = db.execute(text(base + _phase_sql("batter_name", batting=True)), {"match_id": match_id}).mappings().all()
    _attach_phase_rows(result, rows, batting=True, min_balls=min_balls)

    rows = db.execute(text(base + _pace_spin_sql("batter_name", batting=True, source="legacy")), {"match_id": match_id}).mappings().all()
    _attach_pace_spin_rows(result, rows, batting=True, min_balls=min_balls)
    return result


def _details_bowler_breakdowns(match_id: str, min_balls: int, db: Session) -> Dict[tuple, Dict[str, Any]]:
    base = _details_base_cte()
    result: Dict[tuple, Dict[str, Any]] = {}
    _seed_bowlers(result, _details_players(match_id, db), legacy=False)
    rows = db.execute(text(base + _bowl_vs_batter_sql()), {"match_id": match_id}).mappings().all()
    for row in rows:
        key = (int(row["innings"]), row["player"])
        item = result.setdefault(key, _empty_bowler_breakdowns(False, True))
        item["vs_batter"]["rows"].append(_bowl_vs_row(row))

    rows = db.execute(text(base + _phase_sql("bowler_name", batting=False)), {"match_id": match_id}).mappings().all()
    _attach_phase_rows(result, rows, batting=False, min_balls=min_balls)

    rows = db.execute(text(base + _hand_sql("bowler_name", source="details")), {"match_id": match_id}).mappings().all()
    _attach_hand_rows(result, rows, min_balls=min_balls)

    rows = db.execute(text(base + _zones_sql("bowler_name", batting=False)), {"match_id": match_id}).mappings().all()
    _attach_zone_rows(result, rows, min_balls=min_balls)

    rows = db.execute(text(base + _line_length_sql("bowler_name", batting=False)), {"match_id": match_id}).mappings().all()
    _attach_line_length_rows(result, rows, batting=False, min_balls=min_balls)
    return result


def _legacy_bowler_breakdowns(match_id: str, min_balls: int, db: Session) -> Dict[tuple, Dict[str, Any]]:
    base = _legacy_base_cte()
    result: Dict[tuple, Dict[str, Any]] = {}
    _seed_bowlers(result, _legacy_players(match_id, db), legacy=True)
    rows = db.execute(text(base + _bowl_vs_batter_sql()), {"match_id": match_id}).mappings().all()
    for row in rows:
        key = (int(row["innings"]), row["player"])
        item = result.setdefault(key, _empty_bowler_breakdowns(True, True))
        item["vs_batter"]["rows"].append(_bowl_vs_row(row))

    rows = db.execute(text(base + _phase_sql("bowler_name", batting=False)), {"match_id": match_id}).mappings().all()
    _attach_phase_rows(result, rows, batting=False, min_balls=min_balls)

    rows = db.execute(text(base + _hand_sql("bowler_name", source="legacy")), {"match_id": match_id}).mappings().all()
    _attach_hand_rows(result, rows, min_balls=min_balls)
    return result


def _details_base_cte() -> str:
    pace_expr = f"""COALESCE(
        CASE
            WHEN LOWER(COALESCE(dd.bowl_kind, '')) LIKE '%pace%' OR LOWER(COALESCE(dd.bowl_kind, '')) LIKE '%fast%' THEN 'pace'
            WHEN LOWER(COALESCE(dd.bowl_kind, '')) LIKE '%spin%' OR LOWER(COALESCE(dd.bowl_kind, '')) LIKE '%slow%' THEN 'spin'
            ELSE NULL
        END,
        {BOWL_STYLE_CATEGORY_SQL}
    )"""
    return f"""
        WITH alias_map AS (
            SELECT DISTINCT ON (name_key) name_key, canonical_name
            FROM (
                SELECT LOWER(player_name) AS name_key, alias_name AS canonical_name
                FROM player_aliases WHERE player_name IS NOT NULL AND alias_name IS NOT NULL
                UNION ALL
                SELECT LOWER(alias_name) AS name_key, alias_name AS canonical_name
                FROM player_aliases WHERE alias_name IS NOT NULL
            ) a
        ),
        base AS (
            SELECT
                dd.inns AS innings,
                COALESCE(ba.canonical_name, dd.bat) AS batter_name,
                COALESCE(bo.canonical_name, dd.bowl) AS bowler_name,
                dd.team_bat AS batting_team,
                dd.team_bowl AS bowling_team,
                dd.over,
                COALESCE(dd.score, 0) AS total_runs,
                COALESCE(dd.batruns, 0) AS batter_runs,
                COALESCE(dd.wide, 0) AS wide,
                COALESCE(dd.noball, 0) AS noball,
                dd.dismissal,
                dd.bat_hand,
                {pace_expr} AS pace_spin,
                dd.wagon_zone,
                dd.line,
                dd.length,
                dd.control
            FROM delivery_details dd
            LEFT JOIN alias_map ba ON LOWER(dd.bat) = ba.name_key
            LEFT JOIN alias_map bo ON LOWER(dd.bowl) = bo.name_key
            WHERE dd.p_match = :match_id
        )
    """


def _legacy_base_cte() -> str:
    style_sql = get_legacy_bowler_style_sql()
    kind_sql = get_legacy_bowl_kind_sql(style_sql)
    return f"""
        WITH base AS (
            SELECT
                d.innings,
                COALESCE(pa_bat.alias_name, d.batter) AS batter_name,
                COALESCE(pa_bowl.alias_name, d.bowler) AS bowler_name,
                d.batting_team,
                d.bowling_team,
                d.over,
                COALESCE(d.runs_off_bat, 0) + COALESCE(d.extras, 0) AS total_runs,
                COALESCE(d.runs_off_bat, 0) AS batter_runs,
                COALESCE(d.wides, 0) AS wide,
                COALESCE(d.noballs, 0) AS noball,
                d.wicket_type AS dismissal,
                d.striker_batter_type AS bat_hand,
                {kind_sql} AS pace_spin,
                NULL::integer AS wagon_zone,
                NULL::text AS line,
                NULL::text AS length,
                NULL::integer AS control
            FROM deliveries d
            JOIN matches m ON m.id = d.match_id
            LEFT JOIN players p ON p.name = d.bowler
            LEFT JOIN player_aliases pa_bat ON pa_bat.player_name = d.batter
            LEFT JOIN player_aliases pa_bowl ON pa_bowl.player_name = d.bowler
            WHERE d.match_id = :match_id
        )
    """


def _bat_vs_bowler_sql(source_alias: str) -> str:
    return f"""
        SELECT innings, batter_name AS player, bowler_name AS item,
               COUNT(*) AS balls,
               SUM(batter_runs) AS runs,
               SUM(CASE WHEN batter_runs = 4 THEN 1 ELSE 0 END) AS fours,
               SUM(CASE WHEN batter_runs = 6 THEN 1 ELSE 0 END) AS sixes,
               SUM(CASE WHEN total_runs = 0 AND wide = 0 AND noball = 0 THEN 1 ELSE 0 END) AS dots
        FROM {source_alias}
        WHERE batter_name IS NOT NULL AND bowler_name IS NOT NULL
        GROUP BY innings, batter_name, bowler_name
        ORDER BY innings, batter_name, balls DESC
    """


def _bowl_vs_batter_sql() -> str:
    return """
        SELECT innings, bowler_name AS player, batter_name AS item,
               COUNT(*) AS balls,
               SUM(total_runs) AS runs,
               SUM(CASE WHEN dismissal IS NOT NULL AND dismissal != ''
                         AND LOWER(dismissal) NOT LIKE '%run out%' THEN 1 ELSE 0 END) AS wickets,
               SUM(CASE WHEN batter_runs = 4 THEN 1 ELSE 0 END) AS fours,
               SUM(CASE WHEN batter_runs = 6 THEN 1 ELSE 0 END) AS sixes,
               SUM(CASE WHEN total_runs = 0 AND wide = 0 AND noball = 0 THEN 1 ELSE 0 END) AS dots
        FROM base
        WHERE batter_name IS NOT NULL AND bowler_name IS NOT NULL
        GROUP BY innings, bowler_name, batter_name
        ORDER BY innings, bowler_name, balls DESC
    """


def _phase_sql(player_col: str, batting: bool) -> str:
    runs_col = "batter_runs" if batting else "total_runs"
    wicket_sql = "0" if batting else "SUM(CASE WHEN dismissal IS NOT NULL AND dismissal != '' AND LOWER(dismissal) NOT LIKE '%run out%' THEN 1 ELSE 0 END)"
    return f"""
        SELECT innings, {player_col} AS player,
               CASE WHEN over < 6 THEN 'powerplay' WHEN over < 15 THEN 'middle' ELSE 'death' END AS item,
               COUNT(*) AS balls,
               SUM({runs_col}) AS runs,
               {wicket_sql} AS wickets
        FROM base
        WHERE {player_col} IS NOT NULL
        GROUP BY innings, {player_col}, item
        ORDER BY innings, {player_col}, item
    """


def _pace_spin_sql(player_col: str, batting: bool, source: str) -> str:
    runs_col = "batter_runs" if batting else "total_runs"
    return f"""
        SELECT innings, {player_col} AS player,
               CASE
                   WHEN LOWER(COALESCE(pace_spin, '')) LIKE '%pace%'
                        OR LOWER(COALESCE(pace_spin, '')) LIKE '%fast%' THEN 'pace'
                   WHEN LOWER(COALESCE(pace_spin, '')) LIKE '%spin%'
                        OR LOWER(COALESCE(pace_spin, '')) LIKE '%slow%' THEN 'spin'
                   ELSE 'unknown'
               END AS item,
               COUNT(*) AS balls,
               SUM({runs_col}) AS runs,
               SUM(CASE WHEN batter_runs IN (4, 6) THEN batter_runs ELSE 0 END) AS boundary_runs
        FROM base
        WHERE {player_col} IS NOT NULL AND pace_spin IS NOT NULL
        GROUP BY innings, {player_col}, item
        ORDER BY innings, {player_col}, item
    """


def _hand_sql(player_col: str, source: str) -> str:
    return f"""
        SELECT innings, {player_col} AS player,
               UPPER(COALESCE(bat_hand, 'unknown')) AS item,
               COUNT(*) AS balls,
               SUM(total_runs) AS runs,
               SUM(CASE WHEN dismissal IS NOT NULL AND dismissal != ''
                         AND LOWER(dismissal) NOT LIKE '%run out%' THEN 1 ELSE 0 END) AS wickets
        FROM base
        WHERE {player_col} IS NOT NULL AND bat_hand IS NOT NULL AND bat_hand != ''
        GROUP BY innings, {player_col}, UPPER(COALESCE(bat_hand, 'unknown'))
        ORDER BY innings, {player_col}, item
    """


def _zones_sql(player_col: str, batting: bool) -> str:
    runs_col = "batter_runs" if batting else "total_runs"
    return f"""
        SELECT innings, {player_col} AS player, wagon_zone AS item,
               COUNT(*) AS balls,
               SUM({runs_col}) AS runs
        FROM base
        WHERE {player_col} IS NOT NULL AND wagon_zone BETWEEN 1 AND 8
        GROUP BY innings, {player_col}, wagon_zone
        ORDER BY innings, {player_col}, wagon_zone
    """


def _line_length_sql(player_col: str, batting: bool) -> str:
    runs_col = "batter_runs" if batting else "total_runs"
    return f"""
        SELECT innings, {player_col} AS player,
               {_line_bucket_sql("line")} AS line_bucket,
               {_length_bucket_sql("length")} AS length_bucket,
               COUNT(*) AS balls,
               SUM({runs_col}) AS runs
        FROM base
        WHERE {player_col} IS NOT NULL AND line IS NOT NULL AND length IS NOT NULL
        GROUP BY innings, {player_col}, line_bucket, length_bucket
        ORDER BY innings, {player_col}, length_bucket, line_bucket
    """


def _line_bucket_sql(column: str) -> str:
    token = f"UPPER(REPLACE(REPLACE({column}, '-', '_'), ' ', '_'))"
    return f"""CASE
        WHEN {token} IN ('WIDE_OUTSIDE_OFFSTUMP', 'WIDE_OUTSIDE_OFF') THEN 'WIDE_OUTSIDE_OFFSTUMP'
        WHEN {token} IN ('OUTSIDE_OFFSTUMP', 'OUTSIDE_OFF', 'OFF_STUMP', 'OFF') THEN 'OUTSIDE_OFFSTUMP'
        WHEN {token} IN ('ON_THE_STUMPS', 'MIDDLE', 'STUMPS') THEN 'ON_THE_STUMPS'
        WHEN {token} IN ('DOWN_LEG', 'LEG_STUMP', 'LEG') THEN 'DOWN_LEG'
        WHEN {token} IN ('WIDE_DOWN_LEG', 'WIDE_LEG') THEN 'WIDE_DOWN_LEG'
        ELSE NULL
    END"""


def _length_bucket_sql(column: str) -> str:
    token = f"UPPER(REPLACE(REPLACE({column}, '-', '_'), ' ', '_'))"
    return f"""CASE
        WHEN {token} = 'SHORT' THEN 'SHORT'
        WHEN {token} IN ('SHORT_OF_A_GOOD_LENGTH', 'SHORT_OF_GOOD_LENGTH', 'SHORT_OF_LENGTH', 'BACK_OF_A_LENGTH', 'BACK_OF_LENGTH') THEN 'SHORT_OF_A_GOOD_LENGTH'
        WHEN {token} IN ('GOOD_LENGTH', 'GOOD') THEN 'GOOD_LENGTH'
        WHEN {token} = 'FULL' THEN 'FULL'
        WHEN {token} = 'YORKER' THEN 'YORKER'
        ELSE NULL
    END"""


def _details_players(match_id: str, db: Session) -> List[Dict[str, Any]]:
    rows = db.execute(text(_details_base_cte() + " SELECT DISTINCT innings, batter_name, bowler_name FROM base"), {"match_id": match_id}).mappings().all()
    return [dict(r) for r in rows]


def _legacy_players(match_id: str, db: Session) -> List[Dict[str, Any]]:
    rows = db.execute(text(_legacy_base_cte() + " SELECT DISTINCT innings, batter_name, bowler_name FROM base"), {"match_id": match_id}).mappings().all()
    return [dict(r) for r in rows]


def _seed_batters(result: Dict[tuple, Dict[str, Any]], players: Iterable[Dict[str, Any]], legacy: bool) -> None:
    for row in players:
        if row.get("batter_name"):
            result.setdefault((int(row["innings"]), row["batter_name"]), _empty_batter_breakdowns(legacy))


def _seed_bowlers(result: Dict[tuple, Dict[str, Any]], players: Iterable[Dict[str, Any]], legacy: bool) -> None:
    for row in players:
        if row.get("bowler_name"):
            result.setdefault((int(row["innings"]), row["bowler_name"]), _empty_bowler_breakdowns(legacy, True))


def _attach_phase_rows(result: Dict[tuple, Dict[str, Any]], rows: Iterable[Dict[str, Any]], batting: bool, min_balls: int) -> None:
    buckets: Dict[tuple, List[Dict[str, Any]]] = {}
    for row in rows:
        buckets.setdefault((int(row["innings"]), row["player"]), []).append(dict(row))
    for key, group_rows in buckets.items():
        item = result.setdefault(key, _empty_batter_breakdowns(False) if batting else _empty_bowler_breakdowns(False, True))
        total_balls = sum(int(r.get("balls") or 0) for r in group_rows)
        target = item["phase"]
        target["available"] = total_balls >= min_balls
        target["rows"] = []
        for phase in ("powerplay", "middle", "death"):
            source = next((r for r in group_rows if r.get("item") == phase), None)
            balls = int(source.get("balls") or 0) if source else 0
            runs = int(source.get("runs") or 0) if source else 0
            wickets = int(source.get("wickets") or 0) if source else 0
            meta = PHASE_META[phase]
            if batting:
                target["rows"].append({"key": phase, "label": meta["label"], "overs": meta["overs"], "runs": runs, "balls": balls, "sr": _sr(runs, balls)})
            else:
                target["rows"].append({"key": phase, "label": meta["label"], "overs": meta["overs"], "runs": runs, "balls": balls, "wkts": wickets, "econ": _econ(runs, balls)})


def _attach_pace_spin_rows(result: Dict[tuple, Dict[str, Any]], rows: Iterable[Dict[str, Any]], batting: bool, min_balls: int) -> None:
    buckets: Dict[tuple, List[Dict[str, Any]]] = {}
    for row in rows:
        buckets.setdefault((int(row["innings"]), row["player"]), []).append(dict(row))
    for key, group_rows in buckets.items():
        item = result.setdefault(key, _empty_batter_breakdowns(False) if batting else _empty_bowler_breakdowns(False, True))
        target = item["pace_spin"]
        total_balls = sum(int(r.get("balls") or 0) for r in group_rows)
        target["available"] = total_balls >= min_balls
        target["rows"] = []
        for kind in ("pace", "spin"):
            row = next((r for r in group_rows if str(r.get("item")).lower() == kind), None)
            balls = int(row.get("balls") or 0) if row else 0
            runs = int(row.get("runs") or 0) if row else 0
            boundary_runs = int(row.get("boundary_runs") or 0) if row else 0
            target["rows"].append({"key": kind, "label": f"vs {kind.title()}", "runs": runs, "balls": balls, "sr": _sr(runs, balls), "boundary_runs": boundary_runs})


def _attach_hand_rows(result: Dict[tuple, Dict[str, Any]], rows: Iterable[Dict[str, Any]], min_balls: int) -> None:
    buckets: Dict[tuple, List[Dict[str, Any]]] = {}
    for row in rows:
        buckets.setdefault((int(row["innings"]), row["player"]), []).append(dict(row))
    for key, group_rows in buckets.items():
        item = result.setdefault(key, _empty_bowler_breakdowns(False, True))
        target = item["hand"]
        total_balls = sum(int(r.get("balls") or 0) for r in group_rows)
        target["available"] = total_balls >= min_balls
        target["rows"] = []
        labels = {"RHB": "vs Right-hand", "LHB": "vs Left-hand", "RIGHT": "vs Right-hand", "LEFT": "vs Left-hand"}
        for hand in ("RHB", "LHB"):
            row = next((r for r in group_rows if str(r.get("item")).upper() == hand), None)
            balls = int(row.get("balls") or 0) if row else 0
            runs = int(row.get("runs") or 0) if row else 0
            wickets = int(row.get("wickets") or 0) if row else 0
            target["rows"].append({"key": hand, "label": labels[hand], "runs": runs, "balls": balls, "wkts": wickets, "econ": _econ(runs, balls)})


def _attach_zone_rows(result: Dict[tuple, Dict[str, Any]], rows: Iterable[Dict[str, Any]], min_balls: int) -> None:
    buckets: Dict[tuple, List[Dict[str, Any]]] = {}
    for row in rows:
        buckets.setdefault((int(row["innings"]), row["player"]), []).append(dict(row))
    for key, group_rows in buckets.items():
        item = result.setdefault(key, _empty_batter_breakdowns(False))
        target = item["zones"]
        total_balls = sum(int(r.get("balls") or 0) for r in group_rows)
        target["available"] = total_balls >= min_balls and bool(group_rows)
        target["rows"] = []
        for row in group_rows:
            zone = int(row.get("item") or 0)
            if zone not in ZONE_LABELS:
                continue
            target["rows"].append({"zone": zone, "label": ZONE_LABELS[zone], "angle": ZONE_ANGLES[zone], "runs": int(row.get("runs") or 0), "balls": int(row.get("balls") or 0)})


def _attach_line_length_rows(result: Dict[tuple, Dict[str, Any]], rows: Iterable[Dict[str, Any]], batting: bool, min_balls: int) -> None:
    buckets: Dict[tuple, List[Dict[str, Any]]] = {}
    for row in rows:
        if not row.get("line_bucket") or not row.get("length_bucket"):
            continue
        buckets.setdefault((int(row["innings"]), row["player"]), []).append(dict(row))
    for key, group_rows in buckets.items():
        item = result.setdefault(key, _empty_batter_breakdowns(False) if batting else _empty_bowler_breakdowns(False, True))
        target = item["line_length"]
        total_balls = sum(int(r.get("balls") or 0) for r in group_rows)
        target["available"] = total_balls >= min_balls and bool(group_rows)
        target["rows"] = {"lines": [{"key": x, "label": LINE_LABELS[x]} for x in LINE_ORDER], "lengths": [{"key": x, "label": LENGTH_LABELS[x]} for x in LENGTH_ORDER]}
        cells = []
        for row in group_rows:
            balls = int(row.get("balls") or 0)
            runs = int(row.get("runs") or 0)
            metric = _sr(runs, balls) if batting else _econ(runs, balls)
            cells.append({"line": row["line_bucket"], "length": row["length_bucket"], "balls": balls, "runs": runs, "metric": metric})
        target["cells"] = cells


def _details_worm(match_id: str, db: Session) -> Dict[int, List[int]]:
    rows = db.execute(
        text(
            """
            SELECT inns AS innings, over, SUM(COALESCE(score, 0)) AS runs
            FROM delivery_details
            WHERE p_match = :match_id
            GROUP BY inns, over
            ORDER BY inns, over
            """
        ),
        {"match_id": match_id},
    ).mappings().all()
    return _build_cumulative_by_over(rows)


def _legacy_worm(match_id: str, db: Session) -> Dict[int, List[int]]:
    rows = db.execute(
        text(
            """
            SELECT innings, over, SUM(COALESCE(runs_off_bat, 0) + COALESCE(extras, 0)) AS runs
            FROM deliveries
            WHERE match_id = :match_id
            GROUP BY innings, over
            ORDER BY innings, over
            """
        ),
        {"match_id": match_id},
    ).mappings().all()
    return _build_cumulative_by_over(rows)


def _build_cumulative_by_over(rows: Iterable[Dict[str, Any]]) -> Dict[int, List[int]]:
    by_innings: Dict[int, Dict[int, int]] = {}
    for row in rows:
        by_innings.setdefault(int(row["innings"]), {})[int(row["over"] or 0)] = int(row["runs"] or 0)
    out = {}
    for inns, over_runs in by_innings.items():
        max_over = max(19, max(over_runs.keys()) if over_runs else 19)
        total = 0
        values = []
        for over in range(max_over + 1):
            total += over_runs.get(over, 0)
            values.append(total)
        out[inns] = values
    return out


def _score_payload(row: Dict[str, Any], batting_team: str, bowling_team: str) -> Dict[str, Any]:
    runs = int(row.get("runs") or 0)
    wickets = int(row.get("wickets") or 0)
    legal_balls = int(row.get("legal_balls") or row.get("balls") or 0)
    return {
        "innings": int(row["innings"]),
        "team": batting_team,
        "batting_team": batting_team,
        "bowling_team": bowling_team,
        "runs": runs,
        "wickets": wickets,
        "overs": _balls_to_overs(legal_balls),
        "balls": legal_balls,
        "run_rate": round(runs * 6.0 / legal_balls, 2) if legal_balls else 0,
        "target": int(float(row["target"])) if row.get("target") is not None else None,
    }


def _group_player_rows(rows: Iterable[Dict[str, Any]], role: str) -> Dict[int, List[Dict[str, Any]]]:
    out: Dict[int, List[Dict[str, Any]]] = {}
    for row in rows:
        balls = int(row.get("balls") or 0)
        runs = int(row.get("runs") or 0)
        name = row["name"]
        dismissal = row.get("dismissal") or "not out"
        item = {
            "id": _slug(name),
            "name": name,
            "team": row.get("team"),
            "dismissal": dismissal,
            "not_out": dismissal == "not out",
            "runs": runs,
            "balls": balls,
            "fours": int(row.get("fours") or 0),
            "sixes": int(row.get("sixes") or 0),
            "dots": int(row.get("dots") or 0),
            "strike_rate": _sr(runs, balls),
        }
        out.setdefault(int(row["innings"]), []).append(item)
    return out


def _group_bowling_rows(rows: Iterable[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
    out: Dict[int, List[Dict[str, Any]]] = {}
    for row in rows:
        balls = int(row.get("balls") or 0)
        legal_balls = int(row.get("legal_balls") or balls)
        runs = int(row.get("runs") or 0)
        wickets = int(row.get("wickets") or 0)
        overs = _balls_to_overs(legal_balls)
        item = {
            "id": _slug(row["name"]),
            "name": row["name"],
            "team": row.get("team"),
            "style": row.get("style"),
            "figures": f"{overs}-0-{runs}",
            "overs": overs,
            "runs": runs,
            "balls": balls,
            "legal_balls": legal_balls,
            "wickets": wickets,
            "economy": _econ(runs, legal_balls),
            "dots": int(row.get("dots") or 0),
        }
        out.setdefault(int(row["innings"]), []).append(item)
    return out


def _bat_vs_row(row: Dict[str, Any]) -> Dict[str, Any]:
    balls = int(row.get("balls") or 0)
    runs = int(row.get("runs") or 0)
    sr = _sr(runs, balls)
    return {
        "id": _slug(row["item"]),
        "name": row["item"],
        "runs": runs,
        "balls": balls,
        "sr": sr,
        "fours": int(row.get("fours") or 0),
        "sixes": int(row.get("sixes") or 0),
        "dots": int(row.get("dots") or 0),
        "bar_pct": min(100, round(sr / 210.0 * 100)),
        "linkable": True,
    }


def _bowl_vs_row(row: Dict[str, Any]) -> Dict[str, Any]:
    balls = int(row.get("balls") or 0)
    runs = int(row.get("runs") or 0)
    econ = _econ(runs, balls)
    return {
        "id": _slug(row["item"]),
        "name": row["item"],
        "runs": runs,
        "balls": balls,
        "wkts": int(row.get("wickets") or 0),
        "fours": int(row.get("fours") or 0),
        "sixes": int(row.get("sixes") or 0),
        "dots": int(row.get("dots") or 0),
        "econ": econ,
        "bar_pct": min(100, round(econ / 14.0 * 100)),
        "bar_color": _econ_color(econ),
        "linkable": True,
    }


def _empty_batter_breakdowns(legacy: bool) -> Dict[str, Any]:
    return {
        "vs_bowler": {"available": True, "rows": []},
        "phase": {"available": False, "rows": [], "empty": "Not enough balls faced to split by phase."},
        "pace_spin": {"available": False, "rows": [], "empty": "Not enough balls to split pace vs spin."},
        "zones": {"available": False, "rows": [], "empty": "No wagon-wheel data for this innings.", "unsupported": legacy},
        "line_length": {"available": False, "rows": {"lines": [], "lengths": []}, "cells": [], "empty": "Line & length grid needs more tracked balls.", "unsupported": legacy},
    }


def _empty_bowler_breakdowns(legacy: bool, hand_supported: bool) -> Dict[str, Any]:
    return {
        "vs_batter": {"available": True, "rows": []},
        "phase": {"available": False, "rows": [], "empty": "Not enough balls to split by phase."},
        "hand": {"available": False, "rows": [], "empty": "Not enough balls to split by batter hand.", "unsupported": not hand_supported},
        "zones": {"available": False, "rows": [], "empty": "No wagon-wheel data for this spell.", "unsupported": legacy},
        "line_length": {"available": False, "rows": {"lines": [], "lengths": []}, "cells": [], "empty": "Line & length map needs more tracked balls.", "unsupported": legacy},
    }


def _capabilities_for_source(source: str, innings: List[Dict[str, Any]]) -> Dict[str, bool]:
    if source == "delivery_details":
        return {
            "core_scorecard": True,
            "vs_player": True,
            "phase": True,
            "pace_spin": True,
            "hand": True,
            "zones": True,
            "line_length": True,
            "control": True,
        }
    has_hand = any(
        player.get("breakdowns", {}).get("hand", {}).get("rows")
        for item in innings
        for player in item.get("bowling", [])
    )
    return {
        "core_scorecard": True,
        "vs_player": True,
        "phase": True,
        "pace_spin": True,
        "hand": bool(has_hand),
        "zones": False,
        "line_length": False,
        "control": False,
    }


def _top_performers(innings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for item in innings:
        team = item["batting_team"]
        top_bat = max(item.get("batting", []), key=lambda x: x.get("runs", 0), default=None)
        if top_bat:
            out.append({
                "kind": "top_bat",
                "team": team,
                "innings": item["innings"],
                "player_id": top_bat["id"],
                "player": top_bat["name"],
                "label": f"{top_bat['runs']}{'*' if top_bat.get('not_out') else ''}",
                "screen": "batting",
                "lens": "bowler",
            })
        top_bowl = max(item.get("bowling", []), key=lambda x: (x.get("wickets", 0), -x.get("runs", 0)), default=None)
        if top_bowl:
            out.append({
                "kind": "top_bowl",
                "team": item["bowling_team"],
                "innings": item["innings"],
                "player_id": top_bowl["id"],
                "player": top_bowl["name"],
                "label": f"{top_bowl['wickets']}/{top_bowl['runs']}",
                "screen": "bowling",
                "lens": "batter",
            })
    return out


def _build_moment(innings: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for item in innings:
        for batter in item.get("batting", []):
            if batter.get("sixes", 0) >= 4 and batter.get("strike_rate", 0) >= 200:
                return {
                    "label": "The moment",
                    "title": "Boundary burst",
                    "subtitle": f"{batter['name']} changed the match with {batter['sixes']} sixes.",
                    "chips": ["6"] * min(4, batter["sixes"]),
                }
    return None


def _worm_payload(item: Dict[str, Any]) -> Dict[str, Any]:
    values = item.get("worm", [])
    max_score = max([score["runs"] for score in [item["score"]]] + values + [1])
    points = []
    denom = max(1, len(values) - 1)
    for index, value in enumerate(values):
        x = index / denom * 100
        y = 60 - (value / max_score * 56)
        points.append(f"{x:.2f},{y:.2f}")
    return {
        "innings": item["innings"],
        "team": item["batting_team"],
        "values": values,
        "points": " ".join(points),
    }


def _team_accents(innings: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    accents = ["#f0b429", "#5b8def", "#b6f24a", "#e5484d"]
    seen = []
    for item in innings:
        team = item.get("batting_team")
        if team and team not in seen:
            seen.append(team)
    return [{"name": team, "accent": accents[index % len(accents)]} for index, team in enumerate(seen)]


def _result_text(match: Dict[str, Any], innings: List[Dict[str, Any]]) -> str:
    winner = match.get("winner")
    if not winner:
        return "Result unavailable"
    outcome = match.get("outcome") or {}
    by = outcome.get("by") if isinstance(outcome, dict) else None
    if isinstance(by, dict):
        if by.get("runs"):
            return f"{winner} won by {by['runs']} runs"
        if by.get("wickets"):
            return f"{winner} won by {by['wickets']} wickets"
    if len(innings) >= 2 and innings[1]["score"]["team"] == winner:
        wkts = 10 - innings[1]["score"]["wickets"]
        if wkts > 0:
            return f"{winner} won by {wkts} wickets"
    return f"{winner} won"


def _chase_note(innings: List[Dict[str, Any]]) -> Optional[str]:
    if len(innings) < 2:
        return None
    first = innings[0]["score"]
    second = innings[1]["score"]
    target = first["runs"] + 1
    if second["runs"] >= target:
        balls_left = max(0, 120 - int(second.get("balls") or 0))
        return f"Chased {target} with {balls_left} balls to spare"
    return f"Target {target}"


def _sr(runs: int, balls: int) -> int:
    return round(runs * 100.0 / balls) if balls else 0


def _econ(runs: int, balls: int) -> float:
    return round(runs * 6.0 / balls, 1) if balls else 0.0


def _econ_color(econ: float) -> str:
    if econ < 7:
        return "#b6f24a"
    if econ <= 9:
        return "#f0b429"
    return "#e5484d"


def _balls_to_overs(balls: int) -> str:
    return f"{balls // 6}.{balls % 6}"


def _slug(value: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return token or "unknown"
