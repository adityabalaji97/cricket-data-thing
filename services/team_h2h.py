"""
Team head-to-head summary service for IPL teams.

Builds W/L/NR records for a selected IPL team against every other active IPL side.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from ipl_rosters import get_all_ipl_teams, get_ipl_roster, get_team_abbrev_from_name
from services.teams import get_all_team_name_variations


def _expand_team_identifiers(team_identifier: str) -> List[str]:
    """
    Return all known identifiers for a team (full names + abbreviation).
    """
    names = set(get_all_team_name_variations(team_identifier))
    names.add(team_identifier)
    return list(names)


def _get_h2h_rows(db: Session, team_names: List[str], opponent_names: List[str]):
    """
    Reuses the same pair-query pattern used by match preview H2H logic.
    """
    query = text(
        """
        SELECT date, winner
        FROM matches
        WHERE (
          (team1 = ANY(:team_names) AND team2 = ANY(:opponent_names))
          OR (team1 = ANY(:opponent_names) AND team2 = ANY(:team_names))
        )
          AND competition = 'Indian Premier League'
        ORDER BY date DESC
        """
    )
    return db.execute(
        query,
        {"team_names": team_names, "opponent_names": opponent_names},
    ).fetchall()


def _to_outcome(winner: Optional[str], team_names_set: set) -> str:
    if not winner:
        return "NR"
    return "W" if winner in team_names_set else "L"


def get_team_h2h_summary_service(team_name: str, db: Session) -> Dict:
    team_abbrev = get_team_abbrev_from_name(team_name)
    if not team_abbrev:
        raise ValueError(f"Unsupported IPL team: {team_name}")

    team_roster = get_ipl_roster(team_abbrev) or {}
    team_full_name = team_roster.get("full_name", team_abbrev)
    team_identifiers = _expand_team_identifiers(team_abbrev)
    team_identifier_set = set(team_identifiers)

    h2h_rows = []
    total_wins = 0
    total_losses = 0
    total_no_results = 0
    total_matches = 0

    for opponent_abbrev in get_all_ipl_teams():
        if opponent_abbrev == team_abbrev:
            continue

        opponent_roster = get_ipl_roster(opponent_abbrev) or {}
        opponent_full_name = opponent_roster.get("full_name", opponent_abbrev)
        opponent_identifiers = _expand_team_identifiers(opponent_abbrev)

        matches = _get_h2h_rows(db, team_identifiers, opponent_identifiers)
        outcomes = [_to_outcome(row.winner, team_identifier_set) for row in matches]

        wins = outcomes.count("W")
        losses = outcomes.count("L")
        no_results = outcomes.count("NR")
        matches_count = len(matches)
        denominator = wins + losses
        win_pct = (wins / denominator * 100.0) if denominator else None
        last_match_date = matches[0].date.isoformat() if matches and matches[0].date else None
        recent_form = "".join(outcomes[:5])

        h2h_rows.append(
            {
                "opponent": opponent_abbrev,
                "opponent_full_name": opponent_full_name,
                "matches": matches_count,
                "wins": wins,
                "losses": losses,
                "no_results": no_results,
                "win_pct": round(win_pct, 2) if win_pct is not None else None,
                "recent_form": recent_form,
                "last_match_date": last_match_date,
            }
        )

        total_wins += wins
        total_losses += losses
        total_no_results += no_results
        total_matches += matches_count

    return {
        "team": team_abbrev,
        "team_full_name": team_full_name,
        "total_opponents": len(h2h_rows),
        "overall": {
            "matches": total_matches,
            "wins": total_wins,
            "losses": total_losses,
            "no_results": total_no_results,
            "win_pct": round((total_wins / (total_wins + total_losses) * 100.0), 2)
            if (total_wins + total_losses)
            else None,
        },
        "summary": sorted(h2h_rows, key=lambda row: row["opponent"]),
    }
