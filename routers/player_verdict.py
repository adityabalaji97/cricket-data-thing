from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from sqlalchemy.orm import Session

from database import get_session
from services.player_verdict import PoolsCold, SummaryBusy, get_summary

router = APIRouter(tags=["player"])


@router.get("/player/{player_name}/summary")
def player_summary(
    response: Response,
    player_name: str = Path(..., description="Any spelling of the player's name"),
    format: Literal["T20", "ODI"] = Query(default="T20", description="Cricket format"),
    scope: Literal["strong", "all"] = Query(
        default="strong",
        description="strong = major leagues + T20Is between top-12 sides (ODIs: top-12 sides); all = every match",
    ),
    period: Literal["recent", "career"] = Query(default="recent", description="recent = since 1 Jan two years back (T20) "
                                                "or three (ODI); career = since 2015"),
    start_date: Optional[date] = Query(default=None, description="Window start (overrides the period's)"),
    end_date: Optional[date] = Query(default=None, description="Window end (default: today)"),
    db: Session = Depends(get_session),
):
    """The player profile's first screen in one call (VERDICT_SCREEN_PLAN.md, V2): both roles'
    seasons, phases, peer ranks with the peer distribution, and the last 8 matches."""
    try:
        summary = get_summary(db, player_name, format, scope, start_date, end_date, period)
    except PoolsCold:
        raise HTTPException(status_code=503, detail="Career numbers are still being built; try again in a minute",
                            headers={"Retry-After": "60"})
    except SummaryBusy:
        response.headers["Retry-After"] = "10"
        raise HTTPException(status_code=503, detail="Busy building another player's summary; try again in a few seconds",
                            headers={"Retry-After": "10"})
    if not summary.get("roles"):
        raise HTTPException(status_code=404, detail=f"No {format} data for {player_name} in this window")
    # The result cache makes repeat calls cheap; the CDN holds it for an hour and serves a stale copy
    # while it refetches, so a data load shows up within the hour.
    response.headers["Cache-Control"] = "public, max-age=300, s-maxage=3600, stale-while-revalidate=86400"
    return summary
