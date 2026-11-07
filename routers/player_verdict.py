from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from sqlalchemy.orm import Session

from database import get_session
from services.player_cards import CardsBusy, card_slice, get_cards, wheel
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


@router.get("/player/{player_name}/cards")
def player_cards(
    response: Response,
    player_name: str = Path(..., description="Any spelling of the player's name"),
    format: Literal["T20", "ODI"] = Query(default="T20"),
    scope: Literal["strong", "all"] = Query(default="strong"),
    period: Literal["recent", "career"] = Query(default="recent"),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    db: Session = Depends(get_session),
):
    """The profile's role cards (PROFILE_SIMPLIFY_PLAN.md P2) for the verdict's window: batters' start, scoring areas,
    bowling types and dismissals; bowlers' line and length, phases, left v right and wickets."""
    try:
        cards = get_cards(db, player_name, format, scope, start_date, end_date, period)
    except CardsBusy:
        raise HTTPException(status_code=503, detail="Busy building another player's cards; try again in a few seconds",
                            headers={"Retry-After": "10"})
    if not cards.get("roles"):
        raise HTTPException(status_code=404, detail=f"No {format} data for {player_name} in this window")
    response.headers["Cache-Control"] = "public, max-age=300, s-maxage=3600, stale-while-revalidate=86400"
    return cards


@router.get("/player-compare")
def player_compare(
    response: Response,
    a: str = Query(..., description="First player"),
    b: str = Query(..., description="Second player"),
    format: Literal["T20", "ODI"] = Query(default="T20"),
    period: Literal["recent", "career"] = Query(default="recent"),
    scope: Literal["strong", "all"] = Query(default="strong"),
    db: Session = Depends(get_session),
):
    """Two players on every ranked measure (overall, by phase, by opponent) against the same pool: the Compare page."""
    from services.player_compare import get_compare
    from services.player_verdict import PoolsCold

    try:
        out = get_compare(db, a, b, format, period, scope)
    except PoolsCold:
        raise HTTPException(status_code=503, detail="Career pools are still being built; try again shortly", headers={"Retry-After": "30"})
    response.headers["Cache-Control"] = "public, max-age=300, s-maxage=3600, stale-while-revalidate=86400"
    return out


@router.get("/player/{player_name}/wheel")
def player_wheel(
    response: Response,
    player_name: str = Path(..., description="Any spelling of the player's name"),
    role: Literal["bat", "bowl"] = Query(default="bat"),
    format: Literal["T20", "ODI"] = Query(default="T20"),
    scope: Literal["strong", "all"] = Query(default="strong"),
    period: Literal["recent", "career"] = Query(default="recent"),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    phase: Optional[Literal["powerplay", "middle", "death"]] = Query(default=None),
    kind: Optional[Literal["pace", "spin"]] = Query(default=None, description="Pace or spin (a batter's wheel)"),
    family: Optional[str] = Query(default=None, description="One bowling family, e.g. Off-spin (a batter's wheel)"),
    hand: Optional[Literal["RHB", "LHB"]] = Query(default=None, description="The batter's hand (a bowler's wheel)"),
    db: Session = Depends(get_session),
):
    """A scoring wheel with its own filters, for the gear on the profile's wheel cards: zones (runs, balls, strike
    rate) and catches, in the page's window and scope."""
    out = wheel(db, player_name, role, format, scope, period, start_date, end_date, phase, kind, family, hand)
    response.headers["Cache-Control"] = "public, max-age=300, s-maxage=3600, stale-while-revalidate=86400"
    return out


@router.get("/player/{player_name}/slice")
def player_card_slice(
    response: Response,
    player_name: str = Path(..., description="Any spelling of the player's name"),
    card: Literal["wheel_bat", "wheel_bowl", "pace_map", "shot_mix", "pitch", "shots_against", "wickets"] = Query(...),
    format: Literal["T20", "ODI"] = Query(default="T20"),
    scope: Literal["strong", "all"] = Query(default="strong"),
    period: Literal["recent", "career"] = Query(default="recent"),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    phase: Optional[Literal["powerplay", "middle", "death"]] = Query(default=None),
    kind: Optional[Literal["pace", "spin"]] = Query(default=None),
    family: Optional[str] = Query(default=None),
    hand: Optional[Literal["RHB", "LHB"]] = Query(default=None),
    db: Session = Depends(get_session),
):
    """One profile card's numbers under its own filter (the sliders icon on the card), in the page's window and scope."""
    out = card_slice(db, player_name, card, format, scope, period, start_date, end_date, phase, kind, family, hand)
    response.headers["Cache-Control"] = "public, max-age=300, s-maxage=3600, stale-while-revalidate=86400"
    return out
