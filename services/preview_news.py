"""
News per fixture (MATCH_PREVIEW_STORYLINES_PLAN.md chunk 1): for each big fixture in the next few days, the headlines
being written about it, stored in fixture_news for the talking points (chunk 2).

Sources: Google News searches built from the fixture (the two sides, the format, the series), plus the general feeds
the trend radar reads (Reddit r/Cricket and r/IndiaCricket, Cricinfo) where a headline names both sides. Kept per
headline: title, outlet, link, published time and the feed's own one-line summary; never article text (decision 3).
Scope (decision 2): India, the top-10 sides and the major leagues, as the home page ranks them (LandingPage.jsx).
"""
from __future__ import annotations

import difflib
import html
import re
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import quote_plus

import httpx
from sqlalchemy import text

BIG_TEAMS = {"India", "Australia", "England", "South Africa", "New Zealand", "Pakistan", "Sri Lanka", "West Indies",
             "Afghanistan", "Bangladesh"}
BIG_SERIES = re.compile(r"\b(IPL|INDIAN PREMIER LEAGUE|WORLD CUP|ASIA CUP|CHAMPIONS TROPHY|BIG BASH|BBL|PSL|SA20|CPL|"
                        r"THE HUNDRED|MLC)\b", re.I)
DAYS_AHEAD = 3
UA = "hindsight-preview-news/1.0 (+https://hindsightcricket.com)"
GOOGLE = "https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
GENERAL = {"r/Cricket": "https://www.reddit.com/r/Cricket/new/.rss",
           "r/IndiaCricket": "https://www.reddit.com/r/IndiaCricket/new/.rss",
           "Cricinfo": "https://www.espncricinfo.com/rss/content/story/feeds/0.xml"}
#: Names a headline may use for a side (Google's searches use the full name).
SIDE_NAMES = {"New Zealand": ["New Zealand", "NZ", "Black Caps", "BlackCaps", "Kiwis"], "India": ["India", "IND", "Team India"],
              "Australia": ["Australia", "AUS", "Aussies"], "England": ["England", "ENG"], "South Africa": ["South Africa", "SA", "Proteas"],
              "Pakistan": ["Pakistan", "PAK"], "Sri Lanka": ["Sri Lanka", "SL"], "West Indies": ["West Indies", "WI", "Windies"],
              "Afghanistan": ["Afghanistan", "AFG"], "Bangladesh": ["Bangladesh", "BAN", "Tigers"]}
SAME_TITLE = 0.9          # near-identical titles (the same wire story at two outlets) count once
MAX_AGE_DAYS = 10         # older headlines aren't this match's talk


NOT_BIG_SERIES = re.compile(r"LEAGUE 2|CHALLENGE LEAGUE|QUALIFIER|SUB.?REGIONAL", re.I)  # "World Cup League 2" isn't a World Cup
MAX_PER_FIXTURE = 60


def is_big(fx: Dict[str, Any]) -> bool:
    series = fx.get("series") or ""
    return (fx.get("team1") in BIG_TEAMS or fx.get("team2") in BIG_TEAMS
            or (bool(BIG_SERIES.search(series)) and not NOT_BIG_SERIES.search(series)))


def fixtures(days: int = DAYS_AHEAD, today: Optional[date] = None) -> List[Dict[str, Any]]:
    """The big fixtures from today to `days` ahead (the site's own fixture list)."""
    from services.fixture_scraper import fetch_upcoming_fixtures

    today = today or date.today()
    raw = fetch_upcoming_fixtures(20)
    rows = raw.get("fixtures", raw) if isinstance(raw, dict) else raw
    out = []
    for fx in rows or []:
        try:
            d = date.fromisoformat(str(fx.get("date"))[:10])
        except ValueError:
            continue
        if today <= d <= today + timedelta(days=days) and is_big(fx):
            out.append({**fx, "date": d})
    return out


def fixture_key(fx: Dict[str, Any]) -> str:
    return f"{fx['date'].isoformat()}|{fx['team1']}|{fx['team2']}"


def queries(fx: Dict[str, Any]) -> List[str]:
    """Google News searches for a fixture: the sides together, with the format, and the series by name."""
    a, b = fx["team1"], fx["team2"]
    out = [f'"{a}" "{b}" cricket', f'"{a}" vs "{b}" {fx.get("format") or "T20"}']
    series = (fx.get("series") or "").strip()
    if series and len(series) < 60:
        out.append(f'"{series.title()}"')
    return out


def _tag(el, *names: str):
    """The first child with one of these names. (Not `a or b`: an element without children is falsy.)"""
    for name in names:
        found = next((c for c in el if c.tag.split("}")[-1] == name), None)
        if found is not None:
            return found
    return None


def _clean(s: Optional[str], limit: int = 300) -> Optional[str]:
    if not s:
        return None
    s = re.sub(r"<[^>]+>", " ", html.unescape(s))  # a feed summary may be HTML: keep its words only
    s = re.sub(r"\s+", " ", s).strip()
    return s[:limit] or None


def parse(feed: bytes, source: str, query: Optional[str] = None) -> List[Dict[str, Any]]:
    """RSS/Atom items as {title, outlet, url, published_at, summary, source, query}."""
    root = ET.fromstring(feed)
    out = []
    for el in root.iter():
        if el.tag.split("}")[-1] not in ("item", "entry"):
            continue
        t = _tag(el, "title")
        title = _clean(t.text if t is not None else None, 400)
        link_el = _tag(el, "link")
        url = (link_el.text or link_el.get("href")) if link_el is not None else None
        if not title or not url:
            continue
        outlet = None
        src = _tag(el, "source")
        if src is not None and src.text:  # Google News names the outlet, and appends it to the title
            outlet = src.text.strip()
            if title.endswith(f" - {outlet}"):
                title = title[: -len(outlet) - 3].strip()
        elif source == "Cricinfo":
            outlet = "ESPNcricinfo"
        elif source.startswith("r/"):
            outlet = source
        when = _tag(el, "pubDate", "updated", "published")
        published = None
        if when is not None and when.text:
            try:
                published = parsedate_to_datetime(when.text)
            except (TypeError, ValueError):
                try:
                    published = datetime.fromisoformat(when.text.replace("Z", "+00:00"))
                except ValueError:
                    published = None
        summ = _tag(el, "description", "summary", "content")
        summary = _clean(summ.text if summ is not None else None)
        if summary and summary.startswith(title[:40]):  # Google's description repeats the headline
            summary = None
        out.append({"title": title, "outlet": outlet, "url": url.strip(), "published_at": published,
                    "summary": summary, "source": source, "query": query})
    return out


def _names(team: str) -> List[str]:
    return SIDE_NAMES.get(team, [team])


def names_both(title: str, a: str, b: str) -> bool:
    def has(team):
        return any(re.search(rf"\b{re.escape(n)}\b", title) for n in _names(team))
    return has(a) and has(b)


def dedupe(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """One per link, and one per near-identical title (the newest kept)."""
    out: List[Dict[str, Any]] = []
    seen_urls = set()
    for it in sorted(items, key=lambda i: i["published_at"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True):
        if it["url"] in seen_urls:
            continue
        key = it["title"].lower()
        if any(difflib.SequenceMatcher(None, key, o["title"].lower()).ratio() >= SAME_TITLE for o in out):
            continue
        seen_urls.add(it["url"])
        out.append(it)
    return out


def fetch(fx: Dict[str, Any], general: Optional[Dict[str, List[Dict[str, Any]]]] = None, log=print) -> List[Dict[str, Any]]:
    """A fixture's headlines from the last MAX_AGE_DAYS, deduped, newest first."""
    items: List[Dict[str, Any]] = []
    with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=15) as client:
        for q in queries(fx):
            try:
                resp = client.get(GOOGLE.format(q=quote_plus(q)))
                items += parse(resp.content, "Google News", q)
            except Exception as exc:  # one search down doesn't stop the rest
                log(f"  google news '{q}' failed: {exc}")
    for source, rows in (general or {}).items():
        items += [r for r in rows if names_both(r["title"], fx["team1"], fx["team2"])]
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    items = [i for i in items if i["published_at"] is not None and i["published_at"] >= cutoff]
    return dedupe(items)[:MAX_PER_FIXTURE]


def general_feeds(log=print) -> Dict[str, List[Dict[str, Any]]]:
    """The general feeds once per run (Reddit rate-limits back-to-back requests)."""
    out = {}
    with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=15) as client:
        for source, url in GENERAL.items():
            try:
                resp = client.get(url)
                out[source] = parse(resp.content, source) if resp.status_code == 200 else []
                if resp.status_code != 200:
                    log(f"  feed {source}: HTTP {resp.status_code}")
            except Exception as exc:
                log(f"  feed {source} failed: {exc}")
                out[source] = []
            if "reddit.com" in url:
                time.sleep(8)
    return out


def store(conn, fx: Dict[str, Any], items: List[Dict[str, Any]]) -> int:
    """Upsert a fixture's headlines; returns how many were new."""
    new = 0
    for it in items:
        r = conn.execute(text("""
            INSERT INTO fixture_news (fixture_key, match_date, team1, team2, series, title, outlet, url, published_at,
                                      summary, source, query)
            VALUES (:k, :d, :a, :b, :s, :title, :outlet, :url, :published_at, :summary, :source, :query)
            ON CONFLICT (fixture_key, url) DO UPDATE SET fetched_at = now()
            RETURNING (xmax = 0) AS inserted
        """), {"k": fixture_key(fx), "d": fx["date"], "a": fx["team1"], "b": fx["team2"], "s": fx.get("series"), **it})
        new += 1 if r.scalar() else 0
    return new
