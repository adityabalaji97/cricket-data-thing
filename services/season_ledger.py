"""
Who made the playoffs, and who won: per league and season (TEAM_TEMPLATE_PLAN.md, T0).

The knockouts: Cricsheet numbers a league's round-robin games (`matches.event_match_number`) and leaves its knockouts
unnumbered, so a season's playoff sides are the teams in its unnumbered games and the champion is the winner of the last
one. Our own feed numbers nothing (IPL 2026: 74 of 74 unnumbered), so a season without that pattern takes its last k
games as the knockouts, k being the league's usual count (the IPL's 4: qualifier, eliminator, qualifier, final).

Seasons are calendar years, except for leagues that run across New Year (BBL, Super Smash), split at July and named
"2024-25". Teams are keyed by their short code where we have one (models.teams_mapping), so "Royal Challengers Bangalore"
and "Royal Challengers Bengaluru" are one side.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import text

DEFAULT_KNOCKOUTS = 4

# The IPL's playoff sides and champions, checked game by game against the record (6 Nov 2026): 2008-25 are Cricsheet's
# own stage markings, 2026 (our feed, "last 4") against Olympics.com / Outlook India / Wikipedia. ledger() flags any
# season that disagrees, so a data change can't quietly move a side in or out of the template's playoff group.
VERIFIED = {"IPL": {
    "2008": ("RR", {"RR", "CSK", "PBKS", "DC"}), "2009": ("DCh", {"DCh", "RCB", "CSK", "DC"}),
    "2010": ("CSK", {"CSK", "MI", "RCB", "DCh"}), "2011": ("CSK", {"CSK", "RCB", "MI", "KKR"}),
    "2012": ("KKR", {"KKR", "CSK", "DC", "MI"}), "2013": ("MI", {"MI", "CSK", "RR", "SRH"}),
    "2014": ("KKR", {"KKR", "PBKS", "CSK", "MI"}), "2015": ("MI", {"MI", "CSK", "RCB", "RR"}),
    "2016": ("SRH", {"SRH", "RCB", "GL", "KKR"}), "2017": ("MI", {"MI", "RPSG", "KKR", "SRH"}),
    "2018": ("CSK", {"CSK", "SRH", "KKR", "RR"}), "2019": ("MI", {"MI", "CSK", "DC", "SRH"}),
    "2020": ("MI", {"MI", "DC", "SRH", "RCB"}), "2021": ("CSK", {"CSK", "KKR", "DC", "RCB"}),
    "2022": ("GT", {"GT", "RR", "RCB", "LSG"}), "2023": ("CSK", {"CSK", "GT", "MI", "LSG"}),
    "2024": ("KKR", {"KKR", "SRH", "RR", "RCB"}), "2025": ("RCB", {"RCB", "PBKS", "MI", "GT"}),
    "2026": ("RCB", {"RCB", "GT", "RR", "SRH"}),
}}


def team_key(name: Optional[str]) -> Optional[str]:
    """One key per franchise across renames (the short code), else the name."""
    from models import teams_mapping

    if not name:
        return name
    return teams_mapping.get(name, name)


def _season_of(d: date, cross_year: bool) -> str:
    if not cross_year:
        return str(d.year)
    start = d.year if d.month >= 7 else d.year - 1
    return f"{start}-{(start + 1) % 100:02d}"


def _matches(db, competition: str) -> List[Dict[str, Any]]:
    from services.query_builder_v2 import competition_canonical_sql

    rows = db.execute(text(f"""
        SELECT id, date, team1, team2, winner, event_match_number
        FROM matches
        WHERE format = 'T20' AND gender = 'male' AND match_type = 'league'
          AND {competition_canonical_sql('competition')} = :c
        ORDER BY date, id
    """), {"c": competition}).mappings().all()
    return [dict(r) for r in rows]


def ledger(db, competition: str) -> List[Dict[str, Any]]:
    """Every season of a league: its teams, league-stage table, knockout games, playoff sides and champion."""
    ms = _matches(db, competition)
    if not ms:
        return []
    months = Counter(m["date"].month for m in ms)
    n = len(ms)
    cross_year = (months[11] + months[12]) / n > 0.15 and (months[1] + months[2]) / n > 0.15
    seasons: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for m in ms:
        seasons[_season_of(m["date"], cross_year)].append(m)

    # The league's usual number of knockouts, from the seasons Cricsheet marked.
    marked = [sum(1 for m in g if m["event_match_number"] is None) for g in seasons.values()]
    usual = Counter(k for k, g in zip(marked, seasons.values()) if 2 <= k <= 6 and k < len(g) / 3)
    k_default = usual.most_common(1)[0][0] if usual else DEFAULT_KNOCKOUTS

    out = []
    for season, games in sorted(seasons.items()):
        unnumbered = [m for m in games if m["event_match_number"] is None]
        if 2 <= len(unnumbered) <= 6 and len(unnumbered) < len(games) / 3:
            knockouts, method = unnumbered, "marked"
        else:
            knockouts, method = games[-k_default:], f"last {k_default}"
        ko_ids = {m["id"] for m in knockouts}
        table: Dict[str, Dict[str, int]] = defaultdict(lambda: {"played": 0, "won": 0})
        for m in games:
            if m["id"] in ko_ids:
                continue
            for t in (m["team1"], m["team2"]):
                table[team_key(t)]["played"] += 1
            if m["winner"]:
                table[team_key(m["winner"])]["won"] += 1
        playoff = sorted({team_key(t) for m in knockouts for t in (m["team1"], m["team2"]) if t})
        final = max(knockouts, key=lambda m: (m["date"], m["id"])) if knockouts else None
        out.append({
            "competition": competition, "season": season, "start": games[0]["date"], "end": games[-1]["date"],
            "matches": len(games), "teams": sorted(table), "table": dict(table), "knockouts": sorted(ko_ids),
            "method": method, "playoff": playoff,
            "champion": team_key(final["winner"]) if final and final["winner"] else None,
            "runner_up": next((team_key(t) for t in (final["team1"], final["team2"])
                               if final and final["winner"] and t != final["winner"]), None) if final else None,
        })
        check = VERIFIED.get(competition, {}).get(season)
        out[-1]["verified"] = None if check is None else (out[-1]["champion"] == check[0] and set(playoff) == check[1])
    return out
