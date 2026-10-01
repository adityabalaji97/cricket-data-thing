"""How a player gets out (batter) or takes wickets (bowler), under the profile page's filters.

One implementation behind /players/{name}/dismissal_stats (what the profile page calls) and the
filtered /player/{name}/dismissal_stats twins in main.py. The previous versions read only the
legacy ``deliveries`` table by exact name: the page passes the legacy spelling ("V Kohli"), so it
showed that player's pre-2015 and cricsheet-loaded dismissals whatever window was selected (and
nothing at all for a name only delivery_details uses), ignored every filter, split the T20 middle
overs at 16, and charged a non-striker's run out to the striker.

Balls come from delivery_details for every match it holds and from the legacy table only for
matches it does not, so nothing is counted twice. Wicket rules are services/metrics/sql_defs.py's.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from models import INTERNATIONAL_TEAMS_RANKED
from services.analytics_common import phase_case_sql
from services.metrics import sql_defs
from services.player_aliases import get_player_names
from utils.league_utils import expand_league_abbreviations

BATTER = "batter"
BOWLER = "bowler"

# The two tables spell LBW differently; report one mode, not two slices of the same thing.
_MODE_SQL = "CASE WHEN {col} = 'leg before wicket' THEN 'lbw' ELSE {col} END"
# Dismissals that can fall on the non-striker (bat_out = 'false' on the ball).
_NON_STRIKER_MODES = ("run out", "obstructing the field", "retired out")


def _player_names(player_name: str, db: Session) -> List[str]:
    names = get_player_names(player_name, db)
    return list(dict.fromkeys(filter(None, [
        player_name, *names.get("all_names", []), names.get("legacy_name"), names.get("details_name"),
    ])))


def _match_filter(params: Dict[str, Any], leagues: List[str], include_international: bool,
                  top_teams: Optional[int]) -> str:
    """Same competition semantics as the other profile endpoints: leagues (all when none are
    named), plus internationals when asked -- limited to top-N sides when top_teams is set."""
    conditions = []
    if leagues:
        params["leagues"] = expand_league_abbreviations(leagues)
        conditions.append("(m.match_type = 'league' AND m.competition = ANY(:leagues))")
    else:
        conditions.append("m.match_type = 'league'")
    if include_international:
        if top_teams:
            params["top_team_list"] = INTERNATIONAL_TEAMS_RANKED[:top_teams]
            conditions.append(
                "(m.match_type = 'international' AND m.team1 = ANY(:top_team_list) AND m.team2 = ANY(:top_team_list))"
            )
        else:
            conditions.append("m.match_type = 'international'")
    return f"""
        AND (CAST(:start_date AS date) IS NULL OR m.date >= :start_date)
        AND (CAST(:end_date AS date) IS NULL OR m.date <= :end_date)
        AND (CAST(:venue AS text) IS NULL OR m.venue = :venue)
        AND m.format = :fmt AND m.gender = :gender
        AND ({' OR '.join(conditions)})
    """


def _dismissal_rows_sql(role: str, match_filter: str, fmt: str, gender: str) -> str:
    dd_mode = _MODE_SQL.format(col="LOWER(dd.dismissal)")
    legacy_mode = _MODE_SQL.format(col="LOWER(d.wicket_type)")
    dd_phase = phase_case_sql(fmt, gender, over_column="dd.over")
    legacy_phase = phase_case_sql(fmt, gender, over_column="d.over")

    if role == BOWLER:
        dd_who = f"dd.bowl = ANY(:names) AND {sql_defs.delivery_details_defs(sql_defs.BOWLER, 'dd').wicket}"
        legacy_who = f"d.bowler = ANY(:names) AND {sql_defs.legacy_defs(sql_defs.BOWLER, 'd').wicket}"
    else:
        team_dd = sql_defs.delivery_details_defs(sql_defs.TEAM, "dd").wicket
        team_legacy = sql_defs.legacy_defs(sql_defs.TEAM, "d").wicket
        non_striker = ", ".join(f"'{m}'" for m in _NON_STRIKER_MODES)
        # The striker when bat_out says so; otherwise the non-striker, for the modes that can
        # dismiss him (a "caught" with bat_out = false is a feed error, not a non-striker out).
        dd_who = f"""{team_dd} AND (
                (LOWER(dd.bat_out) = 'true' AND dd.bat = ANY(:names))
                OR (LOWER(COALESCE(dd.bat_out, '')) <> 'true' AND dd.non_striker = ANY(:names)
                    AND LOWER(dd.dismissal) IN ({non_striker}))
            )"""
        legacy_who = f"{team_legacy} AND d.player_dismissed = ANY(:names)"

    return f"""
        SELECT mode, phase, COUNT(*) AS count FROM (
            SELECT {dd_mode} AS mode, {dd_phase} AS phase
            FROM delivery_details dd
            JOIN matches m ON m.id = dd.p_match
            WHERE {dd_who}
            {match_filter}
            UNION ALL
            SELECT {legacy_mode}, {legacy_phase}
            FROM deliveries d
            JOIN matches m ON m.id = d.match_id
            WHERE {legacy_who}
              AND NOT EXISTS (SELECT 1 FROM delivery_details x WHERE x.p_match = d.match_id)
            {match_filter}
        ) w
        GROUP BY mode, phase
    """


def get_dismissal_breakdown(
    db: Session,
    player_name: str,
    role: str,
    *,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    leagues: Optional[List[str]] = None,
    include_international: bool = False,
    top_teams: Optional[int] = None,
    venue: Optional[str] = None,
    fmt: str = "T20",
    gender: str = "male",
) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "names": _player_names(player_name, db),
        "start_date": start_date,
        "end_date": end_date,
        "venue": venue,
        "fmt": fmt,
        "gender": gender,
    }
    match_filter = _match_filter(params, leagues or [], include_international, top_teams)
    rows = db.execute(text(_dismissal_rows_sql(role, match_filter, fmt, gender)), params).fetchall()

    overall: Dict[str, int] = {}
    by_phase: Dict[str, Dict[str, int]] = {}
    for row in rows:
        overall[row.mode] = overall.get(row.mode, 0) + row.count
        phase = by_phase.setdefault(row.phase, {})
        phase[row.mode] = phase.get(row.mode, 0) + row.count

    total = sum(overall.values())
    dismissals = [
        {"type": mode, "count": count, "percentage": round(count * 100 / total, 1) if total else 0}
        for mode, count in sorted(overall.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    result: Dict[str, Any] = {
        "player_name": player_name,
        "dismissals": dismissals,
        "by_phase": {
            phase: [{"type": m, "count": c} for m, c in sorted(modes.items(), key=lambda kv: (-kv[1], kv[0]))]
            for phase, modes in by_phase.items()
        },
    }
    result["total_wickets" if role == BOWLER else "total_dismissals"] = total
    return result
