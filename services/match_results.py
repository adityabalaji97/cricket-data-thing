"""
Results the ball-by-ball feed leaves out: ties settled by a Super Over, plain ties and no-results.

delivery_details carries a winner column but nothing for a tie, so a match like LSG v KKR (IPL,
26 Apr 2026, KKR won the Super Over) was loaded with winner NULL and no outcome, and anything that
counts results (league tables, streaks, head-to-heads) read it as a no-result. ESPN's match summary
says what happened ("Match tied (KKR won the Super Over)", "No result"); ESPN event ids are the
cricinfo ids used as matches.id.

Stored the way Cricsheet-loaded matches already store it: winner stays NULL (a tie is a tie for
Elo and the stats) and matches.outcome gets {"result": "tie", "eliminator": <team>} /
{"result": "tie"} / {"result": "no result"}. Code that needs a points-table winner reads
COALESCE(winner, outcome->>'eliminator').
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date, timedelta
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# The summary endpoint wants a league in its path but answers for any event under any league id;
# 8048 (the IPL) is the one services/cricinfo_scraper.py already uses.
SUMMARY = "https://site.web.api.espn.com/apis/site/v2/sports/cricket/8048/summary?event={id}"
UA = {"User-Agent": "Mozilla/5.0 (compatible; CricketDataThing/1.0)", "Accept": "application/json"}
ELIMINATOR = re.compile(r"\((.+?) won (?:the )?(?:super over|one-over eliminator|eliminator|bowl-?out)", re.I)
TIED = re.compile(r"\b(match tied|tied)\b", re.I)
NO_RESULT = re.compile(r"\b(no result|abandoned|cancelled|called off)\b", re.I)


def _fetch(match_id: str) -> Optional[Dict[str, Any]]:
    import time

    for attempt in range(3):
        try:
            with urlopen(Request(SUMMARY.format(id=match_id), headers=UA), timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            if attempt == 2:
                logger.warning("ESPN summary failed for %s: %s", match_id, exc)
            else:
                time.sleep(1.5 * (attempt + 1))
    return None


def parse_result(summary: Dict[str, Any], team1: str, team2: str) -> Optional[Dict[str, Any]]:
    """{'result': 'tie'|'no result'|'win', 'eliminator'?: team} from an ESPN summary, in our team names."""
    comp = (((summary or {}).get("header") or {}).get("competitions") or [{}])[0]
    text_ = str((comp.get("status") or {}).get("summary") or "")
    if not text_:
        return None
    sides = {}
    for c in comp.get("competitors") or []:
        team = c.get("team") or {}
        for key in (team.get("abbreviation"), team.get("shortDisplayName"), team.get("displayName"), team.get("name")):
            if key:
                sides[key.strip().lower()] = team.get("displayName")
    ours = {team1.lower(): team1, team2.lower(): team2}

    def to_ours(name: Optional[str]) -> Optional[str]:
        """ESPN's name (or abbreviation) for a side -> the name in our matches row, or None if unsure."""
        if not name:
            return None
        display = sides.get(name.strip().lower(), name)
        return ours.get(display.strip().lower())

    tied = ELIMINATOR.search(text_)
    if tied:
        winner = to_ours(tied.group(1))
        return {"result": "tie", "eliminator": winner, "text": text_} if winner else None
    if TIED.search(text_):
        return {"result": "tie", "text": text_}
    if NO_RESULT.search(text_):
        return {"result": "no result", "text": text_}
    flagged = [c for c in comp.get("competitors") or [] if str(c.get("winner")).lower() == "true"]
    if len(flagged) == 1:
        return {"result": "win", "winner": to_ours((flagged[0].get("team") or {}).get("displayName")), "text": text_}
    return None


def unresolved(db: Session, days: Optional[int] = None, match_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Ball-by-ball matches with no winner and no recorded outcome."""
    where, params = ["m.winner IS NULL", "(m.outcome IS NULL OR m.outcome::text IN ('null', '{}'))",
                     "EXISTS (SELECT 1 FROM delivery_details d WHERE d.p_match = m.id)"], {}
    if match_ids:
        where.append("m.id = ANY(:ids)")
        params["ids"] = [str(m) for m in match_ids]
    if days:
        where.append("m.date >= :since")
        params["since"] = date.today() - timedelta(days=days)
    rows = db.execute(text(f"SELECT m.id, m.date, m.team1, m.team2 FROM matches m WHERE {' AND '.join(where)} ORDER BY m.date DESC"),
                      params).mappings()
    return [dict(r) for r in rows]


def resolve(db: Session, days: Optional[int] = None, match_ids: Optional[List[str]] = None,
            dry_run: bool = False) -> Dict[str, Any]:
    """Look up each unresolved match on ESPN and record ties, Super Over winners and no-results."""
    summary: Dict[str, Any] = {"checked": 0, "tie_eliminator": [], "tie": [], "no_result": [], "unclear": [], "won": []}
    from concurrent.futures import ThreadPoolExecutor

    updates = []
    todo = unresolved(db, days, match_ids)
    with ThreadPoolExecutor(max_workers=6) as pool:
        pages = list(pool.map(lambda m: _fetch(str(m["id"])), todo))
    for m, page in zip(todo, pages):
        summary["checked"] += 1
        parsed = parse_result(page, m["team1"], m["team2"])
        label = f"{m['id']} {m['date']} {m['team1']} v {m['team2']}"
        if not parsed:
            summary["unclear"].append(label)
            continue
        if parsed["result"] == "win":
            # The feed had no winner but ESPN has one: leave it for a person, never guess a result in.
            summary["won"].append(f"{label}: {parsed['text']}")
            continue
        outcome = {"result": parsed["result"], **({"eliminator": parsed["eliminator"]} if parsed.get("eliminator") else {})}
        key = "tie_eliminator" if "eliminator" in outcome else "tie" if outcome["result"] == "tie" else "no_result"
        summary[key].append(f"{label}: {parsed['text']}")
        updates.append({"id": str(m["id"]), "outcome": json.dumps(outcome)})
    if updates and not dry_run:
        from database import engine

        with engine.begin() as conn:
            conn.execute(text("UPDATE matches SET outcome = CAST(:outcome AS json) WHERE id = :id AND winner IS NULL"), updates)
    summary["updated"] = 0 if dry_run else len(updates)
    return summary
