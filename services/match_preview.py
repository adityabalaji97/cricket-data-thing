from __future__ import annotations

from datetime import date
import re
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from models import teams_mapping
from services.delivery_data_service import get_match_scores, get_venue_match_stats, get_venue_phase_stats
from services.matchups import get_all_team_name_variations, get_team_matchups_service


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

PREVIEW_SECTION_ORDER = [
    ("venue_profile", "Venue Profile"),
    ("form_guide", "Form Guide"),
    ("head_to_head", "Head-to-Head"),
    ("key_matchup_factor", "Key Matchup Factor"),
    ("preview_take", "Preview Take"),
]


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


def _parse_score_total(score: Optional[str]) -> Optional[int]:
    if not score:
        return None
    try:
        token = str(score).split("/")[0].strip()
        return int(token) if token.isdigit() else None
    except Exception:
        return None


def _winner_is_team(match: Dict[str, Any], team_names: List[str]) -> bool:
    return bool(match.get("winner")) and match.get("winner") in set(team_names)


def _format_match_row(match: Any, scores: Dict[int, Dict[int, str]]) -> Dict[str, Any]:
    match_scores = scores.get(match.id, {})
    inns1_score = match_scores.get(1, "0/0")
    inns2_score = match_scores.get(2, "0/0")
    return {
        "id": match.id,
        "date": match.date.isoformat() if getattr(match, "date", None) else None,
        "team1": match.team1,
        "team2": match.team2,
        "team1_display": teams_mapping.get(match.team1, match.team1),
        "team2_display": teams_mapping.get(match.team2, match.team2),
        "venue": match.venue,
        "winner": match.winner,
        "winner_display": teams_mapping.get(match.winner, match.winner) if match.winner else None,
        "won_batting_first": bool(match.won_batting_first) if match.won_batting_first is not None else None,
        "won_fielding_first": bool(match.won_fielding_first) if match.won_fielding_first is not None else None,
        "score1": inns1_score,
        "score2": inns2_score,
        "innings1_total": _parse_score_total(inns1_score),
        "innings2_total": _parse_score_total(inns2_score),
    }


def _get_match_history_bundle(
    db: Session,
    venue: str,
    team1: str,
    team2: str,
    start_date: Optional[date],
    end_date: Optional[date],
) -> Dict[str, Any]:
    team1_names = get_all_team_name_variations(team1)
    team2_names = get_all_team_name_variations(team2)

    venue_matches = db.execute(
        text(
            """
            SELECT m.id, m.date, m.team1, m.team2, m.winner, m.venue, m.won_batting_first, m.won_fielding_first
            FROM matches m
            WHERE (:start_date IS NULL OR m.date >= :start_date)
              AND (:end_date IS NULL OR m.date <= :end_date)
              AND (:venue IS NULL OR m.venue = :venue)
            ORDER BY m.date DESC
            LIMIT 7
            """
        ),
        {"venue": None if venue == "All Venues" else venue, "start_date": start_date, "end_date": end_date},
    ).fetchall()

    team1_matches = db.execute(
        text(
            """
            SELECT m.id, m.date, m.team1, m.team2, m.winner, m.venue, m.won_batting_first, m.won_fielding_first
            FROM matches m
            WHERE (:start_date IS NULL OR m.date >= :start_date)
              AND (:end_date IS NULL OR m.date <= :end_date)
              AND (m.team1 = ANY(:team_names) OR m.team2 = ANY(:team_names))
            ORDER BY m.date DESC
            LIMIT 5
            """
        ),
        {"team_names": team1_names, "start_date": start_date, "end_date": end_date},
    ).fetchall()

    team2_matches = db.execute(
        text(
            """
            SELECT m.id, m.date, m.team1, m.team2, m.winner, m.venue, m.won_batting_first, m.won_fielding_first
            FROM matches m
            WHERE (:start_date IS NULL OR m.date >= :start_date)
              AND (:end_date IS NULL OR m.date <= :end_date)
              AND (m.team1 = ANY(:team_names) OR m.team2 = ANY(:team_names))
            ORDER BY m.date DESC
            LIMIT 5
            """
        ),
        {"team_names": team2_names, "start_date": start_date, "end_date": end_date},
    ).fetchall()

    h2h_matches = db.execute(
        text(
            """
            SELECT m.id, m.date, m.team1, m.team2, m.winner, m.venue, m.won_batting_first, m.won_fielding_first
            FROM matches m
            WHERE (:start_date IS NULL OR m.date >= :start_date)
              AND (:end_date IS NULL OR m.date <= :end_date)
              AND (
                (m.team1 = ANY(:team1_names) AND m.team2 = ANY(:team2_names))
                OR (m.team1 = ANY(:team2_names) AND m.team2 = ANY(:team1_names))
              )
            ORDER BY m.date DESC
            LIMIT 10
            """
        ),
        {"team1_names": team1_names, "team2_names": team2_names, "start_date": start_date, "end_date": end_date},
    ).fetchall()

    all_match_ids = list({m.id for m in [*venue_matches, *team1_matches, *team2_matches, *h2h_matches]})
    scores = get_match_scores(all_match_ids, start_date, end_date, db) if all_match_ids else {}

    return {
        "team1_names": team1_names,
        "team2_names": team2_names,
        "venue_results": [_format_match_row(m, scores) for m in venue_matches],
        "team1_results": [_format_match_row(m, scores) for m in team1_matches],
        "team2_results": [_format_match_row(m, scores) for m in team2_matches],
        "h2h_recent": [_format_match_row(m, scores) for m in h2h_matches],
    }


def _summarize_team_recent_matches(
    team: str,
    team_names: List[str],
    matches: List[Dict[str, Any]],
    avg_winning_score: Optional[float],
    avg_chasing_score: Optional[float],
) -> Dict[str, Any]:
    win_batting_first = 0
    win_chasing = 0
    restrictions_when_bowling_first: List[int] = []
    reached_avg_winning_batting_first = 0
    chased_avg_chasing = 0
    batting_first_opportunities = 0
    chasing_opportunities = 0

    for m in matches:
        winner = m.get("winner")
        team_won = winner in team_names if winner else False
        won_batting_first = m.get("won_batting_first")
        won_fielding_first = m.get("won_fielding_first")
        inns1_total = m.get("innings1_total")
        inns2_total = m.get("innings2_total")

        is_team1 = m.get("team1") in team_names
        is_team2 = m.get("team2") in team_names
        if not (is_team1 or is_team2):
            continue

        # Infer innings role when possible from winner + toss-result flags.
        if team_won and won_batting_first is True:
            win_batting_first += 1
            batting_first_opportunities += 1
            if avg_winning_score and inns1_total is not None and inns1_total >= avg_winning_score:
                reached_avg_winning_batting_first += 1
        elif team_won and won_fielding_first is True:
            win_chasing += 1
            chasing_opportunities += 1
            if avg_chasing_score and inns2_total is not None and inns2_total >= avg_chasing_score:
                chased_avg_chasing += 1
            if inns1_total is not None:
                restrictions_when_bowling_first.append(inns1_total)
        else:
            # Count role opportunities for losses too using winner toss mode.
            if won_batting_first is not None and won_fielding_first is not None:
                if (won_batting_first is True and not team_won) or (won_fielding_first is True and not team_won):
                    # Without innings-order-by-team in each match row, keep opportunity counts conservative.
                    pass

    return {
        "team": team,
        "sample_size": len(matches),
        "wins_batting_first": win_batting_first,
        "wins_chasing": win_chasing,
        "restrictions_when_bowling_first": restrictions_when_bowling_first,
        "avg_restriction_when_bowling_first": round(sum(restrictions_when_bowling_first) / len(restrictions_when_bowling_first), 1)
        if restrictions_when_bowling_first else None,
        "reached_avg_winning_score_batting_first": reached_avg_winning_batting_first,
        "chased_avg_chasing_score": chased_avg_chasing,
        "record": "".join(
            ["W" if _winner_is_team(m, team_names) else ("NR" if not m.get("winner") else "L") for m in matches]
        ),
    }


def _summarize_recent_venue_trend(venue_matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not venue_matches:
        return {"sample_size": 0}
    bat_first_wins = sum(1 for m in venue_matches if m.get("won_batting_first") is True)
    chase_wins = sum(1 for m in venue_matches if m.get("won_fielding_first") is True)
    inns1_scores = [m["innings1_total"] for m in venue_matches if m.get("innings1_total") is not None]
    chased_success_scores = [m["innings1_total"] for m in venue_matches if m.get("won_fielding_first") is True and m.get("innings1_total") is not None]
    defended_scores = [m["innings1_total"] for m in venue_matches if m.get("won_batting_first") is True and m.get("innings1_total") is not None]
    return {
        "sample_size": len(venue_matches),
        "batting_first_wins": bat_first_wins,
        "chasing_wins": chase_wins,
        "avg_first_innings": round(sum(inns1_scores) / len(inns1_scores), 1) if inns1_scores else None,
        "highest_chased_recent": max(chased_success_scores) if chased_success_scores else None,
        "lowest_defended_recent": min(defended_scores) if defended_scores else None,
        "matches": venue_matches,
    }


def _same_country_hint(venue: Optional[str], h2h_matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not venue or venue == "All Venues":
        return {"same_venue_matches": 0, "same_country_like_matches": 0}
    venue_suffix = venue.split(",")[-1].strip().lower() if "," in venue else None
    same_venue = sum(1 for m in h2h_matches if (m.get("venue") or "") == venue)
    same_country_like = 0
    if venue_suffix:
        same_country_like = sum(1 for m in h2h_matches if venue_suffix in str(m.get("venue") or "").lower())
    return {"same_venue_matches": same_venue, "same_country_like_matches": same_country_like}


def _summarize_matchups_and_fantasy(
    db: Session,
    team1: str,
    team2: str,
    start_date: Optional[date],
    end_date: Optional[date],
) -> Dict[str, Any]:
    try:
        matchup_data = get_team_matchups_service(
            team1=team1,
            team2=team2,
            start_date=start_date,
            end_date=end_date,
            team1_players=[],
            team2_players=[],
            db=db,
        )
    except Exception:
        return {"available": False}

    fantasy = (matchup_data or {}).get("fantasy_analysis") or {}
    t1_name = ((matchup_data or {}).get("team1") or {}).get("name", team1)
    t2_name = ((matchup_data or {}).get("team2") or {}).get("name", team2)

    def _top_fantasy(team_key: str, limit: int = 4) -> List[Dict[str, Any]]:
        rows = []
        for stats in (fantasy.get("top_fantasy_picks") or []):
            if stats.get("team") != team_key:
                continue
            rows.append({
                "player": stats.get("player_name"),
                "expected_points": round(float(stats.get("expected_points", 0) or 0), 1),
                "confidence": round(float(stats.get("confidence", 0) or 0), 2),
                "role": stats.get("role"),
            })
        rows.sort(key=lambda x: (x["expected_points"], x["confidence"]), reverse=True)
        return rows[:limit]

    def _top_batting_edges(team_obj: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
        edges = []
        batting = (team_obj or {}).get("batting_matchups") or {}
        for batter, bowlers in batting.items():
            for bowler, s in bowlers.items():
                if bowler == "Overall":
                    continue
                balls = int(s.get("balls", 0) or 0)
                if balls < 6:
                    continue
                edges.append({
                    "batter": batter,
                    "bowler": bowler,
                    "balls": balls,
                    "runs": int(s.get("runs", 0) or 0),
                    "wickets": int(s.get("wickets", 0) or 0),
                    "strike_rate": round(float(s.get("strike_rate", 0) or 0), 1),
                    "dot_percentage": round(float(s.get("dot_percentage", 0) or 0), 1),
                    "boundary_percentage": round(float(s.get("boundary_percentage", 0) or 0), 1),
                })
        edges.sort(key=lambda x: (x["strike_rate"], -x["dot_percentage"], x["balls"]), reverse=True)
        return edges[:limit]

    def _top_bowling_threats(team_obj: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
        rows = []
        for bowler, s in (((team_obj or {}).get("bowling_consolidated") or {}).items()):
            balls = int(s.get("balls", 0) or 0)
            if balls < 6:
                continue
            rows.append({
                "bowler": bowler,
                "balls": balls,
                "wickets": int(s.get("wickets", 0) or 0),
                "economy": round(float(s.get("economy", 0) or 0), 2),
                "dot_percentage": round(float(s.get("dot_percentage", 0) or 0), 1),
                "boundary_percentage": round(float(s.get("boundary_percentage", 0) or 0), 1),
            })
        rows.sort(key=lambda x: (x["wickets"], -x["economy"], x["dot_percentage"]), reverse=True)
        return rows[:limit]

    return {
        "available": True,
        "fantasy_top": {
            t1_name: _top_fantasy("team1"),
            t2_name: _top_fantasy("team2"),
        },
        "batting_edges": {
            t1_name: _top_batting_edges((matchup_data or {}).get("team1")),
            t2_name: _top_batting_edges((matchup_data or {}).get("team2")),
        },
        "bowling_threats": {
            t1_name: _top_bowling_threats((matchup_data or {}).get("team1")),
            t2_name: _top_bowling_threats((matchup_data or {}).get("team2")),
        },
    }


def _phase_entry(stats: Dict[str, Any], innings_key: str, phase: str) -> Optional[Dict[str, Any]]:
    return ((stats.get(innings_key) or {}).get(phase)) if stats else None


def _build_story_signals(context: Dict[str, Any]) -> Dict[str, Any]:
    venue_stats = context.get("venue_stats", {}) or {}
    phase_stats = context.get("phase_stats", {}) or {}
    h2h_summary = ((context.get("head_to_head") or {}).get("summary")) or {}
    recent_form = context.get("recent_form", {}) or {}
    elo = context.get("elo", {}) or {}
    match_history = context.get("match_history", {}) or {}
    screen_story = context.get("screen_story", {}) or {}
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
        "screen_story_available": bool(screen_story),
        "recent_venue_sample": int(((match_history.get("venue_trend") or {}).get("sample_size")) or 0),
    }


def _classify_toss_bias(batting_first_wins: int, total_matches: int) -> Dict[str, Any]:
    if not total_matches:
        return {"label": "no_sample", "bat_first_pct": None}
    bat_first_pct = batting_first_wins * 100.0 / total_matches
    if bat_first_pct >= 58:
        label = "bat_first_edge"
    elif bat_first_pct <= 42:
        label = "chasing_edge"
    else:
        label = "balanced"
    return {"label": label, "bat_first_pct": round(bat_first_pct, 1)}


def build_phase_wise_strategy_templates(context: Dict[str, Any], tolerance_runs: int = 8) -> Dict[str, Any]:
    phase_stats = context.get("phase_stats", {}) or {}
    venue_stats = context.get("venue_stats", {}) or {}
    phase_order = ["powerplay", "middle1", "middle2", "death"]

    def _template_for(key: str, target_key: str) -> Dict[str, Any]:
        raw = (phase_stats.get(key) or {})
        template: Dict[str, Any] = {}
        total_runs = 0.0
        for phase in phase_order:
            s = raw.get(phase) or {}
            runs = float(s.get("runs_per_innings", 0) or 0)
            balls = float(s.get("balls_per_innings", 0) or 0)
            wickets = float(s.get("wickets_per_innings", 0) or 0)
            strike_rate = (runs * 100.0 / balls) if balls else float(s.get("strike_rate", 0) or 0)
            template[phase] = {
                "runs_per_innings": round(runs, 2),
                "wickets_per_innings": round(wickets, 2),
                "balls_per_innings": round(balls, 2),
                "strike_rate": round(strike_rate, 2),
            }
            total_runs += runs
        rounded_total = int(round(total_runs))
        target_val = venue_stats.get(target_key)
        aligns = None
        delta = None
        if target_val is not None:
            delta = round(total_runs - float(target_val), 2)
            aligns = abs(delta) <= tolerance_runs
        return {
            **template,
            "template_total_runs": rounded_total,
            "aligns_with_target": aligns,
            "target_total": round(float(target_val), 2) if target_val is not None else None,
            "target_delta_runs": delta,
        }

    bf = _template_for("batting_first_wins", "average_winning_score")
    ch = _template_for("chasing_wins", "average_chasing_score")

    deltas = {}
    for phase in phase_order:
        deltas[f"{phase}_run_delta_bf_minus_chase"] = round(
            float((bf.get(phase) or {}).get("runs_per_innings", 0))
            - float((ch.get(phase) or {}).get("runs_per_innings", 0)),
            2,
        )

    dominant_phase = None
    if deltas:
        dominant_phase = max(
            phase_order,
            key=lambda p: abs(deltas.get(f"{p}_run_delta_bf_minus_chase", 0)),
        )

    consistency = {
        "valid": bool((bf.get("aligns_with_target") is not False) and (ch.get("aligns_with_target") is not False)),
        "tolerance_runs": tolerance_runs,
        "batting_first_template_total": bf.get("template_total_runs"),
        "average_winning_score": int(round(float(venue_stats.get("average_winning_score", 0) or 0))) if venue_stats.get("average_winning_score") else None,
        "batting_first_delta_runs": bf.get("target_delta_runs"),
        "chasing_template_total": ch.get("template_total_runs"),
        "average_chasing_score": int(round(float(venue_stats.get("average_chasing_score", 0) or 0))) if venue_stats.get("average_chasing_score") else None,
        "chasing_delta_runs": ch.get("target_delta_runs"),
    }

    return {
        "batting_first_wins_template": {
            phase: bf.get(phase) for phase in phase_order
        } | {
            "template_total_runs": bf.get("template_total_runs"),
            "aligns_with_avg_winning_score": bf.get("aligns_with_target"),
        },
        "chasing_wins_template": {
            phase: ch.get(phase) for phase in phase_order
        } | {
            "template_total_runs": ch.get("template_total_runs"),
            "aligns_with_avg_chasing_score": ch.get("aligns_with_target"),
        },
        "template_deltas": deltas,
        "dominant_phase": dominant_phase,
        "consistency_check": consistency,
    }


def _phase_label(phase: Optional[str]) -> str:
    return {
        "powerplay": "powerplay",
        "middle1": "first middle phase",
        "middle2": "second middle phase",
        "death": "death overs",
    }.get(phase or "", "key phase")


def _phase_runs(template: Dict[str, Any], phase: str) -> Optional[int]:
    v = ((template or {}).get(phase) or {}).get("runs_per_innings")
    return int(round(float(v))) if v is not None else None


def _top_fantasy_pick(screen_story: Dict[str, Any], team_name: str, min_confidence: float = 0.55) -> Optional[Dict[str, Any]]:
    fantasy = (((screen_story.get("expected_fantasy_points") or {}).get("fantasy_top") or {}).get(team_name)) or []
    if not fantasy:
        return None
    best = sorted(fantasy, key=lambda x: (float(x.get("expected_points", 0) or 0), float(x.get("confidence", 0) or 0)), reverse=True)[0]
    best["high_confidence"] = float(best.get("confidence", 0) or 0) >= min_confidence
    return best


def _best_edge(screen_story: Dict[str, Any], team_name: str) -> Optional[Dict[str, Any]]:
    edges = (((screen_story.get("expected_fantasy_points") or {}).get("batting_edges") or {}).get(team_name)) or []
    return edges[0] if edges else None


def _best_bowling_threat(screen_story: Dict[str, Any], team_name: str) -> Optional[Dict[str, Any]]:
    threats = (((screen_story.get("expected_fantasy_points") or {}).get("bowling_threats") or {}).get(team_name)) or []
    return threats[0] if threats else None


def _phase_template_fit_score(team_summary: Dict[str, Any], venue_bias_label: str) -> int:
    if venue_bias_label == "bat_first_edge":
        return int(team_summary.get("wins_batting_first", 0) or 0)
    if venue_bias_label == "chasing_edge":
        return int(team_summary.get("wins_chasing", 0) or 0)
    return int((team_summary.get("wins_batting_first", 0) or 0) + (team_summary.get("wins_chasing", 0) or 0))


def score_preview_lean(context: Dict[str, Any]) -> Dict[str, Any]:
    team1 = context.get("team1")
    team2 = context.get("team2")
    if not team1 or not team2:
        return {"winner": None, "score_total": 0, "components": {}, "label": "Too close to call", "top_reasons": []}

    screen_story = context.get("screen_story", {}) or {}
    match_history = context.get("match_history", {}) or {}
    h2h_rows = (match_history.get("h2h_recent_rows") or [])[:3]
    elo = context.get("elo", {}) or {}

    t1_recent = match_history.get("team1_recent") or {}
    t2_recent = match_history.get("team2_recent") or {}
    venue_toss = ((screen_story.get("match_results_distribution") or {}).get("venue_toss_signal")) or {}
    recent_venue = (screen_story.get("recent_matches_at_venue") or {})
    innings_story = (screen_story.get("innings_scores_analysis") or {})
    phase_strategy = (screen_story.get("phase_wise_strategy") or {})
    phase_dom = phase_strategy.get("dominant_phase")

    agg_bias = _classify_toss_bias(int(venue_toss.get("batting_first_wins", 0) or 0), int(venue_toss.get("total_matches", 0) or 0))
    recent_bias = _classify_toss_bias(int(recent_venue.get("batting_first_wins", 0) or 0), int(recent_venue.get("sample_size", 0) or 0))

    c: Dict[str, int] = {}
    reasons: List[Dict[str, Any]] = []

    # Recent form
    t1_form_w = (t1_recent.get("record") or "").count("W")
    t2_form_w = (t2_recent.get("record") or "").count("W")
    c["recent_form"] = max(-2, min(2, t1_form_w - t2_form_w))
    if c["recent_form"]:
        reasons.append({"component": "recent_form", "score": c["recent_form"], "detail": f"Last-5 wins {team1} {t1_form_w}-{t2_form_w} {team2}"})

    # H2H recency weighted
    h2h_score = 0
    for i, row in enumerate(h2h_rows):
        winner = row.get("winner")
        weight = max(1, 3 - i)
        if winner == team1:
            h2h_score += weight
        elif winner == team2:
            h2h_score -= weight
    c["h2h_recent"] = 2 if h2h_score >= 2 else (-2 if h2h_score <= -2 else (1 if h2h_score > 0 else (-1 if h2h_score < 0 else 0)))
    if c["h2h_recent"]:
        reasons.append({"component": "h2h_recent", "score": c["h2h_recent"], "detail": "Recent H2H edge"})

    # ELO
    elo_delta = elo.get("delta_team1_minus_team2")
    if elo_delta is None:
        c["elo_delta"] = 0
    elif elo_delta >= 20:
        c["elo_delta"] = 1
    elif elo_delta <= -20:
        c["elo_delta"] = -1
    else:
        c["elo_delta"] = 0
    if c["elo_delta"]:
        reasons.append({"component": "elo_delta", "score": c["elo_delta"], "detail": f"ELO delta {elo_delta:+.0f}"})

    # Toss-fit vs venue bias
    bias_label = agg_bias.get("label")
    if bias_label == "bat_first_edge":
        c["toss_fit_vs_venue_bias"] = (
            2 if (t1_recent.get("wins_batting_first", 0) or 0) > (t2_recent.get("wins_batting_first", 0) or 0)
            else -2 if (t2_recent.get("wins_batting_first", 0) or 0) > (t1_recent.get("wins_batting_first", 0) or 0)
            else 0
        )
    elif bias_label == "chasing_edge":
        c["toss_fit_vs_venue_bias"] = (
            2 if (t1_recent.get("wins_chasing", 0) or 0) > (t2_recent.get("wins_chasing", 0) or 0)
            else -2 if (t2_recent.get("wins_chasing", 0) or 0) > (t1_recent.get("wins_chasing", 0) or 0)
            else 0
        )
    else:
        c["toss_fit_vs_venue_bias"] = 0
    if c["toss_fit_vs_venue_bias"]:
        reasons.append({"component": "toss_fit_vs_venue_bias", "score": c["toss_fit_vs_venue_bias"], "detail": f"Venue bias: {bias_label}"})

    # Threshold fit
    t1_thresh = (t1_recent.get("reached_avg_winning_score_batting_first", 0) or 0) + (t1_recent.get("chased_avg_chasing_score", 0) or 0)
    t2_thresh = (t2_recent.get("reached_avg_winning_score_batting_first", 0) or 0) + (t2_recent.get("chased_avg_chasing_score", 0) or 0)
    delta_thresh = t1_thresh - t2_thresh
    c["threshold_fit"] = 2 if delta_thresh >= 2 else (-2 if delta_thresh <= -2 else (1 if delta_thresh > 0 else (-1 if delta_thresh < 0 else 0)))
    if c["threshold_fit"]:
        reasons.append({"component": "threshold_fit", "score": c["threshold_fit"], "detail": f"Threshold clears {team1} {t1_thresh}-{t2_thresh} {team2}"})

    # Recent venue override alignment
    if (recent_venue.get("sample_size") or 0) >= 4 and recent_bias.get("label") != agg_bias.get("label"):
        # advantage to better fit with recent bias
        if recent_bias.get("label") == "bat_first_edge":
            c["recent_venue_override_alignment"] = 1 if (t1_recent.get("wins_batting_first", 0) or 0) > (t2_recent.get("wins_batting_first", 0) or 0) else (-1 if (t2_recent.get("wins_batting_first", 0) or 0) > (t1_recent.get("wins_batting_first", 0) or 0) else 0)
        elif recent_bias.get("label") == "chasing_edge":
            c["recent_venue_override_alignment"] = 1 if (t1_recent.get("wins_chasing", 0) or 0) > (t2_recent.get("wins_chasing", 0) or 0) else (-1 if (t2_recent.get("wins_chasing", 0) or 0) > (t1_recent.get("wins_chasing", 0) or 0) else 0)
        else:
            c["recent_venue_override_alignment"] = 0
    else:
        c["recent_venue_override_alignment"] = 0
    if c["recent_venue_override_alignment"]:
        reasons.append({"component": "recent_venue_override_alignment", "score": c["recent_venue_override_alignment"], "detail": "Recent venue trend override"})

    # Phase-template fit (proxy by bias fit and dominant phase)
    c["phase_template_fit"] = 0
    if phase_strategy and phase_strategy.get("consistency_check", {}).get("valid", True):
        fit1 = _phase_template_fit_score(t1_recent, bias_label)
        fit2 = _phase_template_fit_score(t2_recent, bias_label)
        c["phase_template_fit"] = 2 if fit1 - fit2 >= 2 else (-2 if fit2 - fit1 >= 2 else (1 if fit1 > fit2 else (-1 if fit2 > fit1 else 0)))
        if c["phase_template_fit"]:
            reasons.append({"component": "phase_template_fit", "score": c["phase_template_fit"], "detail": f"Winning-template fit via {_phase_label(phase_dom)}"})

    # Fantasy / matchup edge
    t1_f = _top_fantasy_pick(screen_story, team1)
    t2_f = _top_fantasy_pick(screen_story, team2)
    t1_f_score = float((t1_f or {}).get("expected_points", 0) or 0)
    t2_f_score = float((t2_f or {}).get("expected_points", 0) or 0)
    c["fantasy_matchup_edge"] = 2 if t1_f_score - t2_f_score >= 8 else (-2 if t2_f_score - t1_f_score >= 8 else (1 if t1_f_score > t2_f_score else (-1 if t2_f_score > t1_f_score else 0)))
    if c["fantasy_matchup_edge"]:
        reasons.append({"component": "fantasy_matchup_edge", "score": c["fantasy_matchup_edge"], "detail": "Fantasy/matchup edge"})

    total = int(sum(c.values()))
    if total >= 5:
        label = f"Lean {team1}"
        winner = team1
    elif total <= -5:
        label = f"Lean {team2}"
        winner = team2
    elif total >= 3:
        label = f"Slight lean {team1}"
        winner = team1
    elif total <= -3:
        label = f"Slight lean {team2}"
        winner = team2
    else:
        label = "Too close to call"
        winner = None

    reasons_sorted = sorted(reasons, key=lambda x: abs(int(x["score"])), reverse=True)[:3]
    return {"winner": winner, "score_total": total, "components": c, "label": label, "top_reasons": reasons_sorted}


def _add_section(sections: List[Dict[str, Any]], section_id: str, title: str, bullets: List[str], evidence_tags: List[str]) -> None:
    cleaned = [b.strip() for b in bullets if isinstance(b, str) and b.strip()][:2]
    sections.append({"id": section_id, "title": title, "bullets": cleaned or ["Data sample is thin for this section."], "evidence_tags": evidence_tags})


def build_deterministic_preview_sections(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    team1 = context.get("team1")
    team2 = context.get("team2")
    venue = context.get("venue")
    venue_stats = context.get("venue_stats", {}) or {}
    filters = context.get("filters", {}) or {}
    screen_story = context.get("screen_story", {}) or {}
    match_history = context.get("match_history", {}) or {}
    h2h_story = (screen_story.get("head_to_head_stats") or {})
    innings_story = (screen_story.get("innings_scores_analysis") or {})
    phase_story = (screen_story.get("phase_wise_strategy") or {})
    recent_venue = (screen_story.get("recent_matches_at_venue") or {})
    matchup_story = (screen_story.get("expected_fantasy_points") or {})
    team1_recent = match_history.get("team1_recent") or {}
    team2_recent = match_history.get("team2_recent") or {}

    venue_toss = ((screen_story.get("match_results_distribution") or {}).get("venue_toss_signal")) or {}
    agg_bias = _classify_toss_bias(int(venue_toss.get("batting_first_wins", 0) or 0), int(venue_toss.get("total_matches", 0) or 0))
    recent_bias = _classify_toss_bias(int(recent_venue.get("batting_first_wins", 0) or 0), int(recent_venue.get("sample_size", 0) or 0))

    phase_consistency = (phase_story.get("consistency_check") or {})
    bf_template = phase_story.get("batting_first_wins_template") or {}
    ch_template = phase_story.get("chasing_wins_template") or {}
    dominant_phase = phase_story.get("dominant_phase")

    window_label = f"{filters.get('start_date') or 'all-time'} to {filters.get('end_date') or 'latest'}"
    avg_win = innings_story.get("avg_winning_score_rounded")
    avg_chase = innings_story.get("avg_chasing_score_rounded")

    # Venue Profile
    venue_bullets = [
        f"Window {window_label}: {venue_toss.get('total_matches', 0)} matches at {venue}; {int(venue_toss.get('batting_first_wins', 0) or 0)} bat-first wins vs {int(venue_toss.get('chasing_wins', 0) or 0)} chases ({(agg_bias.get('bat_first_pct') or 0):.0f}% bat-first)."
    ]
    recent_override = (
        (recent_venue.get("sample_size") or 0) >= 4 and agg_bias.get("label") != "no_sample" and recent_bias.get("label") != "no_sample"
        and recent_bias.get("label") != agg_bias.get("label")
    )
    threshold_part = f"Winning/chasing score baselines are {avg_win or 'N/A'} and {avg_chase or 'N/A'}"
    range_part = f"range {int(venue_stats.get('lowest_total', 0) or 0)}-{int(venue_stats.get('highest_total', 0) or 0)}"
    if recent_override:
        venue_bullets.append(
            f"{threshold_part} ({range_part}); recent venue sample ({recent_venue.get('sample_size')}) trends {int(recent_venue.get('batting_first_wins', 0) or 0)}-{int(recent_venue.get('chasing_wins', 0) or 0)} and differs from the long-window split."
        )
    elif phase_consistency.get("valid", True):
        template_key = "chasing_wins_template" if agg_bias.get("label") == "chasing_edge" else "batting_first_wins_template"
        template = ch_template if template_key == "chasing_wins_template" else bf_template
        pp_runs = _phase_runs(template, "powerplay")
        death_runs = _phase_runs(template, "death")
        venue_bullets.append(
            f"{threshold_part} ({range_part}); winning-template shape is {_phase_label(dominant_phase)} driven with roughly {pp_runs or 'N/A'} in PP and {death_runs or 'N/A'} at death."
        )
    else:
        venue_bullets.append(f"{threshold_part} ({range_part}); phase-template sums are off tolerance, so preview leans on score and result splits.")

    # Form Guide
    team1_thresh = (team1_recent.get("reached_avg_winning_score_batting_first", 0) or 0) + (team1_recent.get("chased_avg_chasing_score", 0) or 0)
    team2_thresh = (team2_recent.get("reached_avg_winning_score_batting_first", 0) or 0) + (team2_recent.get("chased_avg_chasing_score", 0) or 0)
    form_bullets = [
        f"Last 5: {team1} {team1_recent.get('record', 'N/A')} ({team1_recent.get('wins_batting_first', 0)} bat-first wins, {team1_recent.get('wins_chasing', 0)} chases) vs {team2} {team2_recent.get('record', 'N/A')} ({team2_recent.get('wins_batting_first', 0)} bat-first wins, {team2_recent.get('wins_chasing', 0)} chases)."
    ]
    form_bullets.append(
        f"Threshold checks vs venue baselines ({avg_win or 'N/A'}/{avg_chase or 'N/A'}): {team1} clears {team1_thresh} recent wins/chases, {team2} clears {team2_thresh}; bowling-first winning restrictions avg {(team1_recent.get('avg_restriction_when_bowling_first') or 'N/A')}/{(team2_recent.get('avg_restriction_when_bowling_first') or 'N/A')}."
    )

    # Head-to-Head
    h2h_recent_matches = (h2h_story.get("recent_matches") or [])
    h2h_relevance = (h2h_story.get("relevance") or {})
    h2h_overall = (h2h_story.get("overall_window_summary") or {})
    if h2h_recent_matches:
        latest = h2h_recent_matches[0]
        latest_date = latest.get("date") or "unknown date"
        latest_winner = latest.get("winner_display") or latest.get("winner") or "No result"
        h2h_bullets = [
            f"Most recent H2H ({latest_date}) went to {latest_winner}; window sample is {h2h_overall.get('sample_size', 0)} matches with {team1} {h2h_overall.get('team1_wins', 0)}-{h2h_overall.get('team2_wins', 0)} {team2}."
        ]
    else:
        h2h_bullets = [f"No H2H sample in the selected window for {team1} vs {team2}."]
    if h2h_relevance.get("same_venue_matches", 0):
        h2h_bullets.append(f"H2H relevance is stronger here: {h2h_relevance.get('same_venue_matches')} recent H2H match(es) at {venue}.")
    elif h2h_relevance.get("same_country_like_matches", 0):
        h2h_bullets.append(f"No same-venue H2H, but {h2h_relevance.get('same_country_like_matches')} recent H2H match(es) in the same country-like venue context.")
    else:
        h2h_bullets.append("No same-venue H2H in the selected window, so recent form and venue trends carry more weight.")

    # Key Matchup Factor
    team1_f = _top_fantasy_pick(screen_story, team1)
    team2_f = _top_fantasy_pick(screen_story, team2)
    team1_edge = _best_edge(screen_story, team1)
    team2_threat = _best_bowling_threat(screen_story, team2)
    template_focus = "chasing_wins_template" if agg_bias.get("label") == "chasing_edge" else "batting_first_wins_template"
    template = ch_template if template_focus == "chasing_wins_template" else bf_template
    focus_phase = dominant_phase or "powerplay"
    focus_phase_runs = _phase_runs(template, focus_phase)
    key_bullets = [
        f"Winning-template pressure point is {_phase_label(focus_phase)} ({focus_phase_runs or 'N/A'} runs on average in {('successful chases' if template_focus == 'chasing_wins_template' else 'bat-first wins')})."
    ]
    matchup_parts: List[str] = []
    if team1_f:
        conf = f", conf {team1_f.get('confidence')}" if team1_f.get("high_confidence") else ""
        matchup_parts.append(f"{team1} upside: {team1_f.get('player')} ({int(round(float(team1_f.get('expected_points', 0) or 0)))} exp pts{conf})")
    if team2_f:
        conf = f", conf {team2_f.get('confidence')}" if team2_f.get("high_confidence") else ""
        matchup_parts.append(f"{team2} upside: {team2_f.get('player')} ({int(round(float(team2_f.get('expected_points', 0) or 0)))} exp pts{conf})")
    if team1_edge:
        matchup_parts.append(f"{team1_edge.get('batter')} vs {team1_edge.get('bowler')} ({team1_edge.get('balls')}b, SR {int(round(float(team1_edge.get('strike_rate', 0) or 0)))})")
    if team2_threat:
        matchup_parts.append(f"{team2_threat.get('bowler')} threat ({team2_threat.get('balls')}b, {team2_threat.get('wickets')} wkts, econ {team2_threat.get('economy')})")
    key_bullets.append("; ".join(matchup_parts) + "." if matchup_parts else "Fantasy and matchup samples are thin, so phase-template execution matters more than individual edges.")

    # Preview Take
    lean = score_preview_lean(context)
    reason_text = ", ".join(r.get("detail", "") for r in lean.get("top_reasons", []) if r.get("detail"))
    take_bullets = [f"{lean.get('label')} based on {reason_text or 'a balanced mix of venue, form and matchup signals'}."]
    threshold_gap_close = abs(team1_thresh - team2_thresh) <= 1
    if threshold_gap_close:
        take_bullets.append(
            f"If scores stay close to venue thresholds, tie-breakers are chase ceiling ({innings_story.get('highest_total_chased', 'N/A')}) and lowest defended ({innings_story.get('lowest_total_defended', 'N/A')}) with recent venue trend as context."
        )
    else:
        take_bullets.append(
            f"Toss/innings path still matters: recent venue split is {recent_venue.get('batting_first_wins', 0)} bat-first wins vs {recent_venue.get('chasing_wins', 0)} chases in the last {recent_venue.get('sample_size', 0)}."
        )

    sections: List[Dict[str, Any]] = []
    _add_section(sections, "venue_profile", "Venue Profile", venue_bullets, ["match_results_distribution", "innings_scores_analysis", "phase_wise_strategy"])
    _add_section(sections, "form_guide", "Form Guide", form_bullets, ["match_results_distribution", "innings_scores_analysis"])
    _add_section(sections, "head_to_head", "Head-to-Head", h2h_bullets, ["head_to_head_stats"])
    _add_section(sections, "key_matchup_factor", "Key Matchup Factor", key_bullets, ["phase_wise_strategy", "expected_fantasy_points"])
    _add_section(sections, "preview_take", "Preview Take", take_bullets, ["match_results_distribution", "innings_scores_analysis", "recent_matches_at_venue", "phase_wise_strategy", "expected_fantasy_points"])
    return sections


def serialize_sections_to_markdown(sections: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for section in sections:
        lines.append(f"## {section.get('title', 'Preview')}")
        for bullet in section.get("bullets", []) or []:
            lines.append(f"- {bullet}")
        lines.append("")
    return "\n".join(lines).strip()


def _parse_markdown_sections(markdown_text: str) -> List[Dict[str, Any]]:
    lines = (markdown_text or "").splitlines()
    sections: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("## "):
            if current:
                sections.append(current)
            current = {"title": line[3:].strip(), "bullets": []}
            continue
        if line.startswith("- "):
            if current is None:
                continue
            current["bullets"].append(line[2:].strip())
    if current:
        sections.append(current)
    return sections


def validate_llm_rewrite(original_sections: List[Dict[str, Any]], candidate_markdown: str) -> bool:
    parsed = _parse_markdown_sections(candidate_markdown)
    if len(parsed) != len(PREVIEW_SECTION_ORDER):
        return False

    expected_titles = [title for _, title in PREVIEW_SECTION_ORDER]
    if [s.get("title") for s in parsed] != expected_titles:
        return False

    original_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", serialize_sections_to_markdown(original_sections)))
    candidate_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", candidate_markdown or ""))
    if not original_numbers.issubset(candidate_numbers):
        return False

    for s in parsed:
        bullets = s.get("bullets") or []
        if not (1 <= len(bullets) <= 2):
            return False
    return True


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
    match_history_bundle = _get_match_history_bundle(db, venue, team1, team2, start_date, end_date)

    avg_winning_score = (venue_stats or {}).get("average_winning_score")
    avg_chasing_score = (venue_stats or {}).get("average_chasing_score")
    team1_recent_summary = _summarize_team_recent_matches(
        team1, match_history_bundle["team1_names"], match_history_bundle["team1_results"], avg_winning_score, avg_chasing_score
    )
    team2_recent_summary = _summarize_team_recent_matches(
        team2, match_history_bundle["team2_names"], match_history_bundle["team2_results"], avg_winning_score, avg_chasing_score
    )
    venue_trend = _summarize_recent_venue_trend(match_history_bundle["venue_results"])
    h2h_relevance = _same_country_hint(venue, match_history_bundle["h2h_recent"])
    matchup_fantasy = _summarize_matchups_and_fantasy(db, team1, team2, start_date, end_date)
    serialized_phase_stats = _serialize_phase_stats(phase_stats)

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
        "phase_stats": serialized_phase_stats,
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
        "match_history": {
            "venue_trend": venue_trend,
            "team1_recent": team1_recent_summary,
            "team2_recent": team2_recent_summary,
            "h2h_recent_rows": match_history_bundle["h2h_recent"],
            "h2h_relevance": h2h_relevance,
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
        "screen_story": {
            "match_results_distribution": {
                "venue_toss_signal": {
                    "batting_first_wins": int((venue_stats or {}).get("batting_first_wins", 0) or 0),
                    "chasing_wins": int((venue_stats or {}).get("batting_second_wins", 0) or 0),
                    "total_matches": int((venue_stats or {}).get("total_matches", 0) or 0),
                },
                "team_recent_toss_fit": {
                    team1: team1_recent_summary,
                    team2: team2_recent_summary,
                },
                "recent_venue_override_signal": venue_trend,
            },
            "innings_scores_analysis": {
                "avg_winning_score_rounded": int(round(float(avg_winning_score))) if avg_winning_score else None,
                "avg_chasing_score_rounded": int(round(float(avg_chasing_score))) if avg_chasing_score else None,
                "highest_total": int((venue_stats or {}).get("highest_total", 0) or 0),
                "lowest_total": int((venue_stats or {}).get("lowest_total", 0) or 0),
                "highest_total_chased": int((venue_stats or {}).get("highest_total_chased", 0) or 0),
                "lowest_total_defended": int((venue_stats or {}).get("lowest_total_defended", 0) or 0),
                "lowest_defended_recent": venue_trend.get("lowest_defended_recent"),
                "team_threshold_checks": {
                    team1: team1_recent_summary,
                    team2: team2_recent_summary,
                },
            },
            "head_to_head_stats": {
                "overall_window_summary": {
                    "sample_size": len(h2h),
                    "team1_wins": h2h_team1_wins,
                    "team2_wins": h2h_team2_wins,
                    "no_results": h2h_nr,
                },
                "recent_matches": match_history_bundle["h2h_recent"][:5],
                "relevance": h2h_relevance,
            },
            "recent_matches_at_venue": venue_trend,
            "expected_fantasy_points": matchup_fantasy,
        },
    }
    context["screen_story"]["phase_wise_strategy"] = build_phase_wise_strategy_templates(context)
    context["story_signals"] = _build_story_signals(context)
    return context


def generate_match_preview_fallback(context: Dict[str, Any]) -> str:
    sections = build_deterministic_preview_sections(context)
    return serialize_sections_to_markdown(sections)
