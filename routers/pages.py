"""The venue and team pages (TEAM_VENUE_PLAN.md): one cached call each, for the page's window."""
from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from database import get_session

router = APIRouter(tags=["Pages"])

CACHE = "public, max-age=300, s-maxage=3600, stale-while-revalidate=86400"
BUSY = {"Retry-After": "10"}


@router.get("/venue-page")
def venue_page(
    response: Response,
    venue: str = Query(..., description="The ground, as the venue list names it"),
    format: Literal["T20", "ODI"] = Query(default="T20"),
    period: Literal["recent", "career"] = Query(default="recent"),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    db: Session = Depends(get_session),
):
    """The venue page: summary ranked against the competition's grounds, the preview's ground cards, who does well."""
    from services.page_builds import PageBuilding
    from services.venue_page import get_page

    try:
        page = get_page(db, venue, format, period, start_date, end_date)
    except PageBuilding:
        raise HTTPException(status_code=503, detail="Building this page; try again in a few seconds", headers=BUSY)
    if not page.get("matches"):
        raise HTTPException(status_code=404, detail=f"No {format} matches at {venue} in this window")
    response.headers["Cache-Control"] = CACHE
    return page


@router.get("/team-page")
def team_page(
    response: Response,
    team: str = Query(..., description="The side's full name, as the teams list names it"),
    format: Literal["T20", "ODI"] = Query(default="T20"),
    period: Literal["recent", "career"] = Query(default="recent"),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    db: Session = Depends(get_session),
):
    """The team page: ranks against its competition's sides, rating, phases, batting order, overs, top players, results."""
    from services.page_builds import PageBuilding
    from services.team_page import get_page

    try:
        page = get_page(db, team, format, period, start_date, end_date)
    except PageBuilding:
        raise HTTPException(status_code=503, detail="Building this page; try again in a few seconds", headers=BUSY)
    if not page.get("played"):
        raise HTTPException(status_code=404, detail=f"No {format} matches for {team} in this window")
    response.headers["Cache-Control"] = CACHE
    return page
