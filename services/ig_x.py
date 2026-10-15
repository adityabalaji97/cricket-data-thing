"""
An Instagram carousel as an X thread: one slide per tweet, each with its own line of text and the post's hashtags.
Every tweet carries the post's lead tag (the fixture, e.g. #INDvWI) and #CricketTwitter; the first mention of each
player in the thread ("Shai Hope", or "Hope" when only one of the post's players goes by it) becomes a hashtag
(#ShaiHope), so the thread shows up in each player's search.

    x_thread(slides, caption, chart_titles)  ->  [{"n": 1, "text": "...", "slide": 1}, ...]

Tweet 1 is the hook slide (marked as a thread), each reply is the next slide with the sentence it shows (a card's
title is its takeaway), and the last carries the link (hindsightcricket.com/links?utm_source=x, counted by the usage
report), or, when given, the post's own page: its scorecard, query or note (services/ig_links.py). Every tweet fits
X's 280 characters, counting a link as 23 as X does. Posting is by hand from the admin page.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

LIMIT = 280
LINK = "hindsightcricket.com/links?utm_source=x"
LINK_WEIGHT = 23  # X counts every link as 23 characters, whatever its length
MAX_TAGS = 2      # tags at the end of a tweet: more than two reads as spam on X (player tags sit in the text)
ALWAYS_TAG = "#CricketTwitter"
DEFAULT_TAGS = ["#cricket"]


def tags_from_caption(caption: str) -> List[str]:
    """The post's first hashtags, from the Instagram caption's last line (occasion tags lead, e.g. #INDvWI)."""
    tags = re.findall(r"#\w+", (caption or "").strip().splitlines()[-1] if caption else "")
    return tags[:MAX_TAGS] or DEFAULT_TAGS


def thread_tags(caption: str) -> List[str]:
    """The tags every tweet ends with: the post's lead tag and #CricketTwitter."""
    lead = [t for t in tags_from_caption(caption) if t.lower() != ALWAYS_TAG.lower()][:MAX_TAGS - 1]
    return lead + [ALWAYS_TAG]


#: Payload keys that hold a player's name in the post visuals (rows of bars, scorecards, dumbbells).
NAME_KEYS = ("name", "label", "batter", "bowler", "player")
TEAM_KEYS = ("team", "batting_team", "bowling_team", "legend", "series", "teams")


def _is_name(value: Any) -> bool:
    words = str(value).split()
    return 2 <= len(words) <= 4 and all(w[:1].isupper() and w.replace("-", "").replace("'", "").isalpha() for w in words)


def players_in(slides: List[Dict[str, Any]]) -> List[str]:
    """Player names drawn on the slides' cards (team names left out), in order of first appearance."""
    names: List[str] = []
    teams = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if k in TEAM_KEYS:
                    teams.update([v] if isinstance(v, str) else [t for t in v if isinstance(t, str)] if isinstance(v, list) else [])
                elif k in NAME_KEYS and isinstance(v, str) and _is_name(v) and v not in names:
                    names.append(v)
                else:
                    walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    for slide in slides:
        walk((slide.get("card") or {}).get("payload"))
        walk(slide.get("teams") or [])
    return [n for n in names if n not in teams]


def _aliases(names: List[str]) -> Dict[str, str]:
    """name or unique short form -> the full name: "Hope" -> "Shai Hope" unless two of the players are Hopes."""
    out = {n: n for n in names}
    for pos in (-1, 0):
        counts: Dict[str, int] = {}
        for n in names:
            counts[n.split()[pos]] = counts.get(n.split()[pos], 0) + 1
        for n in names:
            w = n.split()[pos]
            if counts[w] == 1 and w not in out:
                out[w] = n
    return out


def tag_players(texts: List[str], names: List[str]) -> List[str]:
    """Each player's first mention across the texts as a hashtag (#ShaiHope); later mentions stay as written."""
    aliases = _aliases(names)
    if not aliases:
        return texts
    # Longest first, so "Shai Hope" wins over "Hope"; whole words only, never inside an existing hashtag or handle.
    pattern = re.compile(r"(?<![#@\w])(" + "|".join(re.escape(a) for a in sorted(aliases, key=len, reverse=True)) + r")(?!\w)")
    seen = set()
    out = []
    for text in texts:
        def sub(m: "re.Match[str]") -> str:
            full = aliases[m.group(1)]
            if full in seen:
                return m.group(1)
            seen.add(full)
            return "#" + re.sub(r"[^A-Za-z0-9]", "", full)
        out.append(pattern.sub(sub, text))
    return out


URL = re.compile(r"(?:https?://)?hindsightcricket\.com\S*")


def _weight(text: str) -> int:
    text = URL.sub("x" * LINK_WEIGHT, text)
    return len(text) + sum(1 for ch in text if ord(ch) > 0xFFFF)  # emoji count twice


def _fit(body: str, suffix: str) -> str:
    """body + suffix within LIMIT: the body is cut at a word, never the suffix (numbering, tags, link)."""
    room = LIMIT - _weight(suffix)
    body = body.strip()
    if len(body) > room:
        body = body[:room - 1].rsplit(" ", 1)[0].rstrip(" ,;:·—-") + "…"
    return body + suffix


def _lines(text: Optional[str]) -> str:
    return " ".join(line.strip() for line in str(text or "").splitlines() if line.strip())


def slide_text(slide: Dict[str, Any], chart_titles: Dict[str, str]) -> str:
    kind = slide.get("type")
    if kind == "hook":
        kicker = slide.get("kicker")
        return f"{kicker}: {slide.get('text')}" if kicker else str(slide.get("text") or "")
    if kind == "card":
        card = slide.get("card") or {}
        title = str(card.get("title") or "")
        payload = card.get("payload") or {}
        if card.get("visual") == "recap_text":  # the words are the payload: the headline and its first bullets
            title = " ".join([payload.get("headline") or title, *(payload.get("bullets") or [])[:2]])
        elif card.get("visual") == "win_prob_line" and payload.get("bands"):  # the annotated overs
            title = title.split(":")[0] + ". " + ". ".join(f"Over {b['over']}: {b['text']} ({b['from']}→{b['to']}%)"
                                                          for b in payload["bands"])
        return f"{card['kicker']}: {title}" if card.get("kicker") else title
    if kind == "chart":
        return chart_titles.get(slide.get("snapshot_id") or "", "")
    if kind == "verdict":
        return f"Verdict: {slide.get('verdict')}. {_lines(slide.get('body'))}".strip()
    if kind == "end":
        return f"{slide.get('heading') or 'Run it yourself'}: {_lines(slide.get('body'))}".strip()
    heading = slide.get("heading")
    return f"{heading}: {_lines(slide.get('body'))}" if heading else _lines(slide.get("body"))


def x_thread(slides: List[Dict[str, Any]], caption: str, chart_titles: Optional[Dict[str, str]] = None,
             players: Optional[List[str]] = None, link: Optional[str] = None) -> List[Dict[str, Any]]:
    """link: the post's own page (services/ig_links.post_link) for the last tweet; default the bio page."""
    link = link or LINK
    tags = " ".join(thread_tags(caption))
    total = len(slides)
    names = list(dict.fromkeys([*(players or []), *players_in(slides)]))
    bodies = tag_players([slide_text(slide, chart_titles or {}) for slide in slides], names)
    tweets = []
    for i, body in enumerate(bodies, start=1):
        if i == 1:
            suffix = f"\n\nA thread 🧵 1/{total}\n{tags}"
        elif i == total:
            suffix = f"\n\nFull data, free: {link}\nData: @himganj153 & @TechRadar9\n{i}/{total} {tags}"
        else:
            suffix = f"\n\n{i}/{total} {tags}"
        tweets.append({"n": i, "slide": i, "text": _fit(body, suffix)})
    return tweets


def weight(text: str) -> int:
    """A tweet's length as X counts it (links as 23)."""
    return _weight(text)
