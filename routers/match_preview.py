from datetime import date, datetime
import hashlib
import json
import logging
import os
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_session
from services.match_preview import gather_preview_context, generate_match_preview_fallback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/match-preview", tags=["Match Preview"])

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini"
MAX_TOKENS = 800
TEMPERATURE = 0.4

preview_cache: Dict[str, Dict] = {}


MATCH_PREVIEW_PROMPT = """You are a cricket analyst writing a compact, data-first pre-match preview.

Use the JSON context below to produce exactly 5 markdown sections with these headings in this order:

## Venue Profile
## Form Guide
## Head-to-Head
## Key Matchup Factor
## Preview Take

Rules:
- Write 1-2 bullet points per section (prefix bullets with "- ").
- Every section must include at least one number from the context when data exists.
- Prefer the selected date window and sample sizes explicitly.
- Keep bullets tight (roughly 8-22 words each). No filler adjectives.
- Use phase stats (powerplay/middle/death) when making the "Key Matchup Factor".
- Do not invent player availability or team news.
- If data is missing, say so briefly and move on.
- Preview Take should be a lean with reasons tied to venue/form/H2H/phase data, not certainty.

Context JSON:
{context_json}
"""


def _cache_key(
    venue: str,
    team1: str,
    team2: str,
    start_date: Optional[date],
    end_date: Optional[date],
    include_international: bool,
    top_teams: int,
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
        },
        sort_keys=True,
    )
    return hashlib.md5(payload.encode()).hexdigest()


def _generate_with_llm(context: Dict) -> str:
    if not OPENAI_API_KEY:
        return generate_match_preview_fallback(context)

    try:
        import openai

        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        prompt = MATCH_PREVIEW_PROMPT.format(context_json=json.dumps(context, indent=2))
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
        )
        content = response.choices[0].message.content.strip()
        return content or generate_match_preview_fallback(context)
    except Exception as e:
        logger.error(f"Match preview OpenAI call failed: {e}", exc_info=True)
        return generate_match_preview_fallback(context)


@router.get("/{venue}/{team1_id}/{team2_id}")
def get_match_preview(
    venue: str,
    team1_id: str,
    team2_id: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    include_international: bool = Query(True),
    top_teams: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_session),
):
    try:
        key = _cache_key(venue, team1_id, team2_id, start_date, end_date, include_international, top_teams)
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
        preview_text = _generate_with_llm(context)

        result = {
            "success": True,
            "venue": venue,
            "team1": context["team1"],
            "team2": context["team2"],
            "preview": preview_text,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "cached": False,
        }
        preview_cache[key] = result
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate match preview: {str(e)}")
