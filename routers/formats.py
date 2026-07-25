"""Exposes format_config to the frontend.

The frontend fetches this once at boot and threads the result through FormatContext, so the
phase boundaries, over caps and innings counts have exactly one definition (format_config.py)
rather than a hand-maintained JS copy that drifts.

Availability is data-driven: a format only reports ``available: true`` once matches for it
actually exist, so the UI can show Tests as "coming soon" without a separate feature flag.
"""

from __future__ import annotations

from datetime import date
from typing import Dict, Optional, Tuple

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_session
from format_config import Phase, all_formats, effective_over_max

router = APIRouter(prefix="/formats", tags=["formats"])

# Coverage changes only when a data load runs, so a process-lifetime cache is plenty and
# saves a GROUP BY over `matches` on every page load.
_coverage_cache: Optional[Dict[Tuple[str, str], Dict]] = None


def _load_coverage(db: Session) -> Dict[Tuple[str, str], Dict]:
    global _coverage_cache
    if _coverage_cache is not None:
        return _coverage_cache

    rows = db.execute(
        text(
            """
            SELECT format, gender,
                   MIN(date) AS min_date,
                   MAX(date) AS max_date,
                   COUNT(*)  AS match_count
            FROM matches
            GROUP BY format, gender
            """
        )
    ).mappings().all()

    _coverage_cache = {
        (row["format"], row["gender"]): {
            "min_date": row["min_date"],
            "max_date": row["max_date"],
            "match_count": row["match_count"],
        }
        for row in rows
    }
    return _coverage_cache


def reset_coverage_cache() -> None:
    """Call after a data load so newly added formats appear without a restart."""
    global _coverage_cache
    _coverage_cache = None


def _phase_payload(phase: Phase) -> Dict:
    return {
        "key": phase.key,
        "label": phase.label,
        "start_over": phase.start_over,
        "end_over": phase.end_over,
        "display_overs": phase.display_overs,
    }


@router.get("")
def list_formats(db: Session = Depends(get_session)) -> Dict:
    """Every supported format, with its phase model, limits and data coverage."""
    coverage = _load_coverage(db)
    payload = []

    for spec in all_formats():
        stats = coverage.get(spec.key, {})
        match_count = stats.get("match_count", 0) or 0
        min_date: Optional[date] = stats.get("min_date")
        max_date: Optional[date] = stats.get("max_date")

        payload.append(
            {
                "format": spec.format,
                "gender": spec.gender,
                "slug": spec.slug,
                "label": spec.label,
                "innings_count": spec.innings_count,
                "balls_per_innings": spec.balls_per_innings,
                "chase_innings": spec.chase_innings,
                "over_max": effective_over_max(spec),
                "has_fixed_over_cap": spec.over_max is not None,
                "phases": [_phase_payload(p) for p in spec.phases],
                "phases_4": [_phase_payload(p) for p in spec.phases_4],
                "fantasy_ruleset": spec.fantasy_ruleset,
                "sr_bands": {"good": spec.sr_bands[0], "poor": spec.sr_bands[1]},
                "econ_bands": {"good": spec.econ_bands[0], "poor": spec.econ_bands[1]},
                # Drives the format switcher: no data means the entry renders disabled.
                "available": match_count > 0,
                "match_count": match_count,
                "min_date": min_date.isoformat() if min_date else None,
                "max_date": max_date.isoformat() if max_date else None,
            }
        )

    return {"formats": payload, "default": "mens-t20"}
