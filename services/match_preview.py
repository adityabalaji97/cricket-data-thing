from __future__ import annotations

from datetime import date
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
                "highest_total_chased": int((venue_stats or {}).get("highest_total_chased", 0) or 0),
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
