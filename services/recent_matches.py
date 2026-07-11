from sqlalchemy.sql import text
from fastapi import HTTPException
from typing import Any, Dict, List, Optional
from models import teams_mapping, leagues_mapping, INTERNATIONAL_TEAMS_RANKED


def _iso_date(value: Any) -> Optional[str]:
    return value.isoformat() if value else None


def _display_competition(competition: Optional[str], is_t20i: bool = False) -> Optional[str]:
    if is_t20i:
        return "T20I"
    return leagues_mapping.get(competition, competition)


def _format_match(row: Any, *, is_t20i: bool = False) -> Dict[str, Any]:
    competition_display = _display_competition(row.competition, is_t20i=is_t20i)
    return {
        "match_id": row.id,
        "date": _iso_date(row.date),
        "venue": row.venue,
        "team1": teams_mapping.get(row.team1, row.team1),
        "team2": teams_mapping.get(row.team2, row.team2),
        "team1_full": row.team1,
        "team2_full": row.team2,
        "team1_score": None,
        "team2_score": None,
        "winner": teams_mapping.get(row.winner, row.winner) if row.winner else None,
        "competition": "T20I" if is_t20i else row.competition,
        "competition_key": "T20I" if is_t20i else row.competition,
        "competition_abbr": competition_display,
        "competition_display": competition_display,
        "match_type": row.match_type,
        "is_international": is_t20i,
        "scorecard_path": f"/scorecard/{row.id}",
    }


def _competition_stats_from_rows(rows: List[Any]) -> Dict[str, Dict[str, Any]]:
    stats: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        is_t20i = row.match_type == "international"
        key = "T20I" if is_t20i else row.competition
        if not key:
            continue
        stats[key] = {
            "competition": key,
            "competition_key": key,
            "competition_display": _display_competition(row.competition, is_t20i=is_t20i),
            "match_type": row.match_type,
            "match_count": row.match_count,
            "earliest_date": _iso_date(row.earliest_date),
            "latest_date": _iso_date(row.latest_date),
            "date_range": f"{row.earliest_date} to {row.latest_date}" if row.earliest_date and row.latest_date else None,
            "priority": 1 if is_t20i else 2,
        }
    return stats


def _discover_filters(competition_stats: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    filters = [{"key": "all", "label": "All", "match_count": sum(s["match_count"] for s in competition_stats.values())}]
    for key, stat in sorted(
        competition_stats.items(),
        key=lambda item: (item[1].get("priority", 9), -(item[1].get("match_count") or 0), item[1].get("competition_display") or item[0]),
    ):
        filters.append({
            "key": key,
            "label": stat["competition_display"],
            "match_count": stat["match_count"],
            "latest_date": stat["latest_date"],
        })
    return filters


def _bounded_int(value: int, *, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = minimum
    return max(minimum, min(maximum, parsed))

def get_recent_matches_by_league_service(db) -> Dict:
    """
    Get the most recent match for each league and T20 internationals, 
    along with match counts for each competition
    Optimized version without expensive deliveries joins
    T20I matches prioritized at the top
    """
    try:
        # Simplified query for most recent match per league - no scores for speed
        recent_league_matches_query = text("""
            WITH recent_matches AS (
                SELECT DISTINCT ON (m.competition)
                    m.id,
                    m.date,
                    m.venue,
                    m.team1,
                    m.team2,
                    m.winner,
                    m.competition,
                    m.match_type
                FROM matches m
                WHERE m.match_type = 'league'
                ORDER BY m.competition, m.date DESC
            )
            SELECT * FROM recent_matches
            ORDER BY date DESC
        """)
        
        # Simplified query for most recent T20 international match
        recent_t20i_query = text("""
            SELECT 
                m.id,
                m.date,
                m.venue,
                m.team1,
                m.team2,
                m.winner,
                m.competition,
                m.match_type
            FROM matches m
            WHERE m.match_type = 'international'
            AND (m.team1 = ANY(:international_teams) AND m.team2 = ANY(:international_teams))
            ORDER BY m.date DESC
            LIMIT 1
        """)
        
        # Simple and fast match counts query
        match_counts_query = text("""
            SELECT 
                m.competition,
                m.match_type,
                COUNT(*) as match_count,
                MIN(m.date) as earliest_date,
                MAX(m.date) as latest_date
            FROM matches m
            WHERE m.match_type IN ('league', 'international')
            GROUP BY m.competition, m.match_type
            ORDER BY match_count DESC, m.competition
        """)
        
        # Execute queries
        league_results = db.execute(recent_league_matches_query).fetchall()
        t20i_result = db.execute(recent_t20i_query, {
            "international_teams": INTERNATIONAL_TEAMS_RANKED
        }).fetchone()
        count_results = db.execute(match_counts_query).fetchall()
        
        # Format matches - T20I first, then leagues
        recent_matches = []
        
        # Add T20I match first if exists
        if t20i_result:
            t20i_match = {
                "match_id": t20i_result.id,
                "date": t20i_result.date.isoformat() if t20i_result.date else None,
                "venue": t20i_result.venue,
                "team1": teams_mapping.get(t20i_result.team1, t20i_result.team1),
                "team2": teams_mapping.get(t20i_result.team2, t20i_result.team2),
                "team1_full": t20i_result.team1,
                "team2_full": t20i_result.team2,
                "team1_score": None,  # Skip scores for performance
                "team2_score": None,  # Skip scores for performance
                "winner": teams_mapping.get(t20i_result.winner, t20i_result.winner) if t20i_result.winner else None,
                "competition": t20i_result.competition,
                "competition_abbr": "T20I",
                "match_type": t20i_result.match_type,
                "is_international": True
            }
            recent_matches.append(t20i_match)
        
        # Then add league matches sorted by date (most recent first)
        league_matches = []
        for row in league_results:
            match_data = {
                "match_id": row.id,
                "date": row.date.isoformat() if row.date else None,
                "venue": row.venue,
                "team1": teams_mapping.get(row.team1, row.team1),
                "team2": teams_mapping.get(row.team2, row.team2),
                "team1_full": row.team1,
                "team2_full": row.team2,
                "team1_score": None,  # Skip scores for performance
                "team2_score": None,  # Skip scores for performance
                "winner": teams_mapping.get(row.winner, row.winner) if row.winner else None,
                "competition": row.competition,
                "competition_abbr": leagues_mapping.get(row.competition, row.competition),
                "match_type": row.match_type,
                "is_international": False
            }
            league_matches.append(match_data)
        
        # Sort league matches by date (most recent first) and add to recent_matches
        league_matches.sort(key=lambda x: x["date"] or "1900-01-01", reverse=True)
        recent_matches.extend(league_matches)
        
        # Format match counts with T20I prioritized
        competition_stats = {}
        
        # Process international matches first
        for row in count_results:
            if row.match_type == 'international':
                competition_key = "T20 Internationals"
                competition_stats[competition_key] = {
                    "competition": row.competition,
                    "competition_display": "T20I",
                    "match_type": row.match_type,
                    "match_count": row.match_count,
                    "earliest_date": row.earliest_date.isoformat() if row.earliest_date else None,
                    "latest_date": row.latest_date.isoformat() if row.latest_date else None,
                    "date_range": f"{row.earliest_date} to {row.latest_date}" if row.earliest_date and row.latest_date else None,
                    "priority": 1  # Highest priority for sorting
                }
        
        # Then process league matches
        for row in count_results:
            if row.match_type == 'league':
                competition_key = row.competition
                competition_stats[competition_key] = {
                    "competition": row.competition,
                    "competition_display": leagues_mapping.get(row.competition, row.competition),
                    "match_type": row.match_type,
                    "match_count": row.match_count,
                    "earliest_date": row.earliest_date.isoformat() if row.earliest_date else None,
                    "latest_date": row.latest_date.isoformat() if row.latest_date else None,
                    "date_range": f"{row.earliest_date} to {row.latest_date}" if row.earliest_date and row.latest_date else None,
                    "priority": 2  # Lower priority than T20I
                }
        
        return {
            "recent_matches": recent_matches,
            "competition_stats": competition_stats,
            "total_competitions": len(competition_stats),
            "total_recent_matches": len(recent_matches)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching recent matches by league: {str(e)}")


def get_recent_matches_discover_service(
    db,
    competition: str = "all",
    limit: int = 12,
    offset: int = 0,
    per_group: int = 3,
) -> Dict[str, Any]:
    """
    Discover recent scorecard-ready matches.

    competition=all returns grouped latest matches for T20I plus leagues.
    competition=T20I or a league name returns a flat paginated result set.
    """
    try:
        limit = _bounded_int(limit, minimum=1, maximum=48)
        offset = max(0, int(offset or 0))
        per_group = _bounded_int(per_group, minimum=1, maximum=6)
        requested_competition = (competition or "all").strip()

        stats_query = text("""
            SELECT
                'T20I' AS competition,
                'international' AS match_type,
                COUNT(*) AS match_count,
                MIN(m.date) AS earliest_date,
                MAX(m.date) AS latest_date
            FROM matches m
            WHERE m.match_type = 'international'
              AND m.team1 = ANY(:international_teams)
              AND m.team2 = ANY(:international_teams)
            UNION ALL
            SELECT
                m.competition,
                m.match_type,
                COUNT(*) AS match_count,
                MIN(m.date) AS earliest_date,
                MAX(m.date) AS latest_date
            FROM matches m
            WHERE m.match_type = 'league'
              AND m.competition IS NOT NULL
            GROUP BY m.competition, m.match_type
        """)
        stats_rows = db.execute(stats_query, {"international_teams": INTERNATIONAL_TEAMS_RANKED}).fetchall()
        competition_stats = _competition_stats_from_rows(stats_rows)
        filters = _discover_filters(competition_stats)

        if requested_competition.lower() == "all":
            grouped_query = text("""
                WITH base AS (
                    SELECT
                        m.id,
                        m.date,
                        m.venue,
                        m.team1,
                        m.team2,
                        m.winner,
                        CASE WHEN m.match_type = 'international' THEN 'T20I' ELSE m.competition END AS competition_key,
                        CASE WHEN m.match_type = 'international' THEN 'T20I' ELSE m.competition END AS competition,
                        m.match_type,
                        CASE WHEN m.match_type = 'international' THEN 1 ELSE 2 END AS priority
                    FROM matches m
                    WHERE (
                        m.match_type = 'international'
                        AND m.team1 = ANY(:international_teams)
                        AND m.team2 = ANY(:international_teams)
                    )
                    OR (
                        m.match_type = 'league'
                        AND m.competition IS NOT NULL
                    )
                ),
                ranked AS (
                    SELECT
                        base.*,
                        ROW_NUMBER() OVER (
                            PARTITION BY competition_key
                            ORDER BY date DESC NULLS LAST, id DESC
                        ) AS rn
                    FROM base
                )
                SELECT *
                FROM ranked
                WHERE rn <= :per_group
                ORDER BY priority, date DESC NULLS LAST, competition_key, rn
            """)
            rows = db.execute(grouped_query, {
                "international_teams": INTERNATIONAL_TEAMS_RANKED,
                "per_group": per_group,
            }).fetchall()

            grouped: Dict[str, Dict[str, Any]] = {}
            for row in rows:
                key = row.competition_key
                stat = competition_stats.get(key, {})
                group = grouped.setdefault(key, {
                    "key": key,
                    "label": _display_competition(None, is_t20i=key == "T20I") if key == "T20I" else leagues_mapping.get(key, key),
                    "match_type": row.match_type,
                    "total": stat.get("match_count", 0),
                    "latest_date": stat.get("latest_date"),
                    "has_more": (stat.get("match_count") or 0) > per_group,
                    "matches": [],
                })
                group["matches"].append(_format_match(row, is_t20i=key == "T20I"))

            groups = sorted(
                grouped.values(),
                key=lambda group: (
                    0 if group["key"] == "T20I" else 1,
                    -(competition_stats.get(group["key"], {}).get("match_count") or 0),
                    group["label"],
                ),
            )

            return {
                "mode": "grouped",
                "competition": "all",
                "per_group": per_group,
                "groups": groups,
                "competition_stats": competition_stats,
                "filters": filters,
                "total_competitions": len(competition_stats),
                "total_matches": sum(stat["match_count"] for stat in competition_stats.values()),
            }

        is_t20i = requested_competition.upper() == "T20I"
        if is_t20i:
            where_clause = """
                m.match_type = 'international'
                AND m.team1 = ANY(:international_teams)
                AND m.team2 = ANY(:international_teams)
            """
            params = {"international_teams": INTERNATIONAL_TEAMS_RANKED}
            key = "T20I"
            label = "T20I"
        else:
            where_clause = "m.match_type = 'league' AND m.competition = :competition"
            params = {"competition": requested_competition}
            key = requested_competition
            label = leagues_mapping.get(requested_competition, requested_competition)

        total_query = text(f"SELECT COUNT(*) FROM matches m WHERE {where_clause}")
        total = db.execute(total_query, params).scalar() or 0

        flat_query = text(f"""
            SELECT
                m.id,
                m.date,
                m.venue,
                m.team1,
                m.team2,
                m.winner,
                CASE WHEN m.match_type = 'international' THEN 'T20I' ELSE m.competition END AS competition,
                m.match_type
            FROM matches m
            WHERE {where_clause}
            ORDER BY m.date DESC NULLS LAST, m.id DESC
            LIMIT :limit OFFSET :offset
        """)
        flat_params = {**params, "limit": limit, "offset": offset}
        rows = db.execute(flat_query, flat_params).fetchall()
        matches = [_format_match(row, is_t20i=is_t20i) for row in rows]
        next_offset = offset + len(matches)

        return {
            "mode": "filtered",
            "competition": key,
            "label": label,
            "matches": matches,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": next_offset < total,
            "next_offset": next_offset if next_offset < total else None,
            "competition_stats": competition_stats,
            "filters": filters,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error discovering recent matches: {str(e)}")
