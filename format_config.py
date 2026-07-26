"""Single source of truth for everything that differs between cricket formats.

The app was built for men's T20 only, so format-specific facts -- the powerplay ends after
over 6, an innings is 120 balls, the chase is innings 2 -- are scattered through the codebase
as inline literals. This module holds them once, so ODIs, women's T20s and Tests can be added
without re-deriving them in every service.

See MULTI_FORMAT_PLAN.md decision D2. The frontend consumes this through ``GET /formats``
rather than keeping its own copy, so there is no JS mirror to drift out of sync.

Terminology
-----------
``over`` values are **0-indexed everywhere**, matching the database columns. The first over of
an innings is over 0. Display labels ("Overs 1-10") are 1-indexed for humans and are carried
separately in ``label``.

Phases are given as inclusive ``(start_over, end_over)`` bounds. ``end_over`` of ``None`` means
"to the end of the innings", which matters for Tests, where innings have no fixed length.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Tuple

# Canonical values, matching the CHECK constraints in
# scripts/migrations/001_multi_format_columns.sql.
FORMATS = ("T20", "ODI", "TEST")
GENDERS = ("male", "female")

DEFAULT_FORMAT = "T20"
DEFAULT_GENDER = "male"


@dataclass(frozen=True)
class Phase:
    """One phase of an innings, as inclusive 0-indexed over bounds."""

    key: str
    label: str
    start_over: int
    end_over: Optional[int]  # None = to the end of the innings

    @property
    def display_overs(self) -> str:
        """Human-facing 1-indexed over range, e.g. '1-6' or '41+'."""
        if self.end_over is None:
            return f"{self.start_over + 1}+"
        return f"{self.start_over + 1}-{self.end_over + 1}"


@dataclass(frozen=True)
class FormatSpec:
    format: str
    gender: str
    label: str

    # Innings shape
    innings_count: int
    balls_per_innings: Optional[int]  # None for Tests -- innings end on wickets or declaration
    chase_innings: int  # the innings in which a target is being chased
    over_max: Optional[int]  # highest valid 0-indexed over; None = no fixed cap

    # Phase models. `phases` is the 3-way split used almost everywhere (and the one the
    # pp_/middle_/death_ stat columns hold); `phases_4` is the finer split the match preview
    # uses. Both are ordered.
    phases: Tuple[Phase, ...]
    phases_4: Tuple[Phase, ...]

    # Which fantasy ruleset applies, or None if the format has no meaningful fantasy scoring.
    fantasy_ruleset: Optional[str]

    # Benchmark bands used to colour/annotate stats. Strike rate is runs per 100 balls;
    # economy is runs per over. Both are (good_threshold, poor_threshold).
    sr_bands: Tuple[float, float]
    econ_bands: Tuple[float, float]

    # The legacy `deliveries` table only ever held men's T20 data from before this date.
    # Everything else lives in delivery_details regardless of date. See decision D5.
    legacy_table_before: Optional[date] = None

    # Populated at runtime from the database (earliest match we actually hold).
    min_date: Optional[date] = field(default=None, compare=False)

    @property
    def key(self) -> Tuple[str, str]:
        return (self.format, self.gender)

    @property
    def slug(self) -> str:
        """Stable identifier for URLs and localStorage, e.g. 'mens-t20', 'womens-t20'."""
        prefix = "mens" if self.gender == "male" else "womens"
        return f"{prefix}-{self.format.lower()}"


# ---------------------------------------------------------------------------------------
# Phase models
# ---------------------------------------------------------------------------------------
# T20: the familiar 6/9/5-over split. These bounds reproduce the inline literals that were
# scattered through the codebase (`over < 6`, `over < 15`), so migrating a call site to
# phase_case_sql() must not change a single result.
_T20_PHASES = (
    Phase("powerplay", "Powerplay", 0, 5),
    Phase("middle", "Middle", 6, 14),
    Phase("death", "Death", 15, 19),
)
_T20_PHASES_4 = (
    Phase("powerplay", "Powerplay", 0, 5),
    Phase("middle1", "Middle 1", 6, 9),
    Phase("middle2", "Middle 2", 10, 14),
    Phase("death", "Death", 15, 19),
)

# ODI: first powerplay is 10 overs, then the long middle, then the final 10 where the
# field restrictions loosen and scoring accelerates.
_ODI_PHASES = (
    Phase("powerplay", "Powerplay", 0, 9),
    Phase("middle", "Middle", 10, 39),
    Phase("death", "Death", 40, 49),
)
_ODI_PHASES_4 = (
    Phase("powerplay", "Powerplay", 0, 9),
    Phase("middle1", "Middle 1", 10, 24),
    Phase("middle2", "Middle 2", 25, 39),
    Phase("death", "Death", 40, 49),
)

# Tests: there is no powerplay, so the phases follow the ball instead. The second new ball
# becomes available at 80 overs, which is the natural third boundary.
#
# NOTE (recon, 2026-07-26): test_bbb.csv ships real `day` (1-5) and `session` (1-3) columns,
# now preserved by migration 002. Sessions are how Tests are actually structured, so the Phase C
# work should revisit whether these over-based buckets are the right model or whether phases
# should key off session instead. Left over-based for now because nothing consumes them yet.
_TEST_PHASES = (
    Phase("new_ball", "New ball", 0, 19),
    Phase("middle", "Old ball", 20, 79),
    Phase("death", "Second new ball", 80, None),
)
_TEST_PHASES_4 = (
    Phase("new_ball", "New ball", 0, 19),
    Phase("middle1", "Ball 20-49", 20, 49),
    Phase("middle2", "Ball 50-79", 50, 79),
    Phase("death", "Second new ball", 80, None),
)

# NB: the phase *keys* are deliberately reused across formats ("powerplay"/"middle"/"death",
# with Tests substituting "new_ball" for the first). The batting_stats/bowling_stats tables
# store phases as the columns pp_*/middle_*/death_*, so keeping the keys aligned means those
# columns work unchanged for every format -- only the labels and over ranges differ.
# See decision D3.


# ---------------------------------------------------------------------------------------
# The registry
# ---------------------------------------------------------------------------------------
_SPECS: Dict[Tuple[str, str], FormatSpec] = {
    ("T20", "male"): FormatSpec(
        format="T20",
        gender="male",
        label="Men's T20",
        innings_count=2,
        balls_per_innings=120,
        chase_innings=2,
        over_max=19,
        phases=_T20_PHASES,
        phases_4=_T20_PHASES_4,
        fantasy_ruleset="t20",
        sr_bands=(140.0, 110.0),
        econ_bands=(7.0, 9.0),
        legacy_table_before=date(2015, 1, 1),
    ),
    ("T20", "female"): FormatSpec(
        format="T20",
        gender="female",
        label="Women's T20",
        innings_count=2,
        balls_per_innings=120,
        chase_innings=2,
        over_max=19,
        phases=_T20_PHASES,
        phases_4=_T20_PHASES_4,
        fantasy_ruleset="t20",
        # Scoring rates in women's T20 run lower than the men's game, so the same colour
        # bands would mark almost everything as poor.
        sr_bands=(120.0, 95.0),
        econ_bands=(6.0, 8.0),
        # Women's data was never loaded into the legacy table.
        legacy_table_before=None,
    ),
    ("ODI", "male"): FormatSpec(
        format="ODI",
        gender="male",
        label="Men's ODI",
        innings_count=2,
        balls_per_innings=300,
        chase_innings=2,
        over_max=49,
        phases=_ODI_PHASES,
        phases_4=_ODI_PHASES_4,
        fantasy_ruleset="odi",
        sr_bands=(95.0, 70.0),
        econ_bands=(4.5, 6.5),
        legacy_table_before=None,
    ),
    ("TEST", "male"): FormatSpec(
        format="TEST",
        gender="male",
        label="Tests",
        innings_count=4,
        balls_per_innings=None,
        chase_innings=4,
        # Tests have no fixed innings length. The cap only exists to stop an unbounded
        # over filter reaching the API; ~200 overs is longer than any realistic innings.
        over_max=None,
        phases=_TEST_PHASES,
        phases_4=_TEST_PHASES_4,
        # Test fantasy scoring is a different game entirely and is out of scope; the
        # pipeline skips fantasy points for any format whose ruleset is None.
        fantasy_ruleset=None,
        sr_bands=(60.0, 35.0),
        econ_bands=(2.5, 4.0),
        legacy_table_before=None,
    ),
}

# Highest over the API will accept when a format declares no cap (Tests). A Test innings in the
# sample reached over 197, and the longest first-class innings on record run past 250, so this is
# set well clear of anything real rather than at the observed maximum.
UNBOUNDED_OVER_MAX = 299


# ---------------------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------------------
def get_format(
    fmt: Optional[str] = None,
    gender: Optional[str] = None,
) -> FormatSpec:
    """Look up a format spec, defaulting to men's T20.

    Raises ValueError on an unknown combination so a typo fails loudly instead of silently
    falling back to T20 and producing plausible-but-wrong numbers.
    """
    fmt = (fmt or DEFAULT_FORMAT).upper()
    gender = (gender or DEFAULT_GENDER).lower()

    spec = _SPECS.get((fmt, gender))
    if spec is None:
        available = ", ".join(f"{f}/{g}" for f, g in _SPECS)
        raise ValueError(f"Unknown format/gender combination {fmt}/{gender}. Available: {available}")
    return spec


def all_formats() -> List[FormatSpec]:
    """Every supported combination, in display order."""
    return list(_SPECS.values())


def effective_over_max(spec: FormatSpec) -> int:
    """The highest over the API accepts for this format."""
    return spec.over_max if spec.over_max is not None else UNBOUNDED_OVER_MAX
