"""
Suggestions for the query builder's empty screen (QUERY_BUILDER_PLAN.md Q1): questions about the next fixture, in its
format and in our data's own names. The fixture feed uses Cricinfo's names ("Hnry Stadium, Wellington"); the ground
becomes ours ("Sky Stadium, Wellington") through venue_standardization, the sides through team_page.canonical_team, and
the players are each side's top run-scorer and wicket-taker over its last five matches of that format.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import text

FMT_WORDS = {"T20": "T20s", "ODI": "ODIs"}


def our_ground(db, venue: str, fmt: str) -> str:
    """The data's name for a fixture's ground: its standard name, else the alias with the most matches."""
    from services.delivery_data_service import get_venue_aliases

    try:
        from venue_standardization import RESOLVED_VENUE_CANONICAL
    except ImportError:  # pragma: no cover
        RESOLVED_VENUE_CANONICAL = {}
    # A name the standard table knows (an alias or the standard name itself) resolves to the standard name.
    if venue in RESOLVED_VENUE_CANONICAL:
        return RESOLVED_VENUE_CANONICAL[venue]
    aliases = get_venue_aliases(venue) or [venue]
    row = db.execute(text("""
        SELECT ground FROM delivery_details WHERE ground = ANY(:a) AND format = :f
        GROUP BY ground ORDER BY COUNT(DISTINCT p_match) DESC LIMIT 1"""), {"a": aliases, "f": fmt}).scalar()
    return row or venue


def top_players(db, team: str, fmt: str) -> Dict[str, Optional[str]]:
    """The side's top run-scorer and wicket-taker over its last five matches of the format."""
    from services.teams import get_all_team_name_variations

    names = get_all_team_name_variations(team)
    # The last five within two years: an old match (a database that lacks the recent ones) would suggest a retired
    # player (Yuvraj Singh in ODIs, 9 Nov 2026, on a partial local copy).
    recent = """SELECT p_match FROM delivery_details WHERE (team_bat = ANY(:t) OR team_bowl = ANY(:t)) AND format = :f
                AND gender = 'male' AND match_date >= to_char(now() - interval '2 years', 'YYYY-MM-DD')
                GROUP BY p_match ORDER BY MAX(match_date) DESC LIMIT 5"""
    bat = db.execute(text(f"""SELECT bat FROM delivery_details WHERE p_match IN ({recent}) AND team_bat = ANY(:t)
        GROUP BY bat ORDER BY SUM(batruns) DESC LIMIT 1"""), {"t": names, "f": fmt}).scalar()
    bowl = db.execute(text(f"""SELECT bowl FROM delivery_details WHERE p_match IN ({recent}) AND team_bowl = ANY(:t)
        GROUP BY bowl ORDER BY SUM(CASE WHEN p_out IS NOT NULL AND dismissal NOT ILIKE '%run out%' THEN 1 ELSE 0 END) DESC,
        SUM(bowlruns) ASC LIMIT 1"""), {"t": names, "f": fmt}).scalar()
    return {"bat": bat, "bowl": bowl}


def suggestions(db) -> Dict[str, Any]:
    from services.fixture_scraper import fetch_upcoming_fixtures
    from services.team_page import canonical_team

    fixture = next((f for f in fetch_upcoming_fixtures(10) if f.get("format") in FMT_WORDS), None)
    if not fixture:
        return {"label": None, "format": None, "items": []}
    fmt = fixture["format"]
    words = FMT_WORDS[fmt]
    ground = our_ground(db, fixture.get("venue") or "", fmt)
    t1, t2 = canonical_team(fixture.get("team1") or ""), canonical_team(fixture.get("team2") or "")
    p1, p2 = top_players(db, t1, fmt), top_players(db, t2, fmt)
    items = [f"{ground}: pace or spin in {words} since 2023"]
    if p2.get("bat"):
        items.append(f"{p2['bat']} in {words} since 2024 by phase")
    if p1.get("bowl"):
        items.append(f"{p1['bowl']} line and length in {words} since 2024")
    items.append(f"{t1} bowling by phase in {words} since 2024")
    short = lambda t, a: a or t  # noqa: E731
    return {
        "label": f"Next · {short(t1, fixture.get('team1_abbr'))} v {short(t2, fixture.get('team2_abbr'))}, {fmt} at {ground.split(',')[0]}",
        "format": fmt, "items": items[:4],
    }
