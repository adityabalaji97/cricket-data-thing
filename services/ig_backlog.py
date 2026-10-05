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
import re
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

#: One week of slots, Monday first. Evergreen pillars are filled ahead; 'play' and 'reactive' stay open.
WEEK = ["debate", "reactive", "myth", "debate", "play", "reactive", "weird"]
EVERGREEN = ("debate", "myth", "weird")
#: Myth posts: published notes with a chart spec (services/ig_posts/myths.SPECS).
MYTH_POSTS = True
#: Debate posts from the generator: how many to make (the calendar takes what it needs, the rest is bench).
DEBATE_POSTS = 14
#: A player appears at most once in any SPREAD consecutive scheduled posts.
SPREAD = 5
DAYS = 30


def _q(**params) -> Dict[str, Any]:
    return {"gender": "male", "query_mode": "delivery", **params}


#: Curated evergreen ideas. `players` drives the spread rule for ideas whose subject is fixed; a leaderboard's
#: subject (its leader) is only known after the query runs, and is added then.
IDEAS: List[Dict[str, Any]] = [
    # Debate posts come from the question generator (services/ig_posts): many metrics, Jev-chosen, contested only.
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
    # Myth posts wait for charts of the hypothesis results (a text-only carousel says too little); see MYTH_POSTS.
    *[{"key": f"myth-note-{n}", "pillar": "myth", "note_id": n} for n in (34, 35, 36, 37, 38, 39, 40, 41, 42)],
]


#: Slide 1 of each carousel: the question the post answers, written by hand. A hook names no result (the chart
#: does), so it can't disagree with the data; a leaderboard's hook names nobody, since its leader can change.
HOOKS: Dict[str, str] = {
    "ipl-fastest-1000-balls": "Who got to 1,000 IPL runs in the fewest balls?",
    "ipl-fastest-100-wickets": "Who is the fastest to 100 IPL wickets?",
    "ipl-fastest-2000-balls": "Who got to 2,000 IPL runs in the fewest balls?",
    "odi-costliest-debut": "What's the most expensive ODI debut this century?",
    "odi-fastest-200-wickets": "Who is the fastest to 200 ODI wickets?",
    "odi-fastest-5000": "Who is the fastest to 5,000 ODI runs?",
    "odi-three-tons-innings": "How rare are three centuries in one ODI innings?",
    "odi-four-tons-match": "How often does one ODI produce four centuries?",
    "ipl-two-tons-innings": "Two centuries in one IPL innings: how often has it happened?",
    "odi-two-fivefors-match": "Two five-wicket hauls in one ODI: how rare is it?",
    "ipl-debut-runs": "What's the best IPL debut with the bat?",
}


def _kicker(item: Dict[str, Any]) -> str:
    """The small line above the hook: the competition or format ("IPL", "ODI", "T20")."""
    params = (item.get("planned") or {}).get("params") or {}
    if params.get("leagues"):
        return " · ".join(params["leagues"])
    if params.get("fmt"):
        return params["fmt"]
    idea = item.get("idea") or ""
    return next((k for k in ("IPL", "ODI", "T20I", "T20") if k in idea), "")


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
    if note["status"] != "published":
        # An unpublished note's findings haven't been reviewed: they don't go out on Instagram first.
        return {"status": "skipped", "note": f"note {note['id']} is a {note['status']}; publish it to use it"}
    return {"status": "resolved", "fact": fact, "snapshot": None, "warnings": [], "note_row": dict(note)}


def make(db: Session, item: Dict[str, Any], created_by: str = "ig-backlog") -> Dict[str, Any]:
    """Run one idea: {status, fact, snapshot, warnings}. Saves chart snapshots (callers stub that for a dry run)."""
    from services import content_ideas

    from services import ig_captions, ig_carousel

    if item["pillar"] == "myth":
        from services.ig_posts import myths

        result = _note_post(db, item)
        if result.get("status") != "resolved":
            return result
        note = result.pop("note_row")
        built = myths.build(note)  # charts of the result (services/ig_posts/myths.SPECS); None without a spec
        if not built:
            return {"status": "skipped", "note": f"no chart spec for note {note['id']} yet"}
        carousel = ig_carousel.save(db, built["slides"], built["title"], {"myth": built["slug"]}, created_by)
        result["fact"].update(carousel_id=carousel["id"], slides=len(built["slides"]), verdict=built["verdict"], render=True)
        result["snapshot"] = carousel
        result["caption"] = ig_captions.build(note["title"], built["verdict"], "myth",
                                              "a test written down before the analysis ran, on ball-by-ball data.")
        return result
    if item["pillar"] == "weird":
        record = _record_post(db, item, created_by)
        if record:
            return record
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
    hook = HOOKS.get(item["key"]) or item["idea"]
    slides = ig_carousel.for_fact(fact, result["snapshot"]["id"], hook, _kicker(item))
    carousel = ig_carousel.save(db, slides, fact["title"], {"ig": item["key"]}, created_by)
    fact.update(carousel_id=carousel["id"], slides=len(slides))
    caption = ig_captions.build(hook, fact["title"], item["pillar"], fact.get("method"), _players_of(item, fact),
                                _kicker(item))
    return {**result, "warnings": warnings, "caption": caption}


def _record_post(db: Session, item: Dict[str, Any], created_by: str) -> Optional[Dict[str, Any]]:
    """A career race ("fastest to 1,000 IPL runs") as a carousel drawn by the app (services/ig_posts/records.py):
    the race by balls, by innings, and how they got there. None for other record ideas (they keep the ranking form)."""
    from services import ig_captions, ig_carousel
    from services.ig_posts import records

    try:
        built = records.build(db, item["idea"])
    except Exception:  # a race the data can't build: fall back to the ranking form
        logger.exception("record post %s failed", item["key"])
        db.rollback()
        return None
    if not built:
        return None
    slides = ([{"type": "hook", "text": built["hook"], "kicker": built["kicker"], "sub": "By balls, by innings, and how they got there"}]
              + [{"type": "card", "card": c, "teams": None} for c in built["cards"]]
              + [{"type": "end", "heading": "Run it yourself",
                  "body": "Every number comes from ball-by-ball data. Ask your own question on the query builder: it's free."}])
    carousel = ig_carousel.save(db, slides, built["title"], {"record": item["key"]}, created_by)
    fact = {"kind": "record", "subject": None, "title": built["title"], "verdict": built["verdict"],
            "carousel_id": carousel["id"], "slides": len(slides), "render": True}
    caption = ig_captions.build(built["hook"], built["verdict"], "weird",
                                "careers counted from the first ball-by-ball season; rates over each career up to the milestone.",
                                built["players"], built["kicker"])
    return {"status": "resolved", "fact": fact, "snapshot": carousel, "warnings": [], "caption": caption}


def schedule(made: List[Dict[str, Any]], start: date, days: int = DAYS) -> List[Dict[str, Any]]:
    """Assign evergreen posts to the WEEK template from `start`; returns the calendar (one entry per day).

    Each slot takes the first unused post of its pillar (IDEAS order is the priority order) whose players haven't
    appeared in the previous SPREAD - 1 scheduled posts. With none left in its pillar (e.g. no published myth notes),
    an evergreen slot takes the first eligible post of another evergreen pillar; with none at all it stays open.
    """
    # Pools keep their order: weird and myth in IDEAS order, debates as the generator ranked them (fan appeal).
    pools = {p: [m for m in made if m["pillar"] == p] for p in EVERGREEN}
    used, recent, calendar = set(), [], []
    for d in range(days):
        day = start + timedelta(days=d)
        pillar = WEEK[day.weekday()]
        entry = {"date": day, "pillar": pillar, "post": None}
        if pillar in EVERGREEN:
            blocked = {p for post in recent[-(SPREAD - 1):] for p in post["players"]}
            ok = lambda m: m["key"] not in used and not blocked & set(m["players"])  # noqa: E731
            pick = (next((m for m in pools[pillar] if ok(m)), None)
                    or next((m for p in EVERGREEN if p != pillar for m in pools[p] if ok(m)), None))
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
        if item["pillar"] == "myth" and not MYTH_POSTS:
            continue
        result = make(db, item)
        if result.get("status") != "resolved":
            failed.append({"key": item["key"], "status": result.get("status"), "note": result.get("note")})
            continue
        made.append({"key": item["key"], "pillar": item["pillar"], "fact": result["fact"],
                     "snapshot_id": (result.get("snapshot") or {}).get("id"), "warnings": result.get("warnings") or [],
                     "players": _players_of(item, result["fact"]), "caption": result.get("caption")})
    if not keys or any(k.startswith("debate-") for k in keys):
        made += debate_posts(db, only=[k[len("debate-"):] for k in keys if k.startswith("debate-")] or None)
    calendar, bench = schedule(made, start, days)
    if not keys:
        for entry in calendar:  # play-along slots: an old Guess the Innings puzzle each (services/ig_posts/play.py)
            if entry["pillar"] == "play" and not entry["post"]:
                entry["post"] = play_post(db, entry["date"])
    if write:
        _write(calendar, bench, prune=not keys)  # a partial (--only) run must not clear everything else
    return {"calendar": calendar, "bench": bench, "failed": failed}


def play_post(db: Session, day: date, created_by: str = "ig-play") -> Optional[Dict[str, Any]]:
    """'Whose innings is this?' for the play-along slot on `day` (a puzzle from PUZZLE_LAG days earlier)."""
    from services import ig_captions, ig_carousel
    from services.ig_posts import play

    try:
        built = play.guess_innings_post(db, day)
    except Exception:  # the game's pool can be empty on a thin local database: leave the slot open
        logger.exception("play post for %s failed", day)
        db.rollback()
        return None
    if not built:
        return None
    carousel = ig_carousel.save(db, built["slides"], built["title"], {"play": built["puzzle"]}, created_by)
    fact = {"kind": "play", "subject": None, "title": built["title"], "answer": built["answer"], "puzzle": built["puzzle"],
            "carousel_id": carousel["id"], "slides": len(built["slides"]), "render": True}
    caption = ig_captions.build(built["hook"], "", "play",
                                "the innings, then a clue on every swipe; the answer is on the last slide.",
                                kicker=built["kicker"], extra_tags=["#cricketquiz"])
    return {"key": f"play-{day}", "pillar": "play", "fact": fact, "snapshot_id": carousel["id"], "warnings": [],
            "players": [built["answer"]], "caption": caption}


def debate_posts(db: Session, only: Optional[List[str]] = None, limit: int = DEBATE_POSTS) -> List[Dict[str, Any]]:
    """The generator's best contested questions as carousels (services/ig_posts): hook, Jev-chosen angles drawn by the
    app's own visuals, a split-verdict scorecard. Slides render after the pack is written (render_carousels)."""
    from services import ig_captions, ig_carousel
    from services.ig_posts import post as P, questions as Q

    out = []
    for entry in Q.generate(db, limit=limit, only=only, log=lambda m: logger.info(m)):
        q, built = entry["question"], P.build(entry)
        if not built:
            continue
        carousel = ig_carousel.save(db, built["slides"], q.text, {"debate": q.key}, "ig-debate")
        plan = entry["plan"]
        fact = {"kind": "debate", "subject": None, "title": q.text, "verdict": built["verdict"], "question": q.key,
                "leaders": built["leaders"], "angles": [a.id for a in plan["angles"]], "angle_scores": plan["scores"],
                "angles_by": plan["by"], "appeal": entry["appeal"], "appeal_by": entry["appeal_by"],
                "method": built["method"], "carousel_id": carousel["id"], "slides": len(built["slides"]),
                "render": True}
        caption = ig_captions.build(q.text, built["verdict"], "debate", built["method"], built["players"], q.kicker)
        out.append({"key": f"debate-{q.key}", "pillar": "debate", "fact": fact, "snapshot_id": carousel["id"],
                    "warnings": [], "players": built["players"], "caption": caption})
    return out


def render_carousels(posts: List[Dict[str, Any]], base: Optional[str] = None) -> Dict[str, Any]:
    """Render the slides of every post drawn by the app (fact.render) through /ig/<id>/<n> (services/ig_slides)."""
    from services import ig_slides

    from database import engine

    done, failed = 0, []
    with engine.connect() as conn:  # one connection for the "already rendered?" checks
        have = dict(conn.execute(text("SELECT carousel_id, COUNT(*) FROM ig_slide_images GROUP BY 1")).all())
    for post in posts:
        fact = post["fact"]
        if not fact.get("render"):
            continue
        if have.get(fact["carousel_id"], 0) >= fact["slides"]:
            done += 1  # same slides, same carousel (snapshots are keyed by their slides): already rendered
            continue
        result = ig_slides.render(fact["carousel_id"], fact["slides"], *([base] if base else []))
        if result["failed"]:
            failed.append({"key": post["key"], "failed": result["failed"]})
        else:
            done += 1
    return {"rendered": done, "failed": failed}


def _write(calendar: List[Dict[str, Any]], bench: List[Dict[str, Any]], prune: bool = True) -> None:
    """Upsert the posts (angle_key 'ig:<key>'). Posted or skipped packs keep their status and day. With prune, ready
    backlog packs this run didn't make leave the queue."""
    from database import engine

    rows = [(e["post"], e["date"]) for e in calendar if e["post"]] + [(b, None) for b in bench]
    with engine.begin() as conn:
        for post, day in rows:
            upsert_pack(conn, post, day)
        if not prune:
            return
        # Ready backlog packs this run no longer makes (an idea removed, a note unpublished) leave the queue as
        # 'expired' ('skipped' is the admin's own call): a later run that makes them again brings them back.
        conn.execute(text("""
            UPDATE content_packs SET status = 'expired', planned_for = NULL
            WHERE channel = 'instagram' AND source = 'ig-backlog' AND status = 'ready' AND NOT (angle_key = ANY(:keys))
        """), {"keys": [f"ig:{post['key']}" for post, _ in rows]})


def upsert_pack(conn, post: Dict[str, Any], day: Optional[date], source: str = "ig-backlog",
                post_by: Optional[Any] = None) -> None:
    """One Instagram pack: {key, pillar, fact, snapshot_id, warnings} planned for `day` (None = bench)."""
    fact = post["fact"]
    caption = post.get("caption") or (_caption(fact) if fact.get("kind") != "note"
                                      else "\n".join([fact["title"], "", fact.get("finding") or "", "", fact["method"]]))
    conn.execute(text("""
        INSERT INTO content_packs (match_id, snapshot_id, angle_key, title, first_comment, subreddit, flair, facts,
                                   rule_warnings, status, source, channel, planned_for, pillar, caption, post_by)
        VALUES (NULL, :s, :k, :t, NULL, NULL, NULL, CAST(:f AS jsonb), CAST(:w AS jsonb), 'ready', :src,
                'instagram', :d, :p, :c, :pb)
        ON CONFLICT (angle_key) WHERE angle_key IS NOT NULL DO UPDATE SET
            snapshot_id = EXCLUDED.snapshot_id, title = EXCLUDED.title, facts = EXCLUDED.facts,
            rule_warnings = EXCLUDED.rule_warnings, pillar = EXCLUDED.pillar, caption = EXCLUDED.caption,
            post_by = EXCLUDED.post_by,
            planned_for = CASE WHEN content_packs.status IN ('ready', 'expired') THEN EXCLUDED.planned_for
                               ELSE content_packs.planned_for END,
            -- A backlog post the queue retired comes back when a run makes it again; posted and skipped stay.
            status = CASE WHEN content_packs.status = 'expired' AND content_packs.source = 'ig-backlog'
                          THEN 'ready' ELSE content_packs.status END
    """), {"s": post["snapshot_id"], "k": f"ig:{post['key']}", "t": fact["title"],
           "f": json.dumps(fact, default=str), "w": json.dumps(post["warnings"]), "d": day,
           "p": post["pillar"], "c": caption, "src": source, "pb": post_by})


def preview_post(db: Session, venue: str, team1: str, team2: str, cards: Optional[List[str]], day: date, label: str,
                 team1_short: Optional[str] = None, team2_short: Optional[str] = None, fmt: str = "T20") -> Dict[str, Any]:
    """A match-day post (pillar 'reactive'): the chosen cards of the fixture's preview story, as the story's own card
    JSON, so each slide is drawn by the same component as the card in the app (/ig/:id/:n renders it)."""
    from services import ig_captions, ig_carousel
    from services.preview_cards import PreviewContext, build_story, context_params

    ctx = PreviewContext(db=db, venue=venue, team1=team1, team2=team2, fmt=fmt, gender="male",
                         team1_short=team1_short, team2_short=team2_short)
    params = context_params(ctx)
    story = build_story(ctx)
    built = {c["id"]: c for chapter in story["chapters"] for c in chapter["cards"]}
    if not cards:  # the story's best single-image cards (services/ig_posts/match.PREVIEW_CARDS)
        from services.ig_posts.match import pick_preview_cards

        cards = pick_preview_cards(story)
    chosen, titles, warnings = [], [], []
    for card_id in cards:
        card = built.get(card_id)
        if not card:  # a card this fixture doesn't have: leave it out, say so
            warnings.append(f"Card '{card_id}' isn't in this fixture's story.")
            continue
        chosen.append(card)
        titles.append(card["title"])
    if not chosen:
        return {"status": "failed", "note": "None of the chosen cards are in the story.", "warnings": warnings}
    fixture = story.get("fixture") or {}
    teams = [fixture.get("team1") or team1, fixture.get("team2") or team2]
    hook = f"{len(chosen)} things the data says before {team1} v {team2}"
    slides = ig_carousel.for_story_cards(chosen, teams, hook, label)
    carousel = ig_carousel.save(db, slides, hook, {"preview": params, "cards": cards, "day": str(day)}, "ig-preview")
    fact = {"kind": "preview", "subject": None, "title": hook, "card_titles": titles, "fixture": params,
            "carousel_id": carousel["id"], "slides": len(slides)}
    short1, short2 = team1_short or team1, team2_short or team2
    occasion = [ig_captions.tag(f"{short1}v{short2}")] + (["#TeamIndia"] if "India" in (team1, team2) else [])
    caption = ig_captions.build(f"{team1} v {team2} · {label}", "", "reactive",
                                "every card is from ball-by-ball data; the full preview story is free on Hindsight.",
                                kicker=label, extra_tags=occasion, body=[f"• {t}" for t in titles])
    slug = re.sub(r"[^a-z0-9]+", "-", f"{team1}-{team2}-{day}".lower()).strip("-")
    return {"status": "resolved", "key": f"preview-{slug}", "pillar": "reactive", "fact": fact,
            "snapshot_id": carousel["id"], "warnings": warnings, "caption": caption, "players": []}


def recap_pack(db: Session, match_id: str) -> Optional[Dict[str, Any]]:
    """The post-match carousel for a played match (services/ig_posts/match.recap_post), as a pack for the day after."""
    from services import ig_captions, ig_carousel
    from services.ig_posts.match import recap_post

    built = recap_post(db, match_id)
    if not built:
        return None
    slides = ([{"type": "hook", "text": built["hook"], "kicker": built["kicker"], "sub": "The swing, and who swung it"}]
              + [{"type": "card", "card": c, "teams": built["teams"]} for c in built["cards"]]
              + [{"type": "end", "heading": "The full scorecard",
                  "body": "Ball-by-ball win probability, Impact and every innings: free on Hindsight."}])
    carousel = ig_carousel.save(db, slides, built["title"], {"recap": str(match_id)}, "ig-recap")
    fact = {"kind": "recap", "subject": None, "title": built["title"], "verdict": built["verdict"], "match_id": str(match_id),
            "carousel_id": carousel["id"], "slides": len(slides), "render": True}
    a, b = built["teams"]
    occasion = [ig_captions.tag(f"{a}v{b}")] + (["#TeamIndia"] if "India" in (a, b) or "IND" in (a, b) else [])
    primer = any(c["id"] in ("wpa", "impact") for c in built["cards"])
    caption = ig_captions.build(built["hook"], built["verdict"], "reactive",
                                "win probability, Impact and runs saved are computed ball by ball (T20 Primer method)."
                                if primer else "from the ball-by-ball scorecard.",
                                built["players"], built["kicker"], occasion)
    return {"key": f"recap-{match_id}", "pillar": "reactive", "fact": fact, "snapshot_id": carousel["id"],
            "warnings": [], "caption": caption, "players": built["players"], "day": built["day"] + timedelta(days=1)}


def refresh(db: Session, keys: Iterable[str]) -> List[Dict[str, Any]]:
    """Remake these backlog posts in place: same pack, same planned day (a partial build() would reschedule them)."""
    from database import engine

    out = []
    for key in keys:
        item = next((i for i in IDEAS if i["key"] == key), None)
        row = db.execute(text("SELECT planned_for FROM content_packs WHERE angle_key = :k"), {"k": f"ig:{key}"}).first()
        if not item or not row:
            continue
        result = make(db, item)
        if result.get("status") != "resolved":
            continue
        post = {"key": key, "pillar": item["pillar"], "fact": result["fact"],
                "snapshot_id": (result.get("snapshot") or {}).get("id"), "warnings": result.get("warnings") or [],
                "players": _players_of(item, result["fact"]), "caption": result.get("caption")}
        with engine.begin() as conn:
            upsert_pack(conn, post, row[0])
        out.append(post)
    return out


#: A recap with no next meeting in sight (a one-off, or a series' last match) stays this long after the match.
RECAP_DAYS = 3


def recap_post_by(match_day: date, team1: str, team2: str, fixtures: List[Dict[str, Any]]) -> datetime:
    """When a recap stops being news: the start of the sides' next meeting (from the fixture list), else the end of
    RECAP_DAYS after the match. content_packs.expire() marks it expired after that."""
    pair = {team1, team2}
    starts = sorted(datetime.fromisoformat(f["start_utc"]) for f in fixtures
                    if f.get("start_utc") and {f.get("team1"), f.get("team2")} == pair
                    and datetime.fromisoformat(f["start_utc"]).date() > match_day)
    if starts:
        return starts[0]
    return datetime.combine(match_day + timedelta(days=RECAP_DAYS), datetime.max.time(), tzinfo=timezone.utc)


def render_pending(base: Optional[str] = None) -> Dict[str, Any]:
    """Render every ready Instagram pack whose carousel is missing slides (a failed or interrupted render)."""
    from database import engine

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT angle_key, facts FROM content_packs
            WHERE channel = 'instagram' AND status = 'ready' AND facts->>'render' = 'true'
        """)).all()
    return render_carousels([{"key": k, "fact": f} for k, f in rows], base)


def reels_pending() -> Dict[str, Any]:
    """A reel for every ready Instagram carousel that has its slides but no reel yet."""
    from database import engine
    from services import ig_slides

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT p.facts->>'carousel_id', (p.facts->>'slides')::int FROM content_packs p
            WHERE p.channel = 'instagram' AND p.status = 'ready' AND p.facts->>'carousel_id' IS NOT NULL
              AND NOT EXISTS (SELECT 1 FROM ig_reels r WHERE r.carousel_id = p.facts->>'carousel_id')
        """)).all()
    made = [cid for cid, n in rows if n and ig_slides.reel_from_stored(cid, n)]
    return {"made": len(made), "missing": len(rows) - len(made)}
