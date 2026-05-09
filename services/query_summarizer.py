"""
Reusable GPT-powered query result summarization service.
Takes query context + result data and returns a concise summary
highlighting standout numbers.
"""
import os
import json
import logging
import time
from typing import Dict, Any, Optional, List

from openai import OpenAI
from sqlalchemy.orm import Session

from services.nl2query import (
    select_model,
    estimate_cost,
    persist_nl_query_log,
    MODEL_PRIMARY,
)

logger = logging.getLogger(__name__)

SUMMARIZE_SYSTEM_PROMPT = """You are a cricket analytics expert summarizing T20 query results. Given a query context and its result data, write a concise 3-5 bullet point summary.

## What to highlight
- **Standout performers** (both good and bad) — cite specific numbers
- **Key patterns** — notable trends across the data
- **Small sample warnings** — flag rows with very few balls (<12) as unreliable

## Cricket stat benchmarks (T20)
- Batters: SR >140 is good, <100 is concerning; dot% >45% is bad; boundary% >25% is excellent
- Bowlers: economy <7 is good, >10 is concerning; dot% >40% is good for bowlers; SR (balls per wicket) <18 is elite
- Average: contextual, but batting avg >30 at a venue is strong

## Rules
- Be specific — always cite actual numbers (e.g. "SR 158 from 38 balls" not "high strike rate")
- Keep to 3-5 bullet points, each one sentence
- If the result data is empty or has 0 rows, say "No data available for this query."
- Format player names exactly as they appear in the data
- For matchup data (batter + bowler grouped), focus on the most interesting pairings
- Do not invent data — only reference numbers present in the results"""

SUMMARIZE_USER_TEMPLATE = """## Query Context
{context_description}

## Filters Applied
{filters_description}

## Grouped By
{group_by_description}

## Result Data ({result_count} rows{truncation_note})
{result_data_text}

Write a concise summary:"""


def _serialize_result_table(result_data: List[Dict], max_rows: int = 50) -> str:
    """Serialize result rows as a compact text table for the GPT prompt."""
    if not result_data:
        return "(no data)"

    rows = result_data[:max_rows]
    if not rows:
        return "(no data)"

    columns = list(rows[0].keys())
    header = " | ".join(columns)
    lines = [header]
    for row in rows:
        vals = []
        for col in columns:
            v = row.get(col)
            if v is None:
                vals.append("-")
            elif isinstance(v, float):
                vals.append(f"{v:.2f}")
            else:
                vals.append(str(v))
        lines.append(" | ".join(vals))
    return "\n".join(lines)


def _describe_filters(filters: Dict[str, Any]) -> str:
    """Build a human-readable one-liner from a filter dict."""
    parts = []
    for key, val in filters.items():
        if val is None or val == [] or val == "":
            continue
        if isinstance(val, list):
            parts.append(f"{key}: {', '.join(str(v) for v in val[:5])}")
        else:
            parts.append(f"{key}: {val}")
    return "; ".join(parts) if parts else "(none)"


def summarize_query_results(
    context_description: str,
    filters: Dict[str, Any],
    group_by: List[str],
    result_data: List[Dict],
    result_count: int,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """Summarize query builder results using GPT.

    Returns {"success": bool, "summary": str|None, "error": str|None, "_meta": {...}}
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"success": False, "summary": None, "error": "OPENAI_API_KEY not configured"}

    if not result_data or result_count == 0:
        return {"success": True, "summary": "No data available for this query.", "_meta": {}}

    model = select_model(db)
    max_rows = 50
    truncation_note = f", showing first {max_rows}" if result_count > max_rows else ""

    user_message = SUMMARIZE_USER_TEMPLATE.format(
        context_description=context_description,
        filters_description=_describe_filters(filters),
        group_by_description=", ".join(group_by) if group_by else "(none)",
        result_count=result_count,
        truncation_note=truncation_note,
        result_data_text=_serialize_result_table(result_data, max_rows),
    )

    start_time = time.time()
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SUMMARIZE_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
            max_tokens=500,
        )

        summary_text = response.choices[0].message.content.strip()
        usage = response.usage
        meta = {
            "model_used": model,
            "prompt_tokens": usage.prompt_tokens if usage else 0,
            "completion_tokens": usage.completion_tokens if usage else 0,
            "estimated_cost_usd": estimate_cost(
                model,
                usage.prompt_tokens if usage else 0,
                usage.completion_tokens if usage else 0,
            ),
        }

        elapsed_ms = int((time.time() - start_time) * 1000)
        _log_summarization(
            context_description=context_description,
            filters=filters,
            group_by=group_by,
            result_count=result_count,
            meta=meta,
            elapsed_ms=elapsed_ms,
            db=db,
        )

        return {"success": True, "summary": summary_text, "_meta": meta}

    except Exception as exc:
        logger.error("GPT summarization failed: %s", exc, exc_info=True)
        return {"success": False, "summary": None, "error": str(exc)}


def _log_summarization(
    *,
    context_description: str,
    filters: Dict[str, Any],
    group_by: List[str],
    result_count: int,
    meta: Dict[str, Any],
    elapsed_ms: int,
    db: Optional[Session],
) -> None:
    """Log summarization call to nl_query_log for cost tracking."""
    try:
        persist_nl_query_log(
            query_text=context_description[:500],
            parse_result={
                "filters": filters,
                "group_by": group_by,
                "query_mode": "summarize",
                "confidence": "high",
                "explanation": f"GPT summarization of {result_count} result rows",
                "success": True,
                "result_row_count": result_count,
                "_meta": meta,
            },
            ip_address=None,
            execution_time_ms=elapsed_ms,
            model_used=meta.get("model_used", MODEL_PRIMARY),
            db=db,
        )
    except Exception as exc:
        logger.warning("Failed to log summarization: %s", exc)
