"""
Query result summarization router.
Provides endpoints for GPT-powered summarization of query builder results.
"""
import logging
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_session
from services.query_summarizer import summarize_query_results
from services.query_builder_v2 import query_deliveries_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/summarize", tags=["summarize"])


class SummarizeRequest(BaseModel):
    context_description: str = Field(..., max_length=500)
    filters: Dict[str, Any] = {}
    group_by: List[str] = []
    result_data: List[Dict[str, Any]] = Field(..., max_length=100)
    result_count: int = 0


class BatchItem(BaseModel):
    key: str
    context_description: str = Field(..., max_length=500)
    filters: Dict[str, Any] = {}
    group_by: List[str] = []


class BatchRequest(BaseModel):
    items: List[BatchItem] = Field(..., max_length=8)


@router.post("/results")
def summarize_results(
    payload: SummarizeRequest,
    db: Session = Depends(get_session),
):
    result = summarize_query_results(
        context_description=payload.context_description,
        filters=payload.filters,
        group_by=payload.group_by,
        result_data=payload.result_data,
        result_count=payload.result_count,
        db=db,
    )
    result.pop("_meta", None)
    return result


def _execute_query_from_filters(filters: Dict[str, Any], group_by: List[str], db: Session) -> Dict[str, Any]:
    """Execute a query builder query from a filter dict."""
    def _list(key: str) -> list:
        val = filters.get(key, [])
        if isinstance(val, list):
            return val
        return [val] if val else []

    def _str(key: str) -> Optional[str]:
        val = filters.get(key)
        return str(val) if val is not None else None

    def _int(key: str) -> Optional[int]:
        val = filters.get(key)
        if val is None:
            return None
        return int(val)

    return query_deliveries_service(
        venue=_str("venue"),
        start_date=None,
        end_date=None,
        leagues=_list("leagues"),
        teams=_list("teams"),
        batting_teams=_list("batting_teams"),
        bowling_teams=_list("bowling_teams"),
        players=_list("players"),
        batters=_list("batters"),
        bowlers=_list("bowlers"),
        bat_hand=_str("bat_hand"),
        bowl_style=_list("bowl_style"),
        bowl_kind=_list("bowl_kind"),
        crease_combo=_list("crease_combo"),
        line=_list("line"),
        length=_list("length"),
        shot=_list("shot"),
        control=_int("control"),
        wagon_zone=[int(x) for x in _list("wagon_zone")],
        dismissal=_list("dismissal"),
        innings=_int("innings"),
        over_min=_int("over_min"),
        over_max=_int("over_max"),
        match_outcome=_list("match_outcome"),
        is_chase=filters.get("is_chase"),
        chase_outcome=_list("chase_outcome"),
        toss_decision=_list("toss_decision"),
        group_by=group_by,
        show_summary_rows=False,
        min_balls=_int("min_balls"),
        max_balls=None,
        min_runs=None,
        max_runs=None,
        min_wickets=None,
        max_wickets=None,
        limit=200,
        offset=0,
        include_international=bool(filters.get("include_international", False)),
        top_teams=_int("top_teams"),
        query_mode=filters.get("query_mode", "delivery"),
        db=db,
        day_or_night=_str("day_or_night"),
    )


@router.post("/batch")
def summarize_batch(
    payload: BatchRequest,
    db: Session = Depends(get_session),
):
    if len(payload.items) > 8:
        raise HTTPException(status_code=400, detail="Maximum 8 items per batch")

    summaries: Dict[str, Any] = {}

    for item in payload.items:
        try:
            query_result = _execute_query_from_filters(item.filters, item.group_by, db)
            result_data = (query_result or {}).get("data") or []
            result_count = len(result_data)

            if result_count == 0:
                summaries[item.key] = {
                    "summary": "No data available for this query.",
                    "result_count": 0,
                    "error": None,
                }
                continue

            gpt_result = summarize_query_results(
                context_description=item.context_description,
                filters=item.filters,
                group_by=item.group_by,
                result_data=result_data,
                result_count=result_count,
                db=db,
            )
            summaries[item.key] = {
                "summary": gpt_result.get("summary"),
                "result_count": result_count,
                "error": gpt_result.get("error"),
            }
        except Exception as exc:
            logger.error("Batch item %s failed: %s", item.key, exc, exc_info=True)
            summaries[item.key] = {
                "summary": None,
                "result_count": 0,
                "error": str(exc),
            }

    return {"success": True, "summaries": summaries}
