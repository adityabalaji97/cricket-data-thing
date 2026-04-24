"""
Natural Language to Query Builder service.
Translates natural language cricket queries into structured filters
for the query builder API.
"""
import os
import json
import time
import logging
import re
import hashlib
from typing import Dict, Any, Optional, List
from openai import OpenAI
from sqlalchemy.orm import Session
from sqlalchemy import text
try:
    from venue_standardization import VENUE_STANDARDIZATION
except Exception:  # pragma: no cover - defensive fallback
    VENUE_STANDARDIZATION = {}

logger = logging.getLogger(__name__)

# In-memory cache with TTL
_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 86400  # 24 hours
MODEL_PRIMARY = "gpt-4o"
MODEL_FALLBACK = "gpt-4o-mini"
DEFAULT_NL2QUERY_MODEL = MODEL_FALLBACK  # kept for backward compat in tests
MONTHLY_COST_CAP = 15.0  # USD — leaves $5 buffer on $20/mo subscription
MAX_FEW_SHOT_EXAMPLES = 5

# Approximate per-token costs (USD) as of April 2026
MODEL_COSTS = {
    "gpt-4o": {"prompt": 2.50 / 1_000_000, "completion": 10.00 / 1_000_000},
    "gpt-4o-mini": {"prompt": 0.15 / 1_000_000, "completion": 0.60 / 1_000_000},
}
ALLOWED_RECOMMENDED_COLUMNS = {
    "balls",
    "balls_faced",
    "runs",
    "runs_conceded",
    "strike_rate",
    "average",
    "wickets",
    "dots",
    "boundaries",
    "fours",
    "sixes",
    "dot_percentage",
    "boundary_percentage",
    "economy",
    "control_percentage",
    "percent_balls",
    "balls_per_dismissal",
    "balls_per_wicket",
    "overs",
    "innings_count",
}
VALID_RECOMMENDED_CHART_TYPES = {"bar", "scatter"}

SYSTEM_PROMPT = """You are a cricket analytics query parser. Convert natural language queries about cricket into structured JSON filters for a ball-by-ball cricket statistics database.

## Output Format
Return a JSON object with these fields:
{
  "filters": { ... },
  "query_mode": "delivery" | "batting_stats" | "bowling_stats",
  "group_by": [...],
  "explanation": "Human-readable explanation of what the query does",
  "confidence": "high" | "medium" | "low",
  "suggestions": ["optional improvement suggestions"],
  "recommended_columns": ["4-6 metric columns to prioritize in results display"],
  "recommended_chart": {
    "type": "bar" | "scatter" | null,
    "x_axis": "column_name",
    "y_axis": "column_name",
    "reason": "brief explanation"
  },
  "interpretation": {
    "summary": "One-line summary of what will be queried",
    "parsed_entities": [
      {"type": "player" | "team" | "filter", "value": "resolved value", "matched_from": "text fragment from user query"}
    ],
    "suggestions": ["query refinement suggestions as short phrases or prompts"]
  }
}

## Available Filters

### Player filters
- "batters": list of batter names (use full names, e.g. "V Kohli", "MS Dhoni", "JC Buttler")
- "bowlers": list of bowler names (use full names)
- "players": list of player names (when role is ambiguous)

### Team filters
- "batting_teams": list of full team names
- "bowling_teams": list of full team names
- "teams": list of full team names (when batting/bowling context unclear)
- "venue": a single venue/ground string (e.g. "Eden Gardens")

### League/competition filters
- "leagues": list of league abbreviations. Valid values: "IPL", "BBL", "PSL", "CPL", "SA20", "ILT20", "BPL", "LPL", "T20 Blast", "T20I"
- "include_international": true/false (for international T20I matches)

### Batting hand filter
- "bat_hand": "RHB" or "LHB" (right-hand or left-hand batter)

### Bowling style filters
- "bowl_style": list of specific bowling styles. Valid values: "RF" (right fast), "RFM" (right fast-medium), "RM" (right medium), "LF" (left fast), "LFM" (left fast-medium), "LM" (left medium), "RO" (right off-spin), "RL" (right leg-spin), "LO" (left orthodox/slow left arm), "LC" (left chinaman)
- "bowl_kind": list for broad grouping. Valid values: "pace bowler", "spin bowler", "mixture/unknown"

### Over/phase filters
- "over_min": integer 0-19 (minimum over number)
- "over_max": integer 0-19 (maximum over number)
- Phase mappings:
  - Powerplay: over_min=0, over_max=5
  - Middle overs: over_min=6, over_max=14
  - Death overs: over_min=15, over_max=19

### Innings filter
- "innings": 1 or 2
- "is_chase": true/false (true means innings=2 chases)
- "match_outcome": list. Valid values: "win", "loss", "tie", "no_result" (always batting-side perspective)
- "chase_outcome": list. Valid values: "win", "loss", "tie", "no_result" (applies to innings=2)
- "toss_decision": list. Valid values: "bat", "field"
- "toss_match_outcome": group_by only. Values: "win", "loss", "tie", "no_result".
  Shows match outcome from the TOSS-WINNING team's perspective.

### Query mode
- "query_mode": "delivery" (default), "batting_stats", or "bowling_stats"
- Default to "delivery" for almost all queries — it provides the richest aggregated stats (control%, dot%, boundary%, balls_per_dismissal).
- Only use "batting_stats" when the query explicitly needs match-level batting results (e.g. "100+ scores", "fifties list", "team wins while chasing grouped by match").
- Only use "bowling_stats" when the query explicitly needs match-level bowling results (e.g. "5-wicket hauls", "wicketless games").
- For general player/team performance queries (e.g. "bumrah by competition", "kohli in powerplay"), always use "delivery".

### Delivery detail filters
- "line": list. Valid values: "ON_THE_STUMPS", "OUTSIDE_OFFSTUMP", "DOWN_LEG", "WIDE_OUTSIDE_OFFSTUMP", "WIDE_DOWN_LEG"
- "length": list. Valid values: "GOOD_LENGTH", "YORKER", "FULL", "SHORT", "BACK_OF_A_LENGTH", "FULL_TOSS", "BOUNCER"
- "shot": list. Valid values: "COVER_DRIVE", "STRAIGHT_DRIVE", "ON_DRIVE", "OFF_DRIVE", "FLICK", "PULL", "HOOK", "CUT", "LATE_CUT", "SQUARE_CUT", "SWEEP", "REVERSE_SWEEP", "SLOG", "SLOG_SWEEP", "DEFENDED", "LEFT_ALONE", "GLANCE", "UPPER_CUT", "SCOOP", "PADDLE", "INSIDE_OUT", "LOFTED_DRIVE"
- "control": 0 (uncontrolled) or 1 (controlled)
- "wagon_zone": list of integers 0-8 (wagon wheel zones)
- "dismissal": list. Valid values: "caught", "bowled", "lbw", "run out", "stumped", "caught and bowled", "hit wicket"

### Result filters
- "min_balls": minimum number of balls (for meaningful samples, suggest 20-50)
- "min_runs": minimum runs threshold for grouped/stat queries
- "max_runs": maximum runs threshold for grouped/stat queries
- "min_wickets": minimum wickets threshold (bowling_stats or delivery mode with bowler grouping)
- "max_wickets": maximum wickets threshold (bowling_stats or delivery mode with bowler grouping)
- "start_date": "YYYY-MM-DD" format
- "end_date": "YYYY-MM-DD" format

## Recommended metric columns
Also return "recommended_columns": a list of 4-6 metric columns most relevant to this query.
Available metrics: balls, runs, strike_rate, average, wickets, dots, boundaries, fours, sixes,
dot_percentage, boundary_percentage, economy, control_percentage, percent_balls, runs_conceded,
balls_per_dismissal, balls_per_wicket, overs, innings_count, balls_faced.
Choose columns that best answer the user's question.

## Recommended chart
If the query groups data and would benefit from a chart, return:
"recommended_chart": {
  "type": "bar" | "scatter" | null,
  "x_axis": "column_name",
  "y_axis": "column_name",
  "reason": "brief explanation"
}
Return null if the data isn't suitable for charting (for example, ungrouped or single-row output).
Bar charts work well for comparing grouped categories. Scatter plots work for showing relationships between two metrics.

## Available group_by columns
venue, country, match_id, competition, year, batting_team, bowling_team, batter, bowler, innings, phase, match_outcome, chase_outcome, toss_decision, toss_match_outcome, bat_hand, bowl_style, bowl_kind, crease_combo, line, length, shot, control, wagon_zone, dismissal

## Team Name Mappings (use full names in filters)
- CSK → Chennai Super Kings
- MI → Mumbai Indians
- KKR → Kolkata Knight Riders
- GT → Gujarat Titans
- LSG → Lucknow Super Giants
- PBKS / KXIP → Punjab Kings
- RCB → Royal Challengers Bangalore
- DC / DD → Delhi Capitals
- SRH → Sunrisers Hyderabad
- RR → Rajasthan Royals

## League Aliases
- IPL → Indian Premier League
- BBL → Big Bash League
- PSL → Pakistan Super League
- CPL → Caribbean Premier League
- T20I → International Twenty20

## Rules
1. Always include a sensible "group_by" for the query. If the user asks about a specific batter, group by "batter" at minimum.
2. Set "min_balls" to a reasonable value (20-50) for statistical significance unless the user specifies otherwise.
3. For "vs spin" queries, use "bowl_kind": ["spin bowler"]. For specific types like "vs leg spin", use "bowl_style": ["RL", "LC"].
4. For "vs pace" queries, use "bowl_kind": ["pace bowler"].
5. Use correct phase over ranges: powerplay=0-5, middle=6-14, death=15-19.
6. If the query mentions a league (IPL, BBL, etc.), add it to "leagues".
7. If the query is not about cricket or is too vague, set confidence to "low" and add helpful suggestions.
8. Return ONLY valid JSON, no extra text.
9. If the user wants to compare LHB vs RHB (e.g. "vs lhb/rhb"), do NOT set bat_hand as a filter. Instead, add "bat_hand" to group_by.
10. Use the player's full first and last name when possible (e.g. "Jasprit Bumrah" not "J Bumrah", "Virat Kohli" not "V Kohli", "Varun Chakravarthy" not "V Chakravarthy"). The system will resolve names to the database format automatically.
11. When the user asks about toss impact on winning (e.g. "toss decision vs match outcome"), use group_by: ["toss_decision", "toss_match_outcome"] with query_mode: "batting_stats". Do NOT use "match_outcome" for toss analysis — use "toss_match_outcome" instead.
12. For team match-level queries (e.g. "CSK in chasing wins"), group by match_id, batting_team, bowling_team, and year. This shows individual match results rather than aggregated totals.
13. When a query needs both bowling style filters (bowl_kind/bowl_style) AND per-match bowling stats (e.g. "spinners with 4+ wickets"), use query_mode: "delivery" with group_by: ["bowler", "match_id"] and min_wickets filter. Do NOT use bowling_stats mode when bowl_kind or bowl_style filters are needed — those columns only exist in delivery_details.
14. When a query says a bowler "conceded", "conceding", or "gave away" runs (e.g. "Bumrah conceding 30+ runs"), treat it as bowling analysis: use "bowlers" (not "players") and bowling-focused thresholds in bowling_stats mode.
"""

EXAMPLE_QUERIES = [
    {
        "text": "kohli vs spin since 2023",
        "category": "Delivery analysis"
    },
    {
        "text": "csk powerplay batting over the years",
        "category": "Batting stats"
    },
    {
        "text": "MS Dhoni in winning vs losing chases in IPL",
        "category": "Match context"
    },
    {
        "text": "csk in chasing wins since 2018",
        "category": "Team context"
    },
    {
        "text": "varun chakravarthy vs lhb/rhb",
        "category": "Group by bat_hand"
    },
    {
        "text": "bumrah in 2026 grouped by competition",
        "category": "Group by competition"
    },
    {
        "text": "shubman gill batting in first innings vs second innings",
        "category": "Innings comparison"
    },
    {
        "text": "rashid khan bowling by year",
        "category": "Bowling stats"
    }
]


def _get_cache_key(query: str) -> str:
    return query.strip().lower()


def _get_cached(query: str) -> Optional[Dict[str, Any]]:
    key = _get_cache_key(query)
    if key in _cache:
        entry = _cache[key]
        if time.time() - entry["timestamp"] < CACHE_TTL:
            return entry["result"]
        else:
            del _cache[key]
    return None


def _set_cache(query: str, result: Dict[str, Any]):
    key = _get_cache_key(query)
    _cache[key] = {"result": result, "timestamp": time.time()}


def get_cache_size() -> int:
    # Clean expired entries
    now = time.time()
    expired = [k for k, v in _cache.items() if now - v["timestamp"] >= CACHE_TTL]
    for k in expired:
        del _cache[k]
    return len(_cache)


def _infer_query_mode_hint(query: str) -> str:
    q = (query or "").lower()
    bowling_markers = {"wicketless", "wickets", "economy", "bowling", "bowler", "5-wicket", "five wicket"}
    batting_markers = {"batting", "scores", "score", "fifties", "fifty", "century", "hundred", "innings"}
    if any(marker in q for marker in bowling_markers):
        return "bowling_stats"
    if any(marker in q for marker in batting_markers):
        return "batting_stats"
    return "delivery"


def _serialize_few_shot_output(example: Dict[str, Any]) -> str:
    parsed_filters = example.get("parsed_filters") if isinstance(example.get("parsed_filters"), dict) else {}
    suggestions = example.get("suggestions") if isinstance(example.get("suggestions"), list) else []
    interpretation_payload = example.get("interpretation") if isinstance(example.get("interpretation"), dict) else {}
    recommended_columns = (
        example.get("recommended_columns")
        if isinstance(example.get("recommended_columns"), list)
        else []
    )
    recommended_chart = (
        example.get("recommended_chart")
        if isinstance(example.get("recommended_chart"), dict)
        else None
    )
    payload = {
        "filters": parsed_filters,
        "query_mode": example.get("query_mode") or parsed_filters.get("query_mode") or "delivery",
        "group_by": example.get("group_by") if isinstance(example.get("group_by"), list) else [],
        "explanation": example.get("explanation") or "",
        "confidence": example.get("confidence") or "high",
        "suggestions": suggestions,
        "recommended_columns": recommended_columns,
        "recommended_chart": recommended_chart,
        "interpretation": {
            "summary": interpretation_payload.get("summary") or example.get("explanation") or "",
            "parsed_entities": interpretation_payload.get("parsed_entities")
            if isinstance(interpretation_payload.get("parsed_entities"), list)
            else [],
            "suggestions": interpretation_payload.get("suggestions")
            if isinstance(interpretation_payload.get("suggestions"), list)
            else suggestions,
        },
    }
    return json.dumps(payload, ensure_ascii=True)


def get_few_shot_examples(query: str, db: Optional[Session], limit: int = MAX_FEW_SHOT_EXAMPLES) -> List[Dict[str, Any]]:
    """Fetch top successful historical queries to use as few-shot examples."""
    if db is None:
        return []

    normalized_query = _normalize_text(query)
    query_tokens = set(token for token in normalized_query.split() if token)
    if not query_tokens:
        return []

    try:
        rows = (
            db.execute(
                text(
                    """
                    SELECT
                        query_text,
                        parsed_filters,
                        query_mode,
                        group_by,
                        explanation,
                        confidence,
                        created_at
                    FROM nl_query_log
                    WHERE user_feedback = 'good'
                      AND execution_success IS TRUE
                      AND parsed_filters IS NOT NULL
                    ORDER BY created_at DESC
                    LIMIT 200
                    """
                )
            )
            .mappings()
            .all()
        )
    except Exception as exc:
        logger.debug("Skipping few-shot retrieval; nl_query_log unavailable: %s", exc)
        return []

    if not rows:
        return []

    mode_hint = _infer_query_mode_hint(query)
    ranked: List[Dict[str, Any]] = []

    for row in rows:
        candidate_query = str(row.get("query_text") or "").strip()
        if not candidate_query:
            continue

        candidate_tokens = set(token for token in _normalize_text(candidate_query).split() if token)
        overlap = len(query_tokens.intersection(candidate_tokens))
        union = len(query_tokens.union(candidate_tokens))
        lexical_score = (overlap / union) if union else 0.0

        candidate_mode = row.get("query_mode") or "delivery"
        mode_score = 0.35 if candidate_mode == mode_hint else 0.0

        parsed_filters = row.get("parsed_filters")
        parsed_filters = parsed_filters if isinstance(parsed_filters, dict) else {}
        created_at_value = row.get("created_at")
        created_at_epoch = created_at_value.timestamp() if hasattr(created_at_value, "timestamp") else 0.0

        ranked.append(
            {
                "query_text": candidate_query,
                "parsed_filters": parsed_filters,
                "query_mode": candidate_mode,
                "group_by": row.get("group_by") if isinstance(row.get("group_by"), list) else [],
                "explanation": row.get("explanation") or "",
                "confidence": row.get("confidence") or "high",
                "created_at_epoch": created_at_epoch,
                "_score": lexical_score + mode_score,
            }
        )

    if not ranked:
        return []

    ranked.sort(key=lambda item: (item.get("_score", 0.0), item.get("created_at_epoch", 0.0)), reverse=True)
    selected = [item for item in ranked if item.get("_score", 0.0) > 0][:limit]

    if len(selected) < limit:
        seen_queries = {item["query_text"] for item in selected}
        fallback = [item for item in ranked if item["query_text"] not in seen_queries and item.get("query_mode") == mode_hint]
        selected.extend(fallback[: max(0, limit - len(selected))])

    if len(selected) < limit:
        seen_queries = {item["query_text"] for item in selected}
        fallback = [item for item in ranked if item["query_text"] not in seen_queries]
        selected.extend(fallback[: max(0, limit - len(selected))])

    for item in selected:
        item.pop("_score", None)
        item.pop("created_at_epoch", None)

    return selected[:limit]


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate USD cost for a single API call."""
    costs = MODEL_COSTS.get(model, MODEL_COSTS[MODEL_FALLBACK])
    return (prompt_tokens * costs["prompt"]) + (completion_tokens * costs["completion"])


def select_model(db: Optional[Session] = None) -> str:
    """Pick GPT-4o if under monthly spend cap, otherwise fall back to 4o-mini."""
    if db is None:
        try:
            from database import SessionLocal
            db = SessionLocal()
            owns_session = True
        except Exception:
            return MODEL_PRIMARY
    else:
        owns_session = False

    try:
        from datetime import datetime
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        row = db.execute(
            text(
                "SELECT COALESCE(SUM(estimated_cost_usd), 0) AS total "
                "FROM nl_query_log WHERE created_at >= :month_start"
            ),
            {"month_start": month_start},
        ).fetchone()
        total_spend = float(row[0]) if row else 0.0
        return MODEL_PRIMARY if total_spend < MONTHLY_COST_CAP else MODEL_FALLBACK
    except Exception as exc:
        logger.warning("select_model fallback due to: %s", exc)
        return MODEL_PRIMARY
    finally:
        if owns_session:
            try:
                db.close()
            except Exception:
                pass


def get_monthly_usage(db: Session) -> Dict[str, Any]:
    """Return current month's NL query spend summary."""
    from datetime import datetime
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    row = db.execute(
        text(
            """
            SELECT
                COUNT(*) AS total_queries,
                COALESCE(SUM(estimated_cost_usd), 0) AS total_cost,
                COALESCE(SUM(prompt_tokens), 0) AS total_prompt_tokens,
                COALESCE(SUM(completion_tokens), 0) AS total_completion_tokens,
                COALESCE(SUM(CASE WHEN model_used = :primary THEN 1 ELSE 0 END), 0) AS primary_queries,
                COALESCE(SUM(CASE WHEN model_used = :fallback THEN 1 ELSE 0 END), 0) AS fallback_queries
            FROM nl_query_log
            WHERE created_at >= :month_start
            """
        ),
        {"month_start": month_start, "primary": MODEL_PRIMARY, "fallback": MODEL_FALLBACK},
    ).fetchone()

    total_cost = float(row[1]) if row else 0.0
    return {
        "month": month_start.strftime("%Y-%m"),
        "total_queries": int(row[0]) if row else 0,
        "total_cost_usd": round(total_cost, 4),
        "monthly_cap_usd": MONTHLY_COST_CAP,
        "remaining_usd": round(max(MONTHLY_COST_CAP - total_cost, 0), 4),
        "total_prompt_tokens": int(row[2]) if row else 0,
        "total_completion_tokens": int(row[3]) if row else 0,
        "primary_model": MODEL_PRIMARY,
        "fallback_model": MODEL_FALLBACK,
        "primary_queries": int(row[4]) if row else 0,
        "fallback_queries": int(row[5]) if row else 0,
        "active_model": MODEL_PRIMARY if total_cost < MONTHLY_COST_CAP else MODEL_FALLBACK,
    }


def call_openai(
    query: str,
    few_shot_examples: Optional[List[Dict[str, Any]]] = None,
    model: str = DEFAULT_NL2QUERY_MODEL,
) -> Dict[str, Any]:
    """Call OpenAI to parse a natural language cricket query.

    Returns a dict with the parsed JSON plus _meta with token usage.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not configured")

    client = OpenAI(api_key=api_key)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    for example in few_shot_examples or []:
        query_text = str(example.get("query_text") or "").strip()
        if not query_text:
            continue
        messages.append({"role": "user", "content": query_text})
        messages.append({"role": "assistant", "content": _serialize_few_shot_output(example)})
    messages.append({"role": "user", "content": query})

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=1000
    )

    content = response.choices[0].message.content
    parsed = json.loads(content)

    # Attach token usage metadata (non-serialized, stripped before caching)
    usage = response.usage
    if usage:
        parsed["_meta"] = {
            "model_used": model,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "estimated_cost_usd": estimate_cost(model, usage.prompt_tokens, usage.completion_tokens),
        }
    else:
        parsed["_meta"] = {
            "model_used": model,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "estimated_cost_usd": 0.0,
        }

    return parsed


# Valid values for validation
VALID_BAT_HAND = {"RHB", "LHB"}
VALID_BOWL_STYLE = {"RF", "RFM", "RM", "LF", "LFM", "LM", "RO", "RL", "LO", "LC"}
VALID_BOWL_KIND = {"pace bowler", "spin bowler", "mixture/unknown"}
VALID_LEAGUES = {"IPL", "BBL", "PSL", "CPL", "SA20", "ILT20", "BPL", "LPL", "T20 Blast", "T20I"}
VALID_QUERY_MODE = {"delivery", "batting_stats", "bowling_stats"}
VALID_MATCH_OUTCOME = {"win", "loss", "tie", "no_result"}
VALID_TOSS_DECISION = {"bat", "field"}
VALID_CONFIDENCE = {"high", "medium", "low"}
VALID_GROUP_BY = {
    "venue", "country", "match_id", "competition", "year",
    "batting_team", "bowling_team", "batter", "bowler",
    "innings", "phase", "bat_hand", "bowl_style", "bowl_kind",
    "crease_combo", "line", "length", "shot", "control",
    "wagon_zone", "dismissal", "match_outcome", "chase_outcome", "toss_decision",
    "toss_match_outcome"
}


def _normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _build_venue_lookup() -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    candidates: Dict[str, str] = {}
    for alias, canonical in (VENUE_STANDARDIZATION or {}).items():
        if alias and canonical:
            candidates[alias] = canonical
            candidates[canonical] = canonical
    # Ensure key venues are always available even if mapping import fails.
    candidates.setdefault("Eden Gardens", "Eden Gardens")
    candidates.setdefault("Eden Gardens, Kolkata", "Eden Gardens")
    for raw_name, canonical in candidates.items():
        normalized = _normalize_text(raw_name)
        # Avoid very short fragments that cause false matches.
        if len(normalized) < 8 and len(normalized.split()) < 2:
            continue
        if normalized not in lookup:
            lookup[normalized] = canonical
    return lookup


VENUE_LOOKUP = _build_venue_lookup()


def _infer_venue_from_query(query: str) -> Optional[str]:
    normalized_query = f" {_normalize_text(query)} "
    best_match = None
    best_len = -1
    for venue_text, canonical in VENUE_LOOKUP.items():
        token = f" {venue_text} "
        if token in normalized_query and len(venue_text) > best_len:
            best_match = canonical
            best_len = len(venue_text)
    return best_match


def _contains_explicit_end_bound(query: str) -> bool:
    q = (query or "").lower()
    return bool(
        re.search(r"\bbetween\b.+\band\b", q)
        or re.search(r"\bfrom\b.+\bto\b", q)
        or re.search(r"\b(until|till|through|thru|upto|up to|before|ending)\b", q)
    )


def _append_group_by(group_by: List[str], column: str) -> List[str]:
    if column in group_by:
        return group_by
    return [*group_by, column]


def _build_explanation(filters: Dict[str, Any], group_by: List[str]) -> str:
    mode = filters.get("query_mode", "delivery")
    mode_text = {
        "delivery": "delivery-level data",
        "batting_stats": "innings-level batting stats",
        "bowling_stats": "innings-level bowling stats",
    }.get(mode, "delivery-level data")

    scope_bits = []
    if filters.get("batters"):
        scope_bits.append(f"batters {', '.join(filters['batters'])}")
    if filters.get("bowlers"):
        scope_bits.append(f"bowlers {', '.join(filters['bowlers'])}")
    if filters.get("teams"):
        scope_bits.append(f"teams {', '.join(filters['teams'])}")
    if filters.get("venue"):
        scope_bits.append(f"venue {filters['venue']}")

    constraints = []
    if filters.get("min_runs") is not None:
        constraints.append(f"min runs {filters['min_runs']}")
    if filters.get("max_runs") is not None:
        constraints.append(f"max runs {filters['max_runs']}")
    if filters.get("min_wickets") is not None:
        constraints.append(f"min wickets {filters['min_wickets']}")
    if filters.get("max_wickets") is not None:
        constraints.append(f"max wickets {filters['max_wickets']}")
    if filters.get("start_date"):
        constraints.append(f"from {filters['start_date']}")
    if filters.get("end_date"):
        constraints.append(f"to {filters['end_date']}")

    parts = [f"This query retrieves {mode_text}"]
    if scope_bits:
        parts.append(f"for {', '.join(scope_bits)}")
    if constraints:
        parts.append(f"with {', '.join(constraints)}")
    if group_by:
        parts.append(f"grouped by {', '.join(group_by)}")
    return " ".join(parts).strip() + "."


def _sanitize_confidence(value: Any, default: str = "medium") -> str:
    candidate = str(value).strip().lower() if value is not None else ""
    if candidate in VALID_CONFIDENCE:
        return candidate
    return default


def _sanitize_suggestions(raw_suggestions: Any, limit: int = 5) -> List[str]:
    if not isinstance(raw_suggestions, list):
        return []

    suggestions: List[str] = []
    seen = set()
    for item in raw_suggestions:
        suggestion = str(item).strip()
        if not suggestion:
            continue
        key = suggestion.lower()
        if key in seen:
            continue
        seen.add(key)
        suggestions.append(suggestion[:200])
        if len(suggestions) >= limit:
            break
    return suggestions


def _sanitize_recommended_columns(raw_columns: Any, limit: int = 6) -> List[str]:
    if not isinstance(raw_columns, list):
        return []

    columns: List[str] = []
    seen = set()
    for item in raw_columns:
        column = str(item or "").strip().lower()
        if not column or column not in ALLOWED_RECOMMENDED_COLUMNS:
            continue
        if column in seen:
            continue
        seen.add(column)
        columns.append(column)
        if len(columns) >= limit:
            break
    return columns


def _default_recommended_columns(query: str, filters: Dict[str, Any]) -> List[str]:
    q = (query or "").lower()
    mode = (filters.get("query_mode") or "delivery").lower()

    if any(token in q for token in ["boundary", "boundaries", "four", "fours", "six", "sixes"]):
        return ["balls", "runs", "boundaries", "fours", "sixes", "boundary_percentage"]

    if mode == "bowling_stats" or any(token in q for token in ["economy", "bowling", "wicket", "wickets", "dot"]):
        return ["balls", "runs_conceded", "wickets", "economy", "dots", "dot_percentage"]

    if mode == "batting_stats":
        return ["balls", "runs", "average", "strike_rate", "boundaries", "boundary_percentage"]

    if any(token in q for token in ["control", "controlled", "uncontrolled"]):
        return ["balls", "runs", "control_percentage", "strike_rate", "dot_percentage", "boundary_percentage"]

    return ["balls", "runs", "strike_rate", "average", "dot_percentage", "boundary_percentage"]


def _resolve_recommended_columns(raw_columns: Any, query: str, filters: Dict[str, Any]) -> List[str]:
    chosen = _sanitize_recommended_columns(raw_columns, limit=6)
    fallback = _sanitize_recommended_columns(_default_recommended_columns(query, filters), limit=6)

    merged: List[str] = []
    seen = set()
    for column in [*chosen, *fallback]:
        if column in seen:
            continue
        seen.add(column)
        merged.append(column)
        if len(merged) >= 6:
            break

    return merged


def _sanitize_recommended_chart(
    raw_chart: Any,
    query: str,
    filters: Dict[str, Any],
    group_by: List[str],
    recommended_columns: List[str],
) -> Optional[Dict[str, str]]:
    if raw_chart is None:
        return None
    if not isinstance(raw_chart, dict):
        return None

    chart_type = str(raw_chart.get("type") or "").strip().lower()
    if chart_type in {"", "none", "null"}:
        return None
    if chart_type not in VALID_RECOMMENDED_CHART_TYPES:
        return None

    metric_candidates = [
        col for col in (recommended_columns or _default_recommended_columns(query, filters))
        if col in ALLOWED_RECOMMENDED_COLUMNS
    ]
    if not metric_candidates:
        metric_candidates = ["runs", "strike_rate"]

    reason = str(raw_chart.get("reason") or "").strip()
    if not reason:
        reason = (
            "Compares grouped categories clearly."
            if chart_type == "bar"
            else "Shows relationship between two key metrics."
        )
    reason = reason[:240]

    x_axis_raw = str(raw_chart.get("x_axis") or "").strip().lower()
    y_axis_raw = str(raw_chart.get("y_axis") or "").strip().lower()

    if chart_type == "bar":
        selected_metric = None
        if y_axis_raw in ALLOWED_RECOMMENDED_COLUMNS:
            selected_metric = y_axis_raw
        elif x_axis_raw in ALLOWED_RECOMMENDED_COLUMNS:
            selected_metric = x_axis_raw
        else:
            selected_metric = metric_candidates[0]

        if selected_metric not in ALLOWED_RECOMMENDED_COLUMNS:
            return None

        x_axis = x_axis_raw or (group_by[0] if group_by else "")
        return {
            "type": "bar",
            "x_axis": x_axis,
            "y_axis": selected_metric,
            "reason": reason,
        }

    x_metric = x_axis_raw if x_axis_raw in ALLOWED_RECOMMENDED_COLUMNS else None
    y_metric = y_axis_raw if y_axis_raw in ALLOWED_RECOMMENDED_COLUMNS else None

    if x_metric is None:
        x_metric = metric_candidates[0]
    if y_metric is None or y_metric == x_metric:
        y_metric = next((col for col in metric_candidates if col != x_metric), None)

    if not x_metric or not y_metric or x_metric == y_metric:
        return None

    return {
        "type": "scatter",
        "x_axis": x_metric,
        "y_axis": y_metric,
        "reason": reason,
    }


def _match_query_fragment(query: str, value: str) -> Optional[str]:
    normalized_query = _normalize_text(query)
    normalized_value = _normalize_text(value)
    if not normalized_query or not normalized_value:
        return None

    query_tokens = set(token for token in normalized_query.split() if token)
    value_tokens = [token for token in normalized_value.split() if token]
    for token in value_tokens:
        if token in query_tokens and len(token) >= 3:
            return token

    if normalized_value in normalized_query:
        return normalized_value
    return None


def _derive_entities_from_filters(filters: Dict[str, Any], query: str) -> List[Dict[str, str]]:
    entities: List[Dict[str, str]] = []
    seen = set()

    def _add(entity_type: str, value: Any):
        text_value = str(value).strip()
        if not text_value:
            return
        key = (entity_type, text_value.lower())
        if key in seen:
            return
        seen.add(key)
        matched = _match_query_fragment(query, text_value)
        payload = {"type": entity_type, "value": text_value}
        if matched:
            payload["matched_from"] = matched
        entities.append(payload)

    for key in ["batters", "bowlers", "players"]:
        for value in filters.get(key, []) if isinstance(filters.get(key), list) else []:
            _add("player", value)

    for key in ["teams", "batting_teams", "bowling_teams"]:
        for value in filters.get(key, []) if isinstance(filters.get(key), list) else []:
            _add("team", value)

    if filters.get("venue"):
        _add("filter", f"venue: {filters['venue']}")

    for key in ["leagues", "bowl_kind", "bowl_style", "match_outcome", "chase_outcome", "toss_decision"]:
        values = filters.get(key)
        if isinstance(values, list):
            for value in values:
                _add("filter", value)

    for key in ["bat_hand", "innings", "start_date", "end_date", "min_balls", "min_runs", "max_runs", "min_wickets", "max_wickets"]:
        if filters.get(key) is not None:
            _add("filter", f"{key}: {filters[key]}")

    over_min = filters.get("over_min")
    over_max = filters.get("over_max")
    if over_min is not None or over_max is not None:
        if over_min is not None and over_max is not None:
            _add("filter", f"overs {over_min}-{over_max}")
        elif over_min is not None:
            _add("filter", f"from over {over_min}")
        elif over_max is not None:
            _add("filter", f"up to over {over_max}")

    if filters.get("query_mode"):
        _add("filter", f"mode: {filters['query_mode']}")

    return entities[:12]


def _sanitize_interpretation(
    parsed: Dict[str, Any],
    query: str,
    filters: Dict[str, Any],
    fallback_summary: str,
    fallback_suggestions: List[str],
) -> Dict[str, Any]:
    interpretation = parsed.get("interpretation") if isinstance(parsed.get("interpretation"), dict) else {}
    summary = str(interpretation.get("summary") or parsed.get("explanation") or fallback_summary or "").strip()
    if not summary:
        summary = fallback_summary

    parsed_entities: List[Dict[str, str]] = []
    seen = set()
    raw_entities = interpretation.get("parsed_entities") if isinstance(interpretation.get("parsed_entities"), list) else []
    for entity in raw_entities:
        if not isinstance(entity, dict):
            continue
        entity_type = str(entity.get("type") or "").strip().lower()
        value = str(entity.get("value") or "").strip()
        matched_from = str(entity.get("matched_from") or "").strip()
        if not value:
            continue

        if entity_type in {"player", "batter", "bowler"}:
            entity_type = "player"
        elif entity_type in {"team", "batting_team", "bowling_team"}:
            entity_type = "team"
        else:
            entity_type = "filter"

        key = (entity_type, value.lower())
        if key in seen:
            continue
        seen.add(key)

        payload = {"type": entity_type, "value": value}
        if matched_from:
            payload["matched_from"] = matched_from
        parsed_entities.append(payload)

    if not parsed_entities:
        parsed_entities = _derive_entities_from_filters(filters, query)

    suggestions = _sanitize_suggestions(interpretation.get("suggestions"))
    if not suggestions:
        suggestions = _sanitize_suggestions(parsed.get("suggestions"))
    if not suggestions:
        suggestions = _sanitize_suggestions(fallback_suggestions)

    return {
        "summary": summary,
        "parsed_entities": parsed_entities,
        "suggestions": suggestions,
    }


def validate_filters(parsed: Dict[str, Any], query: str = "") -> Dict[str, Any]:
    """Validate and sanitize LLM output, stripping invalid values."""
    filters = parsed.get("filters", {})
    validated = {}

    query_mode = parsed.get("query_mode") or filters.get("query_mode")
    if isinstance(query_mode, str) and query_mode in VALID_QUERY_MODE:
        validated["query_mode"] = query_mode

    # String list filters (pass through - player/team names can't be validated without DB)
    for key in ["batters", "bowlers", "players", "batting_teams", "bowling_teams", "teams"]:
        if key in filters and isinstance(filters[key], list) and len(filters[key]) > 0:
            validated[key] = filters[key]
    if "venue" in filters and isinstance(filters["venue"], str) and filters["venue"].strip():
        validated["venue"] = VENUE_STANDARDIZATION.get(filters["venue"].strip(), filters["venue"].strip())

    # Validated enum filters
    # Track if bat_hand should become a group_by (when LLM returns a list like ["RHB", "LHB"])
    _bat_hand_to_group_by = False
    if "bat_hand" in filters:
        val = filters["bat_hand"]
        if isinstance(val, str) and val in VALID_BAT_HAND:
            validated["bat_hand"] = val
        elif isinstance(val, list):
            # Multiple values means "compare by bat_hand" — use group_by, not filter
            _bat_hand_to_group_by = True

    if "bowl_style" in filters and isinstance(filters["bowl_style"], list):
        valid = [v for v in filters["bowl_style"] if v in VALID_BOWL_STYLE]
        if valid:
            validated["bowl_style"] = valid

    if "bowl_kind" in filters and isinstance(filters["bowl_kind"], list):
        valid = [v for v in filters["bowl_kind"] if v in VALID_BOWL_KIND]
        if valid:
            validated["bowl_kind"] = valid

    if "leagues" in filters and isinstance(filters["leagues"], list):
        valid = [v for v in filters["leagues"] if v in VALID_LEAGUES]
        if valid:
            validated["leagues"] = valid

    # Boolean filters
    if "include_international" in filters:
        validated["include_international"] = bool(filters["include_international"])

    # Integer range filters
    if "over_min" in filters and filters["over_min"] is not None:
        validated["over_min"] = max(0, min(19, int(filters["over_min"])))
    if "over_max" in filters and filters["over_max"] is not None:
        validated["over_max"] = max(0, min(19, int(filters["over_max"])))

    if "innings" in filters:
        val = filters["innings"]
        if isinstance(val, int) and val in (1, 2):
            validated["innings"] = val
        elif isinstance(val, list) and len(val) == 1 and val[0] in (1, 2):
            validated["innings"] = val[0]

    if "is_chase" in filters:
        validated["is_chase"] = bool(filters["is_chase"])

    if "match_outcome" in filters and isinstance(filters["match_outcome"], list):
        valid = [str(v).lower() for v in filters["match_outcome"] if str(v).lower() in VALID_MATCH_OUTCOME]
        if valid:
            validated["match_outcome"] = valid

    if "chase_outcome" in filters and isinstance(filters["chase_outcome"], list):
        valid = [str(v).lower() for v in filters["chase_outcome"] if str(v).lower() in VALID_MATCH_OUTCOME]
        if valid:
            validated["chase_outcome"] = valid

    if "toss_decision" in filters and isinstance(filters["toss_decision"], list):
        valid = [str(v).lower() for v in filters["toss_decision"] if str(v).lower() in VALID_TOSS_DECISION]
        if valid:
            validated["toss_decision"] = valid

    if "control" in filters:
        val = filters["control"]
        if isinstance(val, int) and val in (0, 1):
            validated["control"] = val
        elif isinstance(val, list) and len(val) == 1 and val[0] in (0, 1):
            validated["control"] = val[0]

    # List filters for delivery details
    for key in ["line", "length", "shot", "dismissal"]:
        if key in filters and isinstance(filters[key], list) and len(filters[key]) > 0:
            validated[key] = filters[key]

    if "wagon_zone" in filters and isinstance(filters["wagon_zone"], list):
        valid = [v for v in filters["wagon_zone"] if isinstance(v, int) and 0 <= v <= 8]
        if valid:
            validated["wagon_zone"] = valid

    # Result filters
    if "min_balls" in filters and filters["min_balls"] is not None:
        validated["min_balls"] = max(1, int(filters["min_balls"]))
    if "min_runs" in filters and filters["min_runs"] is not None:
        validated["min_runs"] = max(0, int(filters["min_runs"]))
    if "max_runs" in filters and filters["max_runs"] is not None:
        validated["max_runs"] = max(0, int(filters["max_runs"]))
    if "min_wickets" in filters and filters["min_wickets"] is not None:
        validated["min_wickets"] = max(0, int(filters["min_wickets"]))
    if "max_wickets" in filters and filters["max_wickets"] is not None:
        validated["max_wickets"] = max(0, int(filters["max_wickets"]))

    # Date filters
    for key in ["start_date", "end_date"]:
        if key in filters and filters[key]:
            validated[key] = str(filters[key])

    # Validate group_by
    group_by = parsed.get("group_by", [])
    if isinstance(group_by, list):
        group_by = [col for col in group_by if col in VALID_GROUP_BY]
    else:
        group_by = []

    # If bat_hand was a list (e.g. "vs lhb/rhb"), add it to group_by
    if _bat_hand_to_group_by and "bat_hand" not in group_by:
        group_by.append("bat_hand")

    explanation = str(parsed.get("explanation") or "").strip()
    confidence = _sanitize_confidence(parsed.get("confidence"), default="medium")
    suggestions = _sanitize_suggestions(parsed.get("suggestions"))
    recommended_columns = _resolve_recommended_columns(
        raw_columns=parsed.get("recommended_columns"),
        query=query,
        filters=validated,
    )
    recommended_chart = _sanitize_recommended_chart(
        raw_chart=parsed.get("recommended_chart"),
        query=query,
        filters=validated,
        group_by=group_by,
        recommended_columns=recommended_columns,
    )
    interpretation = _sanitize_interpretation(
        parsed=parsed,
        query=query,
        filters=validated,
        fallback_summary=explanation,
        fallback_suggestions=suggestions,
    )

    if interpretation.get("summary"):
        explanation = interpretation["summary"]
    suggestions = interpretation.get("suggestions", suggestions)

    return {
        "filters": validated,
        "group_by": group_by,
        "explanation": explanation,
        "confidence": confidence,
        "suggestions": suggestions,
        "recommended_columns": recommended_columns,
        "recommended_chart": recommended_chart,
        "interpretation": interpretation,
    }


def _post_process_result(query: str, result: Dict[str, Any]) -> Dict[str, Any]:
    filters = result.get("filters", {}) or {}
    group_by = result.get("group_by", []) or []
    q_lower = (query or "").lower()

    # Milestone batting rules, e.g. "virat kohli 100+ scores".
    runs_plus_match = re.search(r"\b(\d+)\s*\+\s*(?:score|scores|run|runs)\b", q_lower)
    if runs_plus_match:
        filters["query_mode"] = "batting_stats"
        filters["min_runs"] = max(0, int(runs_plus_match.group(1)))
        group_by = _append_group_by(group_by, "match_id")

    # Bowling milestone rules, including wicketless asks.
    wickets_plus_match = re.search(r"\b(\d+)\s*\+\s*wickets?\b", q_lower)
    if wickets_plus_match:
        filters["query_mode"] = "bowling_stats"
        filters["min_wickets"] = max(0, int(wickets_plus_match.group(1)))
        group_by = _append_group_by(group_by, "match_id")

    if re.search(r"\b(wicketless|0\s*wickets?|without\s+a\s+wicket)\b", q_lower):
        filters["query_mode"] = "bowling_stats"
        filters["max_wickets"] = 0
        group_by = _append_group_by(group_by, "match_id")

    # Venue inference and canonicalization.
    inferred_venue = _infer_venue_from_query(query)
    if inferred_venue:
        filters["venue"] = VENUE_STANDARDIZATION.get(inferred_venue, inferred_venue)
        explicit_venue_grouping = bool(
            ("grouped by" in q_lower and "venue" in q_lower)
            or ("group by" in q_lower and "venue" in q_lower)
            or
            re.search(r"\b(group(?:ed)?\s+by|by)\s+venue\b", q_lower)
            or re.search(r"\bvenue[-\s]?wise\b", q_lower)
        )
        if not explicit_venue_grouping:
            group_by = [col for col in group_by if col != "venue"]

    # Toss analysis: replace match_outcome with toss_match_outcome when toss context detected.
    if "toss" in q_lower and "match_outcome" in group_by:
        group_by = [("toss_match_outcome" if c == "match_outcome" else c) for c in group_by]
        if filters.get("query_mode") == "delivery":
            filters["query_mode"] = "batting_stats"

    # Since-date normalization: keep start_date, drop end_date unless explicitly bounded.
    if "since" in q_lower and not _contains_explicit_end_bound(query):
        since_date_match = re.search(r"\bsince\s+(\d{4}-\d{2}-\d{2})\b", q_lower)
        since_year_match = re.search(r"\bsince\s+(20\d{2})\b", q_lower)
        if since_date_match:
            filters["start_date"] = since_date_match.group(1)
        elif since_year_match:
            filters["start_date"] = f"{since_year_match.group(1)}-01-01"
        filters.pop("end_date", None)

    # Prefer delivery mode when group_by contains delivery-only columns
    # or when delivery-only filters are present in filters.
    DELIVERY_ONLY_GROUP_BY = {"bat_hand", "bowl_style", "bowl_kind", "line", "length", "shot", "control", "wagon_zone", "phase", "dismissal"}
    DELIVERY_ONLY_FILTERS = {"bat_hand", "bowl_style", "bowl_kind", "line", "length", "shot", "control", "wagon_zone", "dismissal"}

    def _has_filter_value(value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return value.strip() != ""
        if isinstance(value, (list, tuple, set, dict)):
            return len(value) > 0
        return True

    if filters.get("query_mode") in ("batting_stats", "bowling_stats"):
        if any(c in DELIVERY_ONLY_GROUP_BY for c in group_by):
            filters["query_mode"] = "delivery"
        elif any(
            key in DELIVERY_ONLY_FILTERS and _has_filter_value(value)
            for key, value in filters.items()
        ):
            filters["query_mode"] = "delivery"

    # Chase/win team queries: add match-level grouping and ensure filters
    chase_match = re.search(r"\bchas(e|ing)\b", q_lower)
    win_loss_match = re.search(r"\b(wins?|won|loss(?:es)?|lost)\b", q_lower)
    if chase_match and win_loss_match:
        if not filters.get("is_chase"):
            filters["is_chase"] = True
        # Set match_outcome if not already set
        if not filters.get("match_outcome"):
            wl = win_loss_match.group(1)
            if wl in ("win", "wins", "won"):
                filters["match_outcome"] = ["win"]
            elif wl in ("loss", "losses", "lost"):
                filters["match_outcome"] = ["loss"]
        if filters.get("batting_teams") or filters.get("teams"):
            group_by = _append_group_by(group_by, "match_id")
            group_by = _append_group_by(group_by, "batting_team")
            group_by = _append_group_by(group_by, "bowling_team")

    # Keep query_mode default if absent.
    filters["query_mode"] = filters.get("query_mode", "delivery")

    # Guardrail for wicket filters.
    if filters.get("query_mode") != "bowling_stats":
        filters.pop("min_wickets", None)
        filters.pop("max_wickets", None)

    summary = _build_explanation(filters, group_by)
    interpretation = result.get("interpretation") if isinstance(result.get("interpretation"), dict) else {}
    if not interpretation:
        interpretation = _sanitize_interpretation(
            parsed={},
            query=query,
            filters=filters,
            fallback_summary=summary,
            fallback_suggestions=_sanitize_suggestions(result.get("suggestions")),
        )
    interpretation["summary"] = summary
    if not isinstance(interpretation.get("parsed_entities"), list) or not interpretation.get("parsed_entities"):
        interpretation["parsed_entities"] = _derive_entities_from_filters(filters, query)
    interpretation["suggestions"] = _sanitize_suggestions(
        interpretation.get("suggestions") or result.get("suggestions")
    )
    recommended_columns = _resolve_recommended_columns(
        raw_columns=result.get("recommended_columns"),
        query=query,
        filters=filters,
    )
    recommended_chart = _sanitize_recommended_chart(
        raw_chart=result.get("recommended_chart"),
        query=query,
        filters=filters,
        group_by=group_by,
        recommended_columns=recommended_columns,
    )

    result["filters"] = filters
    result["group_by"] = group_by
    result["explanation"] = summary
    result["suggestions"] = interpretation["suggestions"]
    result["recommended_columns"] = recommended_columns
    result["recommended_chart"] = recommended_chart
    result["interpretation"] = interpretation
    return result


def resolve_player_names(names: List[str], db: Session) -> List[str]:
    """Resolve LLM-generated player names against the database.

    Uses search_players_with_aliases for fuzzy matching, returning the
    display_name (delivery_details format) for each matched player.
    Falls back to the original name if no match is found.
    """
    from services.player_aliases import search_players_with_aliases

    resolved = []
    for name in names:
        try:
            results = search_players_with_aliases(name, db, limit=1)
            if results:
                resolved.append(results[0]["display_name"])
            else:
                resolved.append(name)
        except Exception as e:
            logger.warning(f"Failed to resolve player name '{name}': {e}")
            resolved.append(name)
    return resolved


def _hash_ip(ip_address: Optional[str]) -> Optional[str]:
    if not ip_address:
        return None
    salt = os.getenv("NL_QUERY_IP_SALT", "")
    return hashlib.sha256(f"{salt}:{ip_address}".encode("utf-8")).hexdigest()


def persist_nl_query_log(
    query_text: str,
    parse_result: Dict[str, Any],
    ip_address: Optional[str],
    execution_time_ms: Optional[int],
    model_used: str = DEFAULT_NL2QUERY_MODEL,
    db: Optional[Session] = None,
) -> Optional[int]:
    """Persist one NL query parse log row. Never raises to caller."""
    owns_session = db is None
    session = db
    if session is None:
        try:
            from database import SessionLocal  # local import to avoid tight startup coupling
            session = SessionLocal()
        except Exception as exc:
            logger.warning("Unable to open DB session for NL query logging: %s", exc)
            return None

    filters = parse_result.get("filters") if isinstance(parse_result.get("filters"), dict) else {}
    group_by = parse_result.get("group_by") if isinstance(parse_result.get("group_by"), list) else []
    # Serialize JSON fields explicitly for raw text(...) SQL + psycopg2 compatibility.
    parsed_filters_json = json.dumps(filters, ensure_ascii=True)
    group_by_json = json.dumps(group_by, ensure_ascii=True)
    query_mode = parse_result.get("query_mode") or filters.get("query_mode")
    query_mode = str(query_mode).strip() if query_mode is not None else None
    if not query_mode:
        query_mode = None
    confidence = parse_result.get("confidence")
    confidence = str(confidence) if confidence is not None else None
    explanation = parse_result.get("explanation")
    explanation = str(explanation) if explanation is not None else None
    success = bool(parse_result.get("success"))
    row_count = parse_result.get("result_row_count")
    row_count = int(row_count) if isinstance(row_count, int) else None

    # Token usage from _meta
    api_meta = parse_result.get("_meta") or {}
    actual_model = api_meta.get("model_used") or model_used
    prompt_tokens = api_meta.get("prompt_tokens")
    prompt_tokens = int(prompt_tokens) if prompt_tokens is not None else None
    completion_tokens = api_meta.get("completion_tokens")
    completion_tokens = int(completion_tokens) if completion_tokens is not None else None
    estimated_cost = api_meta.get("estimated_cost_usd")
    estimated_cost = float(estimated_cost) if estimated_cost is not None else None

    try:
        insert_result = session.execute(
            text(
                """
                INSERT INTO nl_query_log (
                    query_text,
                    parsed_filters,
                    query_mode,
                    group_by,
                    explanation,
                    confidence,
                    model_used,
                    execution_success,
                    result_row_count,
                    ip_hash,
                    execution_time_ms,
                    prompt_tokens,
                    completion_tokens,
                    estimated_cost_usd
                )
                VALUES (
                    :query_text,
                    CAST(:parsed_filters AS JSONB),
                    :query_mode,
                    CAST(:group_by AS JSONB),
                    :explanation,
                    :confidence,
                    :model_used,
                    :execution_success,
                    :result_row_count,
                    :ip_hash,
                    :execution_time_ms,
                    :prompt_tokens,
                    :completion_tokens,
                    :estimated_cost_usd
                )
                RETURNING id
                """
            ),
            {
                "query_text": query_text.strip(),
                "parsed_filters": parsed_filters_json,
                "query_mode": query_mode,
                "group_by": group_by_json,
                "explanation": explanation,
                "confidence": confidence,
                "model_used": actual_model,
                "execution_success": success,
                "result_row_count": row_count,
                "ip_hash": _hash_ip(ip_address),
                "execution_time_ms": int(execution_time_ms) if execution_time_ms is not None else None,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "estimated_cost_usd": estimated_cost,
            },
        )
        new_row = insert_result.fetchone()
        session.commit()
        if new_row is None:
            return None
        return int(new_row[0])
    except Exception as exc:
        logger.warning("Skipping nl_query_log insert due to write error: %s", exc)
        try:
            session.rollback()
        except Exception:
            pass
        return None
    finally:
        if owns_session and session is not None:
            try:
                session.close()
            except Exception:
                pass


def log_nl_query_event_background(
    query_text: str,
    parse_result: Dict[str, Any],
    ip_address: Optional[str],
    execution_time_ms: Optional[int],
) -> None:
    """Background task wrapper for non-blocking query logging."""
    persist_nl_query_log(
        query_text=query_text,
        parse_result=parse_result,
        ip_address=ip_address,
        execution_time_ms=execution_time_ms,
        model_used=DEFAULT_NL2QUERY_MODEL,
        db=None,
    )


def update_nl_query_feedback(
    query_text: str,
    feedback: str,
    ip_address: Optional[str],
    db: Session,
    refined_query_text: Optional[str] = None,
    execution_success: Optional[bool] = None,
    result_row_count: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """Update feedback fields on the latest matching log row."""
    normalized_query = (query_text or "").strip()
    if not normalized_query:
        return None

    feedback_value = (feedback or "").strip().lower()
    if feedback_value not in {"good", "bad", "refined"}:
        return None

    ip_hash = _hash_ip(ip_address)
    target_row = None

    try:
        if ip_hash:
            target_row = db.execute(
                text(
                    """
                    SELECT id
                    FROM nl_query_log
                    WHERE query_text = :query_text
                      AND ip_hash = :ip_hash
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                ),
                {"query_text": normalized_query, "ip_hash": ip_hash},
            ).fetchone()

        if target_row is None:
            target_row = db.execute(
                text(
                    """
                    SELECT id
                    FROM nl_query_log
                    WHERE query_text = :query_text
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                ),
                {"query_text": normalized_query},
            ).fetchone()

        if target_row is None:
            return None

        query_log_id = int(target_row[0])
        db.execute(
            text(
                """
                UPDATE nl_query_log
                SET
                    user_feedback = :user_feedback,
                    refined_query_text = COALESCE(:refined_query_text, refined_query_text),
                    execution_success = COALESCE(:execution_success, execution_success),
                    result_row_count = COALESCE(:result_row_count, result_row_count)
                WHERE id = :id
                """
            ),
            {
                "id": query_log_id,
                "user_feedback": feedback_value,
                "refined_query_text": refined_query_text.strip() if refined_query_text else None,
                "execution_success": execution_success,
                "result_row_count": int(result_row_count) if isinstance(result_row_count, int) else None,
            },
        )
        db.commit()

        return {
            "query_log_id": query_log_id,
            "feedback": feedback_value,
        }
    except Exception as exc:
        logger.debug("Failed to update nl_query_log feedback: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass
        return None


def parse_nl_query(query: str, db: Optional[Session] = None) -> Dict[str, Any]:
    """Parse a natural language query into structured filters.

    Returns validated filters, group_by, explanation, confidence, suggestions,
    recommended columns, recommended chart, and a structured interpretation payload.
    """
    if not query or not query.strip():
        return {
            "success": False,
            "error": "Empty query",
            "filters": {},
            "group_by": [],
            "explanation": "",
            "confidence": "low",
            "suggestions": ["Try a query like 'Kohli vs spin in death overs'"],
            "recommended_columns": [],
            "recommended_chart": None,
            "interpretation": {
                "summary": "",
                "parsed_entities": [],
                "suggestions": ["Try a query like 'Kohli vs spin in death overs'"],
            },
        }

    # Check cache
    cached = _get_cached(query)
    if cached:
        return cached

    try:
        few_shot_examples: List[Dict[str, Any]] = []
        if db is not None:
            few_shot_examples = get_few_shot_examples(query, db=db, limit=MAX_FEW_SHOT_EXAMPLES)

        # Select model based on monthly spend
        chosen_model = select_model(db)

        try:
            raw = call_openai(
                query,
                few_shot_examples=few_shot_examples,
                model=chosen_model,
            )
        except TypeError:
            # Backward-compatible fallback for tests that monkeypatch call_openai(query).
            raw = call_openai(query)

        # Extract and preserve _meta from OpenAI response before validation strips it
        api_meta = raw.pop("_meta", None) or {}

        result = validate_filters(raw, query=query)

        # Attach _meta for logging downstream
        result["_meta"] = api_meta

        # Resolve player names against DB if session available
        if db is not None:
            filters = result["filters"]
            for key in ["batters", "bowlers", "players"]:
                if key in filters and isinstance(filters[key], list):
                    filters[key] = resolve_player_names(filters[key], db)

        result = _post_process_result(query, result)
        result["success"] = True

        _set_cache(query, result)
        return result

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response: {e}")
        return {
            "success": False,
            "error": "Failed to parse LLM response",
            "filters": {},
            "group_by": [],
            "explanation": "",
            "confidence": "low",
            "suggestions": ["Try rephrasing your query"],
            "recommended_columns": [],
            "recommended_chart": None,
            "interpretation": {
                "summary": "",
                "parsed_entities": [],
                "suggestions": ["Try rephrasing your query"],
            },
        }
    except Exception as e:
        logger.error(f"NL query parsing error: {e}")
        return {
            "success": False,
            "error": str(e),
            "filters": {},
            "group_by": [],
            "explanation": "",
            "confidence": "low",
            "suggestions": ["Try rephrasing your query"],
            "recommended_columns": [],
            "recommended_chart": None,
            "interpretation": {
                "summary": "",
                "parsed_entities": [],
                "suggestions": ["Try rephrasing your query"],
            },
        }


def get_example_queries() -> List[Dict[str, str]]:
    """Return example queries for the UI."""
    return EXAMPLE_QUERIES
