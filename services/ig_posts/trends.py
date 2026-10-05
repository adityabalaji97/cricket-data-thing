"""
Trend radar: who cricket is talking about this morning, as debate posts with that player highlighted.

  1. Headlines from public feeds (FEEDS: Reddit's r/Cricket and r/IndiaCricket RSS, Cricinfo RSS, Google News RSS).
  2. Players named in them: full names, or a surname that only one active player has, matched against everyone
     with balls in the post scopes (men's T20 and ODI, recent seasons).
  3. For each of the most-mentioned players, a question in the scope where they've played most ("Is Tilak Varma the
     most complete batter in T20Is since 2023?"), built like any debate post (services/ig_posts), the player
     highlighted on every card.
  4. Jev scores how much fans would argue about each, given the headlines that named the player; the top few are
     queued as 'Trending today'.

Feeds are best-effort: one failing doesn't stop the others. Headlines only pick who to look at; every number on a
slide still comes from the database.
"""
from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

FEEDS = {
    "r/Cricket": "https://www.reddit.com/r/Cricket/hot/.rss",
    "r/IndiaCricket": "https://www.reddit.com/r/IndiaCricket/hot/.rss",
    "Cricinfo": "https://www.espncricinfo.com/rss/content/story/feeds/0.xml",
    "Google News": "https://news.google.com/rss/search?q=cricket&hl=en-IN&gl=IN&ceid=IN:en",
}
UA = "hindsight-trend-radar/1.0 (+https://hindsightcricket.com)"
#: Surnames too common in headlines (or among players) to stand for one person on their own.
AMBIGUOUS = {"sharma", "singh", "khan", "kumar", "patel", "yadav", "ali", "ahmed", "iyer", "pandya", "malik", "shah",
             "rahman", "hasan", "smith", "taylor", "williams", "green", "head", "root", "wood", "starc", "king", "hope"}


def headlines(log=print) -> List[Dict[str, str]]:
    out = []
    with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=15) as client:
        for source, url in FEEDS.items():
            root = None
            for attempt in range(2):  # Reddit sends an empty body to back-to-back requests: wait, try once more
                try:
                    root = ET.fromstring(client.get(url).content)
                    break
                except Exception as exc:  # one feed down doesn't stop the radar
                    if attempt:
                        log(f"  feed {source} failed: {exc}")
                    time.sleep(3)
            if root is None:
                continue
            for el in root.iter():
                if el.tag.split("}")[-1] in ("item", "entry"):
                    title = next((c.text for c in el if c.tag.split("}")[-1] == "title" and c.text), None)
                    if title:
                        out.append({"source": source, "title": re.sub(r"\s+", " ", title).strip()})
    return out


def active_players(db: Session) -> Dict[str, Dict[str, Any]]:
    """name -> {balls, role}: everyone with 300+ balls (faced or bowled) in men's T20/ODI since 2023."""
    rows = db.execute(text("""
        SELECT name, role, SUM(balls) AS balls FROM (
            SELECT COALESCE(am.alias_name, dd.bat) AS name, 'batter' AS role, COUNT(*) AS balls
            FROM delivery_details dd LEFT JOIN player_alias_unambiguous am ON am.player_name = dd.bat
            WHERE dd.gender = 'male' AND dd.match_date >= '2023-01-01' GROUP BY 1
            UNION ALL
            SELECT COALESCE(am.alias_name, dd.bowl), 'bowler', COUNT(*)
            FROM delivery_details dd LEFT JOIN player_alias_unambiguous am ON am.player_name = dd.bowl
            WHERE dd.gender = 'male' AND dd.match_date >= '2023-01-01' GROUP BY 1
        ) t GROUP BY 1, 2 HAVING SUM(balls) >= 300
    """)).all()
    players: Dict[str, Dict[str, Any]] = {}
    for name, role, balls in rows:
        p = players.setdefault(name, {"balls": 0, "role": role})
        if balls > p["balls"]:
            p.update(balls=int(balls), role=role)
    return players


def mentions(titles: List[Dict[str, str]], players: Dict[str, Dict[str, Any]]) -> Dict[str, List[Dict[str, str]]]:
    """player -> the headlines naming them (full name, or a surname only one active player has)."""
    by_surname = defaultdict(list)
    for name in players:
        parts = name.split()
        if len(parts) >= 2:
            by_surname[parts[-1].lower()].append(name)
    out: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for h in titles:
        t = h["title"]
        found = set()
        for name in players:
            if len(name) > 5 and re.search(rf"\b{re.escape(name)}\b", t, re.I):
                found.add(name)
        for word in set(re.findall(r"\b[A-Z][a-z]{3,}\b", t)):
            names = by_surname.get(word.lower(), [])
            if len(names) == 1 and word.lower() not in AMBIGUOUS:
                found.add(names[0])
        for name in found:
            out[name].append(h)
    return out


def best_scope(db: Session, name: str, role: str) -> Optional[Dict[str, Any]]:
    """The question scope where the player has most balls and qualifies for the field."""
    from services.ig_posts.context import QuestionContext
    from services.ig_posts.questions import ODI_SCOPES, T20_SCOPES

    best = None
    # Lower than the debate posts' minimums: a player in the news only needs enough balls to stand in the field.
    mins = {"ipl23": 400 if role == "batter" else 240, "t20i23": 250 if role == "batter" else 180,
            "odi19": 800 if role == "batter" else 600}
    for skey, hook, label, kicker, fmt, params in (*T20_SCOPES, *ODI_SCOPES):
        ctx = QuestionContext(db=db, role=role, fmt=fmt, params=params, min_balls=mins[skey], subject=name)
        row = ctx.find(name)
        if row and (not best or row["balls"] > best["balls"]):
            best = {"key": skey, "hook": hook, "label": label, "kicker": kicker, "fmt": fmt, "params": params,
                    "min_balls": mins[skey], "balls": row["balls"], "ctx": ctx}
    return best


def candidates(db: Session, top: int = 6, log=print) -> List[Dict[str, Any]]:
    """generate()-style entries for the most-mentioned players, each with the headlines that named them."""
    from services.ig_posts import angles as A
    from services.ig_posts.planner import plan
    from services.ig_posts.questions import Question, contested

    titles = headlines(log)
    players = active_players(db)
    named = mentions(titles, players)
    # Most feeds first (a name in three feeds is a story), then most headlines.
    ranked = sorted(named.items(), key=lambda kv: (-len({h["source"] for h in kv[1]}), -len(kv[1])))
    log(f"  {len(titles)} headlines, {len(named)} players named")
    out = []
    for name, hs in ranked[: top * 2]:
        role = players[name]["role"]  # what they mostly do (balls faced v bowled since 2023)
        other = "bowler" if role == "batter" else "batter"
        scope = best_scope(db, name, role) or best_scope(db, name, other)
        if not scope:
            log(f"  {name}: not in any post scope")
            continue
        r = scope["ctx"].role
        noun = "batter" if r == "batter" else "bowler"
        text_ = f"Is {name} the most complete {noun} {scope['hook']}?"
        q = Question(key=f"trend-{re.sub(r'[^a-z0-9]+', '-', name.lower())}", text=text_, role=r, fmt=scope["fmt"],
                     params=scope["params"], min_balls=scope["min_balls"],
                     scope_label=f"{scope['label']} · {scope['min_balls']:,}+ balls", kicker=scope["kicker"], subject=name)
        ctx = scope["ctx"]
        p = plan(ctx, q.text, A.available(r, q.fmt, q.params.get("leagues") or ()))
        if len(p["angles"]) < 4:
            continue
        out.append({"question": q, "ctx": ctx, "plan": p, "contest": contested(ctx, p["angles"]), "headlines": hs[:3]})
        if len(out) >= top:
            break
    return out


def rank(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Jev's appeal score with the headlines as context (without Jev: how many feeds named the player)."""
    from services import jev_client
    from services.ig_posts.questions import APPEAL_CRITERIA

    scores = {}
    if entries and jev_client.enabled():
        answers = jev_client.ask(
            {"audience": "Indian and global cricket fans on Instagram, this morning",
             "candidates": {e["question"].key: {"question": e["question"].text,
                                               "in the news": [h["title"] for h in e["headlines"]]} for e in entries}},
            {e["question"].key: {"type": "score", "criteria": APPEAL_CRITERIA,
                                 "instructions": f"Given today's headlines, how much would fans argue about: \"{e['question'].text}\"?"}
             for e in entries}, timeout=10.0) or {}
        scores = {k: float(v["score"]) for k, v in answers.items() if isinstance((v or {}).get("score"), (int, float))}
    for e in entries:
        e["appeal"] = scores.get(e["question"].key, float(len({h["source"] for h in e["headlines"]})))
        e["appeal_by"] = "jev" if e["question"].key in scores else "mentions"
    return sorted(entries, key=lambda e: -e["appeal"])
