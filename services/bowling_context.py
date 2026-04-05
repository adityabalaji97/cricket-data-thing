"""
Bowling context analytics service.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from services.analytics_common import (
    mean,
    normalize_leagues,
    split_spells_by_gap,
)
from services.delivery_data_service import (
    build_competition_filter_deliveries,
    build_competition_filter_delivery_details,
    build_venue_filter_deliveries,
    build_venue_filter_delivery_details,
    should_use_delivery_details,
)
from services.player_aliases import get_all_name_variants, get_player_names


def classify_pressure_bucket(previous_over_runs: Optional[int], threshold: int) -> str:
    if previous_over_runs is None:
        return "no_previous_over"
    low_threshold = max(0, threshold - 4)
    if previous_over_runs >= threshold:
        return "high_pressure"
    if previous_over_runs <= low_threshold:
        return "low_pressure"
    return "neutral_pressure"


def _fetch_bowler_rows_dd(
    *,
    db: Session,
    bowler_names: List[str],
    date_range: Optional[Tuple[date, date]],
    leagues: List[str],
    include_international: bool,
    venue: Optional[str],
) -> List[Dict]:
    if not bowler_names:
        return []
    params: Dict = {"bowler_names": bowler_names, "leagues": leagues}

    venue_filter = build_venue_filter_delivery_details(venue, params)
    comp_filter = build_competition_filter_delivery_details(leagues, include_international, None, params)

    start_date = date_range[0] if date_range else None
    end_date = date_range[1] if date_range else None
    params["start_date"] = start_date
    params["end_date"] = end_date

    query = text(
        f"""
        SELECT
            dd.p_match AS match_id,
            dd.inns AS innings,
            dd.over AS over_num,
            dd.ball AS ball_num,
            dd.bowl AS bowler,
            COALESCE(dd.score, 0) AS total_runs,
            COALESCE(dd.batruns, 0) AS bat_runs,
            CASE WHEN dd.out THEN 1 ELSE 0 END AS wicket,
            COALESCE(dd.wide, 0) AS wide,
            COALESCE(dd.noball, 0) AS noball,
            dd.inns_runs,
            dd.inns_wkts,
            dd.inns_rr
        FROM delivery_details dd
        WHERE dd.bowl = ANY(:bowler_names)
          AND (:start_date IS NULL OR dd.match_date::date >= :start_date)
          AND (:end_date IS NULL OR dd.match_date::date <= :end_date)
          {venue_filter}
          {comp_filter}
        ORDER BY dd.p_match, dd.inns, dd.over, dd.ball
        """
    )
    return [dict(row) for row in db.execute(query, params).mappings().all()]


def _fetch_over_stats_dd(
    *,
    db: Session,
    match_ids: List[str],
) -> Dict[Tuple[str, int, int], Dict]:
    if not match_ids:
        return {}
    query = text(
        """
        SELECT
            dd.p_match AS match_id,
            dd.inns AS innings,
            dd.over AS over_num,
            MIN(dd.bowl) AS bowler,
            SUM(COALESCE(dd.score, 0)) AS runs,
            SUM(CASE WHEN dd.out THEN 1 ELSE 0 END) AS wickets,
            SUM(CASE WHEN COALESCE(dd.wide, 0) = 0 AND COALESCE(dd.noball, 0) = 0 THEN 1 ELSE 0 END) AS legal_balls
        FROM delivery_details dd
        WHERE dd.p_match = ANY(:match_ids)
        GROUP BY dd.p_match, dd.inns, dd.over
        """
    )
    rows = db.execute(query, {"match_ids": match_ids}).mappings().all()
    out: Dict[Tuple[str, int, int], Dict] = {}
    for row in rows:
        key = (str(row["match_id"]), int(row["innings"]), int(row["over_num"]))
        out[key] = {
            "match_id": str(row["match_id"]),
            "innings": int(row["innings"]),
            "over": int(row["over_num"]),
            "bowler": row["bowler"],
            "runs": int(row["runs"] or 0),
            "wickets": int(row["wickets"] or 0),
            "legal_balls": int(row["legal_balls"] or 0),
        }
    return out


def _fetch_bowler_rows_deliveries(
    *,
    db: Session,
    bowler_names: List[str],
    date_range: Optional[Tuple[date, date]],
    leagues: List[str],
    include_international: bool,
    venue: Optional[str],
) -> List[Dict]:
    if not bowler_names:
        return []
    params: Dict = {
        "bowler_names": bowler_names,
        "leagues": leagues,
        "start_date": date_range[0] if date_range else None,
        "end_date": date_range[1] if date_range else None,
    }
    venue_filter = build_venue_filter_deliveries(venue, params)
    comp_filter = build_competition_filter_deliveries(leagues, include_international, None, params)
    query = text(
        f"""
        SELECT
            d.match_id,
            d.innings,
            d.over AS over_num,
            d.ball AS ball_num,
            d.bowler,
            (COALESCE(d.runs_off_bat, 0) + COALESCE(d.extras, 0)) AS total_runs,
            COALESCE(d.runs_off_bat, 0) AS bat_runs,
            CASE WHEN d.wicket_type IS NOT NULL AND d.wicket_type != '' THEN 1 ELSE 0 END AS wicket,
            COALESCE(d.wides, 0) AS wide,
            COALESCE(d.noballs, 0) AS noball
        FROM deliveries d
        JOIN matches m ON m.id = d.match_id
        WHERE d.bowler = ANY(:bowler_names)
          AND (:start_date IS NULL OR m.date >= :start_date)
          AND (:end_date IS NULL OR m.date <= :end_date)
          {venue_filter}
          {comp_filter}
        ORDER BY d.match_id, d.innings, d.over, d.ball
        """
    )
    return [dict(row) for row in db.execute(query, params).mappings().all()]


def _fetch_over_stats_deliveries(
    *,
    db: Session,
    match_ids: List[str],
) -> Dict[Tuple[str, int, int], Dict]:
    if not match_ids:
        return {}
    query = text(
        """
        SELECT
            d.match_id,
            d.innings,
            d.over AS over_num,
            MIN(d.bowler) AS bowler,
            SUM(COALESCE(d.runs_off_bat, 0) + COALESCE(d.extras, 0)) AS runs,
            SUM(CASE WHEN d.wicket_type IS NOT NULL AND d.wicket_type != '' THEN 1 ELSE 0 END) AS wickets,
            SUM(CASE WHEN COALESCE(d.wides, 0) = 0 AND COALESCE(d.noballs, 0) = 0 THEN 1 ELSE 0 END) AS legal_balls
        FROM deliveries d
        WHERE d.match_id = ANY(:match_ids)
        GROUP BY d.match_id, d.innings, d.over
        """
    )
    rows = db.execute(query, {"match_ids": match_ids}).mappings().all()
    out: Dict[Tuple[str, int, int], Dict] = {}
    for row in rows:
        key = (str(row["match_id"]), int(row["innings"]), int(row["over_num"]))
        out[key] = {
            "match_id": str(row["match_id"]),
            "innings": int(row["innings"]),
            "over": int(row["over_num"]),
            "bowler": row["bowler"],
            "runs": int(row["runs"] or 0),
            "wickets": int(row["wickets"] or 0),
            "legal_balls": int(row["legal_balls"] or 0),
        }
    return out


def _aggregate_bowler_overs(rows: List[Dict]) -> Dict[Tuple[str, int, int], Dict]:
    over_map: Dict[Tuple[str, int, int], Dict] = {}
    ordered_rows = sorted(
        rows,
        key=lambda r: (str(r["match_id"]), int(r["innings"]), int(r["over_num"]), int(r["ball_num"])),
    )
    for row in ordered_rows:
        key = (str(row["match_id"]), int(row["innings"]), int(row["over_num"]))
        if key not in over_map:
            over_map[key] = {
                "match_id": str(row["match_id"]),
                "innings": int(row["innings"]),
                "over": int(row["over_num"]),
                "bowler": row["bowler"],
                "runs": 0,
                "wickets": 0,
                "legal_balls": 0,
                "dots": 0,
                "boundaries": 0,
                "first_ball_boundary": None,
                "last_ball_boundary": False,
                "entry_runs": row.get("inns_runs"),
                "entry_wkts": row.get("inns_wkts"),
                "entry_rr": row.get("inns_rr"),
            }

        over = over_map[key]
        total_runs = int(row.get("total_runs") or 0)
        bat_runs = int(row.get("bat_runs") or 0)
        wide = int(row.get("wide") or 0)
        noball = int(row.get("noball") or 0)
        wicket = int(row.get("wicket") or 0)

        over["runs"] += total_runs
        over["wickets"] += wicket
        if bat_runs in (4, 6):
            over["boundaries"] += 1

        first_ball_boundary = bat_runs in (4, 6)
        if over["first_ball_boundary"] is None:
            over["first_ball_boundary"] = first_ball_boundary
        over["last_ball_boundary"] = first_ball_boundary

        if wide == 0 and noball == 0:
            over["legal_balls"] += 1
            if total_runs == 0:
                over["dots"] += 1

    for over in over_map.values():
        if over["first_ball_boundary"] is None:
            over["first_ball_boundary"] = False
    return over_map


def _finalize_over_bucket(agg: Dict) -> Dict:
    overs = int(agg.get("overs", 0))
    legal_balls = int(agg.get("legal_balls", 0))
    runs = int(agg.get("runs", 0))
    wickets = int(agg.get("wickets", 0))
    boundaries = int(agg.get("boundaries", 0))
    return {
        "overs": overs,
        "runs": runs,
        "wickets": wickets,
        "economy": round((runs * 6.0 / legal_balls), 2) if legal_balls else None,
        "wickets_per_over": round((wickets / overs), 3) if overs else None,
        "boundary_pct": round((boundaries * 100.0 / legal_balls), 2) if legal_balls else None,
        "dot_pct": round((int(agg.get("dots", 0)) * 100.0 / legal_balls), 2) if legal_balls else None,
        "avg_previous_over_runs": round(
            (int(agg.get("previous_runs_sum", 0)) / overs), 2
        )
        if overs
        else None,
    }


def get_bowling_context(
    *,
    db: Session,
    player_name: str,
    start_date: Optional[date],
    end_date: Optional[date],
    leagues: Optional[List[str]],
    include_international: bool,
    venue: Optional[str],
    min_overs: int,
    pressure_threshold: int,
) -> Dict:
    names = get_player_names(player_name, db)
    all_name_variants = get_all_name_variants(
        [player_name, names["legacy_name"], names["details_name"]],
        db,
    )
    expanded_leagues = normalize_leagues(leagues)

    routing = should_use_delivery_details(start_date, end_date)
    data_quality_notes: List[str] = []

    bowler_over_map: Dict[Tuple[str, int, int], Dict] = {}
    all_over_map: Dict[Tuple[str, int, int], Dict] = {}

    if routing.get("use_delivery_details"):
        dd_range = routing.get("delivery_details_date_range")
        dd_rows = _fetch_bowler_rows_dd(
            db=db,
            bowler_names=all_name_variants,
            date_range=dd_range,
            leagues=expanded_leagues,
            include_international=include_international,
            venue=venue,
        )
        dd_bowler_over_map = _aggregate_bowler_overs(dd_rows)
        bowler_over_map.update(dd_bowler_over_map)
        dd_match_ids = sorted({over["match_id"] for over in dd_bowler_over_map.values()})
        all_over_map.update(_fetch_over_stats_dd(db=db, match_ids=dd_match_ids))

        # Defensive fallback: if delivery_details has no rows for this bowler/range,
        # still try deliveries as backup even when date routing prefers details only.
        if (
            not dd_bowler_over_map
            and not routing.get("use_deliveries")
        ):
            d_rows = _fetch_bowler_rows_deliveries(
                db=db,
                bowler_names=all_name_variants,
                date_range=(start_date, end_date),
                leagues=expanded_leagues,
                include_international=include_international,
                venue=venue,
            )
            d_bowler_over_map = _aggregate_bowler_overs(d_rows)
            for key, value in d_bowler_over_map.items():
                bowler_over_map.setdefault(key, value)
            d_match_ids = sorted({over["match_id"] for over in d_bowler_over_map.values()})
            d_over_map = _fetch_over_stats_deliveries(db=db, match_ids=d_match_ids)
            for key, value in d_over_map.items():
                all_over_map.setdefault(key, value)
            if d_bowler_over_map:
                data_quality_notes.append(
                    "delivery_details returned no rows for this range; used deliveries fallback."
                )

    if routing.get("use_deliveries"):
        legacy_range = routing.get("deliveries_date_range")
        d_rows = _fetch_bowler_rows_deliveries(
            db=db,
            bowler_names=all_name_variants,
            date_range=legacy_range,
            leagues=expanded_leagues,
            include_international=include_international,
            venue=venue,
        )
        d_bowler_over_map = _aggregate_bowler_overs(d_rows)
        for key, value in d_bowler_over_map.items():
            # Prefer delivery_details if both sources unexpectedly overlap.
            bowler_over_map.setdefault(key, value)
        d_match_ids = sorted({over["match_id"] for over in d_bowler_over_map.values()})
        d_over_map = _fetch_over_stats_deliveries(db=db, match_ids=d_match_ids)
        for key, value in d_over_map.items():
            all_over_map.setdefault(key, value)
        data_quality_notes.append(
            "Used deliveries fallback for date ranges where delivery_details is unavailable."
        )

    if not bowler_over_map:
        return {
            "player_name": player_name,
            "resolved_names": names,
            "total_overs_analyzed": 0,
            "insufficient_sample": True,
            "entry_point_stats": [],
            "spell_stats": {},
            "first_ball_last_ball_stats": {},
            "previous_over_pressure_stats": {},
            "state_on_entry": {},
            "data_quality_note": "No bowling deliveries found for the selected filters.",
        }

    bowler_overs = sorted(
        bowler_over_map.values(),
        key=lambda o: (o["match_id"], o["innings"], o["over"]),
    )

    total_overs = len(bowler_overs)
    insufficient_sample = total_overs < min_overs

    innings_over_map: Dict[Tuple[str, int], List[Dict]] = defaultdict(list)
    for over in bowler_overs:
        innings_over_map[(over["match_id"], over["innings"])].append(over)

    entry_group: Dict[int, Dict] = defaultdict(lambda: {"innings": 0, "overs": 0, "runs": 0, "wickets": 0, "legal_balls": 0})
    entry_states = []
    spell_records = []
    spell_len_dist: Dict[int, int] = defaultdict(int)

    for innings_key, innings_overs in innings_over_map.items():
        innings_overs = sorted(innings_overs, key=lambda o: o["over"])
        entry_over = int(innings_overs[0]["over"])
        entry_stats = entry_group[entry_over]
        entry_stats["innings"] += 1
        entry_stats["overs"] += len(innings_overs)
        entry_stats["runs"] += sum(int(o["runs"]) for o in innings_overs)
        entry_stats["wickets"] += sum(int(o["wickets"]) for o in innings_overs)
        entry_stats["legal_balls"] += sum(int(o["legal_balls"]) for o in innings_overs)

        entry_states.append(
            {
                "runs": innings_overs[0].get("entry_runs"),
                "wickets": innings_overs[0].get("entry_wkts"),
                "run_rate": innings_overs[0].get("entry_rr"),
            }
        )

        over_numbers = [int(o["over"]) for o in innings_overs]
        spells = split_spells_by_gap(over_numbers, gap_threshold=2)
        over_lookup = {int(o["over"]): o for o in innings_overs}
        for idx, spell in enumerate(spells, start=1):
            spell_overs = [over_lookup[n] for n in spell]
            legal_balls = sum(int(o["legal_balls"]) for o in spell_overs)
            spell_record = {
                "is_first_spell": idx == 1,
                "overs": len(spell_overs),
                "runs": sum(int(o["runs"]) for o in spell_overs),
                "wickets": sum(int(o["wickets"]) for o in spell_overs),
                "legal_balls": legal_balls,
                "boundaries": sum(int(o["boundaries"]) for o in spell_overs),
                "dots": sum(int(o["dots"]) for o in spell_overs),
            }
            spell_records.append(spell_record)
            spell_len_dist[len(spell_overs)] += 1

    entry_point_stats = []
    for over_num, agg in sorted(entry_group.items(), key=lambda x: x[0]):
        entry_point_stats.append(
            {
                "entry_over": over_num,
                "innings_count": agg["innings"],
                "overs_bowled": agg["overs"],
                "economy": round((agg["runs"] * 6.0 / agg["legal_balls"]), 2)
                if agg["legal_balls"]
                else None,
                "wickets_per_over": round((agg["wickets"] / agg["overs"]), 3) if agg["overs"] else None,
            }
        )

    first_spell_agg = {"overs": 0, "runs": 0, "wickets": 0, "legal_balls": 0, "boundaries": 0, "dots": 0}
    later_spell_agg = {"overs": 0, "runs": 0, "wickets": 0, "legal_balls": 0, "boundaries": 0, "dots": 0}
    for record in spell_records:
        target = first_spell_agg if record["is_first_spell"] else later_spell_agg
        for key in target:
            target[key] += int(record.get(key, 0))

    first_ball_boundaries = sum(1 for over in bowler_overs if over["first_ball_boundary"])
    last_ball_boundaries = sum(1 for over in bowler_overs if over["last_ball_boundary"])
    legal_balls_total = sum(int(o["legal_balls"]) for o in bowler_overs)
    boundaries_total = sum(int(o["boundaries"]) for o in bowler_overs)
    wickets_total = sum(int(o["wickets"]) for o in bowler_overs)

    pressure_agg: Dict[str, Dict] = defaultdict(
        lambda: {
            "overs": 0,
            "runs": 0,
            "wickets": 0,
            "legal_balls": 0,
            "boundaries": 0,
            "dots": 0,
            "previous_runs_sum": 0,
            "previous_wickets_sum": 0,
        }
    )

    for over in bowler_overs:
        prev_key = (over["match_id"], int(over["innings"]), int(over["over"]) - 1)
        prev = all_over_map.get(prev_key)
        prev_runs = int(prev["runs"]) if prev else None
        bucket = classify_pressure_bucket(prev_runs, pressure_threshold)
        if bucket == "no_previous_over":
            continue
        agg = pressure_agg[bucket]
        agg["overs"] += 1
        agg["runs"] += int(over["runs"])
        agg["wickets"] += int(over["wickets"])
        agg["legal_balls"] += int(over["legal_balls"])
        agg["boundaries"] += int(over["boundaries"])
        agg["dots"] += int(over["dots"])
        agg["previous_runs_sum"] += int(prev_runs or 0)
        agg["previous_wickets_sum"] += int(prev.get("wickets") or 0) if prev else 0

    pressure_stats = {
        "threshold_runs": pressure_threshold,
        "high_pressure": _finalize_over_bucket(pressure_agg.get("high_pressure", {})),
        "neutral_pressure": _finalize_over_bucket(pressure_agg.get("neutral_pressure", {})),
        "low_pressure": _finalize_over_bucket(pressure_agg.get("low_pressure", {})),
    }

    state_on_entry = {
        "sample_innings": len(entry_states),
        "average_runs": round(mean([s["runs"] for s in entry_states if s["runs"] is not None]), 2)
        if entry_states
        else None,
        "average_wickets": round(mean([s["wickets"] for s in entry_states if s["wickets"] is not None]), 2)
        if entry_states
        else None,
        "average_run_rate": round(mean([s["run_rate"] for s in entry_states if s["run_rate"] is not None]), 2)
        if entry_states
        else None,
    }

    first_ball_last_ball_stats = {
        "overs_analyzed": total_overs,
        "first_ball_boundaries": first_ball_boundaries,
        "last_ball_boundaries": last_ball_boundaries,
        "first_ball_boundary_rate_pct": round((first_ball_boundaries * 100.0 / total_overs), 2) if total_overs else None,
        "last_ball_boundary_rate_pct": round((last_ball_boundaries * 100.0 / total_overs), 2) if total_overs else None,
        "overall_boundary_rate_pct": round((boundaries_total * 100.0 / legal_balls_total), 2) if legal_balls_total else None,
        "wickets_per_over": round((wickets_total / total_overs), 3) if total_overs else None,
    }

    spell_stats = {
        "first_spell": _finalize_over_bucket(first_spell_agg),
        "later_spells": _finalize_over_bucket(later_spell_agg),
        "spell_length_distribution": [
            {"overs_in_spell": length, "count": count}
            for length, count in sorted(spell_len_dist.items(), key=lambda x: x[0])
        ],
    }

    payload = {
        "player_name": player_name,
        "resolved_names": names,
        "total_overs_analyzed": total_overs,
        "insufficient_sample": insufficient_sample,
        "entry_point_stats": entry_point_stats,
        "spell_stats": spell_stats,
        "first_ball_last_ball_stats": first_ball_last_ball_stats,
        "previous_over_pressure_stats": pressure_stats,
        "state_on_entry": state_on_entry,
    }
    if data_quality_notes:
        payload["data_quality_note"] = " ".join(data_quality_notes)
    return payload


def _fetch_first_ball_agg_dd(
    *,
    db: Session,
    role: str,
    date_range: Optional[Tuple[date, date]],
    leagues: List[str],
    include_international: bool,
    venue: Optional[str],
) -> Dict[str, Dict]:
    params: Dict = {"leagues": leagues}
    venue_filter = build_venue_filter_delivery_details(venue, params)
    comp_filter = build_competition_filter_delivery_details(leagues, include_international, None, params)
    params["start_date"] = date_range[0] if date_range else None
    params["end_date"] = date_range[1] if date_range else None
    role_col = "bat" if role == "batter" else "bowl"
    query = text(
        f"""
        WITH first_ball AS (
            SELECT
                dd.{role_col} AS player,
                COALESCE(dd.batruns, 0) AS bat_runs,
                COALESCE(dd.score, 0) AS total_runs,
                CASE WHEN dd.out THEN 1 ELSE 0 END AS wicket,
                ROW_NUMBER() OVER (PARTITION BY dd.p_match, dd.inns, dd.over ORDER BY dd.ball) AS rn
            FROM delivery_details dd
            WHERE 1=1
              AND (:start_date IS NULL OR dd.match_date::date >= :start_date)
              AND (:end_date IS NULL OR dd.match_date::date <= :end_date)
              {venue_filter}
              {comp_filter}
        )
        SELECT
            player,
            COUNT(*) AS first_balls,
            SUM(CASE WHEN bat_runs IN (4, 6) THEN 1 ELSE 0 END) AS boundaries,
            SUM(wicket) AS wickets,
            SUM(total_runs) AS total_runs
        FROM first_ball
        WHERE rn = 1
        GROUP BY player
        """
    )
    rows = db.execute(query, params).mappings().all()
    return {
        str(row["player"]): {
            "first_balls": int(row["first_balls"] or 0),
            "boundaries": int(row["boundaries"] or 0),
            "wickets": int(row["wickets"] or 0),
            "total_runs": int(row["total_runs"] or 0),
        }
        for row in rows
        if row.get("player")
    }


def _fetch_first_ball_agg_deliveries(
    *,
    db: Session,
    role: str,
    date_range: Optional[Tuple[date, date]],
    leagues: List[str],
    include_international: bool,
    venue: Optional[str],
) -> Dict[str, Dict]:
    params: Dict = {
        "leagues": leagues,
        "start_date": date_range[0] if date_range else None,
        "end_date": date_range[1] if date_range else None,
    }
    venue_filter = build_venue_filter_deliveries(venue, params)
    comp_filter = build_competition_filter_deliveries(leagues, include_international, None, params)
    role_col = "batter" if role == "batter" else "bowler"
    query = text(
        f"""
        WITH first_ball AS (
            SELECT
                d.{role_col} AS player,
                COALESCE(d.runs_off_bat, 0) AS bat_runs,
                (COALESCE(d.runs_off_bat, 0) + COALESCE(d.extras, 0)) AS total_runs,
                CASE WHEN d.wicket_type IS NOT NULL AND d.wicket_type != '' THEN 1 ELSE 0 END AS wicket,
                ROW_NUMBER() OVER (PARTITION BY d.match_id, d.innings, d.over ORDER BY d.ball) AS rn
            FROM deliveries d
            JOIN matches m ON m.id = d.match_id
            WHERE 1=1
              AND (:start_date IS NULL OR m.date >= :start_date)
              AND (:end_date IS NULL OR m.date <= :end_date)
              {venue_filter}
              {comp_filter}
        )
        SELECT
            player,
            COUNT(*) AS first_balls,
            SUM(CASE WHEN bat_runs IN (4, 6) THEN 1 ELSE 0 END) AS boundaries,
            SUM(wicket) AS wickets,
            SUM(total_runs) AS total_runs
        FROM first_ball
        WHERE rn = 1
        GROUP BY player
        """
    )
    rows = db.execute(query, params).mappings().all()
    return {
        str(row["player"]): {
            "first_balls": int(row["first_balls"] or 0),
            "boundaries": int(row["boundaries"] or 0),
            "wickets": int(row["wickets"] or 0),
            "total_runs": int(row["total_runs"] or 0),
        }
        for row in rows
        if row.get("player")
    }


def get_first_ball_boundary_leaderboard(
    *,
    db: Session,
    role: str,
    start_date: Optional[date],
    end_date: Optional[date],
    leagues: Optional[List[str]],
    include_international: bool,
    venue: Optional[str],
    min_balls: int,
    limit: int,
) -> Dict:
    expanded_leagues = normalize_leagues(leagues)
    routing = should_use_delivery_details(start_date, end_date)

    combined: Dict[str, Dict] = defaultdict(lambda: {"first_balls": 0, "boundaries": 0, "wickets": 0, "total_runs": 0})
    notes: List[str] = []

    if routing.get("use_delivery_details"):
        dd_data = _fetch_first_ball_agg_dd(
            db=db,
            role=role,
            date_range=routing.get("delivery_details_date_range"),
            leagues=expanded_leagues,
            include_international=include_international,
            venue=venue,
        )
        for player, agg in dd_data.items():
            for key, value in agg.items():
                combined[player][key] += int(value)

        if not dd_data and not routing.get("use_deliveries"):
            d_data = _fetch_first_ball_agg_deliveries(
                db=db,
                role=role,
                date_range=(start_date, end_date),
                leagues=expanded_leagues,
                include_international=include_international,
                venue=venue,
            )
            for player, agg in d_data.items():
                for key, value in agg.items():
                    combined[player][key] += int(value)
            if d_data:
                notes.append("delivery_details returned no rows; used deliveries fallback.")

    if routing.get("use_deliveries"):
        d_data = _fetch_first_ball_agg_deliveries(
            db=db,
            role=role,
            date_range=routing.get("deliveries_date_range"),
            leagues=expanded_leagues,
            include_international=include_international,
            venue=venue,
        )
        for player, agg in d_data.items():
            for key, value in agg.items():
                combined[player][key] += int(value)
        notes.append("Used deliveries fallback for legacy date ranges.")

    rows = []
    for player, agg in combined.items():
        balls = int(agg["first_balls"])
        if balls < min_balls:
            continue
        boundaries = int(agg["boundaries"])
        wickets = int(agg["wickets"])
        runs = int(agg["total_runs"])
        rows.append(
            {
                "player": player,
                "first_balls": balls,
                "boundaries": boundaries,
                "boundary_rate_pct": round(boundaries * 100.0 / balls, 2) if balls else None,
                "wickets": wickets,
                "wicket_rate_pct": round(wickets * 100.0 / balls, 2) if balls else None,
                "avg_total_runs_on_first_ball": round(runs / balls, 2) if balls else None,
            }
        )

    rows.sort(key=lambda r: (r["boundary_rate_pct"] or 0, r["first_balls"]), reverse=True)
    leaderboard = rows[:limit]
    for idx, row in enumerate(leaderboard, start=1):
        row["rank"] = idx

    payload = {
        "role": role,
        "min_balls": min_balls,
        "total_players": len(rows),
        "leaderboard": leaderboard,
    }
    if notes:
        payload["data_quality_note"] = " ".join(notes)
    return payload
