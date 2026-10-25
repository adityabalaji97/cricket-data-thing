"""
Results parity: a team's men's T20I record by year in our matches table against a reference (ESPNcricinfo Statsguru,
services/reference/t20i_record_by_year.json), so a missing match or a wrong result shows up as a year that doesn't add up.

    record(rows, team)        -> {year: [matches, won, lost, tied, no result]} from matches rows
    compare(ours, reference)  -> [{year, ours, reference}] for every year that differs

A tie is outcome.result 'tie' (whoever won the Super Over); a no result is no winner and no tie. "-" or a blank is
never a winner (migration 032).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

REFERENCE = Path(__file__).resolve().parent / "reference" / "t20i_record_by_year.json"


def _result(row: Dict[str, Any], team: str) -> str:
    outcome = row.get("outcome") or {}
    if isinstance(outcome, str):
        outcome = json.loads(outcome or "{}")
    if (outcome or {}).get("result") == "tie":
        return "tied"
    winner = (row.get("winner") or "").strip()
    if winner in ("", "-"):
        return "nr"
    return "won" if winner == team else "lost"


def record(rows: List[Dict[str, Any]], team: str) -> Dict[str, List[int]]:
    out: Dict[str, List[int]] = {}
    for r in rows:
        y = str(r["date"])[:4]
        rec = out.setdefault(y, [0, 0, 0, 0, 0])
        rec[0] += 1
        rec[{"won": 1, "lost": 2, "tied": 3, "nr": 4}[_result(r, team)]] += 1
    return out


def compare(ours: Dict[str, List[int]], reference: Dict[str, List[int]]) -> List[Dict[str, Any]]:
    years = sorted(set(ours) | set(reference))
    return [{"year": y, "ours": ours.get(y, [0] * 5), "reference": reference.get(y, [0] * 5)} for y in years
            if ours.get(y, [0] * 5) != reference.get(y, [0] * 5)]


def reference_for(team: str) -> Dict[str, List[int]]:
    return json.loads(REFERENCE.read_text())[team]


def check(db, team: str) -> List[Dict[str, Any]]:
    from sqlalchemy import text

    rows = [dict(r) for r in db.execute(text("""
        SELECT date, winner, outcome FROM matches
        WHERE format = 'T20' AND gender = 'male' AND match_type = 'international' AND :t IN (team1, team2)
    """), {"t": team}).mappings()]
    return compare(record(rows, team), reference_for(team))
