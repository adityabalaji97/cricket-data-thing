from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from models import teams_mapping
from services.delivery_data_service import get_venue_match_stats, get_venue_phase_stats


INTERNATIONAL_ABBR_TO_NAME = {
    "AFG": "Afghanistan",
    "AUS": "Australia",
    "BAN": "Bangladesh",
    "ENG": "England",
    "IND": "India",
    "IRE": "Ireland",
    "NAM": "Namibia",
    "NED": "Netherlands",
    "NZ": "New Zealand",
    "OMN": "Oman",
    "PAK": "Pakistan",
    "PNG": "Papua New Guinea",
    "SA": "South Africa",
    "SL": "Sri Lanka",
    "SCO": "Scotland",
    "UAE": "UAE",
    "USA": "USA",
    "WI": "West Indies",
    "ZIM": "Zimbabwe",
}


def _reverse_team_mapping() -> Dict[str, str]:
    reverse: Dict[str, str] = {}
    for full_name, abbr in teams_mapping.items():
        # Prefer the newer/primary name if duplicates share the same abbreviation
        reverse.setdefault(abbr.upper(), full_name)
    reverse.update(INTERNATIONAL_ABBR_TO_NAME)
    return reverse


def resolve_team_identifier(identifier: str) -> str:
    if not identifier:
        return identifier
    reverse = _reverse_team_mapping()
    return reverse.get(identifier.upper(), identifier)


def _serialize_phase_stats(phase_stats: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not phase_stats:
        return {}
    summary: Dict[str, Any] = {}
    for innings_key in ("batting_first_wins", "chasing_wins"):
        if innings_key not in phase_stats or not isinstance(phase_stats[innings_key], dict):
            continue
        summary[innings_key] = {}
        for phase, stats in phase_stats[innings_key].items():
            if not isinstance(stats, dict):
                continue
            summary[innings_key][phase] = {
                "batting_strike_rate": round(float(stats.get("batting_strike_rate", 0) or 0), 2),
                "boundary_percentage": round(float(stats.get("boundary_percentage", 0) or 0), 2),
                "dot_percentage": round(float(stats.get("dot_percentage", 0) or 0), 2),
                "total_balls": int(stats.get("total_balls", 0) or 0),
                "total_runs": int(stats.get("total_runs", 0) or 0),
                "total_wickets": int(stats.get("total_wickets", 0) or 0),
            }
    return summary


def _get_h2h_last_n(db: Session, team1: str, team2: str, n: int = 10) -> List[Dict[str, Any]]:
    query = text(
        """
        SELECT date, winner, team1, team2, team1_elo, team2_elo, venue
        FROM matches
        WHERE (
          (team1 = :team1 AND team2 = :team2)
          OR (team1 = :team2 AND team2 = :team1)
        )
        ORDER BY date DESC
        LIMIT :limit
        """
    )
    rows = db.execute(query, {"team1": team1, "team2": team2, "limit": n}).fetchall()
    return [
        {
            "date": str(r.date) if r.date else None,
            "winner": r.winner,
            "team1": r.team1,
            "team2": r.team2,
            "team1_elo": r.team1_elo,
            "team2_elo": r.team2_elo,
            "venue": r.venue,
        }
        for r in rows
    ]


def _get_recent_form(db: Session, team: str, n: int = 5) -> Dict[str, Any]:
    query = text(
        """
        SELECT date, team1, team2, winner, venue
        FROM matches
        WHERE team1 = :team OR team2 = :team
        ORDER BY date DESC
        LIMIT :limit
        """
    )
    rows = db.execute(query, {"team": team, "limit": n}).fetchall()
    results: List[str] = []
    recent_matches: List[Dict[str, Any]] = []
    for r in rows:
        if not r.winner:
            outcome = "NR"
        elif r.winner == team:
            outcome = "W"
        else:
            outcome = "L"
        results.append(outcome)
        recent_matches.append(
            {
                "date": str(r.date) if r.date else None,
                "opponent": r.team2 if r.team1 == team else r.team1,
                "result": outcome,
                "winner": r.winner,
                "venue": r.venue,
            }
        )
    return {
        "record": "".join(results),
        "wins": results.count("W"),
        "losses": results.count("L"),
        "no_results": results.count("NR"),
        "matches": recent_matches,
    }


def _get_latest_elo(db: Session, team: str) -> Optional[int]:
    query = text(
        """
        SELECT date, team1, team2, team1_elo, team2_elo
        FROM matches
        WHERE (team1 = :team OR team2 = :team)
          AND (team1_elo IS NOT NULL OR team2_elo IS NOT NULL)
        ORDER BY date DESC
        LIMIT 20
        """
    )
    rows = db.execute(query, {"team": team}).fetchall()
    for r in rows:
        if r.team1 == team and r.team1_elo is not None:
            return int(r.team1_elo)
        if r.team2 == team and r.team2_elo is not None:
            return int(r.team2_elo)
    return None


def gather_preview_context(venue: str, team1_identifier: str, team2_identifier: str, db: Session) -> Dict[str, Any]:
    team1 = resolve_team_identifier(team1_identifier)
    team2 = resolve_team_identifier(team2_identifier)

    venue_stats = get_venue_match_stats(
        venue=venue if venue != "All Venues" else None,
        start_date=None,
        end_date=None,
        leagues=[],
        include_international=True,
        top_teams=20,
        db=db,
    )
    phase_stats = get_venue_phase_stats(
        venue=venue if venue != "All Venues" else None,
        start_date=None,
        end_date=None,
        leagues=[],
        include_international=True,
        top_teams=20,
        db=db,
    )
    h2h = _get_h2h_last_n(db, team1, team2, 10)
    form1 = _get_recent_form(db, team1, 5)
    form2 = _get_recent_form(db, team2, 5)
    elo1 = _get_latest_elo(db, team1)
    elo2 = _get_latest_elo(db, team2)

    h2h_team1_wins = sum(1 for m in h2h if m["winner"] == team1)
    h2h_team2_wins = sum(1 for m in h2h if m["winner"] == team2)
    h2h_nr = sum(1 for m in h2h if not m["winner"])

    return {
        "venue": venue,
        "team1": team1,
        "team2": team2,
        "venue_stats": venue_stats or {},
        "phase_stats": _serialize_phase_stats(phase_stats),
        "head_to_head": {
            "matches": h2h,
            "summary": {
                "sample_size": len(h2h),
                "team1_wins": h2h_team1_wins,
                "team2_wins": h2h_team2_wins,
                "no_results": h2h_nr,
            },
        },
        "recent_form": {
            team1: form1,
            team2: form2,
        },
        "elo": {
            team1: elo1,
            team2: elo2,
            "delta_team1_minus_team2": (elo1 - elo2) if elo1 is not None and elo2 is not None else None,
        },
    }


def generate_match_preview_fallback(context: Dict[str, Any]) -> str:
    team1 = context["team1"]
    team2 = context["team2"]
    venue = context["venue"]
    venue_stats = context.get("venue_stats", {}) or {}
    h2h = context.get("head_to_head", {}).get("summary", {}) or {}
    forms = context.get("recent_form", {}) or {}
    elo = context.get("elo", {}) or {}

    form1 = forms.get(team1, {})
    form2 = forms.get(team2, {})
    record1 = form1.get("record", "N/A")
    record2 = form2.get("record", "N/A")

    avg_1st = venue_stats.get("average_first_innings")
    avg_2nd = venue_stats.get("average_second_innings")
    bat_first_wins = venue_stats.get("batting_first_wins", 0)
    bat_second_wins = venue_stats.get("batting_second_wins", 0)
    total_matches = venue_stats.get("total_matches", 0)

    toss_bias = "balanced"
    if total_matches:
        bat_first_pct = (bat_first_wins * 100.0 / total_matches) if total_matches else 0
        if bat_first_pct >= 58:
            toss_bias = "bat first edge"
        elif bat_first_pct <= 42:
            toss_bias = "chasing edge"

    h2h_sample = h2h.get("sample_size", 0)
    h2h_line = (
        f"{team1} lead {h2h.get('team1_wins', 0)}-{h2h.get('team2_wins', 0)}"
        if h2h_sample
        else "No recent head-to-head sample found"
    )

    elo1 = elo.get(team1)
    elo2 = elo.get(team2)
    if elo1 is not None and elo2 is not None:
        favorite = team1 if elo1 >= elo2 else team2
        favorite_reason = f"ELO edge ({elo1} vs {elo2})"
    else:
        favorite = None
        favorite_reason = "recent form + venue fit"

    preview_take = f"Lean {favorite}" if favorite else "Too close to call"

    return "\n".join(
        [
            f"## Venue Profile\n{venue}: Avg 1st inns {round(avg_1st) if avg_1st else 'N/A'}, Avg 2nd inns {round(avg_2nd) if avg_2nd else 'N/A'}; trend reads as {toss_bias}.",
            f"## Form Guide\n{team1}: {record1} in last 5 | {team2}: {record2} in last 5.",
            f"## Head-to-Head\n{h2h_line} across last {h2h_sample} meetings.",
            f"## Key Matchup Factor\nWatch how each side handles venue tempo early; this ground's score profile and phase patterns can swing the game quickly.",
            f"## Preview Take\n{preview_take} based on {favorite_reason}, but venue conditions and toss strategy will heavily shape the result.",
        ]
    )
