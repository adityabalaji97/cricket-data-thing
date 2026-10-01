"""
The content guidelines (docs/content_guidelines.md) as code: title checks, subreddit routing,
posting deadlines and the first comment for a content pack.

check_title() returns (errors, warnings). An error means the title breaks a rule the Reddit
study found decisive (a question, no number, a number not in the facts) and the pack is not
made with it; a warning is shown on the pack in the admin queue for a human to judge.
"""
import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlencode

from services.competition_aliases import canonical_competition
from services.summary_check import numbers_supported

SITE_URL = "https://hindsightcricket.com"
TITLE_MIN, TITLE_MAX = 60, 200

# Internationals between these sides, and these leagues, get packs; the rest draw no audience.
TOP_INTERNATIONAL = [
    "India", "Australia", "England", "West Indies", "New Zealand", "South Africa", "Pakistan",
    "Sri Lanka", "Bangladesh", "Afghanistan", "Ireland", "Zimbabwe",
]
MAIN_LEAGUES = {"IPL", "BBL", "PSL", "CPL", "SA20", "T20 Blast", "Men's Hundred", "MLC", "ILT20", "BPL", "LPL"}

# Subreddits for facts a side's own fans would share. Only ones seen in the Reddit study or
# long-established; a wrong name is worse than none.
TEAM_SUBREDDITS = {
    "India": "r/IndianCricket",
    "Royal Challengers Bengaluru": "r/RCB", "Royal Challengers Bangalore": "r/RCB",
}

ACRONYMS = {"IPL", "BBL", "PSL", "CPL", "ODI", "ODIS", "T20", "T20I", "T20IS", "WPA", "RAA", "SA20", "MLC",
            "ILT20", "BPL", "LPL", "UAE", "USA", "RCB", "CSK", "KKR", "SRH", "DC", "MI", "GT", "LSG", "PBKS", "RR"}
CLICKBAIT = re.compile(r"\b(insane|shocking|unbelievable|you won'?t believe|mind[- ]?blowing|jaw[- ]?dropping|crazy)\b", re.I)
QUESTION_START = re.compile(r"^(who|what|why|how|is|are|was|were|can|could|should|would|does|did|do|which|will)\b", re.I)


def in_scope(match: Dict[str, Any]) -> bool:
    """Is this men's match worth a pack: top internationals or a main league."""
    if (match.get("gender") or "male") != "male":
        return False
    competition = canonical_competition(match.get("competition"))
    if competition in ("ODI", "T20I") or match.get("match_type") == "international":
        return match.get("team1") in TOP_INTERNATIONAL and match.get("team2") in TOP_INTERNATIONAL
    return competition in MAIN_LEAGUES


def _known_numbers(facts: Iterable[Dict[str, Any]]) -> List[float]:
    from services.summary_check import _walk_numbers

    return list(_walk_numbers(list(facts)))


def check_title(title: str, facts: List[Dict[str, Any]], subject: Optional[str] = None) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    t = (title or "").strip()
    # A title that opens with its subject's name is not a question ("Will Jacks has made...").
    leads_with_subject = bool(subject) and t.lower().startswith(subject.lower())
    if t.endswith("?") or (QUESTION_START.match(t) and not leads_with_subject):
        errors.append("Title is a question; statements do five times better.")
    if not re.search(r"\d", t):
        errors.append("Title has no number.")
    # "1,000" is one number; the checker would otherwise read it as 1 and 000.
    ok, bad = numbers_supported(re.sub(r"(?<=\d),(?=\d{3}\b)", "", t), _known_numbers(facts))
    if not ok:
        errors.append(f"Numbers not in the facts: {', '.join(bad)}")
    if len(t) < TITLE_MIN:
        warnings.append(f"Short title ({len(t)} chars); self-contained titles of {TITLE_MIN}+ do better.")
    if len(t) > TITLE_MAX:
        warnings.append(f"Long title ({len(t)} chars); keep it under {TITLE_MAX}.")
    subject = (subject or "").replace(" & ", " and ")
    if subject and not t.lower().startswith(subject.lower()[:max(4, len(subject) // 2)]):
        warnings.append(f"Title does not lead with {subject}.")
    if CLICKBAIT.search(t) or "!!" in t:
        warnings.append("Clickbait wording.")
    shouty = [w for w in re.findall(r"\b[A-Z]{4,}\b", t) if w not in ACRONYMS]
    if shouty:
        warnings.append(f"ALL CAPS: {', '.join(shouty)}")
    return errors, warnings


def route(match: Dict[str, Any], fact: Dict[str, Any]) -> Dict[str, Any]:
    """Where to post: {subreddit, flair, alternates}. r/Cricket "Stats" unless a team's fans fit better."""
    alternates = []
    team = fact.get("team")
    if team and TEAM_SUBREDDITS.get(team):
        alternates.append(TEAM_SUBREDDITS[team])
    competition = canonical_competition(match.get("competition"))
    if competition == "IPL":
        alternates.append("r/ipl (frame it as a moment, not a stat)")
    return {"subreddit": "r/Cricket", "flair": "Stats", "alternates": alternates}


def post_by(match_date: date, now: Optional[datetime] = None) -> datetime:
    """18:00 UTC three days after the match, but never less than a day from now (data lands late)."""
    now = now or datetime.now(timezone.utc)
    deadline = datetime.combine(match_date + timedelta(days=3), time(18, 0), tzinfo=timezone.utc)
    floor = datetime.combine((now + timedelta(days=1)).date(), time(18, 0), tzinfo=timezone.utc)
    return max(deadline, floor)


def tracked_url(path: str, campaign: str, source: str = "reddit") -> str:
    return f"{SITE_URL}{path}?{urlencode({'utm_source': source, 'utm_campaign': campaign})}"


def first_comment(fact: Dict[str, Any], link: str) -> str:
    """The comment that carries the link: method, window and sample, then the source."""
    lines = [fact.get("method") or "", f"Full scorecard and ball-by-ball numbers: {link}",
             "Data: Hindsight (hindsightcricket.com), a free cricket stats site."]
    return "\n\n".join(l for l in lines if l)
