"""
Rolling form metrics service.
"""

from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from services.analytics_common import (
    build_matches_filter_sql,
    normalize_leagues,
    overs_float_to_balls,
    rolling_mean,
)
from services.player_aliases import get_all_name_variants, get_player_names, resolve_to_legacy_name


def calculate_form_flag(
    current_value: Optional[float],
    baseline_value: Optional[float],
    *,
    higher_is_better: bool = True,
    threshold: float = 0.15,
) -> str:
    if current_value is None or baseline_value is None or baseline_value == 0:
        return "neutral"

    ratio = float(current_value) / float(baseline_value)
    hot_cutoff = 1.0 + threshold
    cold_cutoff = 1.0 - threshold

    if higher_is_better:
        if ratio >= hot_cutoff:
            return "hot"
        if ratio <= cold_cutoff:
            return "cold"
    else:
        if ratio <= cold_cutoff:
            return "hot"
        if ratio >= hot_cutoff:
            return "cold"
    return "neutral"


def _derive_recent_form_flag(values: List[Optional[float]], window: int) -> str:
    clean = [float(v) for v in values if v is not None]
    if not clean:
        return "neutral"
    window = max(1, window)

    recent = clean[-window:]
    previous = clean[-(2 * window) : -window] if len(clean) > window else []

    current_avg = sum(recent) / len(recent) if recent else None
    baseline = (sum(previous) / len(previous)) if previous else (sum(clean) / len(clean))
    return calculate_form_flag(current_avg, baseline, higher_is_better=True, threshold=0.1)


def _fetch_batting_timeline(
    *,
    db: Session,
    player_variants: List[str],
    start_date: Optional[date],
    end_date: Optional[date],
    leagues: List[str],
    include_international: bool,
    venue: Optional[str],
) -> List[Dict]:
    params: Dict = {"player_variants": player_variants}
    match_filter = build_matches_filter_sql(
        alias="m",
        start_date=start_date,
        end_date=end_date,
        leagues=leagues,
        include_international=include_international,
        venue=venue,
        params=params,
    )
    query = text(
        f"""
        SELECT
            bs.match_id,
            m.date,
            m.competition,
            m.venue,
            COALESCE(bs.runs, 0) AS runs,
            COALESCE(bs.balls_faced, 0) AS balls_faced,
            COALESCE(bs.strike_rate, 0) AS strike_rate,
            COALESCE(bs.fantasy_points, 0) AS fantasy_points
        FROM batting_stats bs
        JOIN matches m ON m.id = bs.match_id
        WHERE bs.striker = ANY(:player_variants)
          {match_filter}
        ORDER BY m.date, bs.match_id
        """
    )
    return [dict(row) for row in db.execute(query, params).mappings().all()]


def _fetch_bowling_timeline(
    *,
    db: Session,
    player_variants: List[str],
    start_date: Optional[date],
    end_date: Optional[date],
    leagues: List[str],
    include_international: bool,
    venue: Optional[str],
) -> List[Dict]:
    params: Dict = {"player_variants": player_variants}
    match_filter = build_matches_filter_sql(
        alias="m",
        start_date=start_date,
        end_date=end_date,
        leagues=leagues,
        include_international=include_international,
        venue=venue,
        params=params,
    )
    query = text(
        f"""
        SELECT
            bs.match_id,
            m.date,
            m.competition,
            m.venue,
            COALESCE(bs.overs, 0) AS overs,
            COALESCE(bs.runs_conceded, 0) AS runs_conceded,
            COALESCE(bs.wickets, 0) AS wickets,
            COALESCE(bs.economy, 0) AS economy,
            COALESCE(bs.fantasy_points, 0) AS fantasy_points
        FROM bowling_stats bs
        JOIN matches m ON m.id = bs.match_id
        WHERE bs.bowler = ANY(:player_variants)
          {match_filter}
        ORDER BY m.date, bs.match_id
        """
    )
    return [dict(row) for row in db.execute(query, params).mappings().all()]


def _with_batting_rolling(rows: List[Dict], window: int) -> List[Dict]:
    runs = [float(r["runs"]) for r in rows]
    strike_rate = [float(r["strike_rate"]) for r in rows]
    fantasy = [float(r["fantasy_points"]) for r in rows]

    rolling_runs = rolling_mean(runs, window)
    rolling_sr = rolling_mean(strike_rate, window)
    rolling_fp = rolling_mean(fantasy, window)

    out = []
    for idx, row in enumerate(rows):
        record = dict(row)
        record["rolling_runs_avg"] = round(rolling_runs[idx], 2) if rolling_runs[idx] is not None else None
        record["rolling_strike_rate_avg"] = round(rolling_sr[idx], 2) if rolling_sr[idx] is not None else None
        record["rolling_fantasy_points_avg"] = round(rolling_fp[idx], 2) if rolling_fp[idx] is not None else None
        out.append(record)
    return out


def _with_bowling_rolling(rows: List[Dict], window: int) -> List[Dict]:
    wickets = [float(r["wickets"]) for r in rows]
    economy = [float(r["economy"]) for r in rows]
    fantasy = [float(r["fantasy_points"]) for r in rows]

    rolling_wickets = rolling_mean(wickets, window)
    rolling_economy = rolling_mean(economy, window)
    rolling_fp = rolling_mean(fantasy, window)

    out = []
    for idx, row in enumerate(rows):
        balls = overs_float_to_balls(float(row.get("overs") or 0))
        wkts = int(row.get("wickets") or 0)
        inning_sr = (balls / wkts) if wkts > 0 else None

        start_idx = max(0, idx - window + 1)
        window_chunk = rows[start_idx : idx + 1]
        window_balls = sum(overs_float_to_balls(float(r.get("overs") or 0)) for r in window_chunk)
        window_wkts = sum(int(r.get("wickets") or 0) for r in window_chunk)
        rolling_sr = (window_balls / window_wkts) if window_wkts > 0 else None

        record = dict(row)
        record["bowling_strike_rate"] = round(inning_sr, 2) if inning_sr is not None else None
        record["rolling_wickets_avg"] = round(rolling_wickets[idx], 2) if rolling_wickets[idx] is not None else None
        record["rolling_economy_avg"] = round(rolling_economy[idx], 2) if rolling_economy[idx] is not None else None
        record["rolling_bowling_strike_rate_avg"] = round(rolling_sr, 2) if rolling_sr is not None else None
        record["rolling_fantasy_points_avg"] = round(rolling_fp[idx], 2) if rolling_fp[idx] is not None else None
        out.append(record)
    return out


def get_player_rolling_form(
    *,
    db: Session,
    player_name: str,
    window: int,
    role: str,
    start_date: Optional[date],
    end_date: Optional[date],
    leagues: Optional[List[str]],
    include_international: bool,
    venue: Optional[str],
) -> Dict:
    window = max(1, int(window or 10))
    role = (role or "all").lower()
    if role not in {"batting", "bowling", "all"}:
        raise ValueError("role must be one of: batting, bowling, all")

    names = get_player_names(player_name, db)
    variants = get_all_name_variants(
        [player_name, names["legacy_name"], names["details_name"]],
        db,
    )
    leagues_expanded = normalize_leagues(leagues)

    batting_rows: List[Dict] = []
    bowling_rows: List[Dict] = []

    if role in {"batting", "all"}:
        batting_rows = _fetch_batting_timeline(
            db=db,
            player_variants=variants,
            start_date=start_date,
            end_date=end_date,
            leagues=leagues_expanded,
            include_international=include_international,
            venue=venue,
        )
        batting_rows = _with_batting_rolling(batting_rows, window)

    if role in {"bowling", "all"}:
        bowling_rows = _fetch_bowling_timeline(
            db=db,
            player_variants=variants,
            start_date=start_date,
            end_date=end_date,
            leagues=leagues_expanded,
            include_international=include_international,
            venue=venue,
        )
        bowling_rows = _with_bowling_rolling(bowling_rows, window)

    batting_flag = _derive_recent_form_flag(
        [float(r.get("fantasy_points") or 0) for r in batting_rows],
        window,
    )
    bowling_flag = _derive_recent_form_flag(
        [float(r.get("fantasy_points") or 0) for r in bowling_rows],
        window,
    )

    overall_flag = "neutral"
    if "cold" in {batting_flag, bowling_flag} and "hot" not in {batting_flag, bowling_flag}:
        overall_flag = "cold"
    elif "hot" in {batting_flag, bowling_flag} and "cold" not in {batting_flag, bowling_flag}:
        overall_flag = "hot"

    return {
        "player_name": player_name,
        "resolved_names": names,
        "window": window,
        "role": role,
        "form_flag": overall_flag,
        "batting_form_flag": batting_flag,
        "bowling_form_flag": bowling_flag,
        "batting_innings": batting_rows,
        "bowling_innings": bowling_rows,
    }


def get_form_flags_for_players(
    *,
    db: Session,
    player_names: List[str],
    window: int = 10,
) -> Dict[str, str]:
    """
    Lightweight helper for badge enrichment in match-preview/fantasy APIs.
    """
    out: Dict[str, str] = {}
    if not hasattr(db, "execute"):
        for name in player_names:
            if name:
                out[name] = "neutral"
        return out
    window = max(1, int(window or 10))
    limit = max(window * 2, 10)

    for name in player_names:
        if not name:
            continue
        legacy = resolve_to_legacy_name(name, db)
        query = text(
            """
            WITH combined AS (
                SELECT m.date, bs.fantasy_points
                FROM batting_stats bs
                JOIN matches m ON m.id = bs.match_id
                WHERE bs.striker = :player AND bs.fantasy_points IS NOT NULL
                UNION ALL
                SELECT m.date, bw.fantasy_points
                FROM bowling_stats bw
                JOIN matches m ON m.id = bw.match_id
                WHERE bw.bowler = :player AND bw.fantasy_points IS NOT NULL
            )
            SELECT fantasy_points
            FROM combined
            ORDER BY date DESC
            LIMIT :limit
            """
        )
        rows = db.execute(query, {"player": legacy, "limit": limit}).fetchall()
        values = [float(r[0]) for r in rows if r and r[0] is not None]
        out[name] = _derive_recent_form_flag(list(reversed(values)), window)

    return out
