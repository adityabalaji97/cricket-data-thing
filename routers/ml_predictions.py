"""Read-only API endpoint for ML foresight predictions.

Returns pre-computed predictions from the match_predictions table.
Predictions are generated locally via ml/predict.py and inserted into RDS.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_session

router = APIRouter(prefix="/predictions", tags=["ML Predictions"])


@router.get("/{venue}/{team1_id}/{team2_id}")
def get_prediction(
    venue: str,
    team1_id: str,
    team2_id: str,
    db: Session = Depends(get_session),
):
    """Get the latest ML prediction for a team pair at a venue.

    Team identifiers can be full names or abbreviations — the query checks both
    orderings (team1/team2 swapped) and uses ILIKE for fuzzy matching.
    """
    # Try exact match first (both orderings)
    row = db.execute(text("""
        SELECT
            match_id, team1, team2,
            team1_win_prob, team2_win_prob,
            predicted_1st_innings_score_mean,
            predicted_2nd_innings_score_mean,
            top_features, model_version, gates_passed,
            prediction_date, predicted_winner,
            narrative_insights
        FROM match_predictions
        WHERE (
            (team1 ILIKE :t1 AND team2 ILIKE :t2)
            OR (team1 ILIKE :t2 AND team2 ILIKE :t1)
        )
        ORDER BY prediction_date DESC
        LIMIT 1
    """), {"t1": f"%{team1_id}%", "t2": f"%{team2_id}%"}).fetchone()

    if not row:
        return {"available": False}

    # If teams were swapped in the DB, swap the probabilities back
    t1_prob = row[3]
    t2_prob = row[4]
    db_team1 = row[1]
    db_team2 = row[2]

    # Check if the caller's team1 matches the DB's team2 (swapped order)
    if team1_id.lower() in (db_team2 or "").lower():
        t1_prob, t2_prob = t2_prob, t1_prob
        db_team1, db_team2 = db_team2, db_team1

    # Parse top_features — stored as JSON
    import json
    top_features = row[7]
    if isinstance(top_features, str):
        try:
            top_features = json.loads(top_features)
        except (json.JSONDecodeError, TypeError):
            top_features = []

    # Parse narrative_insights — stored as JSON
    narrative_insights = row[12]
    if isinstance(narrative_insights, str):
        try:
            narrative_insights = json.loads(narrative_insights)
        except (json.JSONDecodeError, TypeError):
            narrative_insights = []

    return {
        "available": True,
        "match_id": row[0],
        "team1": db_team1,
        "team2": db_team2,
        "team1_win_prob": round(t1_prob, 3) if t1_prob else None,
        "team2_win_prob": round(t2_prob, 3) if t2_prob else None,
        "predicted_1st_innings_score": round(row[5], 1) if row[5] else None,
        "predicted_2nd_innings_score": round(row[6], 1) if row[6] else None,
        "top_features": top_features or [],
        "model_version": row[8],
        "gates_passed": row[9],
        "prediction_date": row[10].isoformat() if row[10] else None,
        "predicted_winner": row[11],
        "narrative_insights": narrative_insights or [],
    }
