"""
ODI fantasy points (chunk A10).

Subclasses the T20 calculator and overrides only what the ODI rulebook changes. The scoring
logic itself is single-sourced in fantasy_points_v2.py — this file is deliberately data, not
behaviour, so the two formats cannot drift apart in how a milestone or a rate band is applied.

Values supplied by the project owner from the current published ODI table. Do not "correct"
these against a Dream11 marketing page: those describe a four as "4 runs +1 bonus" while the
detailed scoring tables list "Boundary +4", and this codebase follows the latter throughout —
verified against all twelve strike-rate and economy bands in the T20 set.

Differences from men's T20, all of them intentional:

  duck                 -2  ->  -3
  dot balls            every dot +1  ->  every 3rd dot +1
  wicket               25  ->  30
  haul thresholds      3/4/5 wkts  ->  4/5/6 wkts
  maiden over          12  ->  4
  batting milestones   to 100  ->  to 150 (adds 125 and 150)
  strike-rate minimum  10 balls  ->  20 balls
  economy minimum      2 overs   ->  5 overs

Boundary and six bonuses are unchanged at +4 and +6: the ODI table published alongside these
values omits them, and the owner's instruction was to keep the T20 convention rather than
invent one. Strike-rate and economy *bands* are likewise unchanged — only the minimum
workload before they apply differs.
"""

import logging

from fantasy_points_v2 import FantasyPointsCalculator


class ODIFantasyPointsCalculator(FantasyPointsCalculator):
    """Men's ODI scoring. Only the rulebook differs; the arithmetic is inherited."""

    def __init__(self):
        super().__init__()

        # Batting
        self.DUCK_PENALTY = -3
        self.RUNS_125_BONUS = 20
        self.RUNS_150_BONUS = 24
        # Descending, first match wins — so a 150 scores 24 and not 16.
        self.BATTING_MILESTONES = [
            (150, self.RUNS_150_BONUS),
            (125, self.RUNS_125_BONUS),
            (100, self.RUNS_100_BONUS),
            (75, self.RUNS_75_BONUS),
            (50, self.RUNS_50_BONUS),
            (25, self.RUNS_25_BONUS),
        ]

        # Bowling
        self.WICKET_POINT = 30
        self.DOTS_PER_POINT = 3
        self.MAIDEN_OVER_POINT = 4
        self.WICKETS_4_BONUS = 4
        self.WICKETS_5_BONUS = 8
        self.WICKETS_6_BONUS = 12
        # Thresholds shift up one relative to T20: a 3-for earns nothing in ODIs.
        self.WICKET_MILESTONES = [
            (6, self.WICKETS_6_BONUS),
            (5, self.WICKETS_5_BONUS),
            (4, self.WICKETS_4_BONUS),
        ]

        # Rate-based points apply later in a longer format.
        self.MIN_BALLS_FOR_SR = 20
        self.MIN_OVERS_FOR_ECONOMY = 5

        self.logger = logging.getLogger(__name__)


def get_calculator(fmt: str = "T20", gender: str = "male"):
    """Return the calculator for a format.

    Central lookup so callers do not each re-implement the mapping and quietly default an
    unknown format to T20 scoring — which is exactly how ODI previews came to show fantasy
    projections computed on T20 rules.
    """
    if (fmt or "").upper() == "ODI":
        return ODIFantasyPointsCalculator()
    if (fmt or "").upper() == "TEST":
        raise NotImplementedError(
            "Test fantasy scoring is not implemented; format_config declares no ruleset for it."
        )
    return FantasyPointsCalculator()
