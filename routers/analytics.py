"""
Advanced analytics endpoints:
- bowling context
- first-ball boundary leaderboards
- rolling form
- relative metrics
- match resource benchmark
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_session
from services.bowling_context import (
    get_bowling_context,
    get_first_ball_boundary_leaderboard,
)
from services.relative_metrics import (
    get_player_relative_metrics,
    get_team_relative_metrics,
)
from services.resource_benchmark import get_match_resource_benchmark
from services.rolling_form import get_player_rolling_form
from services.boundary_vs_bowling_type import get_boundary_vs_bowling_type
from services.boundary_analysis import get_boundary_analysis


router = APIRouter(tags=["analytics"])


@router.get("/player/{player_name}/bowling-context")
def player_bowling_context(
    player_name: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    leagues: List[str] = Query(default=[]),
    include_international: bool = Query(default=False),
    venue: Optional[str] = Query(None),
    min_overs: int = Query(default=10, ge=1),
    pressure_threshold: int = Query(default=10, ge=1),
    db: Session = Depends(get_session),
):
    try:
        return get_bowling_context(
            db=db,
            player_name=player_name,
            start_date=start_date,
            end_date=end_date,
            leagues=leagues,
            include_international=include_international,
            venue=venue,
            min_overs=min_overs,
            pressure_threshold=pressure_threshold,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to compute bowling context: {exc}")


@router.get("/leaderboards/first-ball-boundaries")
def first_ball_boundaries_leaderboard(
    role: str = Query(default="batter", pattern="^(batter|bowler)$"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    leagues: List[str] = Query(default=[]),
    include_international: bool = Query(default=False),
    venue: Optional[str] = Query(None),
    min_balls: int = Query(default=60, ge=1),
    limit: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_session),
):
    try:
        return get_first_ball_boundary_leaderboard(
            db=db,
            role=role,
            start_date=start_date,
            end_date=end_date,
            leagues=leagues,
            include_international=include_international,
            venue=venue,
            min_balls=min_balls,
            limit=limit,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to compute leaderboard: {exc}")


@router.get("/player/{player_name}/rolling-form")
def player_rolling_form(
    player_name: str,
    window: int = Query(default=10, ge=1, le=30),
    role: str = Query(default="all", pattern="^(batting|bowling|all)$"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    leagues: List[str] = Query(default=[]),
    include_international: bool = Query(default=False),
    venue: Optional[str] = Query(None),
    db: Session = Depends(get_session),
):
    try:
        return get_player_rolling_form(
            db=db,
            player_name=player_name,
            window=window,
            role=role,
            start_date=start_date,
            end_date=end_date,
            leagues=leagues,
            include_international=include_international,
            venue=venue,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to compute rolling form: {exc}")


@router.get("/relative-metrics/player/{player_name}")
def player_relative_metrics(
    player_name: str,
    benchmark_window_matches: int = Query(default=10, ge=5, le=50),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    leagues: List[str] = Query(default=[]),
    include_international: bool = Query(default=False),
    venue: Optional[str] = Query(None),
    db: Session = Depends(get_session),
):
    try:
        return get_player_relative_metrics(
            db=db,
            player_name=player_name,
            benchmark_window_matches=benchmark_window_matches,
            start_date=start_date,
            end_date=end_date,
            leagues=leagues,
            include_international=include_international,
            venue=venue,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to compute player relative metrics: {exc}")


@router.get("/relative-metrics/team/{team_name}")
def team_relative_metrics(
    team_name: str,
    benchmark_window_matches: int = Query(default=10, ge=5, le=50),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    leagues: List[str] = Query(default=[]),
    include_international: bool = Query(default=False),
    venue: Optional[str] = Query(None),
    db: Session = Depends(get_session),
):
    try:
        return get_team_relative_metrics(
            db=db,
            team_name=team_name,
            benchmark_window_matches=benchmark_window_matches,
            start_date=start_date,
            end_date=end_date,
            leagues=leagues,
            include_international=include_international,
            venue=venue,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to compute team relative metrics: {exc}")


@router.get("/matches/{match_id}/resource-benchmark")
def match_resource_benchmark(
    match_id: str,
    benchmark_window_matches: int = Query(default=10, ge=5, le=50),
    db: Session = Depends(get_session),
):
    try:
        return get_match_resource_benchmark(
            db=db,
            match_id=match_id,
            benchmark_window_matches=benchmark_window_matches,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to compute match resource benchmark: {exc}")


@router.get("/player/{player_name}/boundary-vs-bowling-type")
def player_boundary_vs_bowling_type(
    player_name: str,
    role: str = Query(default="batter", pattern="^(batter|bowler)$"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    leagues: List[str] = Query(default=[]),
    db: Session = Depends(get_session),
):
    try:
        return get_boundary_vs_bowling_type(
            db=db,
            player_name=player_name,
            role=role,
            start_date=start_date,
            end_date=end_date,
            leagues=leagues if leagues else None,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compute boundary vs bowling type: {exc}",
        )


@router.get("/boundary-analysis")
def boundary_analysis(
    context: str = Query(..., pattern="^(venue|batter|bowler)$"),
    name: str = Query(...),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    leagues: List[str] = Query(default=[]),
    db: Session = Depends(get_session),
):
    try:
        return get_boundary_analysis(
            db=db,
            context=context,
            name=name,
            start_date=start_date,
            end_date=end_date,
            leagues=leagues if leagues else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compute boundary analysis: {exc}",
        )

