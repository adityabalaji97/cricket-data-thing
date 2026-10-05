"""
Instagram backlog: about 30 days of posts lined up before the account's first post, then kept topped up.

A post is a content pack with channel 'instagram' (migration 017), a pillar and the day it is planned for. The
evergreen pillars are made ahead from the curated IDEAS below; the 'play' slot is filled by the games and the
'reactive' slots on the day (trend radar). A reactive day with nothing worth posting takes a bench item instead.

    debate    a debate settled with a ranking or scatter ("Gill is the most controlled ODI batter")
    myth      a hypothesis-lab note: "a common claim is...", then what the data says
    weird     records and oddities: fastest to, debuts, many centuries in one innings
    play      play along (games); made by the games, not here
    reactive  match-day and trending; made on the day

Every number comes from the same code as the website (services/content_ideas.attempt): debate ideas carry an
explicit query plan (no language model, so the same idea always gives the same query), record ideas are parsed by
services/idea_stats (regular expressions), and myth posts point at their note.
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

#: One week of slots, Monday first. Evergreen pillars are filled ahead; 'play' and 'reactive' stay open.
WEEK = ["debate", "reactive", "myth", "debate", "play", "reactive", "weird"]
EVERGREEN = ("debate", "myth", "weird")
#: A player appears at most once in any SPREAD consecutive scheduled posts.
SPREAD = 5
DAYS = 30


def _q(**params) -> Dict[str, Any]:
    return {"gender": "male", "query_mode": "delivery", **params}


#: Curated evergreen ideas. `players` drives the spread rule for ideas whose subject is fixed; a leaderboard's
#: subject (its leader) is only known after the query runs, and is added then.
IDEAS: List[Dict[str, Any]] = [
    # --- debate: ODI ---------------------------------------------------------------------------------------
    {"key": "odi-pair-three-ways", "pillar": "debate", "players": ["Shubman Gill", "Virat Kohli"],
     "idea": "No ODI partnership beats Gill and Kohli on average, strike rate and control together",
     "planned": {"params": _q(fmt="ODI", group_by=["partnership"], min_balls=1000), "metric": "control_percentage",
                 "highlight": ["Shubman Gill & Virat Kohli"],
                 "chart": {"type": "scatter", "x_axis": "strike_rate", "y_axis": "average", "also": ["control_percentage"]}}},
    {"key": "odi-control-gill", "pillar": "debate", "players": ["Shubman Gill"],
     "idea": "Most controlled ODI batters with a 40+ average and 90+ strike rate",
     "planned": {"params": _q(fmt="ODI", group_by=["batter"], min_balls=1000, having=["average:gte:40", "strike_rate:gte:90"]),
                 "metric": "control_percentage", "highlight": ["Shubman Gill"]}},
    {"key": "odi-pull-sixes", "pillar": "debate", "players": ["Rohit Sharma"],
     "idea": "Most ODI sixes off the pull and hook",
     "planned": {"params": _q(fmt="ODI", group_by=["batter"], shot_family=["PULL_HOOK"]), "metric": "sixes",
                 "highlight": ["Rohit Sharma"]}},
    {"key": "odi-death-hitters", "pillar": "debate", "idea": "Fastest scorers in ODI death overs since 2015",
     "planned": {"params": _q(fmt="ODI", group_by=["batter"], over_min=40, over_max=49, min_balls=400,
                              start_date="2015-01-01", top_teams=10, include_international=True), "metric": "strike_rate"}},
    {"key": "odi-middle-overs-squeeze", "pillar": "debate", "idea": "Most economical ODI bowlers in the middle overs since 2019",
     "planned": {"params": _q(fmt="ODI", group_by=["bowler"], over_min=10, over_max=39, min_balls=1500,
                              start_date="2019-01-01", top_teams=10, include_international=True), "metric": "economy"}},
    {"key": "odi-death-bowlers", "pillar": "debate", "idea": "Most economical ODI death bowlers since 2015",
     "planned": {"params": _q(fmt="ODI", group_by=["bowler"], over_min=40, over_max=49, min_balls=300,
                              start_date="2015-01-01", top_teams=10, include_international=True), "metric": "economy"}},
    {"key": "odi-chase-average", "pillar": "debate", "players": ["Virat Kohli"],
     "idea": "Best ODI batting average while chasing",
     "planned": {"params": _q(fmt="ODI", group_by=["batter"], is_chase=True, min_balls=3000), "metric": "average",
                 "highlight": ["Virat Kohli"]}},
    {"key": "odi-boundary-hitters", "pillar": "debate", "idea": "Highest boundary % among ODI batters since 2019",
     "planned": {"params": _q(fmt="ODI", group_by=["batter"], min_balls=1500, start_date="2019-01-01", top_teams=10, include_international=True),
                 "metric": "boundary_percentage"}},
    # --- debate: T20 / leagues --------------------------------------------------------------------------------
    {"key": "t20-death-bumrah", "pillar": "debate", "players": ["Jasprit Bumrah"],
     "idea": "Most economical T20 death bowlers since 2020",
     "planned": {"params": _q(fmt="T20", group_by=["bowler"], over_min=15, over_max=19, min_balls=600,
                              start_date="2020-01-01"), "metric": "economy", "highlight": ["Jasprit Bumrah"]}},
    {"key": "ipl-economy", "pillar": "debate", "idea": "Most economical IPL bowlers since 2020",
     "planned": {"params": _q(fmt="T20", leagues=["IPL"], group_by=["bowler"], min_balls=1200, start_date="2020-01-01"),
                 "metric": "economy"}},
    {"key": "ipl-death-hitters", "pillar": "debate", "idea": "Fastest scorers in IPL death overs since 2023",
     "planned": {"params": _q(fmt="T20", leagues=["IPL"], group_by=["batter"], over_min=15, over_max=19,
                              min_balls=200, start_date="2023-01-01"), "metric": "strike_rate"}},
    {"key": "t20-powerplay-hitters", "pillar": "debate", "idea": "Fastest IPL powerplay scorers since 2023",
     "planned": {"params": _q(fmt="T20", leagues=["IPL"], group_by=["batter"], over_min=0, over_max=5, min_balls=300,
                              start_date="2023-01-01"), "metric": "strike_rate"}},
    {"key": "t20-spin-hitters", "pillar": "debate", "idea": "Best T20 hitters of spin since 2023",
     "planned": {"params": _q(fmt="T20", group_by=["batter"], bowl_kind=["spin bowler"], min_balls=500,
                              start_date="2023-01-01"), "metric": "strike_rate"}},
    {"key": "t20-pace-hitters", "pillar": "debate", "idea": "Best T20 hitters of pace since 2023",
     "planned": {"params": _q(fmt="T20", group_by=["batter"], bowl_kind=["pace bowler"], min_balls=800,
                              start_date="2023-01-01"), "metric": "strike_rate"}},
    {"key": "t20-impact-batters", "pillar": "debate", "idea": "Most impactful IPL batters per 100 balls since 2024",
     "planned": {"params": _q(fmt="T20", leagues=["IPL"], group_by=["batter"], min_balls=500, start_date="2024-01-01"),
                 "metric": "impact_per_100"}},
    {"key": "t20-dot-bowlers", "pillar": "debate", "idea": "Highest dot-ball % among IPL bowlers since 2022",
     "planned": {"params": _q(fmt="T20", leagues=["IPL"], group_by=["bowler"], min_balls=1000, start_date="2022-01-01"),
                 "metric": "dot_percentage"}},
    {"key": "ipl-powerplay-bowlers", "pillar": "debate", "idea": "Most economical IPL powerplay bowlers since 2022",
     "planned": {"params": _q(fmt="T20", leagues=["IPL"], group_by=["bowler"], over_min=0, over_max=5, min_balls=480,
                              start_date="2022-01-01"), "metric": "economy"}},
    {"key": "t20-control-hitters", "pillar": "debate", "idea": "Strike rate v control % for IPL batters since 2024",
     "planned": {"params": _q(fmt="T20", leagues=["IPL"], group_by=["batter"], min_balls=600, start_date="2024-01-01"),
                 "metric": "strike_rate", "chart": {"type": "scatter", "x_axis": "control_percentage", "y_axis": "strike_rate"}}},
    # --- weird: records, parsed by services/idea_stats (no language model) ----------------------------------
    {"key": "ipl-fastest-1000-balls", "pillar": "weird", "idea": "Fastest to 1000 IPL runs in balls"},
    {"key": "ipl-fastest-100-wickets", "pillar": "weird", "idea": "Fastest to 100 wickets in IPL"},
    {"key": "ipl-fastest-2000-balls", "pillar": "weird", "idea": "Fastest to 2000 IPL runs in balls"},
    {"key": "odi-costliest-debut", "pillar": "weird", "idea": "Most runs conceded in debut ODI game"},
    {"key": "odi-fastest-200-wickets", "pillar": "weird", "idea": "Fastest to 200 wickets in ODIs"},
    {"key": "odi-fastest-5000", "pillar": "weird", "idea": "Fastest to 5000 runs in ODIs"},
    {"key": "odi-three-tons-innings", "pillar": "weird", "idea": "3 batter centuries in an ODI innings"},
    {"key": "odi-four-tons-match", "pillar": "weird", "idea": "4+ centuries in an ODI match"},
    {"key": "ipl-two-tons-innings", "pillar": "weird", "idea": "2 centuries in an IPL innings"},
    {"key": "odi-two-fivefors-match", "pillar": "weird", "idea": "2 five-wicket hauls in an ODI match"},
    {"key": "ipl-debut-runs", "pillar": "weird", "idea": "Most runs on IPL debut"},
    # --- myth: hypothesis-lab notes ----------------------------------------------------------------------------
    *[{"key": f"myth-note-{n}", "pillar": "myth", "note_id": n} for n in (34, 35, 36, 37, 38, 39, 40, 41, 42)],
]


def _players_of(item: Dict[str, Any], fact: Optional[Dict[str, Any]]) -> List[str]:
    names = list(item.get("players") or [])
    subject = (fact or {}).get("subject")
    if subject and not names:
        names = [s.strip() for s in str(subject).replace(" and ", " & ").split(" & ") if s.strip()]
    return names


def _caption(fact: Dict[str, Any]) -> str:
    """A first Instagram caption: the headline, how it was measured, and where the data lives. (Instagram-specific
    hooks, hashtags and a closing question come with the caption chunk; this keeps the numbers to the fact's own.)"""
    lines = [fact["title"], "", fact.get("method") or "", "", "Data: Hindsight, ball-by-ball cricket stats (link in bio)."]
    return "\n".join(l for l in lines).strip()


def _note_post(db: Session, item: Dict[str, Any]) -> Dict[str, Any]:
    note = db.execute(text("SELECT id, status, title, dek, slug, body_md FROM notes WHERE id = :id"),
                      {"id": item["note_id"]}).mappings().first()
    if not note:
        return {"status": "failed", "note": f"note {item['note_id']} not found"}
    # The note's first line is its finding in one sentence (the hypothesis lab writes it in italics).
    finding = (note["dek"] or (note["body_md"] or "").strip().split("\n", 1)[0]).strip().strip("*_ ")
    fact = {"kind": "note", "subject": None, "title": note["title"], "finding": finding, "note_id": note["id"],
            "note_slug": note["slug"], "method": "Pre-registered test on Hindsight's ball-by-ball data; full write-up linked in bio."}
    warnings = [] if note["status"] == "published" else [f"The note is still a {note['status']}: review and publish it before this goes out."]
    return {"status": "resolved", "fact": fact, "snapshot": None, "warnings": warnings}


def make(db: Session, item: Dict[str, Any], created_by: str = "ig-backlog") -> Dict[str, Any]:
    """Run one idea: {status, fact, snapshot, warnings}. Saves chart snapshots (callers stub that for a dry run)."""
    from services import content_ideas

    if item["pillar"] == "myth":
        return _note_post(db, item)
    try:
        planned = item.get("planned") or content_ideas.plan(item["idea"], None, db)
        result = content_ideas.attempt(db, item["idea"], planned, created_by=created_by)
    except Exception as exc:  # a bad plan or query: report it, keep building the rest
        logger.exception("ig idea %s failed", item["key"])
        db.rollback()
        return {"status": "failed", "note": str(exc)[:300]}
    if result.get("status") != "resolved":
        return result
    fact, warnings = result["fact"], list(result["fact"].get("warnings") or [])
    numbers = fact.get("numbers") or {}
    rank, total = numbers.get("rank"), numbers.get("total")
    if item.get("planned", {}).get("highlight") and rank and total and rank > max(10, total * 0.1):
        warnings.append(f"The highlighted subject ranks {rank} of {total}: not a standout.")
    return {**result, "warnings": warnings}


def schedule(made: List[Dict[str, Any]], start: date, days: int = DAYS) -> List[Dict[str, Any]]:
    """Assign evergreen posts to the WEEK template from `start`; returns the calendar (one entry per day).

    Each slot takes the first unused post of its pillar (IDEAS order is the priority order) whose players haven't
    appeared in the previous SPREAD - 1 scheduled posts; with none left that satisfies the rule, the slot stays open.
    """
    pools = {p: [m for m in made if m["pillar"] == p] for p in EVERGREEN}
    used, recent, calendar = set(), [], []
    for d in range(days):
        day = start + timedelta(days=d)
        pillar = WEEK[day.weekday()]
        entry = {"date": day, "pillar": pillar, "post": None}
        if pillar in EVERGREEN:
            blocked = {p for post in recent[-(SPREAD - 1):] for p in post["players"]}
            pick = next((m for m in pools[pillar] if m["key"] not in used and not blocked & set(m["players"])), None)
            if pick:
                used.add(pick["key"])
                recent.append(pick)
                entry["post"] = pick
        calendar.append(entry)
    bench = [m for m in made if m["key"] not in used]
    return calendar, bench


def build(db: Session, start: date, days: int = DAYS, write: bool = False,
          only: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    """Make every idea, schedule the calendar, and (with write) queue the posts as Instagram packs."""
    keys = set(only or [])
    made, failed = [], []
    for item in IDEAS:
        if keys and item["key"] not in keys:
            continue
        result = make(db, item)
        if result.get("status") != "resolved":
            failed.append({"key": item["key"], "status": result.get("status"), "note": result.get("note")})
            continue
        made.append({"key": item["key"], "pillar": item["pillar"], "fact": result["fact"],
                     "snapshot_id": (result.get("snapshot") or {}).get("id"), "warnings": result.get("warnings") or [],
                     "players": _players_of(item, result["fact"])})
    calendar, bench = schedule(made, start, days)
    if write:
        _write(calendar, bench)
    return {"calendar": calendar, "bench": bench, "failed": failed}


def _write(calendar: List[Dict[str, Any]], bench: List[Dict[str, Any]]) -> None:
    """Upsert the posts (angle_key 'ig:<key>'). Posted or skipped packs keep their status and day."""
    from database import engine

    rows = [(e["post"], e["date"]) for e in calendar if e["post"]] + [(b, None) for b in bench]
    with engine.begin() as conn:
        for post, day in rows:
            fact = post["fact"]
            conn.execute(text("""
                INSERT INTO content_packs (match_id, snapshot_id, angle_key, title, first_comment, subreddit, flair, facts,
                                           rule_warnings, status, source, channel, planned_for, pillar, caption)
                VALUES (NULL, :s, :k, :t, NULL, NULL, NULL, CAST(:f AS jsonb), CAST(:w AS jsonb), 'ready', 'ig-backlog',
                        'instagram', :d, :p, :c)
                ON CONFLICT (angle_key) WHERE angle_key IS NOT NULL DO UPDATE SET
                    snapshot_id = EXCLUDED.snapshot_id, title = EXCLUDED.title, facts = EXCLUDED.facts,
                    rule_warnings = EXCLUDED.rule_warnings, pillar = EXCLUDED.pillar, caption = EXCLUDED.caption,
                    planned_for = CASE WHEN content_packs.status = 'ready' THEN EXCLUDED.planned_for
                                       ELSE content_packs.planned_for END
            """), {"s": post["snapshot_id"], "k": f"ig:{post['key']}", "t": fact["title"],
                   "f": json.dumps(fact, default=str), "w": json.dumps(post["warnings"]), "d": day,
                   "p": post["pillar"], "c": _caption(fact) if fact.get("kind") != "note"
                   else "\n".join([fact["title"], "", fact.get("finding") or "", "", fact["method"]])})
