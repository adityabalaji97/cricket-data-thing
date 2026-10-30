from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from sqlalchemy.orm import Session

from database import get_session
from services.twins import board, twins_for

router = APIRouter(tags=["twins"])


@router.get("/twins/board")
def twins_board(response: Response, db: Session = Depends(get_session)):
    """The doppelgangers page: per role (bat, bowl, allround), the closest pairs and the players with no close twin,
    careers over the profile's window. Built nightly (scripts/build_player_vectors.py)."""
    response.headers["Cache-Control"] = "public, max-age=300, s-maxage=3600, stale-while-revalidate=86400"
    return board(db)


@router.get("/twins/{player_name}")
def player_twins(
    response: Response,
    player_name: str = Path(..., description="The player's name as the site shows it"),
    unit: Literal["window", "career", "season"] = Query(default="window", description="window = the last few seasons "
                                              "(the profile's Recent); career = since 2015; season = one season against "
                                              "every season since 2015"),
    season: Optional[str] = Query(default=None, description="With unit=season, e.g. 2025"),
    role: Optional[Literal["bat", "bowl", "allround"]] = Query(default=None, description="Default: the player's role"),
    n: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_session),
):
    """Statistical twins (DOPPELGANGER_PLAN.md S4): the players who play most like this one, by percentiles within
    the period over usage, scoring shape, shot mix, matchups (batting) or usage, lengths, lines, outcomes (bowling),
    with each twin's closest and furthest features and both players' value side by side."""
    if unit == "season" and not season:
        raise HTTPException(status_code=422, detail="unit=season needs season=YYYY")
    out = twins_for(db, player_name, unit, season if unit == "season" else None, role, n)
    if not out.get("qualified"):
        raise HTTPException(status_code=404, detail=f"{player_name} isn't in the twins pool for this period")
    response.headers["Cache-Control"] = "public, max-age=300, s-maxage=3600, stale-while-revalidate=86400"
    return out
