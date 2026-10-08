"""
The Instagram posting plan: what goes out each day this week, when, and what to comment around it.

    week(db, start)        day by day: the posts planned (and what's already posted or skipped), with a time to post
    comment_kit(db, day)   one-line stats to paste as comments on big accounts' posts that day
    digest(db, day)        both, as the text of the morning digest (GET /digest/instagram, emailed by a routine)

Rules for the day (one feed post a day, spaced when there are two):
  - match days: the preview mid-afternoon, nothing else after 6 pm IST (the match has everyone's attention);
  - recaps the day after a match, around noon;
  - a 'Trending today' post only on a day with nothing else planned (the best one, by Jev's score);
  - evergreen posts (debate, myth, record, play-along) at their usual times.
Every stat in the comment kit is a card title from a queued post: a sentence written from the data.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

#: When to post, by kind of post (IST, Indian evenings and lunch breaks are the busy times).
TIMES = {"preview": "2 pm", "recap": "12 pm", "trend": "6 pm", "debate": "1 pm", "myth": "1 pm", "play": "10 am",
         "weird": "12 pm", "record": "12 pm", "spotlight": "6 pm"}
ORDER = {"play": 0, "recap": 1, "weird": 2, "record": 2, "debate": 3, "myth": 3, "preview": 4, "trend": 5, "spotlight": 5}


def _kind(row: Dict[str, Any]) -> str:
    key, src, facts = row["angle_key"] or "", row["source"] or "", row["facts"] or {}
    if src == "ig-trend" or facts.get("trending"):
        return "trend"
    if key.startswith("ig:preview-"):
        return "preview"
    if key.startswith("ig:recap-"):
        return "recap"
    if key.startswith("ig:spotlight-"):
        return "spotlight"
    return row["pillar"] or "debate"


def _rows(db: Session, start: date, end: date) -> List[Dict[str, Any]]:
    return [dict(r) for r in db.execute(text("""
        SELECT id, angle_key, source, pillar, title, status, planned_for, post_by, facts
        FROM content_packs
        WHERE channel = 'instagram' AND planned_for BETWEEN :s AND :e AND status IN ('ready', 'posted', 'skipped')
        ORDER BY planned_for, id
    """), {"s": start, "e": end}).mappings()]


def week(db: Session, start: date, days: int = 7) -> List[Dict[str, Any]]:
    """[{date, posts: [{id, kind, title, status, time, slides, reel}], trending_extra: n}] for each day."""
    from services import ig_season

    rows = _rows(db, start, start + timedelta(days=days - 1))
    out = []
    for d in range(days):
        day = start + timedelta(days=d)
        todays = [r for r in rows if r["planned_for"] == day]
        # Optional posts (a top-20 preview beyond the day's one) are made but not planned: listed as extras.
        extras = [r for r in todays if (r["facts"] or {}).get("optional") and r["status"] == "ready"]
        todays = [r for r in todays if r not in extras]
        main = [r for r in todays if _kind(r) != "trend"]
        trends = sorted((r for r in todays if _kind(r) == "trend"),
                        key=lambda r: -float((r["facts"] or {}).get("appeal") or 0))
        # A trending post fills a day with nothing else ready, or goes in when it was pinned to the plan
        # (facts.pinned); the rest stay in the queue, unused, and expire.
        pinned = [r for r in trends if (r["facts"] or {}).get("pinned")]
        free = trends[:1] if not [r for r in main if r["status"] != "skipped"] else []
        picked = main + pinned + [r for r in free if r not in pinned]
        picked.sort(key=lambda r: ORDER.get(_kind(r), 3))
        on = ig_season.focus(day, ig_season.major_series(db, day))
        out.append({
            "date": day.isoformat(),
            "focus": {"format": on[0], "label": on[1]} if on else None,
            "extras": [{"id": r["id"], "kind": _kind(r), "title": r["title"]} for r in extras],
            "posts": [{"id": r["id"], "kind": _kind(r), "title": r["title"], "status": r["status"],
                       "format": ig_season.post_format(r["facts"] or {}, r["angle_key"]),
                       "time": (r["facts"] or {}).get("post_time") or TIMES.get(_kind(r), "1 pm"), "slides": (r["facts"] or {}).get("slides"),
                       "carousel_id": (r["facts"] or {}).get("carousel_id"),
                       "note_id": (r["facts"] or {}).get("note_id")} for r in picked],
            "trending_extra": max(0, len(trends) - (1 if trends and trends[0] in picked else 0)),
        })
    return out


#: Card titles that only make sense next to their chart ("1 of 5 tests finds a clear effect"): not for comments.
NEEDS_CHART = re.compile(r"^(\d+ of \d+|None of|Only \d+|Other |How they|Nobody )", re.I)
#: "hits 20% of boundaries to midwicket (field: 20%)": no different from anyone, not worth a comment.
SAME_AS_FIELD = re.compile(r"(\d+)% of .*\(field: \1%\)")
RANK_NOTE = re.compile(r" \([^()]*: #\d+\)")
SCOPE = re.compile(r"\b(IPL|ODIs?|T20Is?|T20|BBL|PSL|SA20|since|20\d\d)\b")


def _card_titles(db: Session, carousel_ids: List[str]) -> List[str]:
    """Each card's title with its scope ("… (IPL since 2023)"), so it stands alone under someone else's post."""
    if not carousel_ids:
        return []
    rows = {r[0]: r[1] for r in db.execute(text("SELECT id, data FROM chart_snapshots WHERE id = ANY(:ids) AND kind = 'carousel'"),
                                           {"ids": carousel_ids}).all()}
    titles = []
    for cid in carousel_ids:  # in the order given (trending first)
        for slide in (rows.get(cid) or {}).get("slides", []):
            c = slide.get("card") or {}
            t = c.get("title")
            if not t or not any(ch.isdigit() for ch in t) or NEEDS_CHART.match(t) or SAME_AS_FIELD.search(t):
                continue
            scope = (c.get("sample") or "").split(" · ")[0].strip()
            # Only a real scope ("IPL since 2023"), not a sample note ("503 boundaries with a direction").
            if not SCOPE.search(scope) or scope[:1].isdigit():
                scope = ""
            t = RANK_NOTE.sub("", t)  # "(Kishan: #26)" only means something on its own post
            line = f"{t} · {scope}" if scope and scope.lower() not in t.lower() else t
            if line not in titles:
                titles.append(line)
    return titles


def comment_kit(db: Session, day: date, limit: int = 10) -> List[str]:
    """Stats for comments today: the card titles (each a number from the data) of today's and tomorrow's posts and
    today's trending drafts, the trending ones first (they're what people are talking about)."""
    rows = _rows(db, day, day + timedelta(days=1))
    trend_first = sorted(rows, key=lambda r: 0 if _kind(r) == "trend" else 1)
    ids = [(r["facts"] or {}).get("carousel_id") for r in trend_first if (r["facts"] or {}).get("carousel_id")]
    return _card_titles(db, ids)[:limit]


def digest(db: Session, day: date) -> Dict[str, Any]:
    plan = week(db, day, 7)
    today = plan[0]
    lines = [f"Hindsight on Instagram · {day:%a %d %b}", ""]
    todo = [p for p in today["posts"] if p["status"] == "ready"]
    if todo:
        lines.append("Post today:")
        lines += [f"  {p['time']} · {p['title']} ({p['slides']} slides)" for p in todo]
    else:
        lines.append("Nothing to post today." if not today["posts"] else "Today's posts are done.")
    lines += ["", "Open the admin Instagram tab: https://hindsightcricket.com/admin", ""]
    kit = comment_kit(db, day)
    if kit:
        lines.append("Comment kit (10 minutes on big accounts' posts; a stat, no links):")
        lines += [f"  • {k}" for k in kit]
        lines.append("")
    matches = _india_matches()
    if matches.get(day):
        lines.insert(2, f"Match today: {matches[day]}. Nothing new after 6 pm IST.")
    lines.append("Coming up:")
    for d in plan[1:]:
        when = date.fromisoformat(d["date"])
        posts = [p for p in d["posts"] if p["status"] == "ready"]
        line = "; ".join(f"{p['time']} {p['title'][:60]}" for p in posts) or "open (a trending post or a bench post)"
        if matches.get(when):
            line = f"{matches[when]} (the preview arrives the night before) · " + line
        lines.append(f"  {when:%a %d}: {line}")
    return {"date": day.isoformat(), "today": today, "week": plan, "comment_kit": kit, "text": "\n".join(lines)}


def _india_matches() -> Dict[date, str]:
    """{IST date: 'India v West Indies, 7 pm IST'} for India's fixtures in the scraper's window (best-effort)."""
    from datetime import datetime, timezone

    try:
        from services.fixture_scraper import fetch_upcoming_fixtures

        out = {}
        ist = timezone(timedelta(hours=5, minutes=30))
        for f in fetch_upcoming_fixtures(10):
            if "India" in (f.get("team1"), f.get("team2")) and f.get("start_utc"):
                start = datetime.fromisoformat(f["start_utc"]).astimezone(ist)
                out[start.date()] = f"{f['team1']} v {f['team2']}, {start:%-I %p} IST".replace("AM", "am").replace("PM", "pm")
        return out
    except Exception:
        return {}
