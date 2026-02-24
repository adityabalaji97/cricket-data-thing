from datetime import date, datetime
import hashlib
import json
import logging
import os
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_session
from services.match_preview import (
    build_deterministic_preview_sections,
    gather_preview_context,
    generate_match_preview_fallback,
    score_preview_lean,
    serialize_sections_to_markdown,
    validate_llm_rewrite,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/match-preview", tags=["Match Preview"])

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini"
MAX_TOKENS = 800
TEMPERATURE = 0.2
PREVIEW_ENGINE_VERSION = "v2-screen-story"
DEFAULT_PREVIEW_MODE = "hybrid"

preview_cache: Dict[str, Dict] = {}


MATCH_PREVIEW_REWRITE_PROMPT = """Rewrite the provided cricket pre-match preview bullets for readability only.

You must preserve:
- all 5 section headings and their order exactly
- 1-2 bullets per section
- all numbers, player names, and factual claims
- the meaning of phase-wise strategy bullets as winning templates

Do not:
- add new facts
- add sections
- remove numeric details
- add prose before or after the sections

Return markdown only.

Canonical preview markdown:
{canonical_markdown}
"""


def _cache_key(
    venue: str,
    team1: str,
    team2: str,
    start_date: Optional[date],
    end_date: Optional[date],
    include_international: bool,
    top_teams: int,
    preview_mode: str,
) -> str:
    payload = json.dumps(
        {
            "venue": venue,
            "team1": team1,
            "team2": team2,
            "start_date": str(start_date) if start_date else None,
            "end_date": str(end_date) if end_date else None,
            "include_international": include_international,
            "top_teams": top_teams,
            "preview_version": PREVIEW_ENGINE_VERSION,
            "preview_mode": preview_mode,
        },
        sort_keys=True,
    )
    return hashlib.md5(payload.encode()).hexdigest()


def _rewrite_with_llm(canonical_markdown: str, original_sections) -> tuple[str, bool]:
    if not OPENAI_API_KEY:
        return canonical_markdown, False

    try:
        import openai

        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        prompt = MATCH_PREVIEW_REWRITE_PROMPT.format(canonical_markdown=canonical_markdown)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
        )
        content = response.choices[0].message.content.strip()
        if not content:
            return canonical_markdown, False
        if not validate_llm_rewrite(original_sections, content):
            logger.warning("Match preview LLM rewrite failed validation; using deterministic sections")
            return canonical_markdown, False
        return content, True
    except Exception as e:
        logger.error(f"Match preview OpenAI rewrite failed: {e}", exc_info=True)
        return canonical_markdown, False


@router.get("/{venue}/{team1_id}/{team2_id}")
def get_match_preview(
    venue: str,
    team1_id: str,
    team2_id: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    include_international: bool = Query(True),
    top_teams: int = Query(20, ge=1, le=50),
    debug: bool = Query(False),
    db: Session = Depends(get_session),
):
    try:
        preview_mode = DEFAULT_PREVIEW_MODE
        key = _cache_key(venue, team1_id, team2_id, start_date, end_date, include_international, top_teams, preview_mode)
        if key in preview_cache:
            cached = preview_cache[key]
            return {**cached, "cached": True}

        context = gather_preview_context(
            venue=venue,
            team1_identifier=team1_id,
            team2_identifier=team2_id,
            db=db,
            start_date=start_date,
            end_date=end_date,
            include_international=include_international,
            top_teams=top_teams,
        )
        sections = build_deterministic_preview_sections(context)
        canonical_markdown = serialize_sections_to_markdown(sections)
        llm_used = False
        preview_text = canonical_markdown
        if preview_mode == "hybrid":
            preview_text, llm_used = _rewrite_with_llm(canonical_markdown, sections)
        if not preview_text:
            preview_text = generate_match_preview_fallback(context)
        decision_scores = score_preview_lean(context)
        phase_check = (((context.get("screen_story") or {}).get("phase_wise_strategy") or {}).get("consistency_check")) or {}

        result = {
            "success": True,
            "venue": venue,
            "team1": context["team1"],
            "team2": context["team2"],
            "sections": sections,
            "preview": preview_text,
            "preview_mode": preview_mode,
            "preview_version": PREVIEW_ENGINE_VERSION,
            "llm_used": llm_used,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "cached": False,
        }
        if debug:
            result["debug"] = {
                "decision_scores": decision_scores,
                "phase_template_consistency_check": phase_check,
            }
        preview_cache[key] = result
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate match preview: {str(e)}")
