from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_session
from services.venue_delivery_stats import get_venue_delivery_stats_payload

router = APIRouter(prefix="/venues", tags=["Venue Delivery Stats"])


@router.get("/{venue}/delivery-stats")
def get_venue_delivery_stats(
    venue: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    leagues: List[str] = Query(default=[]),
    include_international: bool = Query(default=False),
    top_teams: Optional[int] = Query(default=None),
    team1: Optional[str] = None,
    team2: Optional[str] = None,
    db: Session = Depends(get_session),
):
    try:
        return get_venue_delivery_stats_payload(
            venue=venue,
            start_date=start_date,
            end_date=end_date,
            leagues=leagues,
            include_international=include_international,
            top_teams=top_teams,
            team1=team1,
            team2=team2,
            db=db,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
