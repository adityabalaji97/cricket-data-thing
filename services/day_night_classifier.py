"""
Day vs night match classifier.

Heuristic (IPL-only currently):
On a given (date, competition) group with multiple matches, the row with the
LOWER event_match_number is the day game; the other(s) are night. Single
matches default to 'night'. Non-IPL leagues stay None until the heuristic is
broadened to other day-friendly leagues (BBL, etc.).

Used by:
- scripts/classify_day_night_crosscheck.py (compares heuristics A and B)
- scripts/backfill_day_or_night.py (one-time backfill of existing matches)
- enhanced_loadMatches.py end-of-batch reconciler (new matches)
"""

from typing import Optional, Sequence, Mapping, Any

# Competitions the heuristic currently applies to. The matches table stores
# IPL under two strings historically — older rows use the full event name,
# newer rows use the abbreviation (per leagues_mapping in models.py). Treat
# both as IPL.
SUPPORTED_COMPETITIONS = {"IPL", "Indian Premier League"}


def classify_day_night_for_group(
    peer_matches: Sequence[Mapping[str, Any]],
    *,
    method: str = "auto",
) -> dict:
    """
    Classify a group of matches sharing the same (date, competition).

    Args:
        peer_matches: iterable of dicts with keys 'id', 'event_match_number'.
        method: 'auto' (default) uses event_match_number when all peers have
                it, falls back to match_id sort otherwise. Can also force
                'event_match_number' or 'match_id'.

    Returns:
        dict mapping match id -> 'day' | 'night'. Returns 'night' for singletons.
    """
    matches = list(peer_matches)
    if not matches:
        return {}

    if len(matches) == 1:
        return {matches[0]["id"]: "night"}

    if method == "auto":
        all_have_emn = all(m.get("event_match_number") is not None for m in matches)
        effective_method = "event_match_number" if all_have_emn else "match_id"
    else:
        effective_method = method

    if effective_method == "event_match_number":
        # Sort by event_match_number ascending. NULLs go last so they don't
        # spuriously claim the 'day' slot.
        def key(m):
            n = m.get("event_match_number")
            return (n is None, n if n is not None else 0)
        ordered = sorted(matches, key=key)
    elif effective_method == "match_id":
        # Lexicographic sort on match_id string. Cricsheet IDs are typically
        # numeric strings issued sequentially. Used when event_match_number
        # is missing (e.g., the 2026 IPL season at the time of writing).
        ordered = sorted(matches, key=lambda m: m["id"])
    else:
        raise ValueError(f"Unknown method: {effective_method}")

    labels: dict = {}
    for idx, m in enumerate(ordered):
        labels[m["id"]] = "day" if idx == 0 else "night"
    return labels


def classify_day_night(
    *,
    competition: Optional[str],
    peer_matches: Sequence[Mapping[str, Any]],
    method: str = "event_match_number",
) -> dict:
    """
    Top-level classifier. Returns labels only for supported competitions; None
    otherwise (caller should leave the column NULL).

    Args:
        competition: e.g. 'IPL', 'BBL', 'T20I'.
        peer_matches: all matches sharing the same (date, competition).
        method: heuristic to use.

    Returns:
        dict mapping match id -> 'day' | 'night'. Empty dict if competition
        is not supported.
    """
    if competition not in SUPPORTED_COMPETITIONS:
        return {}
    return classify_day_night_for_group(peer_matches, method=method)
