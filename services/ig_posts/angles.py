"""
The angles a post can take on a question: one metric each, with which way is better, how it reads, and the family it
belongs to. services/ig_posts/planner.py has Jev score them for a question; the scorecard and bars draw them.

Families keep a post from saying the same thing five times (strike rate, boundary % and dot % are all "how fast"):
the planner takes at most two from one family.

    pace     how fast they score (or concede)
    value    what it's worth to the team: runs above average, win probability added, Impact (T20 Primer, men's T20)
    risk     how often they get out, or take wickets
    skill    control: how often the ball is hit or left in control
    volume   how much of it: sixes, wickets
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class Angle:
    id: str
    metric: str              # key on the context's rows (query-builder field, or derived in context.py)
    short: str               # scorecard column ("SR", "RAA/100")
    label: str               # in a sentence ("strike rate")
    family: str
    higher_better: bool
    format: str              # postVisuals fmt(): int, dec1, dec2, pct1, signed1, signed2
    description: str         # what Jev reads
    t20_only: bool = False   # Primer metrics: men's T20 from 2015, not The Hundred
    min_coverage: Optional[str] = None  # a tag whose coverage must pass (control)


BATTER: Tuple[Angle, ...] = (
    Angle("sr", "strike_rate", "SR", "strike rate", "pace", True, "dec1",
          "Strike rate: runs per 100 balls. How fast they score."),
    Angle("boundary", "boundary_percentage", "Bdry %", "boundary %", "pace", True, "pct1",
          "Share of balls hit for four or six. How often they find the rope."),
    Angle("dot", "dot_percentage", "Dot %", "dot-ball %", "pace", False, "pct1",
          "Share of balls they don't score off. Lower is better: how rarely they get stuck."),
    Angle("raa", "raa_per_100", "RAA/100", "runs above average per 100 balls", "value", True, "signed1",
          "Runs above what an average batter would score in the same situations, per 100 balls (game-state aware).",
          t20_only=True),
    Angle("impact", "impact_per_100", "Impact/100", "Impact per 100 balls", "value", True, "signed1",
          "Runs added to the team's projected total per 100 balls, including the value of not getting out.",
          t20_only=True),
    Angle("wpa", "wpa_per_100", "WPA/100", "win probability added per 100 balls", "value", True, "signed2",
          "Win probability added per 100 balls: how much their batting moved their team's chance of winning.",
          t20_only=True),
    Angle("bpd", "balls_per_dismissal", "Balls/out", "balls per dismissal", "risk", True, "dec1",
          "Balls faced per dismissal. Higher means harder to get out."),
    Angle("average", "average", "Avg", "average", "risk", True, "dec1", "Runs per dismissal."),
    Angle("control", "control_percentage", "Control", "control %", "skill", True, "pct1",
          "Share of balls played in control (the feed's tag). How rarely they're beaten or edge.",
          min_coverage="control"),
    Angle("sixes", "sixes_per_100", "6s/100", "sixes per 100 balls", "volume", True, "dec1",
          "Sixes per 100 balls. Raw hitting power."),
)

BOWLER: Tuple[Angle, ...] = (
    Angle("economy", "economy", "Econ", "economy", "pace", False, "dec2",
          "Runs conceded per over. Lower is better."),
    Angle("dot", "dot_percentage", "Dot %", "dot-ball %", "pace", True, "pct1",
          "Share of balls not scored off. Higher is better: pressure."),
    Angle("raa", "raa_per_100", "RAA/100", "runs saved per 100 balls", "value", True, "signed1",
          "Runs saved against an average bowler in the same situations, per 100 balls (game-state aware).",
          t20_only=True),
    Angle("wpa", "wpa_per_100", "WPA/100", "win probability added per 100 balls", "value", True, "signed2",
          "Win probability added per 100 balls bowled: how much their bowling moved their team's chance of winning.",
          t20_only=True),
    Angle("strike", "balls_per_dismissal", "Balls/wkt", "balls per wicket", "risk", False, "dec1",
          "Balls per wicket. Lower is better: how often they strike."),
    Angle("wickets_inns", "wickets_per_innings", "Wkts/inns", "wickets per innings", "volume", True, "dec2",
          "Wickets per innings bowled."),
    Angle("control", "control_percentage", "Beaten %", "share of balls the batter didn't control", "skill", False,
          "pct1", "Share of balls the batter played in control. Lower is better for the bowler: how often they beat the bat.",
          min_coverage="control"),
)

PAIR: Tuple[Angle, ...] = (
    Angle("average", "average", "Avg", "runs per dismissal", "risk", True, "dec1", "Partnership runs per wicket."),
    Angle("sr", "strike_rate", "SR", "strike rate", "pace", True, "dec1", "Partnership runs per 100 balls."),
    Angle("control", "control_percentage", "Control", "control %", "skill", True, "pct1",
          "Share of balls the pair played in control.", min_coverage="control"),
    Angle("boundary", "boundary_percentage", "Bdry %", "boundary %", "pace", True, "pct1",
          "Share of balls hit for four or six."),
    Angle("dot", "dot_percentage", "Dot %", "dot-ball %", "pace", False, "pct1", "Share of balls not scored off."),
    Angle("bpd", "balls_per_dismissal", "Balls/wkt", "balls per wicket", "risk", True, "dec1",
          "Balls the pair lasts per wicket."),
)

BY_ROLE: Dict[str, Tuple[Angle, ...]] = {"batter": BATTER, "bowler": BOWLER, "partnership": PAIR}


def available(role: str, fmt: str, leagues: Iterable[str] = ()) -> List[Angle]:
    """Angles that exist for this role and format (Primer metrics: men's T20 only, not The Hundred)."""
    primer = fmt == "T20" and not any("hundred" in str(l).lower() for l in leagues or ())
    return [a for a in BY_ROLE[role] if primer or not a.t20_only]


def by_id(role: str, angle_id: str) -> Angle:
    return next(a for a in BY_ROLE[role] if a.id == angle_id)
