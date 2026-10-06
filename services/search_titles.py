"""
Titles in the words people search: Google's autocomplete suggestions for a topic, then a title built around the
most-searched phrasing that is true of the page.

    suggestions("best finisher in ipl")  -> ["best finisher in ipl", "best finisher in ipl 2026", ...]
    topic("finisher", "IPL", ...)        -> "best finisher in ipl" (the first wording people actually search)
    match_title(...)                     -> "India vs West Indies 2nd T20 2026 preview: ..."

Autocomplete (suggestqueries.google.com) is unofficial and best-effort: on any failure the title falls back to the
plain wording. A suggested year only goes into a title when the page's data is that one year ("best finisher in IPL
2026" over data since 2023 would mislead); otherwise the scope says when ("since 2023").
"""
from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Iterable, List, Optional

import httpx

logger = logging.getLogger(__name__)

SUGGEST_URL = "https://suggestqueries.google.com/complete/search"
#: Suggestions about something else (tickets, live scores, fantasy, betting) don't describe a stats page.
NOT_US = re.compile(r"\b(tickets?|live|today|score ?card|streaming|channel|dream11|fantasy|betting|odds|time|venue|"
                    r"weather|squad|highlights video|kaun|kon|hindi)\b", re.I)
ACRONYMS = {"ipl": "IPL", "odi": "ODI", "odis": "ODIs", "t20": "T20", "t20i": "T20I", "t20is": "T20Is", "bbl": "BBL",
            "psl": "PSL", "sa20": "SA20", "wpa": "WPA", "raa": "RAA", "csk": "CSK", "rcb": "RCB", "mi": "MI", "kkr": "KKR"}


@lru_cache(maxsize=512)
def suggestions(seed: str) -> tuple:
    """Google's suggestions for a phrase (India, English), most-searched first; () on any failure."""
    try:
        r = httpx.get(SUGGEST_URL, params={"client": "firefox", "hl": "en-IN", "gl": "in", "q": seed.lower()},
                      timeout=5, headers={"User-Agent": "hindsight-titles/1.0 (+https://hindsightcricket.com)"})
        data = r.json()
        return tuple(s for s in data[1] if isinstance(s, str))
    except Exception as exc:  # unofficial endpoint: never block a title on it
        logger.info("autocomplete failed for %r: %s", seed, exc)
        return ()


def searched(seed: str) -> bool:
    """Is this exact wording something people search (it comes back as a suggestion of itself)?"""
    return seed.lower() in (s.lower() for s in suggestions(seed))


def first_searched(seeds: Iterable[str]) -> Optional[str]:
    return next((s for s in seeds if searched(s)), None)


#: Words that keep a capital in a sentence-case title (teams, countries, the first word aside).
PROPER = {"india", "west", "indies", "pakistan", "australia", "england", "south", "africa", "new", "zealand", "sri",
          "lanka", "bangladesh", "afghanistan", "ireland", "zimbabwe", "netherlands", "scotland", "nepal", "oman", "uae",
          "usa", "namibia"}


def title_case(phrase: str) -> str:
    """Sentence case, with acronyms (IPL, ODI, T20) and country names capitalised."""
    out = []
    for i, w in enumerate(phrase.split()):
        lw = w.lower()
        if lw in ACRONYMS:
            out.append(ACRONYMS[lw])
        elif i == 0 or lw in PROPER:
            out.append(lw[:1].upper() + lw[1:])
        else:
            out.append(lw)
    return " ".join(out)


def best_phrase(seed: str, years: Iterable[int] = (), prefer: Iterable[str] = ()) -> str:
    """The most-searched suggestion that extends the seed truthfully: no off-topic words, and a year only if it is
    one of `years` (the years the page covers alone). Falls back to the seed."""
    years = {str(y) for y in years}
    prefer = [p.lower() for p in prefer]
    good = []
    for s in suggestions(seed):
        sl = s.lower()
        if not sl.startswith(seed.lower()) or NOT_US.search(sl):
            continue
        found = set(re.findall(r"\b(?:19|20)\d\d\b", sl))
        if found and not found <= years:
            continue
        good.append(sl)
    for p in prefer:  # a preferred word (e.g. "preview") wins over plain popularity
        hit = next((s for s in good if p in s), None)
        if hit:
            return hit
    return good[0] if good else seed.lower()


# --- titles for the kinds of pages we publish ---------------------------------------------------------------

def match_seed(team1: str, team2: str, fmt: str, nth: Optional[int]) -> str:
    word = "t20" if fmt == "T20" else "odi"
    num = f"{nth}{'th' if 11 <= nth % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(nth % 10, 'th')} " if nth else ""
    return f"{team1} vs {team2} {num}{word}".lower()


def match_title(team1: str, team2: str, fmt: str, nth: Optional[int], year: int, kind: str, tail: str) -> str:
    """'India vs West Indies 2nd T20 2026 preview: Par about 185, no clear edge for chasing'.

    The match's year goes in when people search it that way (they usually do for a series match)."""
    seed = match_seed(team1, team2, fmt, nth)
    phrase = best_phrase(seed, years=[year], prefer=[str(year)])
    if str(year) not in phrase and any(str(year) in s for s in suggestions(seed)):
        phrase = f"{seed} {year}"
    head = title_case(phrase) + (" preview" if kind == "preview" else "")
    tail = tail.strip().rstrip(".")
    return f"{head}: {tail[:1].upper()}{tail[1:]}" if tail else head


#: Ways people search for a role, most specific first (the first one Google suggests as itself is used).
NOUN_SEEDS = {
    "finisher": ["best finisher in {s}"], "death bowler": ["best death bowler in {s}"],
    "new-ball bowler": ["best new ball bowler in {s}", "best powerplay bowler in {s}"],
    "powerplay batter": ["best powerplay batter in {s}", "best opener in {s}"],
    "middle-overs batter": ["best middle order batter in {s}", "best middle order batsman in {s}"],
    "middle-overs bowler": ["best middle overs bowler in {s}", "best spinner in {s}"],
    "player of spin": ["best player of spin in {s}", "best batsman against spin in {s}"],
    "player of pace": ["best player of pace in {s}", "best batsman against pace in {s}"],
    "chaser": ["best chaser in {s}"], "spinner": ["best spinner in {s}"], "fast bowler": ["best fast bowler in {s}"],
    "batter": ["best batter in {s}", "best batsman in {s}"], "partnership": ["best partnership in {s}"],
}
SCOPE_WORD = {"IPL": "ipl", "T20Is": "t20i", "ODIs": "odi"}


def debate_title(noun: str, kicker: str, scope_since: str, measures: List[str]) -> str:
    """'Best finisher in IPL since 2023: Impact, win probability and strike rate compared'."""
    s = SCOPE_WORD.get(kicker, kicker.lower())
    seeds = [t.format(s=s) for t in NOUN_SEEDS.get(noun, [f"best {noun} in {{s}}"])]
    phrase = first_searched(seeds) or seeds[0]
    listed = ", ".join(measures[:-1]) + f" and {measures[-1]}" if len(measures) > 1 else (measures[0] if measures else "")
    return f"{title_case(phrase)} {scope_since}: {listed} compared".replace("  ", " ")


def record_title(what: str, kicker: str) -> str:
    """'Fastest to 1000 runs in IPL: by balls and by innings' (records count every season they cover)."""
    m = re.match(r"([\d,]+) (\w+) (\w+)", what)  # "1,000 IPL runs"
    seed = f"fastest to {m.group(1).replace(',', '')} {m.group(3)} in {m.group(2).lower()}" if m else f"fastest to {what}".lower()
    return f"{title_case(seed)}: by balls and by innings"
