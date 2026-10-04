"""
Words on the cards, for an average viewer (MATCH_PREVIEW_VIZ_PLAN.md, "Copy rules").

Metric names on a card are plain; the info sheet carries the real name and its definition.
Formats without game-state metrics (everything but men's T20) fall back to plain stats.
"""
from __future__ import annotations

from datetime import date
from typing import Optional, Tuple

#: metric -> (plain name on the card, definition for the info sheet)
PLAIN = {
    "impact": ("runs added", "Impact: how much a ball moved the batting side's projected total (T20 Primer)."),
    "raa_bat": ("runs above an average batter", "RAA: runs above what an average batter makes in the same situations."),
    "raa_bowl": ("runs saved vs an average bowler", "RAA (bowling): runs saved compared with an average bowler in the same situations."),
    "wpa": ("win chances added", "WPA: how much a player changed his side's chance of winning; 1.0 is one match."),
    "leverage": ("pressure", "Leverage: how much was riding on each ball."),
    "strike_rate": ("strike rate", "Runs per 100 balls."),
    "economy": ("economy", "Runs conceded per over."),
}

HIGHER_IS_BETTER = "Higher is better"
LOWER_IS_BETTER = "Lower is better"

#: Game-state metrics (Impact, RAA, WAA, WPA) exist for men's T20 only.
PRIMER_FORMATS = ("T20",)


def has_primer(fmt: str, gender: str = "male") -> bool:
    return fmt in PRIMER_FORMATS and gender == "male"


def metric_for(fmt: str, gender: str, t20_metric: str, fallback: str) -> str:
    """The metric a card uses: the game-state one where it exists, the plain stat elsewhere."""
    return t20_metric if has_primer(fmt, gender) else fallback


def span(start: Optional[date], end: Optional[date]) -> str:
    """'2022–26', short enough to keep the footer on one line."""
    end_year = (end or date.today()).year
    if not start:
        return f"to {end_year}"
    if start.year == end_year:
        return str(end_year)
    return f"{start.year}–{str(end_year)[2:]}"


def short_venue(venue: str) -> str:
    return (venue or "").split(",")[0].strip()


_PLURALS = {"match": "matches", "innings": "innings", "six": "sixes"}


def plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {_PLURALS.get(word, word + 's')}"


def leader_line(team_a: str, a: int, team_b: str, b: int) -> Tuple[str, Optional[str]]:
    """'MI lead 4–1' / 'Level at 2–2', and the leading side (or None)."""
    if a == b:
        return f"Level at {a}–{b}", None
    if a > b:
        return f"{team_a} lead {a}–{b}", team_a
    return f"{team_b} lead {b}–{a}", team_b
