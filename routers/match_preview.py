from datetime import date, datetime, timedelta
import hashlib
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_session
from services.cricinfo_scraper import scrape_match_setup
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
from services.matchups import (
    _canonicalize_players,
    _calculate_batting_projection_points,
    _calculate_bowling_projection_points,
)
from services.query_builder_v2 import query_deliveries_service
from services.rolling_form import get_form_flags_for_players
try:
    from venue_standardization import VENUE_STANDARDIZATION
except Exception:  # pragma: no cover - defensive fallback
    VENUE_STANDARDIZATION = {}

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
post_toss_cache: Dict[str, Dict[str, Any]] = {}
POST_TOSS_CACHE_TTL_SECONDS = int(os.getenv("POST_TOSS_CACHE_TTL_SECONDS", "21600"))
POST_TOSS_BATTING_MIN_BALLS = int(os.getenv("POST_TOSS_BATTING_MIN_BALLS", "40"))
POST_TOSS_BOWLING_MIN_BALLS = int(os.getenv("POST_TOSS_BOWLING_MIN_BALLS", "30"))


def _inject_form_flags(context: Dict, db: Session) -> None:
    """Best-effort enrichment: add form_flag badges to top-ranked/fantasy player blocks."""
    names = set()

    top_ranked = (context.get("top_ranked_players") or {}).get("teams") or {}
    for team_payload in top_ranked.values():
        for key in ("top_overall", "top_batting", "top_bowling"):
            for row in team_payload.get(key) or []:
                player = row.get("player")
                if player:
                    names.add(player)

    fantasy_top = (
        ((context.get("screen_story") or {}).get("expected_fantasy_points") or {}).get("fantasy_top")
        or {}
    )
    for rows in fantasy_top.values():
        for row in rows or []:
            player = row.get("player")
            if player:
                names.add(player)

    if not names:
        return

    form_flags = get_form_flags_for_players(db=db, player_names=sorted(names), window=10)

    for team_payload in top_ranked.values():
        for key in ("top_overall", "top_batting", "top_bowling"):
            for row in team_payload.get(key) or []:
                player = row.get("player")
                row["form_flag"] = form_flags.get(player, "neutral")

    for rows in fantasy_top.values():
        for row in rows or []:
            player = row.get("player")
            row["form_flag"] = form_flags.get(player, "neutral")

    context["player_form_flags"] = form_flags


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
Write in the style of a TV broadcast preview delivered by a sharp analyst: crisp, confident, and readable under time pressure.

Output requirements:
- Return markdown only
- Write exactly 5 sections, in this exact order
- Each section must begin with a level-2 heading (`## `)
- Each section should contain 1-2 bullet points (use 3 only if absolutely necessary)
- Keep all numbers as integers (no decimals)
- Use plain English. Never expose internal dataset labels or field-like terms such as `chasing_edge`, `bat_first_edge`, `balanced`, `same_country_h2h`, or similar raw identifiers. Do not use the literal label `balanced`; translate it to phrases like "even conditions" or "little to split the sides".
- Be specific: cite scores, dates, player names, and matchup edges only when the data clearly supports them
- If a signal is weak, sparse, zero, null, or obviously not meaningful, omit it instead of narrating it awkwardly
- Do not restate every available number. Select only the 2-3 most decision-relevant facts per section
- Prefer short analytical sentences over raw data dumps
- Prefer verdict-first phrasing. Lead with the takeaway, then support it with the most relevant evidence.
- Avoid generic hedging. If one side has the clearer edge, say so plainly.

How to use the data:
1. MATCH RESULTS DISTRIBUTION: identify toss/innings advantage; cross-reference with each team's recent form.
2. INNINGS SCORES ANALYSIS: use average winning score and average chasing score as benchmarks; compare each team's recent batting/chasing results to those thresholds.
3. HEAD-TO-HEAD: weight recency higher; same venue or same country is more relevant than neutral venues.
4. RECENT MATCHES AT VENUE: recent clusters can matter more than aggregate history; compare recent toss signal to aggregate toss signal.
5. EXPECTED FANTASY POINTS: use this as secondary support only. Prioritize significant positive or negative individual batter-vs-bowler matchups when the sample is meaningful; do not turn the preview into a fantasy picks list. Avoid citing expected-points rankings unless they clearly reinforce a concrete cricketing role, form signal, or matchup edge.
6. PHASE-WISE STRATEGY: the batting-first template and chasing template are winning blueprints; use them to explain pressure points by phase.

Required section order:
1. ## Venue Profile
2. ## Form Guide
3. ## Head-to-Head
4. ## Key Matchup Factor
5. ## Preview Take

Section-specific guidance:
- Venue Profile: state the practical match condition in plain language (for example, “slight chasing advantage” or “even conditions”), not internal tags.
- Form Guide: compare each team to the venue benchmarks, but skip weak or misleading “0” metrics unless they are genuinely informative.
- Head-to-Head: if there is no meaningful H2H signal, say so in one clean line and move on.
- Key Matchup Factor: highlight no more than 2 standout individual matchup edges total. Use fantasy projections only if they directly reinforce the cricketing case. Treat a matchup as meaningful only when the sample is reasonably credible for this format.
- Preview Take: make a clear lean. Prefer one of: team1 edge, team2 edge, or toss-dependent/too close to call. Use toss-dependent/too close only in rare, genuinely split cases. If toss matters but one side still has the stronger overall case, say that team has the slight edge and explain how the toss could strengthen or weaken it. Support the lean with 2 concise reasons.
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
    day_or_night: Optional[str],
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
            "day_or_night": day_or_night,
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
    day_or_night: Optional[str] = Query(None, pattern="^(day|night)$"),
    debug: bool = Query(False),
    db: Session = Depends(get_session),
):
    try:
        preview_mode = DEFAULT_PREVIEW_MODE
        key = _cache_key(
            venue,
            team1_id,
            team2_id,
            start_date,
            end_date,
            include_international,
            top_teams,
            preview_mode,
            day_or_night,
        )
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
            day_or_night=day_or_night,
        )
        try:
            _inject_form_flags(context, db)
        except Exception as enrich_exc:
            logger.warning("Failed to enrich match preview with form flags: %s", enrich_exc)
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
        lineup_selection = context.get("lineup_selection") or {}

        result = {
            "success": True,
            "venue": venue,
            "team1": context["team1"],
            "team2": context["team2"],
            "top_ranked_players": context.get("top_ranked_players") or {},
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
                "lineup_selection": lineup_selection,
            }
        preview_cache[key] = result
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate match preview: {str(e)}")


class PostTossPayload(BaseModel):
    match_id: Optional[str] = None
    venue: str
    team1_id: str
    team2_id: str
    batting_first_team: str
    team1_xi: List[str]
    team2_xi: List[str]
    impact_subs: List[str] = []
    source: str = Field(default="manual", pattern="^(manual|scraped)$")
    general_window_years: int = Field(default=2, ge=1, le=6)
    venue_window_years: int = Field(default=3, ge=1, le=8)
    day_or_night: Optional[str] = Field(default=None, pattern="^(day|night)$")


class ScrapeCricinfoPayload(BaseModel):
    url: str


def _dedupe_names(names: List[str]) -> List[str]:
    seen = set()
    deduped: List[str] = []
    for raw in names or []:
        name = str(raw or "").strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(name)
    return deduped


def _canonicalize_lineup(names: List[str], db: Session) -> List[str]:
    if not names:
        return []
    try:
        canonical = _canonicalize_players(names, db)
        return _dedupe_names(canonical if canonical else names)
    except Exception:
        return _dedupe_names(names)


def _canonicalize_venue_name(venue: Optional[str]) -> Optional[str]:
    if not venue:
        return venue
    if str(venue).strip() == "All Venues":
        return None
    return VENUE_STANDARDIZATION.get(venue, venue)


def _window_date_range(window_years: int) -> Tuple[date, date]:
    end_date = date.today()
    start_date = end_date - timedelta(days=365 * window_years)
    return start_date, end_date


def _normalize_list_for_cache(values: List[str]) -> List[str]:
    return sorted({str(v or "").strip().lower() for v in values or [] if str(v or "").strip()})


def _post_toss_cache_key(
    *,
    venue: Optional[str],
    team1_id: str,
    team2_id: str,
    batting_first_team: str,
    team1_xi: List[str],
    team2_xi: List[str],
    impact_subs: List[str],
    general_window_years: int,
    venue_window_years: int,
) -> str:
    normalized = {
        "venue": str(venue or "").strip().lower(),
        "team1_id": str(team1_id or "").strip().lower(),
        "team2_id": str(team2_id or "").strip().lower(),
        "batting_first_team": str(batting_first_team or "").strip().lower(),
        "team1_xi": _normalize_list_for_cache(team1_xi),
        "team2_xi": _normalize_list_for_cache(team2_xi),
        "impact_subs": _normalize_list_for_cache(impact_subs),
        "general_window_years": general_window_years,
        "venue_window_years": venue_window_years,
    }
    serialized = json.dumps(normalized, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _get_cached_post_toss(key: str) -> Optional[Dict[str, Any]]:
    entry = post_toss_cache.get(key)
    if not entry:
        return None
    expires_at = entry.get("expires_at")
    if not isinstance(expires_at, datetime) or datetime.utcnow() >= expires_at:
        post_toss_cache.pop(key, None)
        return None
    return entry.get("data")


def _set_cached_post_toss(key: str, data: Dict[str, Any]) -> None:
    post_toss_cache[key] = {
        "expires_at": datetime.utcnow() + timedelta(seconds=POST_TOSS_CACHE_TTL_SECONDS),
        "data": data,
    }


def _log_post_toss_prediction(
    *,
    db: Session,
    match_id: Optional[str],
    payload_data: Dict[str, Any],
    result_data: Dict[str, Any],
    source: str,
) -> None:
    try:
        db.execute(
            text(
                """
                INSERT INTO post_toss_predictions (match_id, payload, result, source)
                VALUES (
                    :match_id,
                    CAST(:payload_json AS JSONB),
                    CAST(:result_json AS JSONB),
                    :source
                )
                """
            ),
            {
                "match_id": match_id,
                "payload_json": json.dumps(payload_data, default=str),
                "result_json": json.dumps(result_data, default=str),
                "source": source,
            },
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("Failed to write post_toss_predictions log row: %s", exc)


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def _sum_batting_overall(team_payload: Dict[str, Any]) -> Dict[str, Any]:
    batting = (team_payload or {}).get("batting_matchups") or {}
    balls = runs = wickets = boundaries = dots = 0
    players = 0
    for _, vs_map in batting.items():
        overall = (vs_map or {}).get("Overall")
        if not overall:
            continue
        players += 1
        balls += int(overall.get("balls", 0) or 0)
        runs += int(overall.get("runs", 0) or 0)
        wickets += int(overall.get("wickets", 0) or 0)
        boundaries += int(overall.get("boundaries", 0) or 0)
        dots += int(overall.get("dots", 0) or 0)
    strike_rate = (runs * 100.0 / balls) if balls else 0.0
    boundary_pct = (boundaries * 100.0 / balls) if balls else 0.0
    dot_pct = (dots * 100.0 / balls) if balls else 0.0
    return {
        "sample_balls": balls,
        "sample_players": players,
        "runs": runs,
        "wickets": wickets,
        "strike_rate": round(strike_rate, 2),
        "boundary_percentage": round(boundary_pct, 2),
        "dot_percentage": round(dot_pct, 2),
    }


def _sum_bowling_overall(team_payload: Dict[str, Any]) -> Dict[str, Any]:
    bowling = (team_payload or {}).get("bowling_consolidated") or {}
    balls = runs = wickets = boundaries = dots = 0
    players = 0
    for _, stats in bowling.items():
        if not stats:
            continue
        players += 1
        balls += int(stats.get("balls", 0) or 0)
        runs += int(stats.get("runs", 0) or 0)
        wickets += int(stats.get("wickets", 0) or 0)
        boundaries += int(stats.get("boundaries", 0) or 0)
        dots += int(stats.get("dots", 0) or 0)
    overs = balls / 6.0 if balls else 0.0
    economy = (runs / overs) if overs else 0.0
    dot_pct = (dots * 100.0 / balls) if balls else 0.0
    boundary_pct = (boundaries * 100.0 / balls) if balls else 0.0
    wkts_per_match = (wickets * 120.0 / balls) if balls else 0.0
    return {
        "sample_balls": balls,
        "sample_players": players,
        "runs_conceded": runs,
        "wickets": wickets,
        "economy": round(economy, 2),
        "dot_percentage": round(dot_pct, 2),
        "boundary_percentage": round(boundary_pct, 2),
        "wickets_per_20_overs": round(wkts_per_match, 2),
    }


def _player_points_map(matchup_payload: Dict[str, Any]) -> Dict[str, float]:
    fantasy = (matchup_payload or {}).get("fantasy_analysis") or {}
    players = (fantasy.get("all_fantasy_players") or fantasy.get("top_fantasy_picks") or [])
    output: Dict[str, float] = {}
    for row in players:
        name = str((row or {}).get("player_name") or "").strip()
        if not name:
            continue
        output[name] = _safe_float((row or {}).get("expected_points"))
    return output


def _merge_points(*maps: Dict[str, float]) -> Dict[str, float]:
    merged: Dict[str, float] = {}
    for mapping in maps:
        for player, points in (mapping or {}).items():
            merged[player] = round(_safe_float(merged.get(player)) + _safe_float(points), 3)
    return merged


def _build_query_link(
    *,
    venue: Optional[str],
    start_date: date,
    end_date: date,
    innings: int,
    batters: List[str],
    bowlers: List[str],
) -> str:
    params: List[Tuple[str, str]] = [
        ("query_mode", "delivery"),
        ("start_date", start_date.isoformat()),
        ("end_date", end_date.isoformat()),
        ("innings", str(innings)),
        ("min_balls", "6"),
        ("group_by", "batter"),
        ("group_by", "bowler"),
    ]
    if venue:
        params.append(("venue", venue))
    for batter in batters:
        params.append(("batters", batter))
    for bowler in bowlers:
        params.append(("bowlers", bowler))
    return f"/query?{urlencode(params, doseq=True)}"


def _build_player_drill_link(
    *,
    venue: Optional[str],
    start_date: date,
    end_date: date,
    innings: Optional[int],
    player: str,
    kind: str,  # "batting" | "bowling"
    day_or_night: Optional[str] = None,
) -> str:
    """Drill-down link for a single player's stats in the query builder."""
    params: List[Tuple[str, str]] = [
        ("query_mode", "delivery"),
        ("start_date", start_date.isoformat()),
        ("end_date", end_date.isoformat()),
        ("leagues", "IPL"),
        ("group_by", "batter" if kind == "batting" else "bowler"),
    ]
    if innings is not None:
        params.append(("innings", str(innings)))
    if venue:
        params.append(("venue", venue))
    if day_or_night:
        params.append(("day_or_night", day_or_night))
    if kind == "batting":
        params.append(("batters", player))
    else:
        params.append(("bowlers", player))
    return f"/query?{urlencode(params, doseq=True)}"


def _build_axis_drill_link(
    *,
    venue: Optional[str],
    start_date: date,
    end_date: date,
    innings: int,
    players: List[str],
    kind: str,
    day_or_night: Optional[str] = None,
) -> str:
    """Drill-down link for an entire axis (whole batting/bowling XI)."""
    params: List[Tuple[str, str]] = [
        ("query_mode", "delivery"),
        ("start_date", start_date.isoformat()),
        ("end_date", end_date.isoformat()),
        ("innings", str(innings)),
        ("leagues", "IPL"),
        ("group_by", "batter" if kind == "batting" else "bowler"),
    ]
    if venue:
        params.append(("venue", venue))
    if day_or_night:
        params.append(("day_or_night", day_or_night))
    role_key = "batters" if kind == "batting" else "bowlers"
    for player in players:
        params.append((role_key, player))
    return f"/query?{urlencode(params, doseq=True)}"


def _run_post_toss_axis(
    *,
    db: Session,
    players: List[str],
    kind: str,  # "batting" | "bowling"
    innings: Optional[int],
    venue: Optional[str],
    start_date: date,
    end_date: date,
    day_or_night: Optional[str],
) -> List[Dict[str, Any]]:
    """
    Run a single per-team aggregate query for one axis of the post-toss panel.
    Returns a list of player dicts with stats + computed xPoints + drill link.
    """
    if not players:
        return []

    group_by = ["batter"] if kind == "batting" else ["bowler"]
    role_arg = "batters" if kind == "batting" else "bowlers"
    role_kwargs = {role_arg: players}
    other_arg = "bowlers" if kind == "batting" else "batters"
    role_kwargs[other_arg] = []

    try:
        result = query_deliveries_service(
            venue=venue,
            start_date=start_date,
            end_date=end_date,
            leagues=["IPL"],
            teams=[],
            batting_teams=[],
            bowling_teams=[],
            players=[],
            **role_kwargs,
            bat_hand=None,
            bowl_style=[],
            bowl_kind=[],
            crease_combo=[],
            line=[],
            length=[],
            shot=[],
            control=None,
            wagon_zone=[],
            dismissal=[],
            innings=innings,
            over_min=None,
            over_max=None,
            match_outcome=[],
            is_chase=None,
            chase_outcome=[],
            toss_decision=[],
            group_by=group_by,
            show_summary_rows=False,
            min_balls=None,
            max_balls=None,
            min_runs=None,
            max_runs=None,
            min_wickets=None,
            max_wickets=None,
            limit=200,
            offset=0,
            include_international=False,
            top_teams=None,
            query_mode="delivery",
            db=db,
            day_or_night=day_or_night,
        )
    except Exception as exc:
        logger.warning(
            "Post-toss axis query failed (kind=%s innings=%s venue=%s): %s",
            kind, innings, venue, exc,
        )
        return []

    rows = (result or {}).get("data") or []
    out: List[Dict[str, Any]] = []
    name_key = "batter" if kind == "batting" else "bowler"
    for row in rows:
        player = str(row.get(name_key) or "").strip()
        if not player:
            continue
        stats = {
            "balls": int(row.get("balls") or 0),
            "runs": int(row.get("runs") or 0),
            "wickets": int(row.get("wickets") or 0),
            "boundaries": int(row.get("boundaries") or 0),
            "dots": int(row.get("dots") or 0),
            "strike_rate": float(row.get("strike_rate") or 0.0),
            "average": float(row.get("average") or 0.0) if row.get("average") is not None else None,
            "boundary_percentage": float(row.get("boundary_percentage") or 0.0),
            "dot_percentage": float(row.get("dot_percentage") or 0.0),
        }
        if kind == "batting":
            projection = _calculate_batting_projection_points(stats)
        else:
            projection = _calculate_bowling_projection_points(stats)
        xpoints = float(projection.get("points") or 0.0)
        confidence = float(projection.get("confidence") or 0.0)
        drill_link = _build_player_drill_link(
            venue=venue,
            start_date=start_date,
            end_date=end_date,
            innings=innings,
            player=player,
            kind=kind,
            day_or_night=day_or_night,
        )
        out.append({
            "player": player,
            "balls": stats["balls"],
            "runs": stats["runs"],
            "wickets": stats["wickets"],
            "boundaries": stats["boundaries"],
            "dots": stats["dots"],
            "strike_rate": round(stats["strike_rate"], 2),
            "average": round(stats["average"], 2) if stats["average"] is not None else None,
            "boundary_percentage": round(stats["boundary_percentage"], 2),
            "dot_percentage": round(stats["dot_percentage"], 2),
            "xpoints": round(xpoints, 2),
            "xpoints_confidence": round(confidence, 2),
            "drill_link": drill_link,
        })
    out.sort(key=lambda r: (r["xpoints"], r["balls"]), reverse=True)
    return out


def _sum_player_xpoints(axis_bundle: Dict[str, Any]) -> Dict[str, float]:
    """Sum xPoints by player across all axis rows in a bundle."""
    points_map: Dict[str, float] = {}
    for axis_data in (axis_bundle or {}).values():
        for row in axis_data.get("players", []):
            player = str(row.get("player") or "").strip()
            if not player:
                continue
            points_map[player] = round(
                _safe_float(points_map.get(player)) + _safe_float(row.get("xpoints")),
                3,
            )
    return points_map


def _run_post_toss_window(
    *,
    db: Session,
    batting_first_team: str,
    batting_second_team: str,
    first_team_xi: List[str],
    second_team_xi: List[str],
    start_date: date,
    end_date: date,
    venue_filter: Optional[str],
    day_or_night: Optional[str],
) -> Dict[str, Any]:
    """Build the four per-axis player tables for one (general | venue) window."""
    axes = {
        "first_innings_batting": (first_team_xi, "batting", 1, batting_first_team, batting_second_team),
        "first_innings_bowling": (second_team_xi, "bowling", 1, batting_second_team, batting_first_team),
        "second_innings_batting": (second_team_xi, "batting", 2, batting_second_team, batting_first_team),
        "second_innings_bowling": (first_team_xi, "bowling", 2, batting_first_team, batting_second_team),
    }

    axis_results: Dict[str, Any] = {}
    drill_links: Dict[str, str] = {}
    for axis_name, (players, kind, innings, team, opponent) in axes.items():
        rows = _run_post_toss_axis(
            db=db,
            players=players,
            kind=kind,
            innings=innings,
            venue=venue_filter,
            start_date=start_date,
            end_date=end_date,
            day_or_night=day_or_night,
        )
        axis_results[axis_name] = {
            "kind": kind,
            "innings": innings,
            "team": team,
            "opponent": opponent,
            "players": rows,
            "sample_balls": sum(r["balls"] for r in rows),
            "sample_players": len([r for r in rows if r["balls"] > 0]),
        }
        drill_links[axis_name] = _build_axis_drill_link(
            venue=venue_filter,
            start_date=start_date,
            end_date=end_date,
            innings=innings,
            players=players,
            kind=kind,
            day_or_night=day_or_night,
        )
    return {
        "axes": axis_results,
        "drill_down_links": drill_links,
    }


@router.post("/post-toss")
def post_toss_preview(
    payload: PostTossPayload,
    db: Session = Depends(get_session),
):
    try:
        if payload.batting_first_team not in {payload.team1_id, payload.team2_id}:
            raise HTTPException(
                status_code=400,
                detail="batting_first_team must match either team1_id or team2_id",
            )

        normalized_venue = _canonicalize_venue_name(payload.venue)
        team1_xi = _canonicalize_lineup(payload.team1_xi, db)
        team2_xi = _canonicalize_lineup(payload.team2_xi, db)
        impact_subs = _canonicalize_lineup(payload.impact_subs, db)

        if not team1_xi or not team2_xi:
            raise HTTPException(
                status_code=400,
                detail="Both team1_xi and team2_xi must contain at least one player",
            )

        cache_key = _post_toss_cache_key(
            venue=normalized_venue,
            team1_id=payload.team1_id,
            team2_id=payload.team2_id,
            batting_first_team=payload.batting_first_team,
            team1_xi=team1_xi,
            team2_xi=team2_xi,
            impact_subs=impact_subs,
            general_window_years=payload.general_window_years,
            venue_window_years=payload.venue_window_years,
        )
        # Bake day_or_night into the cache key by appending to it; keeps the
        # existing helper signature stable while still distinguishing day/night
        # results.
        if payload.day_or_night:
            cache_key = f"{cache_key}:{payload.day_or_night}"
        cached = _get_cached_post_toss(cache_key)
        if cached:
            return {
                **cached,
                "cached": True,
                "source": payload.source,
                "match_id": payload.match_id,
            }

        batting_first_team = payload.batting_first_team
        batting_second_team = payload.team2_id if batting_first_team == payload.team1_id else payload.team1_id

        first_team_xi = team1_xi if batting_first_team == payload.team1_id else team2_xi
        second_team_xi = team2_xi if batting_second_team == payload.team2_id else team1_xi

        general_start, general_end = _window_date_range(payload.general_window_years)
        venue_start, venue_end = _window_date_range(payload.venue_window_years)

        general_bundle = _run_post_toss_window(
            db=db,
            batting_first_team=batting_first_team,
            batting_second_team=batting_second_team,
            first_team_xi=first_team_xi,
            second_team_xi=second_team_xi,
            start_date=general_start,
            end_date=general_end,
            venue_filter=None,
            day_or_night=payload.day_or_night,
        )
        venue_bundle = _run_post_toss_window(
            db=db,
            batting_first_team=batting_first_team,
            batting_second_team=batting_second_team,
            first_team_xi=first_team_xi,
            second_team_xi=second_team_xi,
            start_date=venue_start,
            end_date=venue_end,
            venue_filter=normalized_venue,
            day_or_night=payload.day_or_night,
        )

        # Build post-toss xPoints map by summing a player's batting + bowling
        # contributions from innings-aware general-window axes.
        xpoints_post_toss = _sum_player_xpoints(general_bundle.get("axes") or {})

        # Build base (pre-toss) xPoints by removing innings constraints while
        # keeping the same player pools and date window.
        xpoints_base: Dict[str, float] = {}
        base_axes = [
            (first_team_xi, "batting"),
            (first_team_xi, "bowling"),
            (second_team_xi, "batting"),
            (second_team_xi, "bowling"),
        ]
        for axis_players, axis_kind in base_axes:
            base_rows = _run_post_toss_axis(
                db=db,
                players=axis_players,
                kind=axis_kind,
                innings=None,
                venue=None,
                start_date=general_start,
                end_date=general_end,
                day_or_night=payload.day_or_night,
            )
            for row in base_rows:
                player = str(row.get("player") or "").strip()
                if not player:
                    continue
                xpoints_base[player] = round(
                    _safe_float(xpoints_base.get(player)) + _safe_float(row.get("xpoints")),
                    3,
                )

        # Ensure every playing-XI player has a post-toss value; if innings-
        # specific data is missing, fall back to the broader base projection.
        for player in dict.fromkeys([*first_team_xi, *second_team_xi]):
            if player not in xpoints_post_toss:
                xpoints_post_toss[player] = round(_safe_float(xpoints_base.get(player)), 3)
            if player not in xpoints_base:
                xpoints_base[player] = round(_safe_float(xpoints_post_toss.get(player)), 3)

        all_players = set(xpoints_post_toss.keys()) | set(xpoints_base.keys())
        xpoints_delta: Dict[str, float] = {
            player: round(
                _safe_float(xpoints_post_toss.get(player)) - _safe_float(xpoints_base.get(player)),
                3,
            )
            for player in all_players
        }

        # players_by_axis: combine general + venue rows per axis
        players_by_axis: Dict[str, Any] = {}
        player_drill_links: Dict[str, Dict[str, str]] = {"general": {}, "venue": {}}
        player_link_scores: Dict[str, Dict[str, float]] = {"general": {}, "venue": {}}
        for axis_name in (general_bundle["axes"] or {}).keys():
            general_axis = general_bundle["axes"][axis_name]
            venue_axis = (venue_bundle["axes"] or {}).get(axis_name) or {"players": []}
            players_by_axis[axis_name] = {
                "kind": general_axis["kind"],
                "innings": general_axis["innings"],
                "team": general_axis["team"],
                "opponent": general_axis["opponent"],
                "general": {
                    "players": general_axis["players"],
                    "sample_balls": general_axis["sample_balls"],
                    "sample_players": general_axis["sample_players"],
                },
                "venue": {
                    "players": venue_axis.get("players", []),
                    "sample_balls": venue_axis.get("sample_balls", 0),
                    "sample_players": venue_axis.get("sample_players", 0),
                },
            }

            for scope, axis_rows in (
                ("general", general_axis.get("players", [])),
                ("venue", venue_axis.get("players", [])),
            ):
                for row in axis_rows:
                    player = str(row.get("player") or "").strip()
                    link = str(row.get("drill_link") or "").strip()
                    if not player or not link:
                        continue
                    points = _safe_float(row.get("xpoints"))
                    previous = _safe_float(player_link_scores[scope].get(player))
                    if player not in player_drill_links[scope] or points >= previous:
                        player_link_scores[scope][player] = points
                        player_drill_links[scope][player] = link

        result = {
            "success": True,
            "cached": False,
            "source": payload.source,
            "venue": normalized_venue,
            "match_id": payload.match_id,
            "team1_id": payload.team1_id,
            "team2_id": payload.team2_id,
            "batting_first_team": batting_first_team,
            "batting_second_team": batting_second_team,
            "team1_xi": team1_xi,
            "team2_xi": team2_xi,
            "impact_subs": impact_subs,
            "day_or_night": payload.day_or_night,
            "windows": {
                "general": {
                    "start_date": general_start.isoformat(),
                    "end_date": general_end.isoformat(),
                },
                "venue": {
                    "start_date": venue_start.isoformat(),
                    "end_date": venue_end.isoformat(),
                },
            },
            "players_by_axis": players_by_axis,
            "xpoints_post_toss": xpoints_post_toss,
            "xpoints_base": xpoints_base,
            "xpoints_delta": xpoints_delta,
            "player_drill_links": player_drill_links,
            "drill_down_links": {
                "general": general_bundle["drill_down_links"],
                "venue": venue_bundle["drill_down_links"],
            },
            "computed_at": datetime.utcnow().isoformat() + "Z",
        }

        _set_cached_post_toss(cache_key, result)
        _log_post_toss_prediction(
            db=db,
            match_id=payload.match_id,
            payload_data={
                "match_id": payload.match_id,
                "venue": normalized_venue,
                "team1_id": payload.team1_id,
                "team2_id": payload.team2_id,
                "batting_first_team": batting_first_team,
                "team1_xi": team1_xi,
                "team2_xi": team2_xi,
                "impact_subs": impact_subs,
                "general_window_years": payload.general_window_years,
                "venue_window_years": payload.venue_window_years,
                "day_or_night": payload.day_or_night,
            },
            result_data={
                "players_by_axis": result.get("players_by_axis"),
                "xpoints_post_toss": result.get("xpoints_post_toss"),
                "xpoints_base": result.get("xpoints_base"),
                "xpoints_delta": result.get("xpoints_delta"),
                "player_drill_links": result.get("player_drill_links"),
                "windows": result.get("windows"),
                "computed_at": result.get("computed_at"),
            },
            source=payload.source,
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to build post-toss preview: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to build post-toss preview: {exc}")


@router.post("/scrape-cricinfo")
def scrape_cricinfo_endpoint(
    payload: ScrapeCricinfoPayload,
    db: Session = Depends(get_session),
):
    try:
        scraped = scrape_match_setup(payload.url, db=db, timeout_seconds=5.0)
        return {"success": scraped.get("source") != "failed", **scraped}
    except Exception as exc:
        logger.error("Cricinfo scrape failed for %s: %s", payload.url, exc, exc_info=True)
        return {
            "success": False,
            "source": "failed",
            "error": str(exc),
            "team1_xi": [],
            "team2_xi": [],
            "impact_subs": [],
            "toss_winner": None,
            "toss_decision": None,
            "batting_first_team": None,
            "venue": None,
            "match_date": None,
        }
