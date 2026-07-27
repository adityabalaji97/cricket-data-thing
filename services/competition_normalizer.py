"""Normalise the competition/event fields of the ball-by-ball feeds.

The four source files disagree about how to describe what a match belongs to, and the database
has a convention of its own that predates them:

* ``matches.competition`` (NOT NULL) is the **coarse bucket you filter by** -- ``T20I``, ``IPL``,
  ``Vitality Blast``. Every men's T20 international, World Cups included, is ``T20I``.
* ``matches.event_name`` (nullable) is the **specific event** -- "ICC Men's T20 World Cup".

The feeds do not follow that:

* the T20 file already ships ``competition='T20I'`` pre-normalised;
* the ODI file leaves ``competition`` **empty** for bilateral series (56% of matches) and puts the
  tournament name there for multi-team events;
* the Test file always populates ``competition``, but with per-series strings that vary in spelling
  ("Zimbabwe in BDESH Test", "Zimbabwe in Bangladesh Test").

Two consequences drive this module. First, feeding raw series names into ``competition`` would
flood the two competition dropdowns, which are built by ``SELECT DISTINCT`` with no curation
(``scripts/refresh_query_builder_metadata.py`` and ``main.py``'s ``/competitions``). Second, the
existing international check substring-matches ``competition``, so an empty value silently marks
every bilateral ODI as domestic ``'league'`` cricket.

``trophy_name`` turns out to be the most reliable signal: it collapses sponsor renames that
``competition`` splits apart -- "VB Series", "Carlton & United Series", "Commonwealth Bank Series"
and "Carlton Series" all share the trophy "Australian Tri Series (CB Series)".
"""

from __future__ import annotations

import logging
from typing import Iterable, Optional, Set

from models import INTERNATIONAL_TEAMS_RANKED

logger = logging.getLogger(__name__)

# The feeds use "-" (and sometimes "") for "no value".
_EMPTY = {"", "-", "n/a", "na", "none", "null"}

# The default bucket per format: what a bilateral series collapses to. Mirrors the existing
# convention where every men's T20 international is 'T20I' regardless of event.
DEFAULT_BUCKET = {
    "T20": "T20I",
    "ODI": "ODI",
    "TEST": "Test",
}

# Events that get their own bucket instead of collapsing into the default. Keep this list SHORT:
# every entry becomes a dropdown option, and the whole point is to avoid hundreds of series names.
# Keyed on trophy_name where possible, because it survives sponsor renames.
_MAJOR_EVENT_BY_TROPHY = {
    "world cup": "ICC World Cup",
    "icc world cup": "ICC World Cup",
    "icc champions trophy (icc knockout)": "ICC Champions Trophy",
    "icc champions trophy": "ICC Champions Trophy",
    "icc world test championship": "ICC World Test Championship",
    "asia cup": "Asia Cup",
}

# Fallback for feeds that name the event only in `competition`. Substring-matched, longest first,
# so "icc world cup" wins over "world cup".
_MAJOR_EVENT_BY_COMPETITION = {
    "icc world test championship": "ICC World Test Championship",
    "world test championship": "ICC World Test Championship",
    "icc champions trophy": "ICC Champions Trophy",
    "champions trophy": "ICC Champions Trophy",
    "icc world cup": "ICC World Cup",
    "cricket world cup": "ICC World Cup",
    "world cup": "ICC World Cup",
    "asia cup": "Asia Cup",
    "wtc": "ICC World Test Championship",
}

_COUNTRIES: Set[str] = {team.lower() for team in INTERNATIONAL_TEAMS_RANKED} | {
    # Full members and regulars that appear in the older ODI data but not in the T20 ranking list.
    "bermuda", "canada", "kenya", "hong kong", "jersey", "guernsey", "italy", "denmark",
    "east africa", "west indies", "united arab emirates", "papua new guinea",
}

# Competitions seen falling through to the default bucket, so a real gap in the curated maps
# shows up in the logs instead of silently collapsing. Process-lifetime only.
_unmapped_seen: Set[str] = set()


def _blank(value: Optional[str]) -> bool:
    return value is None or str(value).strip().lower() in _EMPTY


def _clean(value: Optional[str]) -> Optional[str]:
    return None if _blank(value) else str(value).strip()


def normalize_competition(
    raw_competition: Optional[str],
    tournament: Optional[str] = None,
    trophy_name: Optional[str] = None,
    fmt: str = "T20",
) -> str:
    """Resolve the coarse bucket that goes into ``matches.competition``.

    Resolution order: the curated major-event maps (trophy first, then competition), then the raw
    competition when it is already a recognised league name, then the format's default bucket.

    Never returns an empty string -- ``matches.competition`` is NOT NULL, and an empty value would
    also satisfy the ``competition != 'T20I'`` predicates that several endpoints use to mean
    "domestic cricket".
    """
    fmt = (fmt or "T20").upper()
    default = DEFAULT_BUCKET.get(fmt, fmt)

    trophy = _clean(trophy_name)
    if trophy:
        mapped = _MAJOR_EVENT_BY_TROPHY.get(trophy.lower())
        if mapped:
            return mapped

    competition = _clean(raw_competition)
    if competition:
        lowered = competition.lower()
        for needle in sorted(_MAJOR_EVENT_BY_COMPETITION, key=len, reverse=True):
            if needle in lowered:
                return _MAJOR_EVENT_BY_COMPETITION[needle]

    # The T20 feed already ships normalised buckets ('T20I', 'IPL', 'BBL'), so anything that
    # reaches here for T20 is a league name we should keep verbatim.
    if fmt == "T20" and competition:
        return competition

    # Everything else -- bilateral series, tri-series, one-off tournaments -- collapses to the
    # default bucket. The specific name is preserved in event_name, so nothing is lost.
    if competition and competition not in _unmapped_seen:
        _unmapped_seen.add(competition)
        logger.info(
            "competition_normalizer: %r (%s) collapsed to %r; specific name kept in event_name",
            competition, fmt, default,
        )

    return default


def resolve_event_name(
    raw_competition: Optional[str],
    tournament: Optional[str] = None,
) -> Optional[str]:
    """The specific event name for ``matches.event_name``.

    Prefers the more specific of the two fields. The ODI feed populates ``competition`` for
    multi-team events and ``tournament`` for bilateral series, and exactly one of them is
    meaningful per match.
    """
    return _clean(raw_competition) or _clean(tournament)


def international_competitions(fmt: str = "T20") -> List[str]:
    """Competition buckets that count as international, for filtering by competition name.

    ``is_international`` above classifies a *match* while syncing. This answers the different
    question a query needs: which values of ``delivery_details.competition`` are international
    for this format. They are not interchangeable -- the sync has team names to work with, a
    WHERE clause only has the bucket string.

    Needed because ``include_international`` filtered on the literal ``'T20I'``. For ODI the
    buckets are 'ODI', 'ICC World Cup', 'ICC Champions Trophy' and 'Asia Cup', so the filter
    matched nothing and the query builder returned zero rows for every ODI international.

    Men's T20 deliberately stays exactly as it was: every men's T20 international collapses
    into 'T20I' (verified -- no T20 row carries a major-event bucket), and widening it would
    change existing results for no gain.
    """
    fmt = (fmt or "T20").upper()
    default = DEFAULT_BUCKET.get(fmt, "T20I")
    if fmt == "T20":
        return [default]
    return [default, *sorted(set(_MAJOR_EVENT_BY_TROPHY.values()))]


def is_international(
    competition: Optional[str],
    teams: Optional[Iterable[str]] = None,
    fmt: str = "T20",
) -> bool:
    """Whether a match is international rather than domestic/franchise cricket.

    This decides ``matches.match_type``, which drives ``include_international``, the top-teams
    filter and ELO tiering.

    ODIs and Tests are international by definition -- they are only played between countries --
    so for those formats the team names settle it. T20 keeps the historical competition-name check
    unchanged, because changing it would move existing rows.
    """
    fmt = (fmt or "T20").upper()

    if fmt in {"ODI", "TEST"}:
        names = [str(t).strip().lower() for t in (teams or []) if t and str(t).strip()]
        if names:
            # Both sides must be recognised countries; an unknown name (an A-team or an invitational
            # XI) should not be promoted to international.
            return all(name in _COUNTRIES for name in names)
        # No usable team names: these formats are overwhelmingly international, so default to
        # True rather than silently classing a World Cup match as domestic.
        return True

    # Unchanged T20 behaviour.
    from sync_from_delivery_details import DeliveryDetailsSync  # noqa: PLC0415  (avoids a cycle)

    haystack = (competition or "").lower()
    return any(token.lower() in haystack for token in DeliveryDetailsSync.INTERNATIONAL_COMPETITIONS)


def unmapped_competitions() -> Set[str]:
    """Competitions that fell through to a default bucket this run -- audit before a big load."""
    return set(_unmapped_seen)
