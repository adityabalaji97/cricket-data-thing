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
    build_narrative_data_context,
    gather_preview_context,
    generate_match_preview_fallback,
    score_preview_lean,
    serialize_sections_to_markdown,
    validate_llm_narrative,
    validate_llm_rewrite,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/match-preview", tags=["Match Preview"])

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("MATCH_PREVIEW_OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TIMEOUT_SECONDS = float(
    os.getenv("MATCH_PREVIEW_OPENAI_TIMEOUT_SECONDS", os.getenv("OPENAI_TIMEOUT_SECONDS", "20"))
)
MAX_TOKENS = 1200
GPT5_MAX_OUTPUT_TOKENS = int(os.getenv("MATCH_PREVIEW_GPT5_MAX_OUTPUT_TOKENS", "4000"))
GPT5_REASONING_EFFORT = os.getenv("MATCH_PREVIEW_GPT5_REASONING_EFFORT", "low")
TEMPERATURE = 0.3
PREVIEW_ENGINE_VERSION = "v3-narrative"
DEFAULT_PREVIEW_MODE = "hybrid"

preview_cache: Dict[str, Dict] = {}


def _is_gpt5_model() -> bool:
    return OPENAI_MODEL.startswith("gpt-5")


def _chat_completion_kwargs() -> Dict[str, float]:
    kwargs: Dict[str, float] = {}
    kwargs["max_tokens"] = MAX_TOKENS
    kwargs["temperature"] = TEMPERATURE
    return kwargs


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

MATCH_PREVIEW_REWRITE_GPT5_INSTRUCTIONS = """Rewrite the provided cricket pre-match preview bullets for readability only.

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
"""

MATCH_PREVIEW_NARRATIVE_PROMPT = """You are a cricket analyst writing a pre-match preview. You're given structured data from a venue analysis page. Your job is to weave the data into a compelling narrative, cross-referencing data points as described below.

Write exactly 5 markdown sections (## heading + 1-3 bullets each). Keep all numbers as integers (no decimals). Be specific — cite scores, dates, player names.

## How to interpret each data source:

1. MATCH RESULTS DISTRIBUTION: Identify whether there's a toss/innings advantage. Cross-reference with each team's recent form — e.g., if there's a bowl-first advantage, how many times has each team won bowling first recently, and what did they restrict opponents to?

2. INNINGS SCORES ANALYSIS: Use avg winning score and avg chasing score as benchmarks. For each team, count how many recent matches batting first they reached the avg winning score, and how many times chasing they reached the avg chasing score. When teams are close, bring in highest chased and lowest defended as tiebreakers.

3. HEAD-TO-HEAD: Weight recent matches more heavily. Same-venue or same-country H2H is more relevant than neutral-venue H2H.

4. RECENT MATCHES AT VENUE: For 2-year windows, recent matches (especially clusters of matches in a short period) can be a better signal than the aggregate. Compare recent toss signal to aggregate toss signal.

5. EXPECTED FANTASY POINTS: Highlight players likely to succeed, especially those with high confidence scores (based on direct matchup data against specific opponents). Reference specific positive/negative matchups from the data.

6. PHASE-WISE STRATEGY: The "batting first" template shows how teams who batted first AND WON averaged per phase (sums to avg winning score). The "chasing" template shows how teams who chased AND WON averaged per phase (sums to avg chasing score). These are winning blueprints.

## Required sections:
1. ## Venue Profile — Toss advantage, scoring benchmarks, phase template shape, any recent-vs-aggregate divergence
2. ## Form Guide — Each team's last 5 results with context (scores, who they beat/lost to, how they align with venue benchmarks)
3. ## Head-to-Head — Recent meetings weighted by recency and venue relevance
4. ## Key Matchup Factor — Phase template pressure point + standout player matchups (fantasy picks + specific batter-vs-bowler edges)
5. ## Preview Take — Prediction with 2-3 supporting reasons drawn from above sections

## Data:
{data_context}
"""

MATCH_PREVIEW_GPT5_INSTRUCTIONS = """You are a cricket analyst writing a pre-match preview from a structured venue-analysis dataset.

Use only the supplied data. Do not invent facts, players, scores, or trends.

Output requirements:
- Return markdown only
- Write exactly 5 sections, in this exact order
- Each section must begin with a level-2 heading (`## `)
- Each section must contain 1-3 bullet points
- Keep all numbers as integers (no decimals)
- Be specific: cite scores, dates, player names, and matchup edges when the data supports them
- If a signal is weak or unavailable, say so directly instead of guessing

How to use the data:
1. MATCH RESULTS DISTRIBUTION: identify toss/innings advantage; cross-reference with each team's recent form.
2. INNINGS SCORES ANALYSIS: use average winning score and average chasing score as benchmarks; compare each team's recent batting/chasing results to those thresholds.
3. HEAD-TO-HEAD: weight recency higher; same venue or same country is more relevant than neutral venues.
4. RECENT MATCHES AT VENUE: recent clusters can matter more than aggregate history; compare recent toss signal to aggregate toss signal.
5. EXPECTED FANTASY POINTS: highlight high-confidence players and specific positive or negative batter-vs-bowler edges.
6. PHASE-WISE STRATEGY: the batting-first template and chasing template are winning blueprints; use them to explain pressure points by phase.

Required section order:
1. ## Venue Profile
2. ## Form Guide
3. ## Head-to-Head
4. ## Key Matchup Factor
5. ## Preview Take
"""


def _call_responses_api(*, instructions: str, input_text: str) -> str:
    import openai

    client = openai.OpenAI(api_key=OPENAI_API_KEY, timeout=OPENAI_TIMEOUT_SECONDS)
    response = client.responses.create(
        model=OPENAI_MODEL,
        instructions=instructions,
        input=input_text,
        max_output_tokens=GPT5_MAX_OUTPUT_TOKENS,
        reasoning={"effort": GPT5_REASONING_EFFORT},
    )
    return response.output_text.strip()


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
            "openai_model": OPENAI_MODEL,
            "preview_mode": preview_mode,
        },
        sort_keys=True,
    )
    return hashlib.md5(payload.encode()).hexdigest()


def _rewrite_with_llm(canonical_markdown: str, original_sections) -> tuple[str, bool]:
    """Legacy rewrite function — kept for backward compat."""
    if not OPENAI_API_KEY:
        return canonical_markdown, False

    try:
        if _is_gpt5_model():
            content = _call_responses_api(
                instructions=MATCH_PREVIEW_REWRITE_GPT5_INSTRUCTIONS,
                input_text=f"Canonical preview markdown:\n{canonical_markdown}",
            )
        else:
            import openai

            client = openai.OpenAI(api_key=OPENAI_API_KEY, timeout=OPENAI_TIMEOUT_SECONDS)
            prompt = MATCH_PREVIEW_REWRITE_PROMPT.format(canonical_markdown=canonical_markdown)
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                **_chat_completion_kwargs(),
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


def _generate_narrative_with_llm(data_context: str, original_sections) -> tuple[str, bool]:
    """Generate narrative preview from structured data context."""
    if not OPENAI_API_KEY:
        return None, False
    try:
        if _is_gpt5_model():
            content = _call_responses_api(
                instructions=MATCH_PREVIEW_GPT5_INSTRUCTIONS,
                input_text=f"## Data\n{data_context}",
            )
        else:
            import openai

            client = openai.OpenAI(api_key=OPENAI_API_KEY, timeout=OPENAI_TIMEOUT_SECONDS)
            prompt = MATCH_PREVIEW_NARRATIVE_PROMPT.format(data_context=data_context)
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                **_chat_completion_kwargs(),
            )
            content = response.choices[0].message.content.strip()
        if not content or not validate_llm_narrative(content):
            logger.warning("Match preview LLM narrative failed validation; falling back to deterministic")
            return None, False
        return content, True
    except Exception as e:
        logger.error(f"Match preview LLM generation failed: {e}", exc_info=True)
        return None, False


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
            # Build data context for LLM narrative generation
            data_context = build_narrative_data_context(context)
            # Try LLM narrative generation first
            llm_preview, llm_used = _generate_narrative_with_llm(data_context, sections)
            if llm_used and llm_preview:
                preview_text = llm_preview
            # else: keep deterministic canonical_markdown as preview_text

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
            "llm_model": OPENAI_MODEL,
            "llm_strategy": "responses" if _is_gpt5_model() else "chat.completions",
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
