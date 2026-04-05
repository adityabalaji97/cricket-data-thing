"""
Rolling form metrics service.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from services.analytics_common import (
    build_matches_filter_sql,
    normalize_leagues,
    overs_float_to_balls,
    rolling_mean,
)
from services.delivery_data_service import (
    build_competition_filter_delivery_details,
    build_venue_filter_delivery_details,
)
from services.player_aliases import get_all_name_variants, get_player_names, resolve_to_legacy_name


BOWLER_WICKET_TYPES = (
    "bowled",
    "caught",
    "lbw",
    "caught and bowled",
    "stumped",
    "hit wicket",
)
DELIVERY_DETAILS_AUGMENT_GAP_DAYS = 45


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


def _as_date(value) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except Exception:
        return None


def _latest_timeline_date(rows: List[Dict]) -> Optional[date]:
    dates = [_as_date(row.get("date")) for row in rows]
    dates = [d for d in dates if d]
    return max(dates) if dates else None


def _needs_delivery_details_augmentation(rows: List[Dict], end_date: Optional[date]) -> bool:
    if not rows:
        return True
    if not end_date:
        return False
    latest = _latest_timeline_date(rows)
    if not latest:
        return True
    return latest <= (end_date - timedelta(days=DELIVERY_DETAILS_AUGMENT_GAP_DAYS))


def _timeline_key(row: Dict) -> tuple:
    return (str(row.get("match_id") or ""), int(row.get("innings") or 0))


def _merge_timeline_rows(primary_rows: List[Dict], augmented_rows: List[Dict]) -> List[Dict]:
    merged: Dict[tuple, Dict] = {}
    for row in primary_rows:
        merged[_timeline_key(row)] = dict(row)

    for row in augmented_rows:
        key = _timeline_key(row)
        existing = merged.get(key)
        if existing is None:
            merged[key] = dict(row)
            continue
        existing_date = _as_date(existing.get("date"))
        new_date = _as_date(row.get("date"))
        # Prefer fresher row if keys collide (should be rare).
        if new_date and (not existing_date or new_date >= existing_date):
            merged[key] = dict(row)

    return sorted(
        merged.values(),
        key=lambda r: (
            _as_date(r.get("date")) or date.min,
            str(r.get("match_id") or ""),
            int(r.get("innings") or 0),
        ),
    )


def _compute_batting_fantasy_points(
    *,
    runs: int,
    balls_faced: int,
    fours: int,
    sixes: int,
    dismissed: bool,
) -> float:
    points = float(runs + (fours * 4) + (sixes * 6))

    if runs >= 100:
        points += 16
    elif runs >= 75:
        points += 12
    elif runs >= 50:
        points += 8
    elif runs >= 25:
        points += 4

    if runs == 0 and dismissed:
        points -= 2

    if balls_faced >= 10:
        sr = (runs * 100.0) / balls_faced if balls_faced else 0.0
        if sr > 170:
            points += 6
        elif 150 < sr <= 170:
            points += 4
        elif 130 <= sr <= 150:
            points += 2
        elif 60 <= sr < 70:
            points -= 2
        elif 50 <= sr < 60:
            points -= 4
        elif sr < 50:
            points -= 6
    return round(points, 2)


def _compute_bowling_fantasy_points(
    *,
    wickets: int,
    dots: int,
    overs: float,
    economy: Optional[float],
) -> float:
    points = float((dots * 1) + (wickets * 25))

    if wickets >= 5:
        points += 12
    elif wickets >= 4:
        points += 8
    elif wickets >= 3:
        points += 4

    if overs >= 2 and economy is not None:
        if economy < 5:
            points += 6
        elif 5 <= economy < 6:
            points += 4
        elif 6 <= economy <= 7:
            points += 2
        elif 10 <= economy < 11:
            points -= 2
        elif 11 <= economy < 12:
            points -= 4
        elif economy >= 12:
            points -= 6
    return round(points, 2)


def _discover_delivery_details_name_variants(
    *,
    db: Session,
    seed_names: List[str],
    role: str,
    start_date: Optional[date],
    end_date: Optional[date],
    leagues: List[str],
    include_international: bool,
    venue: Optional[str],
) -> List[str]:
    role_col = "dd.bat" if role == "batting" else "dd.bowl"
    params: Dict = {
        "seed_names": [name for name in seed_names if name],
        "start_date": start_date,
        "end_date": end_date,
        "leagues": leagues,
    }
    venue_filter = build_venue_filter_delivery_details(venue, params)
    comp_filter = build_competition_filter_delivery_details(leagues, include_international, None, params)

    if params["seed_names"]:
        exact_query = text(
            f"""
            SELECT
                {role_col} AS player_name,
                COUNT(*) AS balls
            FROM delivery_details dd
            WHERE {role_col} = ANY(:seed_names)
              AND (:start_date IS NULL OR dd.match_date::date >= :start_date)
              AND (:end_date IS NULL OR dd.match_date::date <= :end_date)
              {venue_filter}
              {comp_filter}
            GROUP BY {role_col}
            ORDER BY balls DESC
            """
        )
        exact_rows = db.execute(exact_query, params).mappings().all()
        if exact_rows:
            return [str(row["player_name"]) for row in exact_rows if row.get("player_name")]

    candidates: Dict[str, Dict[str, int]] = {}
    seeds = [str(name).strip() for name in seed_names if name]
    for seed in seeds:
        parts = [part for part in seed.split() if part]
        if len(parts) != 2:
            continue
        initials = parts[0].strip()
        tail = parts[1].strip().lower()
        if not initials.isalpha() or initials.upper() != initials or len(initials) > 3 or len(tail) < 3:
            continue

        # Pattern A: "A Mhatre" -> "Ayush Mhatre"
        if len(initials) == 1:
            pattern_query = text(
                f"""
                WITH grouped AS (
                    SELECT
                        {role_col} AS player_name,
                        COUNT(*) AS balls,
                        LOWER(SPLIT_PART({role_col}, ' ', 1)) AS first_token,
                        LOWER(REGEXP_REPLACE({role_col}, '^.*\\s', '')) AS last_token
                    FROM delivery_details dd
                    WHERE (:start_date IS NULL OR dd.match_date::date >= :start_date)
                      AND (:end_date IS NULL OR dd.match_date::date <= :end_date)
                      {venue_filter}
                      {comp_filter}
                    GROUP BY {role_col}
                )
                SELECT player_name, balls
                FROM grouped
                WHERE last_token = :tail
                  AND first_token LIKE :first_initial_prefix
                ORDER BY balls DESC
                LIMIT 5
                """
            )
            rows = db.execute(
                pattern_query,
                {
                    **params,
                    "tail": tail,
                    "first_initial_prefix": initials.lower() + "%",
                },
            ).mappings().all()
            for row in rows:
                name = str(row["player_name"])
                balls = int(row["balls"] or 0)
                prev = candidates.get(name, {"score": 0, "balls": 0})
                candidates[name] = {"score": max(prev["score"], 4), "balls": max(prev["balls"], balls)}
            continue

        # Pattern B: "CV Varun" -> "Varun Chakravarthy"
        if len(initials) >= 2:
            first_name_query = text(
                f"""
                WITH grouped AS (
                    SELECT
                        {role_col} AS player_name,
                        COUNT(*) AS balls,
                        LOWER(SPLIT_PART({role_col}, ' ', 1)) AS first_token,
                        LOWER(REGEXP_REPLACE({role_col}, '^.*\\s', '')) AS last_token
                    FROM delivery_details dd
                    WHERE (:start_date IS NULL OR dd.match_date::date >= :start_date)
                      AND (:end_date IS NULL OR dd.match_date::date <= :end_date)
                      {venue_filter}
                      {comp_filter}
                    GROUP BY {role_col}
                )
                SELECT player_name, balls
                FROM grouped
                WHERE first_token = :tail
                  AND LEFT(last_token, 1) = :surname_initial
                  AND LEFT(first_token, 1) = :given_initial
                ORDER BY balls DESC
                LIMIT 5
                """
            )
            rows = db.execute(
                first_name_query,
                {
                    **params,
                    "tail": tail,
                    "surname_initial": initials[0].lower(),
                    "given_initial": initials[-1].lower(),
                },
            ).mappings().all()
            for row in rows:
                name = str(row["player_name"])
                balls = int(row["balls"] or 0)
                prev = candidates.get(name, {"score": 0, "balls": 0})
                candidates[name] = {"score": max(prev["score"], 6), "balls": max(prev["balls"], balls)}

            # Pattern C: "YB Jaiswal" style legacy tokenization fallback
            surname_query = text(
                f"""
                WITH grouped AS (
                    SELECT
                        {role_col} AS player_name,
                        COUNT(*) AS balls,
                        LOWER(SPLIT_PART({role_col}, ' ', 1)) AS first_token,
                        LOWER(REGEXP_REPLACE({role_col}, '^.*\\s', '')) AS last_token
                    FROM delivery_details dd
                    WHERE (:start_date IS NULL OR dd.match_date::date >= :start_date)
                      AND (:end_date IS NULL OR dd.match_date::date <= :end_date)
                      {venue_filter}
                      {comp_filter}
                    GROUP BY {role_col}
                )
                SELECT player_name, balls
                FROM grouped
                WHERE last_token = :tail
                  AND LEFT(first_token, 1) = :given_initial
                ORDER BY balls DESC
                LIMIT 5
                """
            )
            rows = db.execute(
                surname_query,
                {
                    **params,
                    "tail": tail,
                    "given_initial": initials[-1].lower(),
                },
            ).mappings().all()
            for row in rows:
                name = str(row["player_name"])
                balls = int(row["balls"] or 0)
                prev = candidates.get(name, {"score": 0, "balls": 0})
                candidates[name] = {"score": max(prev["score"], 5), "balls": max(prev["balls"], balls)}

    ranked = sorted(
        candidates.items(),
        key=lambda item: (item[1]["score"], item[1]["balls"]),
        reverse=True,
    )
    # Keep only high-confidence candidates.
    return [name for name, meta in ranked if meta["score"] >= 5 and meta["balls"] >= 12][:3]


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
            bs.innings,
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
            bs.innings,
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


def _fetch_batting_timeline_dd(
    *,
    db: Session,
    player_variants: List[str],
    start_date: Optional[date],
    end_date: Optional[date],
    leagues: List[str],
    include_international: bool,
    venue: Optional[str],
) -> List[Dict]:
    if not player_variants:
        return []

    params: Dict = {
        "player_variants": player_variants,
        "start_date": start_date,
        "end_date": end_date,
        "leagues": leagues,
    }
    venue_filter = build_venue_filter_delivery_details(venue, params)
    comp_filter = build_competition_filter_delivery_details(leagues, include_international, None, params)

    query = text(
        f"""
        SELECT
            dd.p_match AS match_id,
            dd.inns AS innings,
            m.date,
            m.competition,
            m.venue,
            SUM(COALESCE(dd.batruns, 0)) AS runs,
            SUM(CASE WHEN COALESCE(dd.wide, 0) = 0 THEN 1 ELSE 0 END) AS balls_faced,
            SUM(CASE WHEN COALESCE(dd.batruns, 0) = 4 THEN 1 ELSE 0 END) AS fours,
            SUM(CASE WHEN COALESCE(dd.batruns, 0) = 6 THEN 1 ELSE 0 END) AS sixes,
            SUM(
                CASE
                    WHEN LOWER(COALESCE(dd.out::text, '')) IN ('true', 't', '1', 'yes')
                    THEN 1 ELSE 0
                END
            ) AS dismissals
        FROM delivery_details dd
        JOIN matches m ON m.id = dd.p_match
        WHERE dd.bat = ANY(:player_variants)
          AND (:start_date IS NULL OR dd.match_date::date >= :start_date)
          AND (:end_date IS NULL OR dd.match_date::date <= :end_date)
          {venue_filter}
          {comp_filter}
        GROUP BY dd.p_match, dd.inns, m.date, m.competition, m.venue
        ORDER BY m.date, dd.p_match, dd.inns
        """
    )
    rows = db.execute(query, params).mappings().all()
    out: List[Dict] = []
    for row in rows:
        runs = int(row.get("runs") or 0)
        balls_faced = int(row.get("balls_faced") or 0)
        fours = int(row.get("fours") or 0)
        sixes = int(row.get("sixes") or 0)
        dismissals = int(row.get("dismissals") or 0)
        strike_rate = (runs * 100.0 / balls_faced) if balls_faced > 0 else 0.0
        fantasy_points = _compute_batting_fantasy_points(
            runs=runs,
            balls_faced=balls_faced,
            fours=fours,
            sixes=sixes,
            dismissed=dismissals > 0,
        )
        out.append(
            {
                "match_id": str(row.get("match_id")),
                "innings": int(row.get("innings") or 0),
                "date": row.get("date"),
                "competition": row.get("competition"),
                "venue": row.get("venue"),
                "runs": runs,
                "balls_faced": balls_faced,
                "strike_rate": round(strike_rate, 2),
                "fantasy_points": fantasy_points,
            }
        )
    return out


def _fetch_bowling_timeline_dd(
    *,
    db: Session,
    player_variants: List[str],
    start_date: Optional[date],
    end_date: Optional[date],
    leagues: List[str],
    include_international: bool,
    venue: Optional[str],
) -> List[Dict]:
    if not player_variants:
        return []

    params: Dict = {
        "player_variants": player_variants,
        "start_date": start_date,
        "end_date": end_date,
        "leagues": leagues,
        "bowler_wickets": list(BOWLER_WICKET_TYPES),
    }
    venue_filter = build_venue_filter_delivery_details(venue, params)
    comp_filter = build_competition_filter_delivery_details(leagues, include_international, None, params)
    query = text(
        f"""
        SELECT
            dd.p_match AS match_id,
            dd.inns AS innings,
            m.date,
            m.competition,
            m.venue,
            SUM(CASE WHEN COALESCE(dd.wide, 0) = 0 AND COALESCE(dd.noball, 0) = 0 THEN 1 ELSE 0 END) AS legal_balls,
            SUM(COALESCE(dd.score, 0)) AS runs_conceded,
            SUM(
                CASE
                    WHEN LOWER(COALESCE(dd.dismissal, '')) = ANY(:bowler_wickets)
                    THEN 1 ELSE 0
                END
            ) AS wickets,
            SUM(
                CASE
                    WHEN COALESCE(dd.score, 0) = 0 AND COALESCE(dd.wide, 0) = 0 AND COALESCE(dd.noball, 0) = 0
                    THEN 1 ELSE 0
                END
            ) AS dots
        FROM delivery_details dd
        JOIN matches m ON m.id = dd.p_match
        WHERE dd.bowl = ANY(:player_variants)
          AND (:start_date IS NULL OR dd.match_date::date >= :start_date)
          AND (:end_date IS NULL OR dd.match_date::date <= :end_date)
          {venue_filter}
          {comp_filter}
        GROUP BY dd.p_match, dd.inns, m.date, m.competition, m.venue
        ORDER BY m.date, dd.p_match, dd.inns
        """
    )
    rows = db.execute(query, params).mappings().all()
    out: List[Dict] = []
    for row in rows:
        legal_balls = int(row.get("legal_balls") or 0)
        runs_conceded = int(row.get("runs_conceded") or 0)
        wickets = int(row.get("wickets") or 0)
        dots = int(row.get("dots") or 0)
        overs = legal_balls / 6.0
        economy = (runs_conceded * 6.0 / legal_balls) if legal_balls > 0 else 0.0
        fantasy_points = _compute_bowling_fantasy_points(
            wickets=wickets,
            dots=dots,
            overs=overs,
            economy=economy if legal_balls > 0 else None,
        )
        out.append(
            {
                "match_id": str(row.get("match_id")),
                "innings": int(row.get("innings") or 0),
                "date": row.get("date"),
                "competition": row.get("competition"),
                "venue": row.get("venue"),
                "overs": round(overs, 1),
                "runs_conceded": runs_conceded,
                "wickets": wickets,
                "economy": round(economy, 2) if legal_balls > 0 else 0.0,
                "fantasy_points": fantasy_points,
            }
        )
    return out


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
    data_quality_notes: List[str] = []

    batting_rows: List[Dict] = []
    bowling_rows: List[Dict] = []
    seed_names = list(dict.fromkeys([player_name, names["legacy_name"], names["details_name"]]))

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
        if _needs_delivery_details_augmentation(batting_rows, end_date):
            dd_name_variants = _discover_delivery_details_name_variants(
                db=db,
                seed_names=seed_names + variants,
                role="batting",
                start_date=start_date,
                end_date=end_date,
                leagues=leagues_expanded,
                include_international=include_international,
                venue=venue,
            )
            dd_batting_rows = _fetch_batting_timeline_dd(
                db=db,
                player_variants=dd_name_variants,
                start_date=start_date,
                end_date=end_date,
                leagues=leagues_expanded,
                include_international=include_international,
                venue=venue,
            )
            if dd_batting_rows:
                before = len(batting_rows)
                batting_rows = _merge_timeline_rows(batting_rows, dd_batting_rows)
                if len(batting_rows) > before:
                    data_quality_notes.append(
                        "Rolling batting form augmented from delivery_details for missing recent matches."
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
        if _needs_delivery_details_augmentation(bowling_rows, end_date):
            dd_name_variants = _discover_delivery_details_name_variants(
                db=db,
                seed_names=seed_names + variants,
                role="bowling",
                start_date=start_date,
                end_date=end_date,
                leagues=leagues_expanded,
                include_international=include_international,
                venue=venue,
            )
            dd_bowling_rows = _fetch_bowling_timeline_dd(
                db=db,
                player_variants=dd_name_variants,
                start_date=start_date,
                end_date=end_date,
                leagues=leagues_expanded,
                include_international=include_international,
                venue=venue,
            )
            if dd_bowling_rows:
                before = len(bowling_rows)
                bowling_rows = _merge_timeline_rows(bowling_rows, dd_bowling_rows)
                if len(bowling_rows) > before:
                    data_quality_notes.append(
                        "Rolling bowling form augmented from delivery_details for missing recent matches."
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

    payload = {
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
    if data_quality_notes:
        payload["data_quality_note"] = " ".join(data_quality_notes)
    return payload


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
