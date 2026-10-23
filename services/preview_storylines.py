"""
Talking points per fixture (MATCH_PREVIEW_STORYLINES_PLAN.md chunk 2): one model call turns a fixture's headlines
(fixture_news) into short claims fans are arguing about, each with its kind, players, team and the headlines behind it.
Jev scores how much fans would argue about each; the top TOP are stored 'pending' in fixture_storylines for the user
to approve, edit or drop (chunk 7). Nothing here is a number: the testers (chunk 3) answer each claim from the data.

The model sees headlines only (never article text, decision 3) and is told not to add outside knowledge. Players are
matched to Hindsight's names (player_identity, the two sides' recent XIs); a name it can't match is kept as written.
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import text

logger = logging.getLogger(__name__)

KINDS = ("selection", "form", "matchup", "conditions", "milestone", "record", "injury", "tactics")
MAX_HEADLINES = 60
MAX_POINTS = 8
TOP = 5
NEWS_DAYS = 5

PROMPT = """You read cricket headlines and list what people are arguing about before a match.

Match: {team1} v {team2}, {date}{series}.

Headlines (numbered; outlet in brackets):
{headlines}

List up to {n} talking points about this match: things fans, pundits or the teams are saying that could be checked
against ball-by-ball data. Each one:
- "claim": one plain sentence, at most 20 words, stating the point as it's being made (not your opinion). Name the
  player or side. No numbers that aren't in the headlines.
- "kind": one of {kinds}.
- "players": full names of the players the claim is ABOUT (not who said it; a captain's quote about his side is about
  the side), as written in the headlines.
- "team": the side it's about, if one.
- "sources": the numbers of the headlines that make this point.

Use only these headlines: no outside knowledge. Skip results, scores and schedules unless the point is an argument
about them ("India's chase was a record" is a point; "India won by 4 wickets" is not). Merge duplicates. Order by how
much they're being discussed.

Return JSON: {{"talking_points": [{{"claim": "...", "kind": "...", "players": ["..."], "team": "...", "sources": [1, 2]}}]}}"""


def headlines(db, fixture_key: str) -> List[Dict[str, Any]]:
    rows = db.execute(text("""
        SELECT title, outlet, url, published_at FROM fixture_news
        WHERE fixture_key = :k AND (published_at IS NULL OR published_at >= now() - make_interval(days => :d))
        ORDER BY published_at DESC NULLS LAST LIMIT :n
    """), {"k": fixture_key, "d": NEWS_DAYS, "n": MAX_HEADLINES}).mappings().all()
    return [dict(r) for r in rows]


def _squad_names(db, team1: str, team2: str) -> Dict[str, str]:
    """{lower name or surname: Hindsight name} for players in either side's last five XIs."""
    rows = db.execute(text("""
        SELECT DISTINCT mp.player FROM match_players mp JOIN matches m ON m.id = mp.match_id
        WHERE mp.team = ANY(:t) AND m.date >= CURRENT_DATE - 120
    """), {"t": [team1, team2]}).scalars().all()
    out: Dict[str, str] = {}
    surnames: Dict[str, List[str]] = {}
    for name in rows:
        out[name.lower()] = name
        surnames.setdefault(name.split()[-1].lower(), []).append(name)
    for s, names in surnames.items():
        if len(names) == 1:
            out.setdefault(s, names[0])
    return out


def match_players(names: List[str], squad: Dict[str, str]) -> List[str]:
    """Hindsight names for the players a point names: full name, else a surname unique in the two squads."""
    out = []
    for n in names or []:
        key = (n or "").strip().lower()
        hit = squad.get(key) or squad.get(key.split()[-1] if key else "")
        out.append(hit or n)
    return list(dict.fromkeys(x for x in out if x))


def extract(db, fixture: Dict[str, Any], log=print) -> List[Dict[str, Any]]:
    """The fixture's talking points from its headlines: [{claim, kind, players, team, sources}], best first."""
    from services import llm
    from services.ig_reel_v2 import _client

    hs = headlines(db, fixture["fixture_key"])
    if len(hs) < 3:
        return []
    listing = "\n".join(f"{i}. {h['title']} ({h['outlet'] or '?'})" for i, h in enumerate(hs, 1))
    prompt = PROMPT.format(team1=fixture["team1"], team2=fixture["team2"], date=fixture["match_date"],
                           series=f", {fixture['series']}" if fixture.get("series") else "", headlines=listing,
                           n=MAX_POINTS, kinds=", ".join(KINDS))
    model = llm.MODEL_STRONG
    resp = _client().chat.completions.create(model=model, response_format={"type": "json_object"},
                                             messages=[{"role": "user", "content": prompt}],
                                             **llm.chat_kwargs(model, 1500, temperature=0))
    try:
        raw = json.loads(resp.choices[0].message.content or "{}").get("talking_points") or []
    except (ValueError, AttributeError):
        log("  talking points: unreadable model output")
        return []
    squad = _squad_names(db, fixture["team1"], fixture["team2"])
    out = []
    for p in raw[:MAX_POINTS]:
        claim = (p.get("claim") or "").strip()
        kind = (p.get("kind") or "").strip().lower()
        if not claim or kind not in KINDS:
            continue
        src = [hs[i - 1] for i in p.get("sources") or [] if isinstance(i, int) and 1 <= i <= len(hs)]
        if not src:
            continue  # a point no headline makes is the model's, not the news'
        out.append({"claim": claim, "kind": kind, "players": match_players(p.get("players") or [], squad),
                    "team": (p.get("team") or "").strip() or None,
                    "sources": [{"title": s["title"], "outlet": s["outlet"], "url": s["url"],
                                 "published_at": s["published_at"].isoformat() if s["published_at"] else None} for s in src],
                    "model": model})
    return out


def rank(fixture: Dict[str, Any], points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Jev's appeal (how much fans would argue about it), else how many headlines make the point."""
    from services import jev_client, social_rules

    scores: Dict[str, float] = {}
    if points and jev_client.enabled():
        answers = jev_client.ask(
            {"audience": "Indian and global cricket fans before a match",
             "what draws strangers on Instagram": social_rules.section("Appeal"),
             "match": f"{fixture['team1']} v {fixture['team2']}",
             "candidates": {str(i): {"claim": p["claim"], "in the news": [s["title"] for s in p["sources"]]}
                            for i, p in enumerate(points)}},
            {str(i): {"type": "score", "criteria": "How much fans would argue about it before this match (0-10).",
                      "instructions": f"How much would fans argue about: \"{p['claim']}\"?"}
             for i, p in enumerate(points)}, timeout=10.0) or {}
        scores = {k: float(v["score"]) for k, v in answers.items() if isinstance((v or {}).get("score"), (int, float))}
    for i, p in enumerate(points):
        p["appeal"] = scores.get(str(i), float(len(p["sources"])))
        p["appeal_by"] = "jev" if str(i) in scores else "headlines"
    return sorted(points, key=lambda p: -p["appeal"])


def store(conn, fixture: Dict[str, Any], points: List[Dict[str, Any]]) -> int:
    """The top TOP as 'pending'; a point already reviewed keeps its review. Returns how many are new."""
    new = 0
    for n, p in enumerate(points[:TOP], 1):
        r = conn.execute(text("""
            INSERT INTO fixture_storylines (fixture_key, match_date, team1, team2, rank, claim, kind, players, team,
                                            sources, appeal, appeal_by, model)
            VALUES (:k, :d, :a, :b, :rank, :claim, :kind, CAST(:players AS jsonb), :team, CAST(:sources AS jsonb),
                    :appeal, :appeal_by, :model)
            ON CONFLICT (fixture_key, claim) DO UPDATE SET rank = EXCLUDED.rank, sources = EXCLUDED.sources,
                appeal = EXCLUDED.appeal
            RETURNING (xmax = 0) AS inserted
        """), {"k": fixture["fixture_key"], "d": fixture["match_date"], "a": fixture["team1"], "b": fixture["team2"],
               "rank": n, "claim": p["claim"], "kind": p["kind"], "players": json.dumps(p["players"]),
               "team": p["team"], "sources": json.dumps(p["sources"]), "appeal": p["appeal"],
               "appeal_by": p["appeal_by"], "model": p.get("model")})
        new += 1 if r.scalar() else 0
    return new


def fixtures_with_news(db, days: int = 3) -> List[Dict[str, Any]]:
    rows = db.execute(text("""
        SELECT fixture_key, match_date, team1, team2, MAX(series) AS series, COUNT(*) AS n FROM fixture_news
        WHERE match_date BETWEEN CURRENT_DATE AND CURRENT_DATE + :d GROUP BY 1, 2, 3, 4 ORDER BY 2
    """), {"d": days}).mappings().all()
    return [dict(r) for r in rows]


def approved(db, fixture_key: str) -> List[Dict[str, Any]]:
    """What a preview may use: the approved points, in the user's wording."""
    rows = db.execute(text("""
        SELECT id, COALESCE(edited_claim, claim) AS claim, kind, players, team, sources, appeal FROM fixture_storylines
        WHERE fixture_key = :k AND status = 'approved' ORDER BY rank
    """), {"k": fixture_key}).mappings().all()
    return [dict(r) for r in rows]


def fixture_info(fixture_key: str) -> Dict[str, Any]:
    """The fixture as the site lists it (venue, series), for the testers; the key's parts when it's no longer listed."""
    from services.fixture_scraper import fetch_upcoming_fixtures

    d, a, b = fixture_key.split("|")
    raw = fetch_upcoming_fixtures(20)
    rows = raw.get("fixtures", raw) if isinstance(raw, dict) else raw
    for fx in rows or []:
        if str(fx.get("date"))[:10] == d and {fx.get("team1"), fx.get("team2")} == {a, b}:
            return {**fx, "team1": a, "team2": b}
    return {"date": d, "team1": a, "team2": b, "venue": None}


def test_point(db, point_id: int, store: bool = True) -> Optional[Dict[str, Any]]:
    """Run a point's tester (services/storyline_testers.py); stored on the row unless store=False."""
    from services import storyline_testers as T

    row = db.execute(text("""
        SELECT id, fixture_key, COALESCE(edited_claim, claim) AS claim, kind, players, team FROM fixture_storylines
        WHERE id = :i
    """), {"i": point_id}).mappings().first()
    if not row:
        return None
    result = T.run(db, dict(row), fixture_info(row["fixture_key"]))
    if store:
        db.execute(text("UPDATE fixture_storylines SET test = CAST(:t AS jsonb), tested_at = now() WHERE id = :i"),
                   {"t": json.dumps(result, default=str), "i": point_id})
        db.commit()
    return result


LEDE_PROMPT = """Write the opening of a cricket match preview: {team1} v {team2}.

What's being said this week, and what the ball-by-ball data says about each:
{facts}

Two or three short sentences, at most 25 words each, for a phone screen. Lead with a player and a number. Say what
people are saying and what the numbers say, including where they disagree. Use only these facts and only these
numbers. No blame: describe what the numbers show, not failures or problems. No predictions, no hype, no adjectives
the numbers don't earn. House words: "runs above par", "strike rate", "an over". Return JSON {{"lede": "..."}}."""


def write_lede(db, fixture_key: str) -> Optional[str]:
    """The lede from the approved, tested points; sentences whose numbers aren't in the findings are dropped.
    Stored in fixture_ledes (removed when nothing is left)."""
    import re as _re

    from services import llm
    from services.ig_reel_v2 import _client
    from services.summary_check import _walk_numbers, numbers_supported

    rows = db.execute(text("""
        SELECT id, COALESCE(edited_claim, claim) AS claim, test FROM fixture_storylines
        WHERE fixture_key = :k AND status = 'approved' ORDER BY rank
    """), {"k": fixture_key}).mappings().all()
    facts = [r for r in rows if (r["test"] or {}).get("finding")]
    if not facts:
        db.execute(text("DELETE FROM fixture_ledes WHERE fixture_key = :k"), {"k": fixture_key})
        db.commit()
        return None
    d, a, b = fixture_key.split("|")
    listing = "\n".join(f"- Said: {r['claim']}\n  Data ({r['test']['verdict']}): {r['test']['finding']}" for r in facts)
    model = llm.MODEL_STRONG
    resp = _client().chat.completions.create(model=model, response_format={"type": "json_object"},
                                             messages=[{"role": "user", "content": LEDE_PROMPT.format(team1=a, team2=b, facts=listing)}],
                                             **llm.chat_kwargs(model, 400, temperature=0.2))
    try:
        lede = (json.loads(resp.choices[0].message.content or "{}").get("lede") or "").strip()
    except ValueError:
        lede = ""
    known = list(_walk_numbers([r["test"]["finding"] for r in facts] + [r["claim"] for r in facts]))
    kept, dropped = [], []
    for sentence in [x.strip() for x in _re.split(r"(?<=[.!?])\s+", lede) if x.strip()]:
        ok, _bad = numbers_supported(sentence, known)
        (kept if ok else dropped).append(sentence)
    text_ = " ".join(kept[:3])
    if not text_:
        db.execute(text("DELETE FROM fixture_ledes WHERE fixture_key = :k"), {"k": fixture_key})
        db.commit()
        return None
    db.execute(text("""
        INSERT INTO fixture_ledes (fixture_key, lede, point_ids, dropped, model) VALUES (:k, :l, CAST(:p AS jsonb), CAST(:d AS jsonb), :m)
        ON CONFLICT (fixture_key) DO UPDATE SET lede = EXCLUDED.lede, point_ids = EXCLUDED.point_ids,
            dropped = EXCLUDED.dropped, model = EXCLUDED.model, written_at = now()
    """), {"k": fixture_key, "l": text_, "p": json.dumps([r["id"] for r in facts]), "d": json.dumps(dropped), "m": model})
    db.commit()
    return text_
