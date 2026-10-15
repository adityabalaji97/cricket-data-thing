"""
Browse every scorecard: one paginated, newest-first list across all competitions, filtered by competition, team,
opponent, year, a calendar day ("on this day": the same month and day in every year) or a date range. The
/scorecards page reads it (src/components/scorecard/ScorecardsBrowse.jsx).

    browse(db, competition="all", team=None, opponent=None, year=None, month_day=None, date_from=None, date_to=None,
           limit=24, offset=0)  ->  {matches, total, offset, next_offset, has_more}

Each match is services/recent_matches._format_match's shape plus `top`: the match's biggest Impact, batting or bowling,
counted as the scorecard counts it (no wides; a bowler's Impact is the batters' Impact against him, sign flipped).
Matches before 2015 have no Impact, so `top` is None for them. Scope is the landing card's: internationals between
INTERNATIONAL_TEAMS_RANKED, and every league.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from models import INTERNATIONAL_TEAMS_RANKED
from services.recent_matches import (COMPETITION_CANONICAL_SQL, INTERNATIONAL_BUCKETS, INTERNATIONAL_LABEL_SQL,
                                     IPL_COMPETITIONS, _base_scope_clauses, _bounded_int,
                                     _competition_values_for_key, _format_match, _parse_iso_date,
                                     _score_summaries_for_rows, _team_candidates)

MAX_LIMIT = 48
MONTH_DAY = re.compile(r"^(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")


def _team_clause(name: str, value: Optional[str], params: Dict[str, Any]) -> Optional[str]:
    candidates = [c.lower() for c in _team_candidates(value)]
    if not candidates:
        return None
    params[name] = candidates
    return f"(LOWER(m.team1) = ANY(:{name}) OR LOWER(m.team2) = ANY(:{name}))"


def _where(competition: str, team: Optional[str], opponent: Optional[str], year: Optional[int],
           month_day: Optional[str], date_from: Optional[str], date_to: Optional[str]) -> tuple[str, Dict[str, Any]]:
    params: Dict[str, Any] = {"international_teams": INTERNATIONAL_TEAMS_RANKED}
    clauses = [f"({_base_scope_clauses()})"]
    comp = (competition or "all").strip()
    bucket = next((b for b in INTERNATIONAL_BUCKETS if b.upper() == comp.upper()), None)
    if bucket:
        clauses.append("m.match_type = 'international' AND UPPER(COALESCE(m.format, 'T20')) = :intl_format")
        params["intl_format"] = {"T20I": "T20", "ODI": "ODI", "Test": "TEST"}[bucket]
    elif comp.lower() != "all":
        clauses.append("m.match_type = 'league' AND m.competition = ANY(:competition_values)")
        params["competition_values"] = _competition_values_for_key(comp)
    for name, value in (("team_candidates", team), ("opponent_candidates", opponent)):
        clause = _team_clause(name, value, params)
        if clause:
            clauses.append(clause)
    if year:
        clauses.append("m.date >= :year_start AND m.date < :year_end")
        params["year_start"], params["year_end"] = date(int(year), 1, 1), date(int(year) + 1, 1, 1)
    if month_day and MONTH_DAY.match(month_day):
        clauses.append("to_char(m.date, 'MM-DD') = :month_day")
        params["month_day"] = month_day
    parsed_from, parsed_to = _parse_iso_date(date_from), _parse_iso_date(date_to)
    if parsed_from:
        clauses.append("m.date >= :date_from")
        params["date_from"] = parsed_from
    if parsed_to:
        clauses.append("m.date <= :date_to")
        params["date_to"] = parsed_to
    return " AND ".join(clauses), params


def top_impact(db: Session, match_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """Each match's biggest Impact (batting or bowling), as the scorecard counts it."""
    if not match_ids:
        return {}
    rows = db.execute(text("""
        WITH balls AS (
            SELECT dd.p_match, dd.bat, dd.bowl, dd.team_bat, dd.team_bowl, bm.impact
            FROM delivery_details dd JOIN ball_metrics bm ON bm.delivery_id = dd.id
            WHERE dd.p_match = ANY(:ids) AND COALESCE(dd.wide, 0) = 0
        ),
        people AS (
            SELECT p_match, bat AS name, MIN(team_bat) AS team, 'bat' AS role, SUM(impact) AS impact
            FROM balls WHERE bat IS NOT NULL GROUP BY p_match, bat
            UNION ALL
            SELECT p_match, bowl AS name, MIN(team_bowl) AS team, 'bowl' AS role, -SUM(impact) AS impact
            FROM balls WHERE bowl IS NOT NULL GROUP BY p_match, bowl
        )
        SELECT DISTINCT ON (p.p_match) p.p_match, COALESCE(pa.canonical_name, p.name) AS name, p.team, p.role, p.impact
        FROM people p LEFT JOIN player_alias_map pa ON LOWER(p.name) = pa.name_key
        WHERE p.impact IS NOT NULL
        ORDER BY p.p_match, p.impact DESC
    """), {"ids": [str(i) for i in match_ids]}).mappings().all()
    return {str(r["p_match"]): {"name": r["name"], "team": r["team"], "role": r["role"],
                                "impact": round(float(r["impact"]), 1)} for r in rows}


def browse(db: Session, competition: str = "all", team: Optional[str] = None, opponent: Optional[str] = None,
           year: Optional[int] = None, month_day: Optional[str] = None, date_from: Optional[str] = None,
           date_to: Optional[str] = None, limit: int = 24, offset: int = 0) -> Dict[str, Any]:
    limit = _bounded_int(limit, minimum=1, maximum=MAX_LIMIT)
    offset = max(0, int(offset or 0))
    where, params = _where(competition, team, opponent, year, month_day, date_from, date_to)
    total = db.execute(text(f"SELECT COUNT(*) FROM matches m WHERE {where}"), params).scalar() or 0
    rows = db.execute(text(f"""
        SELECT m.id, m.date, m.venue, m.team1, m.team2, m.winner, m.outcome, m.match_type, m.format,
               CASE WHEN m.match_type = 'international' THEN {INTERNATIONAL_LABEL_SQL}
                    WHEN m.competition = ANY(:ipl_competitions) THEN 'IPL'
                    ELSE {COMPETITION_CANONICAL_SQL} END AS competition
        FROM matches m
        WHERE {where}
        ORDER BY m.date DESC NULLS LAST, m.id DESC
        LIMIT :limit OFFSET :offset
    """), {**params, "ipl_competitions": list(IPL_COMPETITIONS), "limit": limit, "offset": offset}).fetchall()
    scores = _score_summaries_for_rows(db, rows)
    tops = top_impact(db, [str(r.id) for r in rows])
    matches = []
    for r in rows:
        m = _format_match(r, is_t20i=r.match_type == "international", score_summary=scores.get(r.id))
        m["top"] = tops.get(str(r.id))
        matches.append(m)
    next_offset = offset + len(matches)
    return {"matches": matches, "total": total, "offset": offset, "limit": limit, "has_more": next_offset < total,
            "next_offset": next_offset if next_offset < total else None}
