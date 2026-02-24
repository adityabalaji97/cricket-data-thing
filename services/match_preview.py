from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

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
            runs_per_innings = float(stats.get("runs_per_innings", 0) or 0)
            wickets_per_innings = float(stats.get("wickets_per_innings", 0) or 0)
            balls_per_innings = float(stats.get("balls_per_innings", 0) or 0)
            strike_rate = (runs_per_innings * 100.0 / balls_per_innings) if balls_per_innings else 0
            summary[innings_key][phase] = {
                "runs_per_innings": round(runs_per_innings, 2),
                "wickets_per_innings": round(wickets_per_innings, 2),
                "balls_per_innings": round(balls_per_innings, 2),
                "strike_rate": round(strike_rate, 2),
            }
    return summary


def _get_h2h_last_n(
    db: Session,
    team1: str,
    team2: str,
    n: int = 10,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    venue: Optional[str] = None,
) -> List[Dict[str, Any]]:
    query = text(
        """
        SELECT date, winner, team1, team2, team1_elo, team2_elo, venue
        FROM matches
        WHERE (
          (team1 = :team1 AND team2 = :team2)
          OR (team1 = :team2 AND team2 = :team1)
        )
          AND (:start_date IS NULL OR date >= :start_date)
          AND (:end_date IS NULL OR date <= :end_date)
          AND (:venue IS NULL OR venue = :venue)
        ORDER BY date DESC
        LIMIT :limit
        """
    )
    rows = db.execute(
        query,
        {"team1": team1, "team2": team2, "limit": n, "start_date": start_date, "end_date": end_date, "venue": venue},
    ).fetchall()
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


def _get_recent_form(
    db: Session,
    team: str,
    n: int = 5,
    end_date: Optional[date] = None,
) -> Dict[str, Any]:
    query = text(
        """
        SELECT date, team1, team2, winner, venue
        FROM matches
        WHERE team1 = :team OR team2 = :team
          AND (:end_date IS NULL OR date <= :end_date)
        ORDER BY date DESC
        LIMIT :limit
        """
    )
    rows = db.execute(query, {"team": team, "limit": n, "end_date": end_date}).fetchall()
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


def _phase_entry(stats: Dict[str, Any], innings_key: str, phase: str) -> Optional[Dict[str, Any]]:
    return ((stats.get(innings_key) or {}).get(phase)) if stats else None


def _build_story_signals(context: Dict[str, Any]) -> Dict[str, Any]:
    venue_stats = context.get("venue_stats", {}) or {}
    phase_stats = context.get("phase_stats", {}) or {}
    h2h_summary = ((context.get("head_to_head") or {}).get("summary")) or {}
    recent_form = context.get("recent_form", {}) or {}
    elo = context.get("elo", {}) or {}
    team1 = context.get("team1")
    team2 = context.get("team2")

    total_matches = int(venue_stats.get("total_matches", 0) or 0)
    bat_first_wins = int(venue_stats.get("batting_first_wins", 0) or 0)
    chase_wins = int(venue_stats.get("batting_second_wins", 0) or 0)
    avg_1st = venue_stats.get("average_first_innings")
    avg_2nd = venue_stats.get("average_second_innings")

    toss_bias = "balanced"
    if total_matches:
        bat_first_pct = (bat_first_wins * 100.0 / total_matches)
        if bat_first_pct >= 58:
            toss_bias = "bat_first"
        elif bat_first_pct <= 42:
            toss_bias = "chasing"

    pp_bf = _phase_entry(phase_stats, "batting_first_wins", "powerplay") or {}
    pp_ch = _phase_entry(phase_stats, "chasing_wins", "powerplay") or {}
    d_bf = _phase_entry(phase_stats, "batting_first_wins", "death") or {}
    d_ch = _phase_entry(phase_stats, "chasing_wins", "death") or {}

    form1 = recent_form.get(team1, {}) if team1 else {}
    form2 = recent_form.get(team2, {}) if team2 else {}
    elo1 = elo.get(team1) if team1 else None
    elo2 = elo.get(team2) if team2 else None

    return {
        "venue_balance": {
            "total_matches": total_matches,
            "batting_first_wins": bat_first_wins,
            "chasing_wins": chase_wins,
            "toss_bias": toss_bias,
            "avg_first_innings": round(float(avg_1st), 2) if avg_1st is not None else None,
            "avg_second_innings": round(float(avg_2nd), 2) if avg_2nd is not None else None,
        },
        "phase_pressure_points": {
            "powerplay_batting_first": pp_bf,
            "powerplay_chasing": pp_ch,
            "death_batting_first": d_bf,
            "death_chasing": d_ch,
        },
        "matchup_edges": {
            "h2h_sample": int(h2h_summary.get("sample_size", 0) or 0),
            "h2h_team1_wins": int(h2h_summary.get("team1_wins", 0) or 0),
            "h2h_team2_wins": int(h2h_summary.get("team2_wins", 0) or 0),
            "recent_form_team1": form1.get("record"),
            "recent_form_team2": form2.get("record"),
            "elo_delta_team1_minus_team2": elo1 - elo2 if elo1 is not None and elo2 is not None else None,
        },
    }


def gather_preview_context(
    venue: str,
    team1_identifier: str,
    team2_identifier: str,
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    include_international: bool = True,
    top_teams: int = 20,
) -> Dict[str, Any]:
    team1 = resolve_team_identifier(team1_identifier)
    team2 = resolve_team_identifier(team2_identifier)

    venue_stats = get_venue_match_stats(
        venue=venue if venue != "All Venues" else None,
        start_date=start_date,
        end_date=end_date,
        leagues=[],
        include_international=include_international,
        top_teams=top_teams,
        db=db,
    )
    phase_stats = get_venue_phase_stats(
        venue=venue if venue != "All Venues" else None,
        start_date=start_date,
        end_date=end_date,
        leagues=[],
        include_international=include_international,
        top_teams=top_teams,
        db=db,
    )
    h2h = _get_h2h_last_n(db, team1, team2, 10, start_date=start_date, end_date=end_date)
    venue_h2h = _get_h2h_last_n(
        db, team1, team2, 10, start_date=start_date, end_date=end_date, venue=venue if venue != "All Venues" else None
    )
    form1 = _get_recent_form(db, team1, 5, end_date=end_date)
    form2 = _get_recent_form(db, team2, 5, end_date=end_date)
    elo1 = _get_latest_elo(db, team1)
    elo2 = _get_latest_elo(db, team2)

    h2h_team1_wins = sum(1 for m in h2h if m["winner"] == team1)
    h2h_team2_wins = sum(1 for m in h2h if m["winner"] == team2)
    h2h_nr = sum(1 for m in h2h if not m["winner"])

    context = {
        "venue": venue,
        "team1": team1,
        "team2": team2,
        "filters": {
            "start_date": str(start_date) if start_date else None,
            "end_date": str(end_date) if end_date else None,
            "include_international": include_international,
            "top_teams": top_teams,
        },
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
        "venue_head_to_head": {
            "matches": venue_h2h,
            "summary": {
                "sample_size": len(venue_h2h),
                "team1_wins": sum(1 for m in venue_h2h if m["winner"] == team1),
                "team2_wins": sum(1 for m in venue_h2h if m["winner"] == team2),
                "no_results": sum(1 for m in venue_h2h if not m["winner"]),
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
    context["story_signals"] = _build_story_signals(context)
    return context


def generate_match_preview_fallback(context: Dict[str, Any]) -> str:
    team1 = context["team1"]
    team2 = context["team2"]
    venue = context["venue"]
    venue_stats = context.get("venue_stats", {}) or {}
    h2h = context.get("head_to_head", {}).get("summary", {}) or {}
    forms = context.get("recent_form", {}) or {}
    elo = context.get("elo", {}) or {}
    phase_stats = context.get("phase_stats", {}) or {}
    filters = context.get("filters", {}) or {}
    venue_h2h = ((context.get("venue_head_to_head") or {}).get("summary")) or {}

    form1 = forms.get(team1, {})
    form2 = forms.get(team2, {})
    record1 = form1.get("record", "N/A")
    record2 = form2.get("record", "N/A")

    avg_1st = venue_stats.get("average_first_innings")
    avg_2nd = venue_stats.get("average_second_innings")
    bat_first_wins = venue_stats.get("batting_first_wins", 0)
    bat_second_wins = venue_stats.get("batting_second_wins", 0)
    total_matches = venue_stats.get("total_matches", 0)

    toss_bias = "balanced split"
    if total_matches:
        bat_first_pct = (bat_first_wins * 100.0 / total_matches) if total_matches else 0
        if bat_first_pct >= 58:
            toss_bias = f"bat-first edge ({bat_first_pct:.0f}% wins)"
        elif bat_first_pct <= 42:
            toss_bias = f"chasing edge ({100 - bat_first_pct:.0f}% wins)"
        else:
            toss_bias = f"balanced ({bat_first_pct:.0f}% bat-first wins)"

    h2h_sample = h2h.get("sample_size", 0)
    h2h_line = (
        f"{team1} {h2h.get('team1_wins', 0)}-{h2h.get('team2_wins', 0)} {team2}"
        if h2h_sample
        else "No H2H sample in selected window"
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

    pp_bf = ((phase_stats.get("batting_first_wins") or {}).get("powerplay")) or {}
    death_chase = ((phase_stats.get("chasing_wins") or {}).get("death")) or {}
    pp_sr = pp_bf.get("strike_rate")
    death_sr = death_chase.get("strike_rate")
    date_window = f"{filters.get('start_date') or 'all-time'} to {filters.get('end_date') or 'latest'}"

    return "\n".join(
        [
            "## Venue Profile",
            f"- Window: {date_window}; sample {total_matches or 0} matches at {venue}.",
            f"- Avg 1st/2nd inns: {round(avg_1st) if avg_1st else 'N/A'}/{round(avg_2nd) if avg_2nd else 'N/A'}; result split: {toss_bias}.",
            "## Form Guide",
            f"- Last 5: {team1} {record1} vs {team2} {record2}.",
            f"- ELO: {team1} {elo1 if elo1 is not None else 'N/A'} vs {team2} {elo2 if elo2 is not None else 'N/A'}.",
            "## Head-to-Head",
            f"- Overall (window): {h2h_line} across {h2h_sample} matches.",
            f"- At {venue}: {team1} {venue_h2h.get('team1_wins', 0)}-{venue_h2h.get('team2_wins', 0)} {team2} (sample {venue_h2h.get('sample_size', 0)}).",
            "## Key Matchup Factor",
            f"- Powerplay batting-first SR: {pp_sr if pp_sr is not None else 'N/A'}; chasing death SR: {death_sr if death_sr is not None else 'N/A'}.",
            "- Use venue phase tempo with each side's current form; middle/death execution is the swing factor.",
            "## Preview Take",
            f"- {preview_take} based on {favorite_reason}.",
            "- Keep confidence moderate; venue result split is close enough for toss + phase execution to decide it.",
        ]
    )
