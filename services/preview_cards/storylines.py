"""
"The storylines" chapter (MATCH_PREVIEW_STORYLINES_PLAN.md chunk 4): the fixture's talking points the user approved in
/admin/storylines, each answered from the data (services/storyline_testers.py). A card: what's being said (the claim,
the headlines making it), the verdict, the tester's chart; titled by the data's finding, player and number first.
Nothing here is unapproved: a fixture with no approved points has no chapter, and the preview is as before. A point
with no data answer gets no card (it can still feed the lede).
"""
from __future__ import annotations

import hashlib
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from services.preview_cards.spec import Card, Info

VERDICT_RANK = {"not supported": 0, "supported": 1, "partly": 2, "context": 3, "too little data": 4}


def points(ctx) -> List[Dict[str, Any]]:
    """The fixture's approved points: its nearest date from yesterday on, the sides in either order."""
    store = ctx.__dict__.setdefault("_storylines", {})
    if "points" not in store:
        day = ctx.end or date.today()
        try:
            rows = ctx.db.execute(text("""
                SELECT id, fixture_key, COALESCE(edited_claim, claim) AS claim, kind, players, team, sources, test, rank,
                       match_date
                FROM fixture_storylines
                WHERE status = 'approved' AND match_date BETWEEN :a AND :b
                  AND ((team1 = ANY(:t1) AND team2 = ANY(:t2)) OR (team1 = ANY(:t2) AND team2 = ANY(:t1)))
                ORDER BY match_date, rank
            """), {"a": day - timedelta(days=1), "b": day + timedelta(days=7),
                   "t1": ctx.team_names[ctx.t1], "t2": ctx.team_names[ctx.t2]}).mappings().all()
        except Exception:  # no fixture_storylines table (a database before migration 028)
            ctx.db.rollback()
            rows = []
        first = rows[0]["match_date"] if rows else None
        store["points"] = [dict(r) for r in rows if r["match_date"] == first]
    return store["points"]


def fingerprint(ctx) -> Optional[str]:
    """Changes when an approval, edit or test changes, so the cached story is rebuilt (cached_story's key)."""
    ps = points(ctx)
    if not ps:
        return None
    return ",".join(f"{p['id']}:{(p.get('test') or {}).get('verdict')}:{p['claim'][:20]}" for p in ps) + "|" + hashlib.md5((lede(ctx) or "").encode()).hexdigest()[:8]


def lede(ctx) -> Optional[str]:
    ps = points(ctx)
    if not ps:
        return None
    try:
        return ctx.db.execute(text("SELECT lede FROM fixture_ledes WHERE fixture_key = :k"),
                              {"k": ps[0]["fixture_key"]}).scalar()
    except Exception:  # before migration 031
        ctx.db.rollback()
        return None


def players(ctx) -> List[str]:
    """Everyone the approved points are about: the rest of the preview moves their cards up (chunk 5)."""
    return sorted({n for p in points(ctx) for n in (p.get("players") or [])})


def cards(ctx) -> List[Card]:
    out, seen = [], set()
    text_ = lede(ctx)
    if text_:
        import re as _re

        sentences = [x.strip() for x in _re.split(r"(?<=[.!?])\s+", text_) if x.strip()]
        out.append(Card(
            id="storyline-lede", chapter="storylines", visual="recap_text", title=sentences[0],
            sample="From this week's headlines and the ball-by-ball data",
            payload={"headline": " ".join(sentences[1:]), "bullets": [f"Being said: {p['claim']}" for p in points(ctx)][:4]},
            n=1,
            info=Info(what="The talking points picked for this preview, and what the data says about them, in two or "
                           "three sentences. Every number in it is checked against the findings on the cards that follow."),
            relevance=10.0,
        ))
    for p in points(ctx):
        test = p.get("test") or {}
        if not test.get("card"):
            continue  # no data answer, no card (plan rule): such a point can still feed the lede (chunk 5)
        if test["finding"] in seen:
            continue  # two points the same numbers answer: the first carries them
        seen.add(test.get("finding"))
        inner = test.get("card")
        title = (test.get("finding") or p["claim"]).split(";")[0]
        sources = [{"title": s.get("title"), "outlet": s.get("outlet"), "url": s.get("url")} for s in (p.get("sources") or [])]
        outlets = sorted({s["outlet"] for s in sources if s.get("outlet")})
        out.append(Card(
            id=f"storyline-{p['id']}", chapter="storylines", visual="storyline",
            title=title,
            sample=(inner or {}).get("sample") or ("Being said by " + ", ".join(outlets[:3]) if outlets else "In the news"),
            payload={"said": p["claim"], "sources": sources, "verdict": test.get("verdict"), "finding": test.get("finding"),
                     "inner": {"visual": inner["visual"], "payload": inner["payload"]} if inner else None},
            n=1,
            info=Info(
                what="A talking point from this week's headlines, picked for this preview, and what the ball-by-ball "
                     "data says about it.",
                how_to_read="The verdict compares the claim with the numbers: supported, not supported, partly (about "
                            "usual), or too little data. Context points show the numbers without a verdict.",
                definitions=[("Sources", "; ".join(f"{s['title']} ({s['outlet']})" for s in sources[:4] if s.get("title")))],
                method="Headlines: Google News, Reddit, ESPNcricinfo. Numbers: Hindsight's query builder.",
            ),
            query_url=test.get("query_url"),
            # A finding that contradicts the talk leads ("everyone says X; the data says Y"), then the rest.
            relevance=3.0 - VERDICT_RANK.get(test.get("verdict") or "context", 3) * 0.1 - (p.get("rank") or 5) * 0.01,
        ))
    return out
