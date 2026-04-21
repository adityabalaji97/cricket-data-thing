"""
Natural Language to Query Builder router.
Provides endpoints for parsing natural language cricket queries.
"""
import time
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Request, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from sqlalchemy.orm import Session
from services.nl2query import (
    parse_nl_query,
    get_example_queries,
    get_cache_size,
    log_nl_query_event_background,
    update_nl_query_feedback,
)
from database import get_session
import os

router = APIRouter(prefix="/nl2query", tags=["nl2query"])

# Simple rate limiting: track request timestamps per IP
_rate_limit_store: Dict[str, List[float]] = defaultdict(list)
RATE_LIMIT = 10  # requests per minute
RATE_WINDOW = 60  # seconds


def _check_rate_limit(ip: str):
    now = time.time()
    timestamps = _rate_limit_store[ip]
    # Remove old entries
    _rate_limit_store[ip] = [t for t in timestamps if now - t < RATE_WINDOW]
    if len(_rate_limit_store[ip]) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please wait a minute before trying again."
        )
    _rate_limit_store[ip].append(now)


class NLQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Natural language cricket query")


class NLQueryFilters(BaseModel):
    query_mode: Optional[str] = None
    batters: Optional[List[str]] = None
    bowlers: Optional[List[str]] = None
    players: Optional[List[str]] = None
    batting_teams: Optional[List[str]] = None
    bowling_teams: Optional[List[str]] = None
    teams: Optional[List[str]] = None
    venue: Optional[str] = None
    leagues: Optional[List[str]] = None
    include_international: Optional[bool] = None
    bat_hand: Optional[str] = None
    bowl_style: Optional[List[str]] = None
    bowl_kind: Optional[List[str]] = None
    over_min: Optional[int] = None
    over_max: Optional[int] = None
    innings: Optional[int] = None
    match_outcome: Optional[List[str]] = None
    is_chase: Optional[bool] = None
    chase_outcome: Optional[List[str]] = None
    toss_decision: Optional[List[str]] = None
    line: Optional[List[str]] = None
    length: Optional[List[str]] = None
    shot: Optional[List[str]] = None
    control: Optional[int] = None
    wagon_zone: Optional[List[int]] = None
    dismissal: Optional[List[str]] = None
    min_balls: Optional[int] = None
    min_runs: Optional[int] = None
    max_runs: Optional[int] = None
    min_wickets: Optional[int] = None
    max_wickets: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class NLParsedEntity(BaseModel):
    type: str
    value: str
    matched_from: Optional[str] = None


class NLInterpretation(BaseModel):
    summary: str = ""
    parsed_entities: List[NLParsedEntity] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


class NLQueryResponse(BaseModel):
    success: bool
    filters: Dict[str, Any] = {}
    group_by: List[str] = []
    explanation: str = ""
    confidence: str = "medium"
    suggestions: List[str] = []
    interpretation: NLInterpretation = Field(default_factory=NLInterpretation)
    error: Optional[str] = None


class NLQueryFeedbackRequest(BaseModel):
    query_text: str = Field(..., min_length=1, max_length=500)
    feedback: Literal["good", "bad", "refined"]
    refined_query_text: Optional[str] = Field(default=None, max_length=500)
    execution_success: Optional[bool] = None
    result_row_count: Optional[int] = Field(default=None, ge=0)


class NLQueryFeedbackResponse(BaseModel):
    success: bool
    query_log_id: int
    feedback: Literal["good", "bad", "refined"]


class ExampleQuery(BaseModel):
    text: str
    category: str


@router.post("/parse", response_model=NLQueryResponse)
def parse_query(
    request: NLQueryRequest,
    req: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_session),
):
    """Parse a natural language cricket query into structured filters."""
    client_ip = req.client.host if req.client else "unknown"
    _check_rate_limit(client_ip)

    started_at = time.time()
    result = parse_nl_query(request.query, db=db)
    execution_time_ms = int((time.time() - started_at) * 1000)

    background_tasks.add_task(
        log_nl_query_event_background,
        query_text=request.query,
        parse_result=result,
        ip_address=client_ip,
        execution_time_ms=execution_time_ms,
    )

    return NLQueryResponse(**result)


@router.post("/feedback", response_model=NLQueryFeedbackResponse)
def submit_feedback(
    request: NLQueryFeedbackRequest,
    req: Request,
    db: Session = Depends(get_session),
):
    """Capture user feedback for a previously parsed NL query."""
    client_ip = req.client.host if req.client else "unknown"
    _check_rate_limit(f"{client_ip}:feedback")

    if request.feedback == "refined" and not (request.refined_query_text or "").strip():
        raise HTTPException(status_code=400, detail="refined_query_text is required when feedback='refined'")

    updated = update_nl_query_feedback(
        query_text=request.query_text,
        feedback=request.feedback,
        ip_address=client_ip,
        db=db,
        refined_query_text=request.refined_query_text,
        execution_success=request.execution_success,
        result_row_count=request.result_row_count,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Matching NL query log entry not found")

    return NLQueryFeedbackResponse(
        success=True,
        query_log_id=int(updated["query_log_id"]),
        feedback=updated["feedback"],
    )


@router.get("/examples", response_model=List[ExampleQuery])
def get_examples():
    """Get example natural language queries for the UI."""
    return get_example_queries()


@router.get("/health")
def health_check():
    """Check NL query service health."""
    api_key = os.getenv("OPENAI_API_KEY")
    return {
        "status": "ok",
        "openai_configured": bool(api_key),
        "cache_size": get_cache_size()
    }
