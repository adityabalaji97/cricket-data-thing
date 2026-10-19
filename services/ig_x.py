"""
An Instagram carousel as an X thread: one slide per tweet, each with its own line of text and the post's hashtags.
Every tweet carries the post's lead tag (the fixture, e.g. #INDvWI) and #CricketTwitter; the first mention of each
player in the thread ("Shai Hope", or "Hope" when only one of the post's players goes by it) becomes a hashtag
(#ShaiHope), so the thread shows up in each player's search.

    x_thread(slides, caption, chart_titles)  ->  [{"n": 1, "text": "...", "slide": 1}, ...]

Tweet 1 is the hook with the lead chart (slide 2) attached and its takeaway, marked as a thread (X gives native images
more reach than a text cover; lead_chart=False keeps the old hook-slide tweet); each reply is the next slide with the
sentence it shows (a card's title is its takeaway), and the last carries the link (hindsightcricket.com/links?utm_source=x, counted by the usage
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


PARTICLES = {"de", "du", "van", "von", "der", "den", "ul", "al", "da", "di", "le", "la", "ten"}


def _is_name(value: Any) -> bool:
    """"Shai Hope", "Quinton de Kock" (surname particles in lower case), not "Good length (SR 128)"."""
    words = str(value).split()
    return (2 <= len(words) <= 5 and words[0][:1].isupper()
            and all((w[:1].isupper() or w in PARTICLES) and w.replace("-", "").replace("'", "").isalpha() for w in words))


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
    from services.ig_posts.spotlight import short_name

    out = {n: n for n in names}
    forms = [lambda n: short_name(n), lambda n: n.split()[-1], lambda n: n.split()[0]]  # "de Kock", "Kock", "Quinton"
    for form in forms:
        counts: Dict[str, int] = {}
        for n in names:
            counts[form(n)] = counts.get(form(n), 0) + 1
        for n in names:
            w = form(n)
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


def _f(value: Any, kind: str = "dec1") -> str:
    from services.ig_posts.cards import fmt

    return fmt(value, kind)


def _first(name: str) -> str:
    from services.ig_posts.spotlight import short_name

    return short_name(name)


def _series_word(w: str) -> str:
    """"This match" -> "this match" mid-sentence; a player's name stays as it is."""
    return w if _is_name(w) else w[:1].lower() + w[1:]


def _figures(r: Dict[str, Any]) -> str:
    """"4.0-0-18" with 2 wickets -> "2/18 (4 ov)"."""
    parts = str(r.get("figures") or "").split("-")
    if len(parts) < 3:
        return str(r.get("figures") or "")
    overs = parts[0][:-2] if parts[0].endswith(".0") else parts[0]
    return f"{r.get('wickets') or 0}/{parts[2]} ({overs} ov)"


def details(card: Dict[str, Any]) -> List[str]:
    """Stat lines a tweet can carry beyond the slide's title: the numbers the slide draws as a chart (a leaderboard's
    values, a comparison's two sides, a scorecard's top lines). X has room the image doesn't need, so the thread
    reads as more than the slides' captions. Every number is from the card's own payload."""
    p = card.get("payload") or {}
    v = card.get("visual")
    lines: List[str] = []
    if v == "recap_text":
        lines = list(p.get("bullets") or [])
    elif v == "win_prob_line":
        lines = [f"Over {b['over']}: {b['text']} ({b['from']}→{b['to']}%)" for b in p.get("bands") or []]
    elif v == "metric_bars":
        rows = p.get("rows") or []
        fmt_ = (p.get("metric") or {}).get("format", "dec1")
        top = rows[:3] + [r for r in rows[3:] if r.get("highlight")][:1]
        lines = [f"{'→ ' if r.get('highlight') else ''}{r['name']} {_f(r['value'], fmt_)}"
                 + (f" ({r['detail']})" if r.get("detail") else "") for r in top]
    elif v == "scatter_plus":
        x, y = p.get("x") or {}, p.get("y") or {}
        ranked = sorted((pt for pt in p.get("points") or [] if pt.get("label") or pt.get("highlight")),
                        key=lambda pt: (pt.get("label") or 99))[:3]
        lines = [f"{pt['name']}: {_f(pt['y'], y.get('format', 'dec1'))} {y.get('label', '')}, "
                 f"{_f(pt['x'], x.get('format', 'dec1'))} {x.get('label', '')}" for pt in ranked]
    elif v == "deep_compare":
        a, b = (_series_word(w) for w in (p.get("series") or ["", ""])[:2])
        fmt_ = (p.get("metric") or {}).get("format", "dec1")
        lines = [f"{r['label']}: {_f(r['subject'], fmt_)} {a} v {_f(r['field'], fmt_)} {b}"
                 for r in p.get("rows") or [] if r.get("field") is not None]
    elif v == "pair_dumbbell":
        a, b = (p.get("series") or ["", ""])[:2]
        fmt_ = p.get("format", "dec1")
        lines = [f"{_first(r['label'])}: {_f(r['a'], fmt_)} {a}, {_f(r['b'], fmt_)} {b}" for r in p.get("rows") or []]
    elif v == "score_race":
        series, mark = p.get("series") or [], p.get("mark")
        for o in (6, 10):
            if mark and o < mark and all(len(s_["values"]) >= o for s_ in series):
                lines.append(f"After {o}: " + ", ".join(f"{s_['team']} {s_['values'][o - 1]}/{s_['wickets'][o - 1]}"
                                                       for s_ in series))
    elif v == "innings_scorecard":
        bats = sorted(p.get("batting") or [], key=lambda r: -(r.get("runs") or 0))[:3]
        bowls = sorted(p.get("bowling") or [], key=lambda r: -(r.get("wickets") or 0))[:2]
        imp = lambda r: f", {_f(r['impact'], 'signed1')}" if r.get("impact") is not None else ""  # noqa: E731
        # Full names: a scorecard's "Rahul" could be either Rahul in the thread (and the hashtag needs the full name).
        lines = [f"{r['name']} {r['runs']}{'*' if r.get('not_out') else ''} ({r['balls']}){imp(r)}" for r in bats]
        lines += [f"{r['name']} {_figures(r)}{imp(r)}" for r in bowls]
    elif v == "scorecard":
        metrics = p.get("metrics") or []
        for r in (p.get("rows") or [])[:3]:
            vals = ", ".join(f"{m['label']} {_f((r.get('values') or {}).get(m['key']), m.get('format', 'dec1'))}"
                             for m in metrics[:3])
            lines.append(f"{r['name']}: {vals}")
    if not lines and card.get("help") and any(ch.isdigit() for ch in str(card["help"])):
        lines = [str(card["help"])]  # a note with numbers in it; never the chart's reading instructions
    title = str(card.get("title") or "")
    return [l for l in lines if l and l.rstrip(".") not in title]


def slide_text(slide: Dict[str, Any], chart_titles: Dict[str, str]) -> str:
    """The slide's own sentence: a card's title (its takeaway), the hook, a chart's title."""
    kind = slide.get("type")
    if kind == "hook":
        kicker = slide.get("kicker")
        return f"{kicker}: {slide.get('text')}" if kicker else str(slide.get("text") or "")
    if kind == "card":
        card = slide.get("card") or {}
        title = str(card.get("title") or "")
        payload = card.get("payload") or {}
        if card.get("visual") == "recap_text":  # the words are the payload: the headline (bullets are its details)
            title = payload.get("headline") or title
        elif card.get("visual") == "win_prob_line" and payload.get("bands"):
            title = title.split(":")[0] + "."
        return f"{card['kicker']}: {title}" if card.get("kicker") else title
    if kind == "chart":
        return chart_titles.get(slide.get("snapshot_id") or "", "")
    if kind == "verdict":
        return f"Verdict: {slide.get('verdict')}. {_lines(slide.get('body'))}".strip()
    if kind == "end":
        return f"{slide.get('heading') or 'Run it yourself'}: {_lines(slide.get('body'))}".strip()
    heading = slide.get("heading")
    return f"{heading}: {_lines(slide.get('body'))}" if heading else _lines(slide.get("body"))


def slide_lines(slide: Dict[str, Any]) -> List[str]:
    if slide.get("type") == "hook":
        return [str(slide["sub"])] if slide.get("sub") else []
    if slide.get("type") == "card":
        return details(slide.get("card") or {})
    return []


def _fit_lines(head: str, lines: List[str], suffix: str) -> str:
    """The head, then as many whole stat lines as fit with the suffix (a line is dropped, never cut)."""
    body = head.strip()
    for line in lines:
        trial = f"{body}\n{line}"
        if _weight(trial + suffix) > LIMIT:
            break
        body = trial
    return _fit(body, suffix)


def x_thread(slides: List[Dict[str, Any]], caption: str, chart_titles: Optional[Dict[str, str]] = None,
             players: Optional[List[str]] = None, link: Optional[str] = None, lead_chart: bool = True) -> List[Dict[str, Any]]:
    """link: the post's own page (services/ig_links.post_link) for the last tweet; default the bio page. Each tweet is
    the slide's sentence plus the stat lines that fit (details())."""
    link = link or LINK
    tags = " ".join(thread_tags(caption))
    # (slide number, sentence, stat lines) per tweet: with lead_chart, the hook rides on the lead card's tweet.
    units = [(i, slide_text(s, chart_titles or {}), slide_lines(s)) for i, s in enumerate(slides, start=1)]
    hero_card = (slides[0].get("hero") or {}).get("card") if slides and slides[0].get("type") == "hook" else None
    if lead_chart and hero_card:  # the cover carries the lead chart (services/ig_cover.py): tweet 1 shows the cover
        hook = str(slides[0].get("text") or "").strip()
        units[0] = (1, f"{hook}\n\n{hero_card.get('title', '')}", details(hero_card))
    elif lead_chart and len(slides) > 2 and slides[0].get("type") == "hook" and slides[1].get("type") == "card":
        hook = str(slides[0].get("text") or "").strip()
        units = [(2, f"{hook}\n\n{slide_text(slides[1], chart_titles or {})}", slide_lines(slides[1]))] + units[2:]
    total = len(units)
    names = list(dict.fromkeys([*(players or []), *players_in(slides)]))
    suffixes = []
    for i in range(1, total + 1):
        if i == 1:
            suffixes.append(f"\n\nA thread 🧵 1/{total}\n{tags}")
        elif i == total:
            suffixes.append(f"\n\nFull data, free: {link}\nData: @himganj153 & @TechRadar9\n{i}/{total} {tags}")
        else:
            suffixes.append(f"\n\n{i}/{total} {tags}")
    # Which stat lines fit is settled first, then players are tagged across what's left: a line dropped for length
    # mustn't use up a player's first mention (a hashtag is never longer than the name it replaces).
    bodies = [_fit_lines(head, lines, sfx)[: -len(sfx)] for (_n, head, lines), sfx in zip(units, suffixes)]
    tagged = tag_players(bodies, names)
    tweets = [{"n": i, "slide": unit[0], "text": _fit(body, sfx)}
              for i, (unit, body, sfx) in enumerate(zip(units, tagged, suffixes), start=1)]
    return tweets


def weight(text: str) -> int:
    """A tweet's length as X counts it (links as 23)."""
    return _weight(text)
