from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_session
from services.match_recap import build_recap
from services.match_scorecard import get_match_scorecard_service


router = APIRouter(prefix="/matches", tags=["match_scorecard"])


@router.get("/{match_id}/scorecard")
def get_match_scorecard(
    match_id: str,
    min_balls: int = Query(default=6, ge=1, le=60),
    db: Session = Depends(get_session),
):
    return get_match_scorecard_service(match_id=match_id, min_balls=min_balls, db=db)



@router.get("/{match_id}/recap")
def get_match_recap(match_id: str, db: Session = Depends(get_session)):
    """Headline and bullets explaining a finished men's T20 (Impact/WPA facts, ranked by Jev)."""
    scorecard = get_match_scorecard_service(match_id=match_id, min_balls=6, db=db)
    if not (scorecard.get("summary") or {}).get("primer"):
        return {"available": False}
    return build_recap(scorecard, db)
