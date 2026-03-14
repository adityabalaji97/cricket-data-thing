from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from database import get_session
from services.global_t20_rankings import (
    get_batting_rankings_service,
    get_bowling_rankings_service,
    get_competition_weights_service,
    get_player_rankings_service,
)


router = APIRouter(prefix="/rankings", tags=["rankings"])


@router.get("/batting")
def get_batting_rankings(
    start_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=500, description="Number of rows to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    bowl_kind: str = Query("all", description="One of: all, pace, spin"),
    force_refresh: bool = Query(False, description="Bypass rankings cache"),
    db: Session = Depends(get_session),
):
    try:
        return get_batting_rankings_service(
            db=db,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
            bowl_kind=bowl_kind,
            force_refresh=force_refresh,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/bowling")
def get_bowling_rankings(
    start_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=500, description="Number of rows to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    bowl_kind: str = Query("all", description="One of: all, pace, spin"),
    force_refresh: bool = Query(False, description="Bypass rankings cache"),
    db: Session = Depends(get_session),
):
    try:
        return get_bowling_rankings_service(
            db=db,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
            bowl_kind=bowl_kind,
            force_refresh=force_refresh,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/player/{player_name}")
def get_player_rankings(
    player_name: str = Path(..., description="Player name"),
    start_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    bowl_kind: str = Query("all", description="One of: all, pace, spin"),
    mode: str = Query("all", description="One of: all, batting, bowling"),
    snapshots: int = Query(24, ge=1, le=36, description="Monthly trajectory snapshots to return"),
    force_refresh: bool = Query(False, description="Bypass rankings cache"),
    db: Session = Depends(get_session),
):
    try:
        return get_player_rankings_service(
            player_name=player_name,
            db=db,
            start_date=start_date,
            end_date=end_date,
            bowl_kind=bowl_kind,
            mode=mode,
            snapshots=snapshots,
            force_refresh=force_refresh,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/competition-weights")
def get_competition_weights(
    start_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    force_refresh: bool = Query(False, description="Bypass competition-weight cache"),
    db: Session = Depends(get_session),
):
    try:
        return get_competition_weights_service(
            db=db,
            start_date=start_date,
            end_date=end_date,
            force_refresh=force_refresh,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
